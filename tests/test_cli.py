"""Command line: input validation, exit codes and the two output modes."""
import json

import fitz
import pytest

from pdf_compare.cli import main, validate_pdf
from tests.conftest import write_pdf


def run(monkeypatch, *argv):
    """Invoke the CLI, returning its exit code (0 when it returns normally)."""
    monkeypatch.setattr("sys.argv", ["pdf-compare", *argv])
    try:
        main()
    except SystemExit as exit_:
        return exit_.code or 0
    return 0


class TestValidatePdf:
    def test_accepts_a_readable_pdf(self, pdf):
        assert validate_pdf(pdf("ok", ["content"])) is None

    def test_rejects_a_missing_file(self, tmp_path):
        assert "not found" in validate_pdf(str(tmp_path / "nope.pdf"))

    def test_rejects_a_file_that_is_not_a_pdf(self, tmp_path):
        fake = tmp_path / "fake.pdf"
        fake.write_text("this is plain text, not a PDF")
        assert "not a valid PDF" in validate_pdf(str(fake))

    def test_rejects_a_password_protected_pdf(self, tmp_path):
        path = tmp_path / "locked.pdf"
        doc = fitz.open()
        doc.new_page().insert_text((72, 72), "secret")
        doc.save(str(path), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="hunter2")
        doc.close()

        assert "password protected" in validate_pdf(str(path))

    def test_rejects_a_pdf_with_no_pages(self, tmp_path):
        # Written by hand: PyMuPDF refuses to save a document with zero pages,
        # but it opens one happily, so the check is worth having.
        path = tmp_path / "empty.pdf"
        path.write_bytes(
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
            b"trailer<</Root 1 0 R>>\n%%EOF\n"
        )

        assert "no pages" in validate_pdf(str(path))


class TestExitCodes:
    def test_invalid_input_exits_non_zero(self, monkeypatch, pdf, tmp_path):
        code = run(monkeypatch, str(tmp_path / "nope.pdf"), pdf("b", ["x"]))
        assert code == 1

    def test_identical_documents_are_not_an_error(self, monkeypatch, pdf, tmp_path):
        path = pdf("doc", ["alpha"])
        code = run(monkeypatch, path, path, "-o", str(tmp_path / "out.pdf"))
        assert code == 0


class TestPdfOutput:
    def test_writes_the_report(self, monkeypatch, pdf, tmp_path, capsys):
        out = tmp_path / "report.pdf"
        run(monkeypatch, pdf("a", ["alpha beta"]), pdf("b", ["alpha OMEGA"]), "-o", str(out))

        assert out.exists()
        assert "Done." in capsys.readouterr().out

    def test_identical_documents_write_no_file(self, monkeypatch, pdf, tmp_path, capsys):
        path = pdf("doc", ["alpha"])
        out = tmp_path / "report.pdf"
        run(monkeypatch, path, path, "-o", str(out))

        assert not out.exists()
        assert "No differences found" in capsys.readouterr().out


class TestJsonOutput:
    def test_writes_a_valid_report(self, monkeypatch, pdf, tmp_path):
        out = tmp_path / "result.json"
        run(monkeypatch, pdf("a", ["alpha beta"]), pdf("b", ["alpha OMEGA gamma"]), "--json", str(out))

        report = json.loads(out.read_text(encoding="utf-8"))

        assert report["identical"] is False
        assert set(report) == {"files", "identical", "missing_text_layer", "changes"}
        assert report["files"]["original"]["name"] == "a.pdf"

    def test_does_not_build_the_pdf(self, monkeypatch, pdf, tmp_path):
        out = tmp_path / "result.json"
        monkeypatch.chdir(tmp_path)
        run(monkeypatch, pdf("a", ["alpha"]), pdf("b", ["omega"]), "--json", str(out))

        assert out.exists()
        assert not (tmp_path / "report.pdf").exists(), "the default PDF must not be produced"

    def test_warns_that_output_is_ignored(self, monkeypatch, pdf, tmp_path, capsys):
        out_pdf = tmp_path / "ignored.pdf"
        run(monkeypatch, pdf("a", ["alpha"]), pdf("b", ["omega"]),
            "--json", str(tmp_path / "r.json"), "-o", str(out_pdf))

        assert "-o/--output is ignored" in capsys.readouterr().out
        assert not out_pdf.exists()

    def test_reports_identical_documents(self, monkeypatch, pdf, tmp_path):
        path = pdf("doc", ["alpha beta"])
        out = tmp_path / "result.json"
        run(monkeypatch, path, path, "--json", str(out))

        assert json.loads(out.read_text(encoding="utf-8"))["identical"] is True


class TestMissingTextLayerWarning:
    @pytest.mark.parametrize("mode", ["pdf", "json"])
    def test_warns_on_a_scan(self, monkeypatch, pdf, tmp_path, capsys, mode):
        a, b = pdf("scan_a", ["", ""]), pdf("scan_b", ["", ""])
        flag = ["-o", str(tmp_path / "o.pdf")] if mode == "pdf" else ["--json", str(tmp_path / "o.json")]

        run(monkeypatch, a, b, *flag)

        assert "no text layer" in capsys.readouterr().out


@pytest.fixture
def two_folders(tmp_path):
    """Two folders: one changed pair, one identical pair, one without counterpart."""
    left, right = tmp_path / "v1", tmp_path / "v2"
    left.mkdir()
    right.mkdir()

    write_pdf(left / "changed.pdf", ["alpha beta gamma"])
    write_pdf(right / "changed.pdf", ["alpha beta OMEGA"])
    write_pdf(left / "same.pdf", ["unchanged"])
    write_pdf(right / "same.pdf", ["unchanged"])
    write_pdf(left / "withdrawn.pdf", ["gone"])

    return str(left), str(right)


class TestBatchMode:
    """The CLI dispatches on whether the paths are files or directories."""

    def test_two_directories_report_only(self, monkeypatch, two_folders, tmp_path, capsys):
        left, right = two_folders
        report = tmp_path / "r.html"

        run(monkeypatch, left, right, "--report", str(report))

        assert report.exists()
        assert "Report only" in capsys.readouterr().out

    def test_report_only_writes_no_pdf(self, monkeypatch, two_folders, tmp_path):
        left, right = two_folders
        workdir = tmp_path / "cwd"
        workdir.mkdir()
        monkeypatch.chdir(workdir)

        run(monkeypatch, left, right)

        produced = sorted(path.name for path in workdir.iterdir())
        assert produced == ["pdf-compare-report.html"], "only the report, and at the default path"

    def test_out_writes_diffs_and_the_report_beside_them(self, monkeypatch, two_folders, tmp_path):
        left, right = two_folders
        out = tmp_path / "diffs"

        run(monkeypatch, left, right, "--out", str(out))

        produced = sorted(path.name for path in out.iterdir())
        assert produced == ["changed-diff.pdf", "report.html"], \
            "identical pairs produce no diff, and the report ships with the diffs"

    def test_report_overrides_the_default_location(self, monkeypatch, two_folders, tmp_path):
        left, right = two_folders
        out = tmp_path / "diffs"
        report = tmp_path / "elsewhere.html"

        run(monkeypatch, left, right, "--out", str(out), "--report", str(report))

        assert report.exists()
        assert not (out / "report.html").exists()

    def test_announces_documents_with_no_counterpart(self, monkeypatch, two_folders, tmp_path, capsys):
        left, right = two_folders

        run(monkeypatch, left, right, "--report", str(tmp_path / "r.html"))

        output = capsys.readouterr().out
        assert "1 document(s) had no counterpart" in output
        assert "2 pairs compared" in output and "1 with differences" in output

    def test_mixing_a_file_and_a_directory_is_an_error(self, monkeypatch, two_folders, pdf):
        left, _ = two_folders

        code = run(monkeypatch, left, pdf("single", ["content"]))

        assert code == 1

    def test_batch_flags_are_ignored_for_two_files(self, monkeypatch, pdf, tmp_path, capsys):
        run(monkeypatch, pdf("a", ["alpha"]), pdf("b", ["omega"]),
            "-o", str(tmp_path / "out.pdf"), "--out", str(tmp_path / "diffs"))

        assert "only apply when comparing two directories" in capsys.readouterr().out
        assert not (tmp_path / "diffs").exists()

    def test_warns_about_pairs_that_cannot_be_trusted(self, monkeypatch, tmp_path, capsys):
        left, right = tmp_path / "a", tmp_path / "b"
        left.mkdir()
        right.mkdir()
        write_pdf(left / "scan.pdf", ["", ""])
        write_pdf(right / "scan.pdf", ["", ""])

        run(monkeypatch, str(left), str(right), "--report", str(tmp_path / "r.html"))

        output = capsys.readouterr().out
        assert "no text layer, unreliable" in output, "per document, while it runs"
        assert "1 pair(s) have no text layer" in output, "and again in the summary"
