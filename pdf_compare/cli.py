import argparse
import os
import sys
from pdf_compare.comparator import PDFComparator

# Load configuration from config.py (kept for backward compatibility)
try:
    from pdf_compare.config import PDF_RENDER_DPI, JPEG_QUALITY
except ImportError:
    # Fallback defaults if config.py is not found
    PDF_RENDER_DPI = 75
    JPEG_QUALITY = 75

def main():
    parser = argparse.ArgumentParser(description="Compare two PDF files and generate a vector-based diff report.")
    parser.add_argument("file_a", help="Path to the first PDF file (Original)")
    parser.add_argument("file_b", help="Path to the second PDF file (Modified)")
    parser.add_argument("-o", "--output", default="report.pdf", help="Path to save the output report (default: report.pdf)")
    # DPI and quality kept for backward compatibility but not used in vector rendering
    parser.add_argument("--dpi", type=int, default=PDF_RENDER_DPI, help=f"DPI for PDF rendering (not used in vector mode, kept for compatibility)")
    parser.add_argument("--quality", type=int, default=JPEG_QUALITY, help=f"JPEG quality (not used in vector mode, kept for compatibility)")

    args = parser.parse_args()

    if not os.path.exists(args.file_a):
        print(f"Error: File '{args.file_a}' not found.")
        sys.exit(1)

    if not os.path.exists(args.file_b):
        print(f"Error: File '{args.file_b}' not found.")
        sys.exit(1)

    print(f"Comparing '{args.file_a}' and '{args.file_b}'...")
    print("Using vector-based rendering (preserves text and graphics quality)")

    try:
        comparator = PDFComparator(args.file_a, args.file_b)
        pdf_bytes = comparator.compare_visuals()

        if not pdf_bytes:
            print("No differences found or error occurred.")
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
