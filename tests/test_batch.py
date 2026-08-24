"""Folder comparison: pairing documents by name, and the HTML report."""
import html.parser
import os

import pytest

from pdf_compare.batch import (
    NAME_SIMILARITY_THRESHOLD,
    compare_directories,
    list_pdfs,
    pair_documents,
    render_html,
)
from tests.conftest import write_pdf


def names(pairs):
    return [(a, b) for a, b, _ in pairs]


class TestPairDocuments:
    def test_matches_identical_names(self):
        pairs, left, right = pair_documents(["a.pdf", "b.pdf"], ["b.pdf", "a.pdf"])

        assert names(pairs) == [("a.pdf", "a.pdf"), ("b.pdf", "b.pdf")]
        assert (left, right) == ([], [])

    def test_matches_names_that_differ_slightly(self):
        pairs, left, right = pair_documents(["contrato-2025-v1.pdf"], ["contrato-2025-v2.pdf"])

        assert names(pairs) == [("contrato-2025-v1.pdf", "contrato-2025-v2.pdf")]
        assert (left, right) == ([], [])

    def test_ignores_case_and_extension_case(self):
        pairs, _, _ = pair_documents(["Poliza.PDF"], ["poliza.pdf"])

        assert names(pairs) == [("Poliza.PDF", "poliza.pdf")]
        assert pairs[0][2] == 1.0, "an exact stem match scores 1.0"

    def test_an_exact_match_is_never_stolen_by_a_similar_name(self):
        """Greedy fuzzy matching must not outrank a perfect name."""
        pairs, left, right = pair_documents(
            ["informe.pdf", "informe-anexo.pdf"],
            ["informe-anexo.pdf", "informe.pdf"],
        )

        assert names(pairs) == [("informe-anexo.pdf", "informe-anexo.pdf"),
                                ("informe.pdf", "informe.pdf")]
        assert (left, right) == ([], [])

    def test_reports_documents_with_no_counterpart(self):
        pairs, left, right = pair_documents(
            ["shared.pdf", "only-here.pdf"], ["shared.pdf", "brand-new.pdf"])

        assert names(pairs) == [("shared.pdf", "shared.pdf")]
        assert left == ["only-here.pdf"]
        assert right == ["brand-new.pdf"]

    def test_unrelated_names_are_not_paired(self):
        pairs, left, right = pair_documents(["zzzz.pdf"], ["aircraft-maintenance-log.pdf"])

        assert pairs == []
        assert (left, right) == (["zzzz.pdf"], ["aircraft-maintenance-log.pdf"])

    def test_pairing_is_one_to_one(self):
        pairs, left, _ = pair_documents(
            ["report-a.pdf", "report-b.pdf"], ["report-a.pdf"])

        assert names(pairs) == [("report-a.pdf", "report-a.pdf")]
        assert left == ["report-b.pdf"], "the second file must not reuse the same counterpart"

    def test_threshold_is_honoured(self):
        far = pair_documents(["alpha.pdf"], ["alpine.pdf"], threshold=0.99)[0]
        near = pair_documents(["alpha.pdf"], ["alpine.pdf"], threshold=0.1)[0]

        assert far == []
        assert len(near) == 1


class TestListPdfs:
    def test_only_pdfs_and_only_files(self, tmp_path):
        write_pdf(tmp_path / "keep.pdf", ["content"])
        (tmp_path / "notes.txt").write_text("ignore me")
        (tmp_path / "subdir.pdf").mkdir()

        assert list_pdfs(str(tmp_path)) == ["keep.pdf"]


@pytest.fixture
def folders(tmp_path):
    """Two folders covering every outcome the report has to show."""
    left, right = tmp_path / "v1", tmp_path / "v2"
    left.mkdir()
    right.mkdir()

    write_pdf(left / "changed.pdf", ["cover for alpha beta", "second"])
    write_pdf(right / "changed.pdf", ["cover for alpha OMEGA", "second"])
    write_pdf(left / "same.pdf", ["unchanged text"])
    write_pdf(right / "same.pdf", ["unchanged text"])
    write_pdf(left / "renamed-v1.pdf", ["body of the renamed document"])
    write_pdf(right / "renamed-v2.pdf", ["body of the renamed document changed"])
    write_pdf(left / "scan.pdf", ["", ""])
    write_pdf(right / "scan.pdf", ["", ""])
    write_pdf(left / "withdrawn.pdf", ["gone"])
    write_pdf(right / "introduced.pdf", ["new"])

    return str(left), str(right)


class TestCompareDirectories:
    def test_compares_every_matched_pair(self, folders):
        left, right = folders
        batch = compare_directories(left, right)

        assert len(batch["results"]) == 4
        assert batch["unmatched"] == {"original": ["withdrawn.pdf"], "modified": ["introduced.pdf"]}

    def test_writes_no_documents_without_an_output_directory(self, folders, tmp_path):
        left, right = folders
        batch = compare_directories(left, right)

        assert batch["output_dir"] is None
        assert all(result["diff_file"] is None for result in batch["results"])

    def test_writes_a_diff_for_every_differing_pair(self, folders, tmp_path):
        left, right = folders
        out = tmp_path / "diffs"

        batch = compare_directories(left, right, str(out))

        written = sorted(os.listdir(out))
        produced = sorted(r["diff_file"] for r in batch["results"] if r["diff_file"])
        assert written == produced
        assert "changed-diff.pdf" in written
        assert "same-diff.pdf" not in written, "identical documents produce no diff"

    def test_creates_the_output_directory(self, folders, tmp_path):
        left, right = folders
        out = tmp_path / "nested" / "diffs"

        compare_directories(left, right, str(out))

        assert out.is_dir()

    def test_reports_the_name_similarity_of_each_pair(self, folders):
        left, right = folders
        by_name = {r["files"]["original"]["name"]: r for r in compare_directories(left, right)["results"]}

        assert by_name["same.pdf"]["match"]["name_similarity"] == 1.0
        assert NAME_SIMILARITY_THRESHOLD <= by_name["renamed-v1.pdf"]["match"]["name_similarity"] < 1.0

    def test_progress_is_announced_per_pair(self, folders):
        left, right = folders
        seen = []

        compare_directories(left, right, on_progress=seen.append)

        assert len(seen) == 4


class TestHtmlReport:
    def test_is_well_formed_and_self_contained(self, folders, tmp_path):
        left, right = folders
        report = tmp_path / "report.html"

        render_html(compare_directories(left, right), str(report))
        source = report.read_text(encoding="utf-8")

        html.parser.HTMLParser().feed(source)          # raises if malformed
        assert "http://" not in source and "https://" not in source

    def test_counts_every_outcome(self, folders, tmp_path):
        left, right = folders
        totals = render_html(compare_directories(left, right), str(tmp_path / "r.html"))

        assert totals == {"pairs": 4, "changed": 2, "identical": 2, "unreliable": 1,
                          "unmatched": 2, "failed": 0}

    def test_names_the_documents_with_no_counterpart(self, folders, tmp_path):
        left, right = folders
        report = tmp_path / "r.html"

        render_html(compare_directories(left, right), str(report))
        source = report.read_text(encoding="utf-8")

        assert "withdrawn.pdf" in source
        assert "introduced.pdf" in source

    def test_links_the_diff_documents_when_they_exist(self, folders, tmp_path):
        left, right = folders
        out = tmp_path / "diffs"
        report = out / "report.html"

        render_html(compare_directories(left, right, str(out)), str(report))

        assert 'href="changed-diff.pdf"' in report.read_text(encoding="utf-8"), \
            "the link must be relative to the report, which sits beside the diffs"

    def test_escapes_names_that_look_like_markup(self, tmp_path):
        """Rendered straight from data: such names are illegal on Windows."""
        batch = {
            "directories": {"original": "/in", "modified": "/out"},
            "output_dir": None,
            "unmatched": {"original": ["<i>ghost</i>.pdf"], "modified": []},
            "results": [{
                "files": {
                    "original": {"name": "<script>alert(1)</script>.pdf", "path": "/in/x", "pages": 1},
                    "modified": {"name": "b.pdf", "path": "/out/b.pdf", "pages": 1},
                },
                "identical": False,
                "missing_text_layer": False,
                "changes": {"pages_added": 0, "pages_removed": 0, "pages_modified": 1,
                            "words_added": 1, "words_removed": 1},
                "match": {"name_similarity": 1.0},
                "diff_file": None,
            }],
        }
        report = tmp_path / "r.html"

        render_html(batch, str(report))
        source = report.read_text(encoding="utf-8")

        assert "<script>alert(1)</script>" not in source
        assert "&lt;script&gt;" in source
        assert "&lt;i&gt;ghost" in source, "unmatched names are escaped too"

    def test_handles_folders_with_nothing_comparable(self, tmp_path):
        left, right = tmp_path / "a", tmp_path / "b"
        left.mkdir()
        right.mkdir()
        report = tmp_path / "r.html"

        totals = render_html(compare_directories(str(left), str(right)), str(report))

        assert totals["pairs"] == 0
        assert "No comparable documents found" in report.read_text(encoding="utf-8")


class TestAPairThatCannotBeCompared:
    """Regression: one unreadable document used to abort the whole batch."""

    @pytest.fixture
    def with_a_locked_document(self, tmp_path):
        import fitz

        left, right = tmp_path / "a", tmp_path / "b"
        left.mkdir()
        right.mkdir()

        write_pdf(left / "before.pdf", ["alpha"])
        write_pdf(right / "before.pdf", ["beta"])
        write_pdf(left / "after.pdf", ["gamma"])
        write_pdf(right / "after.pdf", ["delta"])

        for folder in (left, right):
            doc = fitz.open()
            doc.new_page().insert_text((72, 72), "secret")
            doc.save(str(folder / "locked.pdf"),
                     encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="hunter2")
            doc.close()

        return str(left), str(right)

    def test_the_rest_of_the_batch_still_runs(self, with_a_locked_document):
        left, right = with_a_locked_document

        results = compare_directories(left, right)["results"]

        by_name = {r["files"]["original"]["name"]: r for r in results}
        assert len(results) == 3, "every pair is accounted for"
        assert by_name["locked.pdf"]["error"], "the failure is recorded, not raised"
        assert not by_name["before.pdf"].get("error")
        assert not by_name["after.pdf"].get("error")

    def test_diffs_are_still_written_for_the_pairs_that_worked(self, with_a_locked_document, tmp_path):
        left, right = with_a_locked_document
        out = tmp_path / "diffs"

        compare_directories(left, right, str(out))

        assert sorted(os.listdir(out)) == ["after-diff.pdf", "before-diff.pdf"]

    def test_the_report_counts_and_explains_the_failure(self, with_a_locked_document, tmp_path):
        left, right = with_a_locked_document
        report = tmp_path / "r.html"

        totals = render_html(compare_directories(left, right), str(report))
        source = report.read_text(encoding="utf-8")

        assert totals["failed"] == 1
        assert totals["changed"] == 2, "a failure is not counted as a difference"
        assert "Could not compare" in source
        assert "locked.pdf" in source

    def test_a_failure_is_not_reported_as_identical(self, with_a_locked_document):
        left, right = with_a_locked_document

        failed = [r for r in compare_directories(left, right)["results"] if r.get("error")]

        assert failed[0]["identical"] is False, "unknown must never read as unchanged"


class TestDiffNamesDoNotCollide:
    """Regression: names differing only in case overwrite each other on macOS."""

    def test_names_differing_only_in_case_get_distinct_diffs(self, tmp_path):
        left, right = tmp_path / "a", tmp_path / "b"
        left.mkdir()
        right.mkdir()
        for folder, text in ((left, "one"), (right, "one changed")):
            write_pdf(folder / "report.pdf", [text])
            write_pdf(folder / "REPORT.PDF", [text + " too"])
        out = tmp_path / "diffs"

        batch = compare_directories(str(left), str(right), str(out))

        produced = [r["diff_file"] for r in batch["results"] if r["diff_file"]]
        assert len(produced) == 2
        assert len({name.lower() for name in produced}) == 2, \
            "case-insensitive filesystems would treat these as one file"
