import os
from collections import Counter

import fitz  # PyMuPDF
import difflib

# Page alignment tuning.
# SIMILARITY_THRESHOLD answers "are these the same page?" (equal vs replace).
SIMILARITY_THRESHOLD = 0.6
# How many pages ahead to look for a displaced counterpart.
LOOKAHEAD_WINDOW = 3
# Detecting a displaced page is a *relative* question: the candidate only has to
# fit better than the current pairing. Requiring SIMILARITY_THRESHOLD here made
# insertions undetectable whenever the displaced page had also been edited, so
# its similarity never reached the absolute bar.
SHIFT_MIN_SIMILARITY = 0.2   # below this a candidate is noise, not a match
SHIFT_MARGIN = 2.0           # ... and it must fit this much better than the current pairing

# Layout of the generated report, in PDF points.
MARGIN = 20
GAP = 10
# Vertical space reserved above each page for its label. The label box itself is
# shorter: the difference is the breathing room between label and page content.
LABEL_AREA_HEIGHT = 40
LABEL_BOX_HEIGHT = 30


class PDFComparator:
    def __init__(self, file_path_a, file_path_b, dpi=None, jpeg_quality=None):
        self.file_path_a = file_path_a
        self.file_path_b = file_path_b
        # DPI and jpeg_quality parameters kept for backward compatibility but not used in vector rendering
        self.dpi = dpi
        self.jpeg_quality = jpeg_quality
        # Set by compare_visuals(): True when either document has no usable text
        # layer (e.g. a scan), which makes the comparison unreliable.
        self.missing_text_layer = False

    def extract_text(self, file_path):
        """Extract text from all pages of a PDF."""
        text_content = []
        with fitz.open(file_path) as doc:
            for page in doc:
                text = page.get_text()
                text_content.append(text if text else "")
        return text_content

    @staticmethod
    def _is_displaced(candidate, current, best):
        """Decide whether a page further ahead is the real counterpart.

        A page that was both moved and edited never reaches the absolute
        "same page" bar against its counterpart, so what matters is that it
        fits clearly better than the pairing at the current position: it must
        beat the best candidate so far, stay above the noise floor, and either
        be an outright match or fit SHIFT_MARGIN times better than the current
        pairing.
        """
        if candidate <= best or candidate < SHIFT_MIN_SIMILARITY:
            return False

        return candidate > SIMILARITY_THRESHOLD or candidate >= current * SHIFT_MARGIN

    def align_pages(self, text_a, text_b):
        """
        Aligns pages based on their text content similarity.
        Returns a list of tuples (tag, i1, i2, j1, j2) describing alignment.
        """
        len_a = len(text_a)
        len_b = len(text_b)

        alignments = []
        i, j = 0, 0

        while i < len_a or j < len_b:
            if i >= len_a:
                alignments.append(('insert', i, i, j, len_b))
                break
            elif j >= len_b:
                alignments.append(('delete', i, len_a, j, j))
                break
            else:
                current_similarity = difflib.SequenceMatcher(None, text_a[i], text_b[j]).ratio()
                best_match = {'type': 'equal', 'i': i, 'j': j, 'similarity': current_similarity}

                # Look ahead for better alignment. The upper bound is exclusive,
                # so it needs +1 to actually explore LOOKAHEAD_WINDOW positions.
                for skip_j in range(1, min(LOOKAHEAD_WINDOW + 1, len_b - j)):
                    similarity = difflib.SequenceMatcher(None, text_a[i], text_b[j + skip_j]).ratio()
                    if self._is_displaced(similarity, current_similarity, best_match['similarity']):
                        best_match = {'type': 'insert', 'i': i, 'j': j + skip_j, 'similarity': similarity, 'skip': skip_j}

                for skip_i in range(1, min(LOOKAHEAD_WINDOW + 1, len_a - i)):
                    similarity = difflib.SequenceMatcher(None, text_a[i + skip_i], text_b[j]).ratio()
                    if self._is_displaced(similarity, current_similarity, best_match['similarity']):
                        best_match = {'type': 'delete', 'i': i + skip_i, 'j': j, 'similarity': similarity, 'skip': skip_i}

                if best_match['type'] == 'insert':
                    alignments.append(('insert', i, i, j, best_match['j']))
                    j = best_match['j']
                elif best_match['type'] == 'delete':
                    alignments.append(('delete', i, best_match['i'], j, j))
                    i = best_match['i']
                elif current_similarity > SIMILARITY_THRESHOLD:
                    alignments.append(('equal', i, i + 1, j, j + 1))
                    i += 1
                    j += 1
                else:
                    alignments.append(('replace', i, i + 1, j, j + 1))
                    i += 1
                    j += 1

        return alignments

    def extract_words_with_bbox(self, page):
        """Extract words with their bounding boxes from a page.

        Word coordinates come in the page's unrotated space, while page.rect and
        show_pdf_page work in the rotated (displayed) one. Applying the page's
        rotation matrix here keeps every caller in the displayed space.
        """
        words = page.get_text("words")  # Returns list of (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        rotation = page.rotation_matrix
        return [{'text': w[4], 'bbox': fitz.Rect(w[:4]) * rotation} for w in words]

    @staticmethod
    def _has_text_layer(pages_text):
        """True if at least one page yields non-blank text."""
        return any(text.strip() for text in pages_text)

    @staticmethod
    def _iter_page_events(opcodes):
        """Walk the alignment and yield one event per output page.

        This is the single place that turns alignment opcodes into "what
        happened to this page", so every consumer -- the PDF report, the JSON
        report, anything added later -- sees exactly the same comparison.

        Yields ('compared', idx_a, idx_b), ('added', None, idx_b) or
        ('removed', idx_a, None).
        """
        for tag, i1, i2, j1, j2 in opcodes:
            if tag in ('equal', 'replace'):
                for k in range(max(i2 - i1, j2 - j1)):
                    idx_a = i1 + k if i1 + k < i2 else None
                    idx_b = j1 + k if j1 + k < j2 else None

                    if idx_a is not None and idx_b is not None:
                        yield 'compared', idx_a, idx_b
                    elif idx_b is not None:
                        yield 'added', None, idx_b
                    else:
                        yield 'removed', idx_a, None

            elif tag == 'delete':
                for k in range(i1, i2):
                    yield 'removed', k, None

            elif tag == 'insert':
                for k in range(j1, j2):
                    yield 'added', None, k

    @staticmethod
    def _word_texts(page):
        """The words of a page, without building a box for each one."""
        return [word[4] for word in page.get_text("words")]

    @staticmethod
    def _word_opcodes(texts_a, texts_b):
        """The word-level diff.

        The only implementation, so the PDF report and the JSON report cannot
        disagree about what changed on a page.
        """
        return difflib.SequenceMatcher(None, texts_a, texts_b).get_opcodes()

    @staticmethod
    def _changed_words(word_opcodes):
        """Yield ('removed', index) or ('added', index) per changed word.

        Keeps the knowledge that a replacement counts on both sides in one
        place, instead of in every consumer of the diff.
        """
        for tag, ii1, ii2, jj1, jj2 in word_opcodes:
            if tag in ('replace', 'delete'):
                for index in range(ii1, ii2):
                    yield 'removed', index
            if tag in ('replace', 'insert'):
                for index in range(jj1, jj2):
                    yield 'added', index

    def _page_alignment(self):
        """Align both documents, flagging a missing text layer on the way."""
        text_a = self.extract_text(self.file_path_a)
        text_b = self.extract_text(self.file_path_b)

        self.missing_text_layer = not (
            self._has_text_layer(text_a) and self._has_text_layer(text_b)
        )

        return self.align_pages(text_a, text_b)

    def compare(self, build_pdf=False):
        """Run the comparison once, in a single pass over both documents.

        Returns (summary, pdf_bytes). The summary is always produced; pdf_bytes
        is None unless build_pdf is set and something actually differs. Callers
        that need both -- batch runs writing a diff and a report -- get them
        without aligning and diffing the documents twice.
        """
        opcodes = self._page_alignment()

        pages_added = pages_removed = pages_modified = 0
        words_added = words_removed = 0

        with fitz.open(self.file_path_a) as doc_a, \
                fitz.open(self.file_path_b) as doc_b, \
                fitz.open() as output_doc:

            for event, idx_a, idx_b in self._iter_page_events(opcodes):
                if event == 'added':
                    pages_added += 1
                    words_added += len(self._word_texts(doc_b[idx_b]))
                    if build_pdf:
                        self._add_single_page(output_doc, doc_b, idx_b, 'right', 'Added')

                elif event == 'removed':
                    pages_removed += 1
                    words_removed += len(self._word_texts(doc_a[idx_a]))
                    if build_pdf:
                        self._add_single_page(output_doc, doc_a, idx_a, 'left', 'Missing')

                else:
                    changed = self._compare_pages(output_doc, doc_a, doc_b, idx_a, idx_b, build_pdf)
                    if changed:
                        pages_modified += 1
                        words_added += changed['added']
                        words_removed += changed['removed']

            summary = self._summarise(
                doc_a.page_count, doc_b.page_count,
                pages_added, pages_removed, pages_modified, words_added, words_removed,
            )

            if not build_pdf or summary['identical'] and not self.missing_text_layer:
                return summary, None

            return summary, output_doc.tobytes()

    def _compare_pages(self, output_doc, doc_a, doc_b, idx_a, idx_b, build_pdf):
        """Count the words that changed between two pages, drawing them if asked."""
        if build_pdf:
            return self._add_comparison_page(output_doc, doc_a, doc_b, idx_a, idx_b)

        word_opcodes = self._word_opcodes(
            self._word_texts(doc_a[idx_a]), self._word_texts(doc_b[idx_b])
        )
        return Counter(side for side, _ in self._changed_words(word_opcodes))

    def _summarise(self, page_count_a, page_count_b,
                   pages_added, pages_removed, pages_modified, words_added, words_removed):
        """Shape the result as plain data."""
        return {
            'files': {
                'original': {'name': os.path.basename(self.file_path_a),
                             'path': os.path.abspath(self.file_path_a),
                             'pages': page_count_a},
                'modified': {'name': os.path.basename(self.file_path_b),
                             'path': os.path.abspath(self.file_path_b),
                             'pages': page_count_b},
            },
            # False here is only trustworthy when missing_text_layer is False:
            # a scan yields no extractable text, so it looks unchanged.
            'identical': not (pages_added or pages_removed or pages_modified),
            'missing_text_layer': self.missing_text_layer,
            'changes': {
                'pages_added': pages_added,
                'pages_removed': pages_removed,
                'pages_modified': pages_modified,
                'words_added': words_added,
                'words_removed': words_removed,
            },
        }

    def compare_visuals(self):
        """
        Create a vector-based PDF comparison report.
        Returns the output PDF as bytes, or None when both documents are equal.

        When either document has no usable text layer the differences cannot be
        determined, so the report is returned anyway and self.missing_text_layer
        is set: reporting "no differences" would be a claim we cannot make.
        """
        return self.compare(build_pdf=True)[1]

    def analyze(self):
        """Compare both documents and return the result as plain data.

        Runs the same alignment and the same word-level diff as
        compare_visuals(), but composes no PDF. Intended for automation: report
        which files were compared and how much changed, without producing a
        document to read. Note this is not meaningfully faster -- composing the
        report references the source pages as vector objects rather than
        rendering them, so it costs almost nothing; the saving is the file.

        Counts are reported rather than a similarity percentage on purpose: a
        percentage needs a denominator nobody can agree on (words of the
        original? of both? how much is a whole added page worth?), while counts
        are facts the caller can turn into whatever ratio they need.
        """
        return self.compare()[0]

    def _add_comparison_page(self, output_doc, doc_a, doc_b, idx_a, idx_b):
        """Add a side-by-side comparison page to the output PDF.

        Returns a Counter of the words highlighted on each side, empty when the
        pages match, so the caller can both draw and count in one pass.
        """
        page_a = doc_a[idx_a]
        page_b = doc_b[idx_b]

        # Get page dimensions
        rect_a = page_a.rect
        rect_b = page_b.rect

        # Calculate output page size (side by side with margins)
        margin = MARGIN
        gap = GAP
        label_height = LABEL_AREA_HEIGHT

        width = rect_a.width + rect_b.width + gap + 2 * margin
        height = max(rect_a.height, rect_b.height) + 2 * margin + label_height

        # Create new page
        new_page = output_doc.new_page(width=width, height=height)

        # Add labels
        self._add_label(new_page, f"Original - Page {idx_a + 1}", margin, margin, rect_a.width)
        self._add_label(new_page, f"Modified - Page {idx_b + 1}", margin + rect_a.width + gap, margin, rect_b.width)

        # Copy page content (shows vector content)
        # Left page (A)
        new_page.show_pdf_page(
            fitz.Rect(margin, margin + label_height, margin + rect_a.width, margin + label_height + rect_a.height),
            doc_a,
            idx_a
        )

        # Right page (B)
        new_page.show_pdf_page(
            fitz.Rect(margin + rect_a.width + gap, margin + label_height,
                     margin + rect_a.width + gap + rect_b.width, margin + label_height + rect_b.height),
            doc_b,
            idx_b
        )

        has_changes = self._highlight_differences(
            new_page, page_a, page_b,
            left_x=margin,
            right_x=margin + rect_a.width + gap,
            top_y=margin + label_height,
        )

        # Add visual indicator if pages are shifted
        if idx_a != idx_b:
            # Draw a yellow border to indicate page shift
            new_page.draw_rect(fitz.Rect(5, 5, width - 5, height - 5), color=(1, 1, 0), width=3)
            self._add_text(new_page, "(Page Shifted)", width / 2 - 50, height - 15, fontsize=10, color=(0.8, 0.6, 0))

        return has_changes

    def _highlight_differences(self, new_page, page_a, page_b, left_x, right_x, top_y):
        """Draw a box over every word that changed between the two pages.

        Returns a Counter of how many words were highlighted per side.
        Deletions go in red over the original and insertions in green over the
        modified one; only the source panel, offset and colour differ.
        """
        words_a = self.extract_words_with_bbox(page_a)
        words_b = self.extract_words_with_bbox(page_b)

        # The same word-level diff the JSON report counts
        word_opcodes = self._word_opcodes(
            [word['text'] for word in words_a], [word['text'] for word in words_b]
        )

        panels = {
            'removed': (words_a, left_x, (1, 0, 0), (1, 0.7, 0.7)),
            'added': (words_b, right_x, (0, 1, 0), (0.7, 1, 0.7)),
        }

        highlighted = Counter()
        for side, index in self._changed_words(word_opcodes):
            highlighted[side] += 1
            words, x_offset, colour, fill = panels[side]
            bbox = words[index]['bbox']

            new_page.draw_rect(
                fitz.Rect(bbox.x0 + x_offset, bbox.y0 + top_y,
                          bbox.x1 + x_offset, bbox.y1 + top_y),
                color=colour, fill=fill, fill_opacity=0.3,
            )

        return highlighted

    def _add_single_page(self, output_doc, source_doc, page_idx, position, label_type):
        """Add a single page (for insertions/deletions) with a blank space on the other side."""
        page = source_doc[page_idx]
        rect = page.rect

        margin = MARGIN
        gap = GAP
        label_height = LABEL_AREA_HEIGHT

        # Create page with space for both sides
        width = rect.width * 2 + gap + 2 * margin
        height = rect.height + 2 * margin + label_height

        new_page = output_doc.new_page(width=width, height=height)

        # Determine positions
        if position == 'left':
            # Page on left, blank on right
            page_x = margin
            label_x = margin
            blank_label_x = margin + rect.width + gap
            bg_color = (1, 0.8, 0.8)  # Light red for missing
            label_text = f"Missing - Page {page_idx + 1}"
            blank_label_text = "No Corresponding Page"
        else:
            # Blank on left, page on right
            page_x = margin + rect.width + gap
            label_x = margin + rect.width + gap
            blank_label_x = margin
            bg_color = (0.8, 1, 0.8)  # Light green for added
            label_text = f"Added - Page {page_idx + 1}"
            blank_label_text = "No Corresponding Page"

        # Add labels
        self._add_label(new_page, blank_label_text, blank_label_x, margin, rect.width)
        self._add_label(new_page, label_text, label_x, margin, rect.width, bg_color=bg_color)

        # Show the page
        new_page.show_pdf_page(
            fitz.Rect(page_x, margin + label_height, page_x + rect.width, margin + label_height + rect.height),
            source_doc,
            page_idx
        )

        # Draw blank area background
        blank_x = margin if position == 'right' else margin + rect.width + gap
        new_page.draw_rect(
            fitz.Rect(blank_x, margin + label_height, blank_x + rect.width, margin + label_height + rect.height),
            color=(0.9, 0.9, 0.9),
            fill=(0.98, 0.98, 0.98)
        )

    def _add_label(self, page, text, x, y, width, bg_color=(1, 1, 1)):
        """Add a label box at the top of the page area."""
        label_height = LABEL_BOX_HEIGHT

        # Draw background
        page.draw_rect(fitz.Rect(x, y, x + width, y + label_height), color=(0, 0, 0), fill=bg_color, width=1)

        # Add text
        self._add_text(page, text, x + 5, y + 20, fontsize=12)

    def _add_text(self, page, text, x, y, fontsize=12, color=(0, 0, 0)):
        """Add text to a page."""
        page.insert_text(
            (x, y),
            text,
            fontsize=fontsize,
            color=color
        )
