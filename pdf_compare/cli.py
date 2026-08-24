import argparse
import json
import os
import sys
import fitz  # PyMuPDF
from pdf_compare.batch import compare_directories, render_html
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


def warn_missing_text_layer(comparator):
    """Warn when the comparison cannot be trusted because there is no text."""
    if comparator.missing_text_layer:
        print("Warning: at least one document has no text layer (a scan, for example).")
        print("Differences are detected from text, so the result is not reliable.")


def report_json(comparator, output_path):
    """Write the machine-readable summary of the comparison."""
    report = comparator.analyze()

    with open(output_path, 'w', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    warn_missing_text_layer(comparator)

    changes = report['changes']
    print(f"Wrote JSON summary to '{output_path}'.")
    print(f"Identical: {report['identical']} | "
          f"pages +{changes['pages_added']} -{changes['pages_removed']} "
          f"~{changes['pages_modified']} | "
          f"words +{changes['words_added']} -{changes['words_removed']}")


def report_pdf(comparator, output_path):
    """Build the side-by-side report and save it, if there is anything to show."""
    print("Using vector-based rendering (preserves text and graphics quality)")
    pdf_bytes = comparator.compare_visuals()

    warn_missing_text_layer(comparator)

    if pdf_bytes is None:
        print("No differences found. No report generated.")
        return

    print(f"Saving vector-based report to '{output_path}'...")
    with open(output_path, 'wb') as handle:
        handle.write(pdf_bytes)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done. Report size: {size_mb:.2f} MB")
    print("Vector-based PDF created - text is searchable and file size is optimized")


def run_batch(dir_a, dir_b, output_dir, report_path):
    """Compare two directories, writing the diffs when asked and always a report."""
    if report_path is None:
        report_path = (os.path.join(output_dir, "report.html") if output_dir
                       else "pdf-compare-report.html")

    print(f"Comparing directories '{dir_a}' and '{dir_b}'...")
    if output_dir:
        print(f"Diff documents will be written to '{output_dir}'.")
    else:
        print("Report only: no diff documents will be produced.")

    def announce(summary):
        name = summary["files"]["original"]["name"]
        if summary["missing_text_layer"]:
            state = "no text layer, unreliable"
        elif summary["identical"]:
            state = "identical"
        else:
            changes = summary["changes"]
            state = (f"+{changes['pages_added']} -{changes['pages_removed']} "
                     f"~{changes['pages_modified']} pages")
        print(f"  {name}: {state}")

    batch = compare_directories(dir_a, dir_b, output_dir, on_progress=announce)
    totals = render_html(batch, report_path)

    print(f"\nWrote report to '{report_path}'.")
    print(f"{totals['pairs']} pairs compared | {totals['changed']} with differences | "
          f"{totals['identical']} identical")

    if totals["unmatched"]:
        print(f"Warning: {totals['unmatched']} document(s) had no counterpart and were not compared.")
    if totals["unreliable"]:
        print(f"Warning: {totals['unreliable']} pair(s) have no text layer; those results are not reliable.")


def main():
    parser = argparse.ArgumentParser(description="Compare two PDF files and generate a vector-based diff report.")
    parser.add_argument("file_a", help="Path to the first PDF file (Original)")
    parser.add_argument("file_b", help="Path to the second PDF file (Modified)")
    parser.add_argument("-o", "--output", default=None, help="Path to save the output PDF report (default: report.pdf)")
    parser.add_argument("--out", metavar="DIR", default=None,
                        help="Batch mode: write the diff PDF of every differing pair into DIR")
    parser.add_argument("--report", metavar="PATH", default=None,
                        help="Batch mode: where to write the HTML report "
                             "(default: report.html inside --out, or ./pdf-compare-report.html)")
    parser.add_argument("--json", metavar="PATH", default=None,
                        help="Write a JSON summary of the comparison to PATH instead of "
                             "building the PDF report")
    # DPI and quality kept for backward compatibility but not used in vector rendering
    parser.add_argument("--dpi", type=int, default=PDF_RENDER_DPI, help=f"DPI for PDF rendering (not used in vector mode, kept for compatibility)")
    parser.add_argument("--quality", type=int, default=JPEG_QUALITY, help=f"JPEG quality (not used in vector mode, kept for compatibility)")

    args = parser.parse_args()

    both_directories = os.path.isdir(args.file_a) and os.path.isdir(args.file_b)

    if os.path.isdir(args.file_a) != os.path.isdir(args.file_b):
        print("Error: compare two files or two directories, not one of each.")
        sys.exit(1)

    if both_directories:
        try:
            run_batch(args.file_a, args.file_b, args.out, args.report)
        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        return

    if args.out or args.report:
        print("Warning: --out and --report only apply when comparing two directories.")

    for file_path in (args.file_a, args.file_b):
        error = validate_pdf(file_path)
        if error:
            print(f"Error: {error}")
            sys.exit(1)

    if args.json and args.output:
        print("Warning: --json skips the PDF report, so -o/--output is ignored.")

    print(f"Comparing '{args.file_a}' and '{args.file_b}'...")

    try:
        comparator = PDFComparator(args.file_a, args.file_b)

        if args.json:
            report_json(comparator, args.json)
        else:
            report_pdf(comparator, args.output or "report.pdf")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
