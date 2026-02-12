"""PDF Compare - Vector-based PDF comparison tool."""

__version__ = "2026.2.2"

from pdf_compare.comparator import PDFComparator
from pdf_compare.config import PDF_RENDER_DPI, JPEG_QUALITY

__all__ = [
    "PDFComparator",
    "PDF_RENDER_DPI",
    "JPEG_QUALITY",
]
