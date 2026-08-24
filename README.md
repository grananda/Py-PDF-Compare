# PDF-Compare

A powerful tool for comparing PDF files. Generates vector-based side-by-side comparison reports with content-aware highlighting.

<a href="https://www.buymeacoffee.com/grananda" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

## Features

- **Vector-Based Rendering**: Preserves text quality and keeps file sizes small (no image conversion)
- **Searchable Output**: Generated PDFs maintain searchable, selectable text
- **Visual Comparison**: Side-by-side view of two PDFs with intelligent page alignment
- **Content-Aware Highlighting**: Detects text changes based on content, ignoring layout shifts
- **Smart Page Alignment**: Automatically detects inserted/deleted pages
- **Color-Coded Differences**:
  - **Red**: Deleted text (on the original document)
  - **Green**: Added text (on the modified document)
- **Multiple Interfaces**: CLI, GUI Desktop App, and Python API
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

The package is published on PyPI as **`py-pdf-compare`**:

```bash
pip install py-pdf-compare
```

Or, to install it as a standalone command-line tool with `uv` (recommended — no virtual environment to manage):

```bash
uv tool install py-pdf-compare
```

To add it as a dependency of your own project instead:

```bash
uv add py-pdf-compare
```

> **Note on names:** the distribution is `py-pdf-compare`, but the import name is `pdf_compare` and the commands are `pdf-compare` and `pdf-compare-gui`.

### Prerequisites

- **Python 3.12+** is required

**Windows:**
Download from [python.org](https://www.python.org/downloads/) and check "Add Python to PATH" during installation.

**macOS:**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install python3.12 python3.12-venv
```

**Note:** No additional dependencies (like Poppler) are required. PyMuPDF handles all PDF operations natively.

## Quick Start

### CLI Usage

```bash
# Compare two PDFs
pdf-compare original.pdf modified.pdf -o diff.pdf

# Get a machine-readable summary instead of a PDF
pdf-compare original.pdf modified.pdf --json result.json

# Launch GUI application
pdf-compare-gui

# Show help
pdf-compare --help
```

### Python API

```python
from pdf_compare import PDFComparator

# Create comparator instance
comparator = PDFComparator('original.pdf', 'modified.pdf')

# Generate comparison report (None when both documents are identical)
pdf_bytes = comparator.compare_visuals()

if pdf_bytes is None:
    print('No differences found')
else:
    # Save to file
    with open('report.pdf', 'wb') as f:
        f.write(pdf_bytes)
```

## API Reference

### `PDFComparator(file_a, file_b)`

Main class for comparing PDF files.

**Parameters:**
- `file_a` (str): Path to the first PDF (Original)
- `file_b` (str): Path to the second PDF (Modified)

**Methods:**

#### `compare_visuals() -> bytes | None`

Generate a vector-based visual comparison report.

**Returns:** PDF report as bytes, or `None` if no differences found. "No differences" means no page was added or removed and no word changed on any matched page.

**Attributes:**
- `missing_text_layer` (bool): set after calling `compare_visuals()`. `True` when either document has no extractable text (a scan, for example), which makes the comparison unreliable — the report is still returned in that case, since the absence of differences cannot be confirmed.

**Example:**
```python
from pdf_compare import PDFComparator

comparator = PDFComparator('a.pdf', 'b.pdf')
result = comparator.compare_visuals()

if comparator.missing_text_layer:
    print("Warning: no text layer, differences cannot be detected reliably")

if result is not None:
    with open('diff.pdf', 'wb') as f:
        f.write(result)
    print("Report generated successfully")
else:
    print("No differences found")
```

#### `analyze() -> dict`

Run the same comparison without composing the PDF, and return the result as plain data. Intended for automation: which files were compared and how much changed.

```json
{
  "files": {
    "original": {"name": "a.pdf", "path": "/abs/a.pdf", "pages": 3},
    "modified": {"name": "b.pdf", "path": "/abs/b.pdf", "pages": 4}
  },
  "identical": false,
  "missing_text_layer": false,
  "changes": {
    "pages_added": 1, "pages_removed": 0, "pages_modified": 0,
    "words_added": 78, "words_removed": 0
  }
}
```

Counts are reported rather than a similarity percentage, deliberately: a percentage needs a denominator nobody agrees on (words of the original? of both? what is a whole added page worth?), while counts are facts the caller can turn into whatever ratio they need.

`identical: true` is only trustworthy when `missing_text_layer` is `false`. A scan has no extractable text, so it looks unchanged — always check both fields together.

The same comparison, literally: `analyze()` and `compare_visuals()` share the page alignment and the word-level diff, so they can never disagree. It is **not** meaningfully faster, though — composing the report references the source pages as vector objects rather than rendering them, so building the PDF costs almost nothing. The reason to use it is the format, and not writing a large file you do not need.

## How It Works

1. **Text Extraction**: Extracts text and layout information from each page using PyMuPDF
2. **Similarity Scoring**: Calculates similarity between pages using sequence matching
3. **Smart Alignment**: Detects insertions, deletions, and shifts between documents
4. **Vector-Based Report**: Creates a new PDF that preserves the original vector content
5. **Visual Highlighting**: Adds vector-based highlights over text differences (no rasterization)
6. **Optimized Output**: Maintains searchable text and small file sizes

### Example: Inserted Page

If you insert a page in the middle of a document:
- The inserted page is shown with a blank page on the left, labeled "Added"
- Subsequent pages are correctly aligned and labeled as "Shifted"

### Limitations and edge cases

- **Identical documents**: no report is produced. The CLI says so and exits with code `0`; the API returns `None`.
- **Scanned documents (no text layer)**: differences are detected from extractable text, so a scan cannot be compared. The tool detects this and warns instead of reporting "no differences"; there is no OCR.
- **GUI preview**: only the first 20 pages are rendered in the window, to keep memory bounded. The generated report file always contains every page.
- **Large page shifts**: alignment looks at most 3 pages ahead, so a block of more than 3 consecutive inserted or deleted pages in the middle of a document may not be recovered, and the pages after it can be reported as changed.

## Project Structure

```
Py-PDF-Compare/
├── pdf_compare/
│   ├── __init__.py         # Package initialization
│   ├── comparator.py       # Core comparison logic
│   ├── cli.py              # Command-line interface
│   ├── gui.py              # Desktop GUI application
│   └── config.py           # Configuration
├── scripts/
│   ├── build_windows.py    # Build Windows executable
│   ├── build_linux.py      # Build Linux executable
│   └── build_macos.py      # Build macOS application
├── sample-files/           # Test PDFs for development
│   ├── original.pdf
│   ├── modified.pdf
│   ├── modified_extra_page.pdf
│   └── modified_removed_page.pdf
└── pyproject.toml          # Python package configuration
```

## Development

### From Source

```bash
git clone https://github.com/grananda/Py-PDF-Compare.git
cd Py-PDF-Compare
uv sync
```

`uv sync` installs the project into `.venv` in editable mode, but it does **not** put `pdf-compare` on your `PATH`. From source, run the commands through `uv run` — that way every change to the code takes effect immediately, with no reinstall step:

```bash
# Compare sample files
uv run pdf-compare sample-files/original.pdf sample-files/modified.pdf -o test-output.pdf

# Launch the GUI
uv run pdf-compare-gui

# From outside the repository
uv run --project /path/to/Py-PDF-Compare pdf-compare a.pdf b.pdf -o diff.pdf
```

> **Careful:** `uv tool install py-pdf-compare` installs the **published** version from PyPI, so it will never pick up your local changes. To get a global `pdf-compare` command that tracks your working copy, install it from the repository instead:
>
> ```bash
> uv tool install --editable .
> ```

**Sample files included for testing:**
- `sample-files/original.pdf` - Base document
- `sample-files/modified.pdf` - Document with text changes
- `sample-files/modified_extra_page.pdf` - Document with added page
- `sample-files/modified_removed_page.pdf` - Document with removed page

### GUI Application

```bash
# From source
uv run pdf-compare-gui

# Or after installing the package
pdf-compare-gui
```

The GUI needs the Tk system libraries, which are not part of the Python package. If it fails with `ImportError: libtk8.6.so`, install them:

```bash
sudo pacman -S tk          # Arch / CachyOS
sudo apt install python3-tk # Debian / Ubuntu
brew install python-tk      # macOS
```

They are already included in the standard Python installers for Windows and macOS.

### Building Standalone Executables

**Windows Executable:**
```bash
uv run python scripts/build_windows.py
# Result: dist/PDF Compare.exe
```

**Linux Binary:**
```bash
uv run python scripts/build_linux.py
# Result: dist/pdf-compare
```

**macOS Application:**
```bash
uv run python scripts/build_macos.py
# Result: dist/PDF Compare.app
```

## Using as Git Submodule

This package can be integrated into other projects as a Git submodule:

```bash
git submodule add https://github.com/grananda/Py-PDF-Compare.git
```

Then import in your Python code:
```python
from pdf_compare import PDFComparator
```

## License

[MIT](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or contributions, visit: https://github.com/grananda/Py-PDF-Compare
