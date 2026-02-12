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

```bash
pip install pdf-compare
```

Or using `uv` (recommended):

```bash
uv pip install pdf-compare
```

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

# Generate comparison report
pdf_bytes = comparator.compare_visuals()

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

#### `compare_visuals() -> bytes`

Generate a vector-based visual comparison report.

**Returns:** PDF report as bytes, or `None` if no differences found.

**Example:**
```python
from pdf_compare import PDFComparator

comparator = PDFComparator('a.pdf', 'b.pdf')
result = comparator.compare_visuals()

if result:
    with open('diff.pdf', 'wb') as f:
        f.write(result)
    print("Report generated successfully")
else:
    print("No differences found")
```

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

## Project Structure

```
pdf-compare-py/
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
git clone https://github.com/grananda/PDF-Compare-Py.git
cd PDF-Compare-Py
uv pip install -e .
```

**Testing:**
```bash
# Compare sample files
pdf-compare sample-files/original.pdf sample-files/modified.pdf -o test-output.pdf

# Launch GUI
pdf-compare-gui
```

**Sample files included for testing:**
- `sample-files/original.pdf` - Base document
- `sample-files/modified.pdf` - Document with text changes
- `sample-files/modified_extra_page.pdf` - Document with added page
- `sample-files/modified_removed_page.pdf` - Document with removed page

### GUI Application

```bash
# From source
uv run python pdf_compare/gui.py

# Or after installation
pdf-compare-gui
```

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
git submodule add https://github.com/grananda/PDF-Compare-Py.git
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

For issues, questions, or contributions, visit: https://github.com/grananda/PDF-Compare-Py
