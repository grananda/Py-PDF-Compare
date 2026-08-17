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

    def compare_text(self):
        """Compare text content of both PDFs and return unified diff."""
        text_a = self.extract_text(self.file_path_a)
        text_b = self.extract_text(self.file_path_b)

        full_text_a = "\n".join(text_a)
        full_text_b = "\n".join(text_b)

        diff = difflib.unified_diff(
            full_text_a.splitlines(),
            full_text_b.splitlines(),
            fromfile='PDF A',
            tofile='PDF B',
            lineterm=''
        )

        return list(diff)

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

    def compare_visuals(self):
        """
        Create a vector-based PDF comparison report.
        Returns the output PDF as bytes, or None when both documents are equal.

        When either document has no usable text layer the differences cannot be
        determined, so the report is returned anyway and self.missing_text_layer
        is set: reporting "no differences" would be a claim we cannot make.
        """
        # Extract text for alignment
        text_a = self.extract_text(self.file_path_a)
        text_b = self.extract_text(self.file_path_b)

        self.missing_text_layer = not (
            self._has_text_layer(text_a) and self._has_text_layer(text_b)
        )

        # Align pages
        opcodes = self.align_pages(text_a, text_b)

        # Tracks whether any real difference was found, to tell "identical
        # documents" apart from "documents that differ".
        has_differences = False

        with fitz.open(self.file_path_a) as doc_a, \
                fitz.open(self.file_path_b) as doc_b, \
                fitz.open() as output_doc:

            for tag, i1, i2, j1, j2 in opcodes:
                if tag == 'equal' or tag == 'replace':
                    count = max(i2 - i1, j2 - j1)

                    for k in range(count):
                        idx_a = i1 + k if i1 + k < i2 else None
                        idx_b = j1 + k if j1 + k < j2 else None

                        if idx_a is not None and idx_b is not None:
                            # Both pages exist - compare them
                            if self._add_comparison_page(output_doc, doc_a, doc_b, idx_a, idx_b, tag):
                                has_differences = True
                        elif idx_a is None and idx_b is not None:
                            # Page only in B (insertion)
                            self._add_single_page(output_doc, doc_b, idx_b, 'right', 'Added')
                            has_differences = True
                        elif idx_b is None and idx_a is not None:
                            # Page only in A (deletion)
                            self._add_single_page(output_doc, doc_a, idx_a, 'left', 'Missing')
                            has_differences = True

                elif tag == 'delete':
                    # Pages in A but not in B
                    for k in range(i1, i2):
                        self._add_single_page(output_doc, doc_a, k, 'left', 'Missing')
                        has_differences = True

                elif tag == 'insert':
                    # Pages in B but not in A
                    for k in range(j1, j2):
                        self._add_single_page(output_doc, doc_b, k, 'right', 'Added')
                        has_differences = True

            if not has_differences and not self.missing_text_layer:
                return None

            return output_doc.tobytes()

    def _add_comparison_page(self, output_doc, doc_a, doc_b, idx_a, idx_b, comparison_type):
        """Add a side-by-side comparison page to the output PDF.

        Returns True if any textual difference was highlighted on the page.
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

        # Extract words and find differences
        words_a = self.extract_words_with_bbox(page_a)
        words_b = self.extract_words_with_bbox(page_b)

        text_a = [w['text'] for w in words_a]
        text_b = [w['text'] for w in words_b]

        matcher = difflib.SequenceMatcher(None, text_a, text_b)

        # Highlight differences
        has_changes = False
        for inner_tag, ii1, ii2, jj1, jj2 in matcher.get_opcodes():
            if inner_tag == 'equal':
                continue

            has_changes = True

            # Highlight deletions (red on left page)
            if inner_tag in ('replace', 'delete'):
                for w_idx in range(ii1, ii2):
                    bbox = words_a[w_idx]['bbox']
                    # Adjust bbox to output page coordinates
                    adjusted_bbox = fitz.Rect(
                        bbox.x0 + margin,
                        bbox.y0 + margin + label_height,
                        bbox.x1 + margin,
                        bbox.y1 + margin + label_height
                    )
                    new_page.draw_rect(adjusted_bbox, color=(1, 0, 0), fill=(1, 0.7, 0.7), fill_opacity=0.3)

            # Highlight insertions (green on right page)
            if inner_tag in ('replace', 'insert'):
                for w_idx in range(jj1, jj2):
                    bbox = words_b[w_idx]['bbox']
                    # Adjust bbox to output page coordinates
                    adjusted_bbox = fitz.Rect(
                        bbox.x0 + margin + rect_a.width + gap,
                        bbox.y0 + margin + label_height,
                        bbox.x1 + margin + rect_a.width + gap,
                        bbox.y1 + margin + label_height
                    )
                    new_page.draw_rect(adjusted_bbox, color=(0, 1, 0), fill=(0.7, 1, 0.7), fill_opacity=0.3)

        # Add visual indicator if pages are shifted
        if idx_a != idx_b:
            # Draw a yellow border to indicate page shift
            new_page.draw_rect(fitz.Rect(5, 5, width - 5, height - 5), color=(1, 1, 0), width=3)
            self._add_text(new_page, "(Page Shifted)", width / 2 - 50, height - 15, fontsize=10, color=(0.8, 0.6, 0))

        return has_changes

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
