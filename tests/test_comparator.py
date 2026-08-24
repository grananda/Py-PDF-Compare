"""compare_visuals() and analyze(): the two renderers of one comparison."""
import re

import fitz
import pytest

from pdf_compare.comparator import PDFComparator

LABEL = re.compile(r"(?:Original|Modified|Added|Missing) - Page \d+|No Corresponding Page")


def labels(pdf_bytes):
    """The set of labels on each page of a report.

    Sets, not lists: the labels come back in the order they were written to the
    content stream, which is not the order they appear on the page.
    """
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return [set(LABEL.findall(page.get_text())) for page in doc]


class TestCompareVisuals:
    def test_identical_documents_produce_no_report(self, pdf):
        path = pdf("doc", ["alpha beta", "gamma delta"])
        assert PDFComparator(path, path).compare_visuals() is None

    def test_differing_documents_produce_a_report(self, pdf):
        a = pdf("a", ["alpha beta gamma"])
        b = pdf("b", ["alpha beta DELTA"])
        assert PDFComparator(a, b).compare_visuals() is not None

    def test_added_page_is_labelled_and_the_rest_stays_aligned(self, pdf):
        a = pdf("a", ["first page content", "second page content"])
        b = pdf("b", ["brand new unrelated leading page", "first page content", "second page content"])

        result = labels(PDFComparator(a, b).compare_visuals())

        assert result[0] == {"No Corresponding Page", "Added - Page 1"}
        assert result[1] == {"Original - Page 1", "Modified - Page 2"}

    def test_removed_page_is_labelled_as_missing(self, pdf):
        a = pdf("a", ["kept page", "page that disappears entirely"])
        b = pdf("b", ["kept page"])

        result = labels(PDFComparator(a, b).compare_visuals())

        assert result[1] == {"Missing - Page 2", "No Corresponding Page"}

    def test_report_keeps_text_selectable(self, pdf):
        """The whole point of the vector approach: no rasterisation."""
        a = pdf("a", ["findable marker alpha"])
        b = pdf("b", ["findable marker omega"])

        with fitz.open(stream=PDFComparator(a, b).compare_visuals(), filetype="pdf") as doc:
            assert "findable" in doc[0].get_text()

    def test_documents_are_closed_even_when_composition_fails(self, pdf):
        """Regression: without a with block a failure leaked three documents."""
        a = pdf("a", ["alpha"])
        b = pdf("b", ["omega"])

        class Boom(PDFComparator):
            def _add_comparison_page(self, *args):
                raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            Boom(a, b).compare_visuals()


class TestRotatedPages:
    """Regression: word boxes arrive unrotated while the page is drawn rotated."""

    def test_word_boxes_are_mapped_into_the_displayed_space(self, pdf):
        path = pdf("rotated", ["marker word"], rotation=90)

        with fitz.open(path) as doc:
            page = doc[0]
            raw = fitz.Rect(page.get_text("words")[0][:4])
            mapped = PDFComparator(path, path).extract_words_with_bbox(page)[0]["bbox"]

            assert mapped != raw, "the rotation matrix was not applied"
            assert mapped == raw * page.rotation_matrix

    def test_unrotated_pages_are_untouched(self, pdf):
        path = pdf("plain", ["marker word"])

        with fitz.open(path) as doc:
            page = doc[0]
            raw = fitz.Rect(page.get_text("words")[0][:4])
            assert PDFComparator(path, path).extract_words_with_bbox(page)[0]["bbox"] == raw

    def test_a_rotated_pair_still_produces_a_report(self, pdf):
        a = pdf("ra", ["alpha beta gamma"], rotation=90)
        b = pdf("rb", ["alpha beta omega"], rotation=90)
        assert PDFComparator(a, b).compare_visuals() is not None


class TestAnalyze:
    def test_reports_names_paths_and_page_counts(self, pdf):
        a = pdf("original", ["one"])
        b = pdf("modified", ["one", "two"])

        files = PDFComparator(a, b).analyze()["files"]

        assert files["original"]["name"] == "original.pdf"
        assert files["original"]["path"] == a
        assert files["original"]["pages"] == 1
        assert files["modified"]["pages"] == 2

    def test_identical_documents(self, pdf):
        path = pdf("doc", ["alpha beta", "gamma"])
        report = PDFComparator(path, path).analyze()

        assert report["identical"] is True
        assert report["changes"] == {
            "pages_added": 0, "pages_removed": 0, "pages_modified": 0,
            "words_added": 0, "words_removed": 0,
        }

    def test_counts_an_added_page(self, pdf):
        a = pdf("a", ["shared page content here"])
        b = pdf("b", ["shared page content here", "one two three four"])

        changes = PDFComparator(a, b).analyze()["changes"]

        assert changes["pages_added"] == 1
        assert changes["pages_removed"] == 0
        assert changes["words_added"] == 4

    def test_counts_a_removed_page(self, pdf):
        a = pdf("a", ["shared page content here", "one two three"])
        b = pdf("b", ["shared page content here"])

        changes = PDFComparator(a, b).analyze()["changes"]

        assert changes["pages_removed"] == 1
        assert changes["words_removed"] == 3

    def test_counts_words_changed_within_a_page(self, pdf):
        a = pdf("a", ["alpha beta gamma delta"])
        b = pdf("b", ["alpha beta gamma OMEGA"])

        changes = PDFComparator(a, b).analyze()["changes"]

        assert changes["pages_modified"] == 1
        assert changes["words_added"] == 1
        assert changes["words_removed"] == 1

    def test_flags_a_missing_text_layer(self, pdf):
        a = pdf("scan_a", ["", ""])
        b = pdf("scan_b", ["", ""])

        report = PDFComparator(a, b).analyze()

        assert report["missing_text_layer"] is True
        # Without text the documents look identical; the flag is the only warning
        assert report["identical"] is True

    def test_a_text_layer_on_both_sides_is_not_flagged(self, pdf):
        a = pdf("a", ["has text"])
        b = pdf("b", ["has text too"])
        assert PDFComparator(a, b).analyze()["missing_text_layer"] is False


class TestBothRenderersAgree:
    """RF-32: the JSON and the PDF must come from the same comparison."""

    @pytest.mark.parametrize("key", ["modified", "extra_page", "removed_page"])
    def test_agreement_on_the_sample_documents(self, samples, key):
        a, b = samples["original"], samples[key]

        pdf_bytes = PDFComparator(a, b).compare_visuals()
        report = PDFComparator(a, b).analyze()

        assert (pdf_bytes is None) == report["identical"]
        assert len(labels(pdf_bytes)) == (
            report["files"]["original"]["pages"]
            + report["changes"]["pages_added"]
        ), "one report page per compared pair, plus one per added page"

    def test_identical_samples_agree(self, samples):
        a = samples["original"]
        assert PDFComparator(a, a).compare_visuals() is None
        assert PDFComparator(a, a).analyze()["identical"] is True

    def test_word_counts_match_the_highlights_drawn(self, pdf):
        """The counted words are exactly the rectangles the PDF draws."""
        a = pdf("a", ["alpha beta gamma delta epsilon"])
        b = pdf("b", ["alpha beta GAMMA delta OMEGA"])

        report = PDFComparator(a, b).analyze()
        changes = report["changes"]

        with fitz.open(stream=PDFComparator(a, b).compare_visuals(), filetype="pdf") as doc:
            drawings = len(doc[0].get_drawings())

        # two label boxes plus one rectangle per added and per removed word
        assert drawings == 2 + changes["words_added"] + changes["words_removed"]
