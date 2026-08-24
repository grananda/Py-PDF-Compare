"""PDF Compare - Vector-based PDF comparison tool."""
from importlib.metadata import PackageNotFoundError, version

try:
    # Single source of truth: the version declared in pyproject.toml. Kept by
    # hand this drifted, and a release shipped announcing the wrong version.
    __version__ = version("py-pdf-compare")
except PackageNotFoundError:  # a source tree with nothing installed
    __version__ = "unknown"

from pdf_compare.comparator import PDFComparator
from pdf_compare.config import PDF_RENDER_DPI, JPEG_QUALITY

__all__ = [
    "PDFComparator",
    "PDF_RENDER_DPI",
    "JPEG_QUALITY",
    "__version__",
]
