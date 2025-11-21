# PDF Comparison Tool

A powerful Python-based tool for comparing PDF files. It provides both text-based analysis and visual side-by-side comparisons with content-aware highlighting.

## Features

- **Visual Comparison**: Side-by-side view of two PDFs.
- **Content-Aware Highlighting**: Detects text changes based on content, ignoring layout shifts (e.g., inserted paragraphs).
- **Color-Coded Differences**:
    - **Red**: Deleted text (on the original document).
    - **Green**: Added text (on the modified document).
- **GUI & CLI**: Easy-to-use Graphical User Interface and Command Line Interface.
- **Export**: Save the visual comparison report as a PDF.

## Prerequisites

### 1. Python
Ensure you have Python 3.8 or higher installed.

### 2. Poppler
This tool requires **Poppler** for converting PDFs to images.

#### Windows
1.  Download the latest binary from [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/).
2.  Extract the zip file.
3.  Add the `bin` folder (e.g., `C:\poppler-xx\Library\bin`) to your System **PATH**.
    - *Note: The code attempts to look for Poppler at `C:\poppler-25.11.0\Library\bin` by default. If you installed it elsewhere, ensure it is in your PATH.*

#### macOS
Install via Homebrew:
```bash
brew install poppler
```

#### Linux (Ubuntu/Debian)
Install via apt:
```bash
sudo apt-get install poppler-utils
```

## Installation

1.  Clone the repository:
    ```bash
    git clone git@github.com:grananda/PDF-Compare.git
    cd PDF-Compare
    ```

2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Graphical User Interface (GUI)
Run the main script to launch the GUI:
```bash
python main.py
```
1.  Select "PDF A" (Original).
2.  Select "PDF B" (Modified).
3.  Click **Compare PDFs**.
4.  View the results and click **Download Report** to save.

### Command Line Interface (CLI)
Run the comparison from the terminal:
```bash
python compare_pdf.py path/to/original.pdf path/to/modified.pdf -o output_report.pdf
```

### Docker
You can also run the tool using Docker without installing dependencies locally.

1.  **Build the image**:
    ```bash
    docker build -t pdf-compare .
    ```

2.  **Run the comparison**:
    Use the following command to mount your current directory to `/data` inside the container. This allows the container to read your input files and write the output report back to your host machine.

    **Linux/macOS**:
    ```bash
    docker run --rm -v "$(pwd):/data" pdf-compare /data/original.pdf /data/modified.pdf -o /data/report.pdf
    ```

    **Windows (PowerShell)**:
    ```powershell
    docker run --rm -v "${PWD}:/data" pdf-compare /data/original.pdf /data/modified.pdf -o /data/report.pdf
    ```

    *Note: Replace `original.pdf` and `modified.pdf` with your actual filenames. They must be in the current directory (or the path you mounted).*

## License
[MIT](LICENSE)
