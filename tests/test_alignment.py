"""Page alignment: the part that has produced every bug so far."""
import difflib

import pytest

from pdf_compare.comparator import (
    LOOKAHEAD_WINDOW,
    SHIFT_MARGIN,
    SHIFT_MIN_SIMILARITY,
    SIMILARITY_THRESHOLD,
    PDFComparator,
)


def tags(comparator, text_a, text_b):
    return [op[0] for op in comparator.align_pages(text_a, text_b)]


@pytest.fixture
def cmp_():
    # align_pages only works on text, so the paths are never opened here.
    return PDFComparator("unused-a.pdf", "unused-b.pdf")


def test_identical_pages_align_one_to_one(cmp_):
    pages = ["alpha beta gamma", "delta epsilon zeta"]
    assert tags(cmp_, pages, pages) == ["equal", "equal"]


def test_inserted_page_is_reported_as_insert(cmp_):
    a = ["alpha beta gamma", "delta epsilon zeta"]
    b = ["alpha beta gamma", "brand new unrelated content here", "delta epsilon zeta"]
    assert tags(cmp_, a, b) == ["equal", "insert", "equal"]


def test_deleted_page_is_reported_as_delete(cmp_):
    a = ["alpha beta gamma", "brand new unrelated content here", "delta epsilon zeta"]
    b = ["alpha beta gamma", "delta epsilon zeta"]
    assert tags(cmp_, a, b) == ["equal", "delete", "equal"]


def test_rewritten_page_is_reported_as_replace(cmp_):
    a = ["alpha beta gamma"]
    b = ["completely different words with nothing in common"]
    assert tags(cmp_, a, b) == ["replace"]


def test_trailing_pages_are_reported_as_a_single_insert(cmp_):
    a = ["alpha beta gamma"]
    b = ["alpha beta gamma", "second", "third", "fourth", "fifth"]
    align = cmp_.align_pages(a, b)
    assert align[-1] == ("insert", 1, 1, 1, 5)


def test_lookahead_covers_the_declared_window(cmp_):
    """Regression: the loop bound explored WINDOW-1 positions, not WINDOW.

    With three consecutive inserted pages the trailing page must still be
    recognised as the same page, not dragged out of alignment.
    """
    tail = "shared trailing page content that must stay aligned"
    a = ["header page", tail]
    b = ["header page"] + [f"inserted filler number {n}" for n in range(LOOKAHEAD_WINDOW)] + [tail]

    assert tags(cmp_, a, b) == ["equal", "insert", "equal"]


class TestDisplacedAndEdited:
    """Regression: a page that was both moved and edited.

    Its similarity against its real counterpart never reaches the absolute
    "same page" bar, so requiring SIMILARITY_THRESHOLD to accept a shift made
    the insertion undetectable: the new page was paired with the original and
    the true counterpart was reported as added.
    """

    # Tuned so the pair lands in the band that used to fail: similar enough to
    # be the same page, below the absolute bar, and a far better fit than the
    # page that was actually inserted. test_similarities_sit_in_the_band
    # guards these properties so the regression cannot silently stop being one.
    _IDENTITY = "Poliza 1234 tomador Ada Lovelace. "
    ORIGINAL_COVER = _IDENTITY + (
        "Cobertura de responsabilidad civil hasta 300000 euros, franquicia de 300, "
        "vigencia desde enero."
    )
    EDITED_COVER = _IDENTITY + (
        "Se anula la garantia anterior y se sustituye por el pack integral con "
        "asistencia 24 horas."
    )
    NEW_FIRST_PAGE = "AVISO: 96/2015 DGSFP C0109"

    def test_similarities_sit_in_the_band_that_used_to_fail(self):
        """Guard the premise, so the test cannot pass for the wrong reason."""
        to_counterpart = difflib.SequenceMatcher(None, self.ORIGINAL_COVER, self.EDITED_COVER).ratio()
        to_new_page = difflib.SequenceMatcher(None, self.ORIGINAL_COVER, self.NEW_FIRST_PAGE).ratio()

        assert SHIFT_MIN_SIMILARITY <= to_counterpart <= SIMILARITY_THRESHOLD, (
            "the counterpart must be recognisable yet below the absolute bar, "
            f"got {to_counterpart:.3f}"
        )
        assert to_counterpart >= to_new_page * SHIFT_MARGIN, (
            f"the counterpart must fit clearly better, got {to_counterpart:.3f} "
            f"vs {to_new_page:.3f}"
        )

    def test_new_first_page_is_detected_as_inserted(self, cmp_):
        a = [self.ORIGINAL_COVER, "second page", "third page"]
        b = [self.NEW_FIRST_PAGE, self.EDITED_COVER, "second page", "third page"]

        align = cmp_.align_pages(a, b)

        assert align[0] == ("insert", 0, 0, 0, 1), "the new page must be the inserted one"
        assert align[1][1:] == (0, 1, 1, 2), "the original cover must pair with its moved counterpart"


class TestIsDisplaced:
    def test_rejects_a_candidate_that_is_no_better(self):
        assert not PDFComparator._is_displaced(0.5, current=0.5, best=0.5)

    def test_rejects_noise_below_the_floor(self):
        tiny = SHIFT_MIN_SIMILARITY / 2
        assert not PDFComparator._is_displaced(tiny, current=0.0, best=0.0)

    def test_accepts_an_outright_match(self):
        assert PDFComparator._is_displaced(0.95, current=0.9, best=0.9)

    def test_accepts_a_relatively_much_better_fit(self):
        assert PDFComparator._is_displaced(0.4, current=0.1, best=0.1)

    def test_rejects_a_marginally_better_fit(self):
        assert not PDFComparator._is_displaced(0.4, current=0.35, best=0.35)


def test_blank_pages_are_indistinguishable(cmp_):
    """difflib rates two empty strings as a perfect match.

    This is why a scan yields a report claiming nothing changed, and why
    missing_text_layer exists.
    """
    assert difflib.SequenceMatcher(None, "", "").ratio() == 1.0
    assert tags(cmp_, ["", ""], ["", ""]) == ["equal", "equal"]
