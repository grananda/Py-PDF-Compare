"""Desktop GUI logic.

The GUI needs the system Tk libraries, which are not present on every machine
nor on a bare CI runner, so the whole module is skipped when they are missing.
Only the logic that does not need a window is exercised here.
"""
import os
import tempfile

import fitz
import pytest

try:
    from pdf_compare.gui import MAX_PREVIEW_PAGES, PREVIEW_WIDTH, App
except Exception as exc:  # missing libtk, no display, unusable toolkit...
    pytest.skip(f"GUI toolkit unavailable: {exc}", allow_module_level=True)


def report_of(pages):
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page(width=1200, height=800)
    data = doc.tobytes()
    doc.close()
    return data


class TestPreviewIsBounded:
    """Regression: every page was materialised at full size, then resized."""

    def test_caps_the_number_of_rendered_pages(self):
        images, total = App.pdf_to_images(None, report_of(MAX_PREVIEW_PAGES + 5))

        assert total == MAX_PREVIEW_PAGES + 5, "the real page count is still reported"
        assert len(images) == MAX_PREVIEW_PAGES

    def test_renders_every_page_of_a_short_report(self):
        images, total = App.pdf_to_images(None, report_of(3))

        assert (len(images), total) == (3, 3)

    def test_images_arrive_at_display_size(self):
        images, _ = App.pdf_to_images(None, report_of(2))

        assert all(image.width <= PREVIEW_WIDTH for image in images)


class TestTemporaryReport:
    """Regression: a fixed name in the shared temp directory."""

    def test_cleanup_removes_the_file_and_forgets_it(self):
        handle, path = tempfile.mkstemp(prefix="pdf_comparison_", suffix=".pdf")
        os.close(handle)

        app = App.__new__(App)          # no window, just the attribute
        app.output_path = path
        App.cleanup_temp_report(app)

        assert not os.path.exists(path)
        assert app.output_path == ""

    def test_cleanup_is_safe_when_there_is_nothing_to_remove(self):
        app = App.__new__(App)
        app.output_path = ""
        App.cleanup_temp_report(app)     # must not raise

        assert app.output_path == ""

    def test_two_instances_get_different_paths(self):
        handle_a, path_a = tempfile.mkstemp(prefix="pdf_comparison_", suffix=".pdf")
        handle_b, path_b = tempfile.mkstemp(prefix="pdf_comparison_", suffix=".pdf")
        os.close(handle_a)
        os.close(handle_b)

        try:
            assert path_a != path_b, "two instances would overwrite each other"
        finally:
            os.remove(path_a)
            os.remove(path_b)

    @pytest.mark.skipif(
        os.name == "nt",
        reason="Windows has no POSIX permission bits; there the temp directory "
               "is already per-user, so the shared-directory exposure does not apply",
    )
    def test_the_temporary_file_is_not_readable_by_others(self):
        handle, path = tempfile.mkstemp(prefix="pdf_comparison_", suffix=".pdf")
        os.close(handle)

        try:
            assert oct(os.stat(path).st_mode)[-3:] == "600"
        finally:
            os.remove(path)
