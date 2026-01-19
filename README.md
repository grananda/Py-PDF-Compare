# PDF Comparison Tool

A powerful Python-based tool for comparing PDF files. It provides both text-based analysis and visual side-by-side comparisons with content-aware highlighting.

## Features

- **Visual Comparison**: Side-by-side view of two PDFs with intelligent page alignment
- **Content-Aware Highlighting**: Detects text changes based on content, ignoring layout shifts (e.g., inserted paragraphs)
- **Smart Page Alignment**: Automatically detects inserted/deleted pages and aligns the rest correctly
- **Color-Coded Differences**:
    - **Red**: Deleted text (on the original document)
    - **Green**: Added text (on the modified document)
- **Multiple Interfaces**:
    - **GUI**: Easy-to-use Graphical User Interface
    - **CLI**: Command Line Interface for automation (Python and Node.js)
    - **Node.js Wrapper**: Direct Python integration without REST API
    - **REST API**: HTTP API for integration with web applications
- **Export**: Save the visual comparison report as a PDF

## Prerequisites

### 1. Python
Ensure you have Python 3.12 or higher installed.

### 2. Package Manager
You can use either **uv** (recommended, faster) or **pip**:

**Option A: uv (Recommended)**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Option B: pip**
Comes pre-installed with Python.

### 3. Poppler
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

    **Option A: Using uv (Recommended - Fast)**
    ```bash
    uv sync
    ```

    **Option B: Using pip (Traditional)**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Graphical User Interface (GUI)
Run the main script to launch the GUI:

**With uv:**
```bash
uv run python main.py
```

**With pip (activate venv first):**
```bash
python main.py
```
1.  Select "PDF A" (Original).
2.  Select "PDF B" (Modified).
3.  Click **Compare PDFs**.
4.  View the results and click **Download Report** to save.

### Command Line Interface (CLI)
Run the comparison from the terminal:

**With uv:**
```bash
uv run python compare_pdf.py ./sample_files/original.pdf ./sample_files/modified.pdf -o ./sample_files/output_report.pdf
```

**With pip (activate venv first):**
```bash
python compare_pdf.py ./sample_files/original.pdf ./sample_files/modified.pdf -o ./sample_files/output_report.pdf
```

### Node.js CLI Wrapper

A Node.js module that calls the Python script directly, without needing the REST API.

#### Installation

```bash
# No external dependencies required - uses only Node.js built-in modules
npm install  # Optional: creates package.json if needed
```

#### CLI Usage

```bash
# Basic usage
node pdf-compare.js original.pdf modified.pdf -o report.pdf

# Using npm script
npm test  # Runs comparison with sample files

# After npm link (global command)
npm link
pdf-compare original.pdf modified.pdf -o report.pdf

# Show help
node pdf-compare.js --help
```

#### Programmatic API

```javascript
const { comparePDFs, findPython } = require('./pdf-compare');

// Basic usage
async function example() {
    const result = await comparePDFs(
        'original.pdf',
        'modified.pdf',
        'report.pdf'
    );

    console.log(result);
    // {
    //   success: true,
    //   output: 'Report generated with 5 page(s)...',
    //   pageCount: 5,
    //   reportPath: '/absolute/path/to/report.pdf'
    // }
}

// With options
async function advancedExample() {
    const result = await comparePDFs('a.pdf', 'b.pdf', 'out.pdf', {
        pythonPath: '/usr/bin/python3',  // Custom Python path
        cwd: '/path/to/pdf-compare',     // Working directory
        timeout: 120000                   // Timeout in ms (default: 60000)
    });
}

// Find Python executable
const pythonPath = await findPython();
console.log(pythonPath);  // 'python3', 'python', or 'py'
```

#### Return Values

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether comparison succeeded |
| `output` | string | Console output from Python script |
| `pageCount` | number \| null | Number of pages in report (0 if no differences) |
| `reportPath` | string \| null | Absolute path to generated report (null if no differences) |

#### Error Handling

```javascript
try {
    const result = await comparePDFs('a.pdf', 'b.pdf', 'out.pdf');
} catch (error) {
    // Possible errors:
    // - "File not found: /path/to/file.pdf"
    // - "Python not found. Please install Python 3..."
    // - "compare_pdf.py not found in /path"
    // - "Comparison timed out after 60000ms"
    // - "Comparison failed (exit code 1): ..."
    console.error(error.message);
}
```

### REST API (for JavaScript/Node.js integration)

Start the API server:

```bash
uv run python api.py

# With custom configuration
PORT=8080 DEBUG=true python api.py
```

The server will be available at `http://localhost:5000`

#### API Endpoints

**1. Health Check**
```bash
GET /health
```

**2. Compare PDFs (file upload)**
```bash
POST /compare
Content-Type: multipart/form-data

Parameters:
- file_a: PDF file (original)
- file_b: PDF file (modified)
- output_format: 'pdf' or 'json' (optional, default: 'pdf')
```

**3. Compare PDFs from URLs**
```bash
POST /compare-urls
Content-Type: application/json

Body:
{
  "url_a": "https://example.com/original.pdf",
  "url_b": "https://example.com/modified.pdf",
  "output_format": "pdf"
}
```

#### JavaScript Examples

**Browser (Fetch API):**
```javascript
async function comparePDFs(fileA, fileB) {
    const formData = new FormData();
    formData.append('file_a', fileA);
    formData.append('file_b', fileB);

    const response = await fetch('http://localhost:5000/compare', {
        method: 'POST',
        body: formData
    });

    const blob = await response.blob();

    // Download the PDF
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'comparison_report.pdf';
    a.click();
}
```

**Node.js (with axios):**
```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

async function comparePDFs(pathA, pathB, outputPath) {
    const formData = new FormData();
    formData.append('file_a', fs.createReadStream(pathA));
    formData.append('file_b', fs.createReadStream(pathB));

    const response = await axios.post('http://localhost:5000/compare', formData, {
        headers: formData.getHeaders(),
        responseType: 'arraybuffer'
    });

    fs.writeFileSync(outputPath, response.data);
}

// Usage
comparePDFs('./original.pdf', './modified.pdf', './report.pdf');
```

**cURL:**
```bash
# Compare files
curl -X POST http://localhost:5000/compare \
  -F "file_a=@./sample_files/original.pdf" \
  -F "file_b=@./sample_files/modified.pdf" \
  -F "output_format=pdf" \
  --output comparison_report.pdf

# Get JSON response
curl -X POST http://localhost:5000/compare \
  -F "file_a=@./original.pdf" \
  -F "file_b=@./modified.pdf" \
  -F "output_format=json"
```

See `client-example.js` for complete HTML form example and more usage patterns.

#### Using Postman

**Method 1: Upload Files**

1. **Create a new request**
   - Method: `POST`
   - URL: `http://localhost:5000/compare`

2. **Set up the body**
   - Go to the **Body** tab
   - Select **form-data**
   - Add the following fields:
     - Key: `file_a` | Type: `File` | Value: Select your original PDF
     - Key: `file_b` | Type: `File` | Value: Select your modified PDF
     - Key: `output_format` | Type: `Text` | Value: `pdf` (or `json`)

3. **Send the request**
   - Click **Send**
   - For PDF output: Click **Save Response** → **Save to a file** → Save as `.pdf`
   - For JSON output: View the response in the **Body** tab

**Method 2: Compare from URLs**

1. **Create a new request**
   - Method: `POST`
   - URL: `http://localhost:5000/compare-urls`

2. **Set up the headers**
   - Go to the **Headers** tab
   - Add: `Content-Type: application/json`

3. **Set up the body**
   - Go to the **Body** tab
   - Select **raw** and **JSON**
   - Enter:
     ```json
     {
       "url_a": "https://example.com/original.pdf",
       "url_b": "https://example.com/modified.pdf",
       "output_format": "pdf"
     }
     ```

4. **Send the request**
   - Click **Send**
   - Save the response as a `.pdf` file

**Testing the Health Endpoint**

1. **Create a new request**
   - Method: `GET`
   - URL: `http://localhost:5000/health`

2. **Send the request**
   - You should receive: `{"status": "ok", "service": "PDF Compare API"}`

### Docker

You can also run the tool using Docker without installing dependencies locally (uses Python 3.12).

**Note:** The `.dockerignore` file excludes virtual environments and other unnecessary files from the build context, making builds faster and preventing issues with symbolic links on Windows.

1.  **Build the image**:
    ```bash
    docker build -t pdf-compare .
    ```

2.  **Run CLI comparison**:
    Use the following command to mount your current directory to `/app` inside the container. This allows the container to read your input files and write the output report back to your host machine.

    **Linux/macOS**:
    ```bash
    docker run --rm -v "$(pwd):/app" pdf-compare /app/sample_files/original.pdf /app/sample_files/modified.pdf -o /app/sample_files/report.pdf
    ```

    **Windows (PowerShell)**:
    ```powershell
    docker run --rm -v "${PWD}:/app" pdf-compare /app/sample_files/original.pdf /app/sample_files/modified.pdf -o /app/sample_files/report.pdf
    ```

3. **Run API server**:
    ```bash
    docker run -p 5000:5000 pdf-compare python api.py
    ```

## API Configuration

### Environment Variables

- `PORT`: Server port (default: 5000)
- `DEBUG`: Enable debug mode (default: False)

### Production Deployment

For production, use a WSGI server like Gunicorn:

```bash
# Install gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 api:app
```

### Security Considerations for API

⚠️ **Important for production:**

1. Configure file size limits
2. Validate file types
3. Implement authentication/authorization
4. Configure CORS for specific domains:
   ```python
   CORS(app, resources={r"/*": {"origins": "https://your-domain.com"}})
   ```
5. Use HTTPS
6. Implement rate limiting
7. Add request timeout limits

## How It Works

### Smart Page Alignment

The tool uses a content-similarity algorithm to intelligently align pages between documents:

1. **Text Extraction**: Extracts text from each page of both PDFs
2. **Similarity Scoring**: Calculates similarity between pages using sequence matching
3. **Lookahead Detection**: Looks ahead up to 3 pages to detect insertions/deletions
4. **Smart Alignment**:
   - Detects when pages are inserted in the modified PDF
   - Detects when pages are deleted from the original PDF
   - Properly aligns remaining pages after insertions/deletions
5. **Visual Highlighting**: Highlights text differences within aligned pages

### Example: Inserted Page

If you insert a page in the middle of a document:
- The inserted page is shown with a blank page on the left and labeled as "Added"
- All subsequent pages are correctly aligned (e.g., original page 6 → modified page 7)
- Pages are labeled as "Shifted" to indicate the alignment adjustment

## Project Structure

```
PDF-Compare/
├── api.py                  # REST API server
├── client-example.js       # JavaScript client examples (API usage)
├── compare_pdf.py          # Python CLI entry point
├── comparator.py           # Core comparison logic
├── main.py                 # GUI entry point
├── pdf-compare.js          # Node.js CLI wrapper
├── package.json            # Node.js package configuration
├── sample_files/           # Sample PDFs for testing
├── Dockerfile              # Docker configuration
└── README.md               # This file
```

## License

[MIT](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Troubleshooting

### Poppler not found
- **Windows**: Ensure Poppler's `bin` folder is in your System PATH
- **macOS/Linux**: Install poppler-utils via package manager

### API CORS errors
- The API has CORS enabled by default for development
- For production, configure CORS to allow only specific domains

### Large PDF files
- The default file size limit is ~16MB
- Configure Flask's `MAX_CONTENT_LENGTH` for larger files
- Consider using background tasks for very large PDFs

## Support

For issues, questions, or contributions, please visit the [GitHub repository](https://github.com/grananda/PDF-Compare).
