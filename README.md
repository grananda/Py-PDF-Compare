# PDF-Compare

A powerful tool for comparing PDF files. Generates visual side-by-side comparison reports with content-aware highlighting.

## Features

- **Visual Comparison**: Side-by-side view of two PDFs with intelligent page alignment
- **Content-Aware Highlighting**: Detects text changes based on content, ignoring layout shifts
- **Smart Page Alignment**: Automatically detects inserted/deleted pages
- **Color-Coded Differences**:
  - **Red**: Deleted text (on the original document)
  - **Green**: Added text (on the modified document)
- **Multiple Interfaces**: CLI, Programmatic API, TypeScript support
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

```bash
npm install pdf-compare
```

The installation will automatically:
1. Detect Python 3.12+ on your system
2. Create an isolated virtual environment
3. Install required Python dependencies

### Prerequisites

#### Python 3.12+

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

#### Poppler

Poppler is required for PDF to image conversion.

**Windows:**
1. Download from [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)
2. Extract and add `Library\bin` folder to your PATH

**macOS:**
```bash
brew install poppler
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install poppler-utils

# Fedora
sudo dnf install poppler-utils
```

## Quick Start

### CLI Usage

```bash
# Compare two PDFs
npx pdf-compare original.pdf modified.pdf -o diff.pdf

# Check dependencies
npx pdf-compare --check

# Run setup manually (if automatic setup failed)
npx pdf-compare --setup

# Show help
npx pdf-compare --help
```

### Programmatic API

```javascript
const pdfCompare = require('pdf-compare');

// Check if dependencies are ready
const status = pdfCompare.checkDependencies();
console.log(status);
// { ready: true, python: true, poppler: true, ... }

// Compare PDFs
async function compare() {
    const result = await pdfCompare.comparePDFs(
        'original.pdf',
        'modified.pdf',
        'report.pdf'
    );

    if (result.pageCount === 0) {
        console.log('No visual differences found');
    } else {
        console.log(`Report generated: ${result.reportPath}`);
        console.log(`Pages with differences: ${result.pageCount}`);
    }
}

compare();
```

### TypeScript

```typescript
import { comparePDFs, checkDependencies, CompareResult } from 'pdf-compare';

const status = checkDependencies();
if (!status.ready) {
    console.error('Dependencies not configured');
    process.exit(1);
}

const result: CompareResult = await comparePDFs('a.pdf', 'b.pdf', 'diff.pdf');
```

## API Reference

### `comparePDFs(fileA, fileB, outputPath, options?)`

Compare two PDF files and generate a visual diff report.

**Parameters:**
- `fileA` (string): Path to the first PDF (Original)
- `fileB` (string): Path to the second PDF (Modified)
- `outputPath` (string): Path for the output report
- `options` (object, optional):
  - `timeout` (number): Timeout in ms (default: 120000)
  - `pythonPath` (string): Custom Python path

**Returns:** `Promise<CompareResult>`
```typescript
{
    success: boolean;
    pageCount: number | null;  // 0 if no differences
    reportPath: string | null; // null if no differences
    output: string;
}
```

### `comparePDFsFromBuffer(bufferA, bufferB, options?)`

Compare PDFs from Buffer data (useful for streams/uploads).

**Parameters:**
- `bufferA` (Buffer): First PDF as Buffer
- `bufferB` (Buffer): Second PDF as Buffer
- `options` (object, optional): Same as `comparePDFs`

**Returns:** `Promise<CompareBufferResult>`
```typescript
{
    success: boolean;
    pageCount: number | null;
    reportBuffer: Buffer | null;
    output: string;
}
```

### `checkDependencies()`

Check if all dependencies are installed and configured.

**Returns:** `DependencyStatus`
```typescript
{
    ready: boolean;
    python: boolean;
    poppler: boolean;
    pythonPath: string | null;
    popplerPath: string | null;
}
```

### `runSetup(options?)`

Manually run the Python environment setup.

**Parameters:**
- `options` (object, optional):
  - `force` (boolean): Force reinstall
  - `quiet` (boolean): Suppress output

**Returns:** `Promise<SetupResult>`

### `getVersion()`

Get the package version.

**Returns:** `string`

## Environment Variables

- `PDF_COMPARE_SKIP_SETUP=1`: Skip automatic setup during npm install

## How It Works

1. **Text Extraction**: Extracts text from each page of both PDFs
2. **Similarity Scoring**: Calculates similarity between pages using sequence matching
3. **Smart Alignment**: Detects insertions, deletions, and shifts between documents
4. **Visual Highlighting**: Highlights text differences within aligned pages
5. **Report Generation**: Creates a side-by-side PDF report

### Example: Inserted Page

If you insert a page in the middle of a document:
- The inserted page is shown with a blank page on the left, labeled "Added"
- Subsequent pages are correctly aligned and labeled as "Shifted"

## Project Structure

```
pdf-compare/
├── lib/
│   ├── index.js            # Main API exports
│   ├── cli.js              # CLI entry point
│   ├── python-bridge.js    # Python subprocess handling
│   └── setup.js            # Environment setup
├── python/
│   ├── comparator.py       # Core comparison logic
│   ├── compare_pdf.py      # Python CLI
│   ├── main.py             # GUI application
│   └── requirements.txt    # Python dependencies (npm)
├── scripts/
│   ├── postinstall.js      # Auto-setup on npm install
│   ├── build_windows.py    # Build Windows executable
│   └── download_poppler.py # Download Poppler for Windows
├── sample-files/           # Test PDFs for development
│   ├── original.pdf
│   ├── modified.pdf
│   ├── modified_extra_page.pdf
│   └── modified_removed_page.pdf
├── types/
│   └── index.d.ts          # TypeScript definitions
├── Containerfile           # Docker/Podman build
├── package.json            # npm configuration
└── pyproject.toml          # Python dependencies (dev)
```

## Troubleshooting

### Setup failed: Python not found

Ensure Python 3.12+ is installed and in your PATH:
```bash
python --version  # or python3 --version
```

After installing Python, run:
```bash
npx pdf-compare --setup
```

### Poppler not found

Install Poppler for your platform (see Prerequisites above), then verify:
```bash
npx pdf-compare --check
```

### Permission errors on Linux/macOS

The virtual environment is created in `node_modules/pdf-compare/.venv`. Ensure you have write permissions.

### Skipping automatic setup in CI

Set the environment variable:
```bash
PDF_COMPARE_SKIP_SETUP=1 npm install
```

## Development

### From Source

```bash
git clone https://github.com/grananda/PDF-Compare.git
cd PDF-Compare
npm install
```

**npm scripts:**
```bash
npm run check    # Verify dependencies are installed
npm run setup    # Run Python environment setup manually
npm test         # Compare sample files (quick test)
npm run compare -- a.pdf b.pdf -o output.pdf  # Compare any PDFs
```

**Sample files included for testing:**
- `sample-files/original.pdf` - Base document
- `sample-files/modified.pdf` - Document with text changes
- `sample-files/modified_extra_page.pdf` - Document with added page
- `sample-files/modified_removed_page.pdf` - Document with removed page

### Docker

Run PDF comparisons in a container without installing dependencies locally.

**Build:**
```bash
# Docker
docker build -f Containerfile -t pdf-compare .

# Podman
podman build -t pdf-compare .
```

**Run comparison:**
```bash
# Docker (Linux/macOS)
docker run --rm -v "$(pwd):/data" pdf-compare /data/original.pdf /data/modified.pdf -o /data/report.pdf

# Docker (Windows PowerShell)
docker run --rm -v "${PWD}:/data" pdf-compare /data/original.pdf /data/modified.pdf -o /data/report.pdf

# Podman (Linux with SELinux)
podman run --rm -v "$(pwd):/data:Z" pdf-compare /data/original.pdf /data/modified.pdf -o /data/report.pdf
```

**Build arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `PYTHON_VERSION` | 3.12 | Python version to use |
| `UID` | 1000 | User ID for non-root user |
| `GID` | 1000 | Group ID for non-root user |

**Note:** On SELinux systems (Fedora, RHEL), use `:Z` flag when mounting volumes.

### GUI Application

```bash
uv run python python/main.py
```

### Windows Executable

```bash
# Download Poppler (one-time)
uv run python scripts/download_poppler.py

# Build executable
uv run python scripts/build_windows.py

# Result: dist/PDF Compare.exe
```

## License

[MIT](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or contributions, visit: https://github.com/grananda/PDF-Compare
