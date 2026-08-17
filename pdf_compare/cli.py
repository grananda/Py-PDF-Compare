import argparse
import os
import sys
import fitz  # PyMuPDF
from pdf_compare.comparator import PDFComparator

# Load configuration from config.py (kept for backward compatibility)
try:
    from pdf_compare.config import PDF_RENDER_DPI, JPEG_QUALITY
except ImportError:
    # Fallback defaults if config.py is not found
    PDF_RENDER_DPI = 75
    JPEG_QUALITY = 75

def validate_pdf(file_path):
    """Check the file is a PDF we can actually read.

    Returns an error message, or None if the file is usable. Existence alone is
    not enough: a renamed text file, a corrupt document or a password-protected
    one would otherwise fail deep inside PyMuPDF with an opaque traceback.
    """
    if not os.path.exists(file_path):
        return f"File '{file_path}' not found."

    try:
        with fitz.open(file_path) as doc:
            if doc.needs_pass:
                return f"File '{file_path}' is password protected."
            if doc.page_count == 0:
                return f"File '{file_path}' has no pages."
    except Exception as e:
        return f"File '{file_path}' is not a valid PDF ({e})."

    return None


def main():
    parser = argparse.ArgumentParser(description="Compare two PDF files and generate a vector-based diff report.")
    parser.add_argument("file_a", help="Path to the first PDF file (Original)")
    parser.add_argument("file_b", help="Path to the second PDF file (Modified)")
    parser.add_argument("-o", "--output", default="report.pdf", help="Path to save the output report (default: report.pdf)")
    # DPI and quality kept for backward compatibility but not used in vector rendering
    parser.add_argument("--dpi", type=int, default=PDF_RENDER_DPI, help=f"DPI for PDF rendering (not used in vector mode, kept for compatibility)")
    parser.add_argument("--quality", type=int, default=JPEG_QUALITY, help=f"JPEG quality (not used in vector mode, kept for compatibility)")

    args = parser.parse_args()

    for file_path in (args.file_a, args.file_b):
        error = validate_pdf(file_path)
        if error:
            print(f"Error: {error}")
            sys.exit(1)

    print(f"Comparing '{args.file_a}' and '{args.file_b}'...")
    print("Using vector-based rendering (preserves text and graphics quality)")

    try:
        comparator = PDFComparator(args.file_a, args.file_b)
        pdf_bytes = comparator.compare_visuals()

        if comparator.missing_text_layer:
            print("Warning: at least one document has no text layer (a scan, for example).")
            print("Differences are detected from text, so the result is not reliable.")

        if pdf_bytes is None:
            print("No differences found. No report generated.")
        else:
            print(f"Saving vector-based report to '{args.output}'...")

            # Write the PDF bytes directly to file
            with open(args.output, 'wb') as f:
                f.write(pdf_bytes)

            # Get file size
            file_size = os.path.getsize(args.output)
            file_size_mb = file_size / (1024 * 1024)

            print(f"Done. Report size: {file_size_mb:.2f} MB")
            print("Vector-based PDF created - text is searchable and file size is optimized")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
