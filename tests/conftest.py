"""Shared fixtures: synthetic PDFs built on the fly.

Synthetic documents are preferred over the files in sample-files/ for anything
that needs precise control (rotation, a missing text layer, encryption). The
sample files are used where a realistic document matters.
"""
import pathlib

import fitz
import pytest

def write_pdf(path, pages, rotation=0):
    """Create a PDF at `path`, one page per entry in `pages`.

    An empty string produces a page with no text layer, which is how a scan
    behaves as far as this tool is concerned.
    """
    doc = fitz.open()
    for text in pages:
        page = doc.new_page(width=612, height=792)
        if text:
            page.insert_text((72, 72), text, fontsize=11)
        if rotation:
            page.set_rotation(rotation)
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture
def pdf(tmp_path):
    """Factory: pdf("name", ["page one", "page two"], rotation=90) -> path."""
    def _make(name, pages, rotation=0):
        return write_pdf(tmp_path / f"{name}.pdf", pages, rotation)
    return _make


@pytest.fixture
def samples():
    """Paths to the sample documents committed with the project."""
    base = pathlib.Path(__file__).resolve().parent.parent / "sample-files"
    return {
        "original": str(base / "original.pdf"),
        "modified": str(base / "modified.pdf"),
        "extra_page": str(base / "modified_extra_page.pdf"),
        "removed_page": str(base / "modified_removed_page.pdf"),
    }
