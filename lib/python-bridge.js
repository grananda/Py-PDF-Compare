/**
 * Python Bridge Module
 *
 * Handles communication between Node.js and Python scripts for PDF comparison.
 * Manages subprocess spawning, error handling, and result parsing.
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { getVenvPython, checkSetup, PYTHON_DIR } = require('./setup');

/**
 * Default options for Python execution
 */
const DEFAULT_OPTIONS = {
    timeout: 120000, // 2 minutes default timeout
    pythonPath: null, // Auto-detect from venv if null
};

/**
 * Execute a Python script with arguments
 * @param {string} scriptName - Name of the Python script (without path)
 * @param {string[]} args - Arguments to pass to the script
 * @param {Object} options - Execution options
 * @param {string|null} options.pythonPath - Custom Python path (uses venv if null)
 * @param {number} options.timeout - Timeout in milliseconds
 * @param {string} options.cwd - Working directory
 * @returns {Promise<{stdout: string, stderr: string, code: number}>}
 */
async function executePython(scriptName, args = [], options = {}) {
    const opts = { ...DEFAULT_OPTIONS, ...options };

    // Determine Python path
    let pythonPath = opts.pythonPath;
    if (!pythonPath) {
        const status = checkSetup();
        if (!status.python) {
            throw new Error(
                'Python environment not set up. Run "npx pdf-compare-setup" to configure.'
            );
        }
        pythonPath = status.pythonPath;
    }

    // Resolve script path
    const scriptPath = path.join(PYTHON_DIR, scriptName);
    if (!fs.existsSync(scriptPath)) {
        throw new Error(`Python script not found: ${scriptPath}`);
    }

    return new Promise((resolve, reject) => {
        const fullArgs = [scriptPath, ...args];
        let timedOut = false;

        const proc = spawn(pythonPath, fullArgs, {
            cwd: opts.cwd || PYTHON_DIR,
            stdio: ['pipe', 'pipe', 'pipe'],
            shell: process.platform === 'win32'
        });

        let stdout = '';
        let stderr = '';

        // Set timeout
        const timer = setTimeout(() => {
            timedOut = true;
            proc.kill('SIGTERM');
            // Force kill after 5 seconds if still running
            setTimeout(() => {
                if (!proc.killed) {
                    proc.kill('SIGKILL');
                }
            }, 5000);
        }, opts.timeout);

        proc.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        proc.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        proc.on('close', (code) => {
            clearTimeout(timer);

            if (timedOut) {
                reject(new Error(`Python script timed out after ${opts.timeout}ms`));
                return;
            }

            resolve({
                stdout: stdout.trim(),
                stderr: stderr.trim(),
                code: code || 0
            });
        });

        proc.on('error', (err) => {
            clearTimeout(timer);
            reject(new Error(`Failed to execute Python: ${err.message}`));
        });
    });
}

/**
 * Compare two PDFs using the Python comparator
 * @param {string} fileA - Path to the first PDF file (Original)
 * @param {string} fileB - Path to the second PDF file (Modified)
 * @param {string} outputPath - Path to save the output report
 * @param {Object} options - Comparison options
 * @returns {Promise<{success: boolean, pageCount: number|null, reportPath: string|null, output: string}>}
 */
async function comparePDFs(fileA, fileB, outputPath, options = {}) {
    // Resolve paths to absolute
    const resolvedFileA = path.resolve(fileA);
    const resolvedFileB = path.resolve(fileB);
    const resolvedOutput = path.resolve(outputPath);

    // Validate input files exist
    if (!fs.existsSync(resolvedFileA)) {
        throw new Error(`File not found: ${resolvedFileA}`);
    }
    if (!fs.existsSync(resolvedFileB)) {
        throw new Error(`File not found: ${resolvedFileB}`);
    }

    // Ensure output directory exists
    const outputDir = path.dirname(resolvedOutput);
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    // Execute comparison
    const result = await executePython('compare_pdf.py', [
        resolvedFileA,
        resolvedFileB,
        '-o',
        resolvedOutput
    ], options);

    const combinedOutput = [result.stdout, result.stderr].filter(Boolean).join('\n');

    if (result.code !== 0) {
        throw new Error(`PDF comparison failed (exit code ${result.code}): ${combinedOutput}`);
    }

    // Parse output
    let pageCount = null;
    const pageMatch = combinedOutput.match(/Report generated with (\d+) page/);
    if (pageMatch) {
        pageCount = parseInt(pageMatch[1], 10);
    }

    const noDifferences = combinedOutput.includes('No visual differences found');

    return {
        success: true,
        pageCount: noDifferences ? 0 : pageCount,
        reportPath: noDifferences ? null : resolvedOutput,
        output: combinedOutput
    };
}

/**
 * Compare two PDFs from Buffer data
 * @param {Buffer} bufferA - First PDF as Buffer
 * @param {Buffer} bufferB - Second PDF as Buffer
 * @param {Object} options - Comparison options
 * @returns {Promise<{success: boolean, pageCount: number|null, reportBuffer: Buffer|null, output: string}>}
 */
async function comparePDFsFromBuffer(bufferA, bufferB, options = {}) {
    const os = require('os');
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pdf-compare-'));

    const tempFileA = path.join(tmpDir, 'input_a.pdf');
    const tempFileB = path.join(tmpDir, 'input_b.pdf');
    const tempOutput = path.join(tmpDir, 'output.pdf');

    try {
        // Write buffers to temp files
        fs.writeFileSync(tempFileA, bufferA);
        fs.writeFileSync(tempFileB, bufferB);

        // Compare
        const result = await comparePDFs(tempFileA, tempFileB, tempOutput, options);

        // Read output if it exists
        let reportBuffer = null;
        if (result.reportPath && fs.existsSync(result.reportPath)) {
            reportBuffer = fs.readFileSync(result.reportPath);
        }

        return {
            success: result.success,
            pageCount: result.pageCount,
            reportBuffer,
            output: result.output
        };

    } finally {
        // Cleanup temp files
        try {
            fs.rmSync(tmpDir, { recursive: true, force: true });
        } catch {
            // Ignore cleanup errors
        }
    }
}

module.exports = {
    executePython,
    comparePDFs,
    comparePDFsFromBuffer,
    DEFAULT_OPTIONS
};
