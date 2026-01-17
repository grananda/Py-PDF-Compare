/**
 * PDF Compare Client Examples
 *
 * Examples of how to call the PDF Compare API from JavaScript/Node.js
 */

// ============================================================
// Example 1: Browser JavaScript (using Fetch API)
// ============================================================

/**
 * Compare two PDF files from file inputs in the browser
 */
async function comparePDFsFromBrowser(fileA, fileB) {
    const formData = new FormData();
    formData.append('file_a', fileA);
    formData.append('file_b', fileB);
    formData.append('output_format', 'pdf'); // or 'json'

    try {
        const response = await fetch('http://localhost:5000/compare', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Comparison failed');
        }

        // Get the PDF blob
        const blob = await response.blob();

        // Download the PDF
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'comparison_report.pdf';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        console.log('Comparison completed successfully');
    } catch (error) {
        console.error('Error comparing PDFs:', error);
        throw error;
    }
}

/**
 * Compare PDFs and get JSON response
 */
async function comparePDFsGetJSON(fileA, fileB) {
    const formData = new FormData();
    formData.append('file_a', fileA);
    formData.append('file_b', fileB);
    formData.append('output_format', 'json');

    try {
        const response = await fetch('http://localhost:5000/compare', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Comparison failed');
        }

        const result = await response.json();
        console.log('Text differences:', result.text_differences);
        return result;
    } catch (error) {
        console.error('Error comparing PDFs:', error);
        throw error;
    }
}

/**
 * Compare PDFs from URLs
 */
async function comparePDFsFromURLs(urlA, urlB) {
    try {
        const response = await fetch('http://localhost:5000/compare-urls', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url_a: urlA,
                url_b: urlB,
                output_format: 'pdf'
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Comparison failed');
        }

        const blob = await response.blob();

        // Download the PDF
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'comparison_report.pdf';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        console.log('Comparison completed successfully');
    } catch (error) {
        console.error('Error comparing PDFs from URLs:', error);
        throw error;
    }
}

// ============================================================
// Example 2: Node.js (using axios and fs)
// ============================================================

/**
 * Compare two PDF files from Node.js
 *
 * Usage:
 *   npm install axios form-data
 *   node client-example.js
 */
async function comparePDFsFromNode(pathA, pathB, outputPath) {
    const axios = require('axios');
    const FormData = require('form-data');
    const fs = require('fs');

    const formData = new FormData();
    formData.append('file_a', fs.createReadStream(pathA));
    formData.append('file_b', fs.createReadStream(pathB));
    formData.append('output_format', 'pdf');

    try {
        const response = await axios.post('http://localhost:5000/compare', formData, {
            headers: formData.getHeaders(),
            responseType: 'arraybuffer'
        });

        // Save the PDF
        fs.writeFileSync(outputPath, response.data);
        console.log(`Comparison report saved to ${outputPath}`);
    } catch (error) {
        console.error('Error comparing PDFs:', error.response?.data || error.message);
        throw error;
    }
}

/**
 * Compare PDFs from URLs (Node.js)
 */
async function comparePDFsFromURLsNode(urlA, urlB, outputPath) {
    const axios = require('axios');
    const fs = require('fs');

    try {
        const response = await axios.post('http://localhost:5000/compare-urls', {
            url_a: urlA,
            url_b: urlB,
            output_format: 'pdf'
        }, {
            responseType: 'arraybuffer'
        });

        fs.writeFileSync(outputPath, response.data);
        console.log(`Comparison report saved to ${outputPath}`);
    } catch (error) {
        console.error('Error comparing PDFs:', error.response?.data || error.message);
        throw error;
    }
}

/**
 * Get JSON comparison results (Node.js)
 */
async function getComparisonJSON(pathA, pathB) {
    const axios = require('axios');
    const FormData = require('form-data');
    const fs = require('fs');

    const formData = new FormData();
    formData.append('file_a', fs.createReadStream(pathA));
    formData.append('file_b', fs.createReadStream(pathB));
    formData.append('output_format', 'json');

    try {
        const response = await axios.post('http://localhost:5000/compare', formData, {
            headers: formData.getHeaders()
        });

        console.log('Comparison results:', response.data);
        return response.data;
    } catch (error) {
        console.error('Error comparing PDFs:', error.response?.data || error.message);
        throw error;
    }
}

// ============================================================
// Example 3: HTML Form Example
// ============================================================

const htmlFormExample = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Comparison Tool</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="file"] {
            display: block;
            margin-bottom: 10px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        #status {
            margin-top: 20px;
            padding: 10px;
            border-radius: 5px;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <h1>PDF Comparison Tool</h1>

    <div class="form-group">
        <label for="fileA">Select First PDF (Original):</label>
        <input type="file" id="fileA" accept=".pdf" required>
    </div>

    <div class="form-group">
        <label for="fileB">Select Second PDF (Modified):</label>
        <input type="file" id="fileB" accept=".pdf" required>
    </div>

    <button id="compareBtn">Compare PDFs</button>

    <div id="status"></div>

    <script>
        document.getElementById('compareBtn').addEventListener('click', async () => {
            const fileA = document.getElementById('fileA').files[0];
            const fileB = document.getElementById('fileB').files[0];
            const statusDiv = document.getElementById('status');
            const compareBtn = document.getElementById('compareBtn');

            if (!fileA || !fileB) {
                statusDiv.className = 'error';
                statusDiv.textContent = 'Please select both PDF files';
                return;
            }

            const formData = new FormData();
            formData.append('file_a', fileA);
            formData.append('file_b', fileB);
            formData.append('output_format', 'pdf');

            try {
                compareBtn.disabled = true;
                statusDiv.className = '';
                statusDiv.textContent = 'Comparing PDFs...';

                const response = await fetch('http://localhost:5000/compare', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Comparison failed');
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'comparison_report.pdf';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                statusDiv.className = 'success';
                statusDiv.textContent = 'Comparison completed! Report downloaded.';
            } catch (error) {
                statusDiv.className = 'error';
                statusDiv.textContent = 'Error: ' + error.message;
            } finally {
                compareBtn.disabled = false;
            }
        });
    </script>
</body>
</html>
`;

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        comparePDFsFromNode,
        comparePDFsFromURLsNode,
        getComparisonJSON
    };
}

// Example usage in Node.js
if (require.main === module) {
    // Uncomment to test:
    // comparePDFsFromNode('./sample_files/original.pdf', './sample_files/modified.pdf', './output.pdf');
    console.log('PDF Compare Client Examples');
    console.log('See code for usage examples');
}