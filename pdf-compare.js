#!/usr/bin/env node

/**
 * PDF Compare - Node.js CLI Wrapper
 *
 * A Node.js module that calls the Python compare_pdf.py script directly.
 * Provides both a programmatic API and CLI interface.
 *
 * Usage (CLI):
 *   node pdf-compare.js original.pdf modified.pdf -o report.pdf
 *
 * Usage (Programmatic):
 *   const { comparePDFs } = require('./pdf-compare');
 *   const result = await comparePDFs('original.pdf', 'modified.pdf', 'output.pdf');
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * Default options for PDF comparison
 */DEFAULT_OPTIONS = {
    pythonPath: null,  // Auto-detect if null
    cwd: null,         // Use script directory if null
    timeout: 60000     // 60 seconds default timeout
};

/**
 * Find available Python executable
 * Tries python3, python, and py (Windows) in order
 *
 * @param {string|null} preferredPath - Preferred Python path to try first
 * @returns {Promise<string>} - Path to Python executable
 */
async function findPython(preferredPath = null) {
    const candidates = preferredPath
        ? [preferredPath, 'python3', 'python', 'py']
        : ['python3', 'python', 'py'];

    for (const candidate of candidates) {
        try {
            const result = await new Promise((resolve, reject) => {
                const proc = spawn(candidate, ['--version'], {
                    stdio: ['pipe', 'pipe', 'pipe'],
                    shell: process.platform === 'win32'
                });

                let stdout = '';
                let stderr = '';

                proc.stdout.on('data', (data) => { stdout += data.toString(); });
                proc.stderr.on('data', (data) => { stderr += data.toString(); });

                proc.on('close', (code) => {
                    if (code === 0) {
                        resolve({ candidate, version: (stdout || stderr).trim() });
                    } else {
                        reject(new Error(`Exit code ${code}`));
                    }
                });

                proc.on('error', reject);
            });

            return result.candidate;
        } catch {
            // Try next candidate
            continue;
        }
    }

    throw new Error(
        'Python not found. Please install Python 3 or specify pythonPath option.\n' +
        'Tried: ' + candidates.join(', ')
    );
}

/**
 * Compare two PDF files and generate a visual diff report
 *
 * @param {string} fileA - Path to the first PDF file (Original)
 * @param {string} fileB - Path to the second PDF file (Modified)
 * @param {string} output - Path to save the output report
 * @param {Object} options - Optional configuration
 * @param {string|null} options.pythonPath - Path to Python executable (auto-detect if null)
 * @param {string|null} options.cwd - Working directory (script directory if null)
 * @param {number} options.timeout - Timeout in milliseconds (default: 60000)
 * @returns {Promise<{success: boolean, output: string, pageCount: number|null}>}
 */
async function comparePDFs(fileA, fileB, output, options = {}) {
    const opts = { ...DEFAULT_OPTIONS, ...options };

    // Resolve paths
    const resolvedFileA = path.resolve(fileA);
    const resolvedFileB = path.resolve(fileB);
    const resolvedOutput = path.resolve(output);

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

    // Find Python executable
    const pythonPath = await findPython(opts.pythonPath);

    // Get script directory
    const scriptDir = opts.cwd || __dirname;
    const comparePdfScript = path.join(scriptDir, 'compare_pdf.py');

    if (!fs.existsSync(comparePdfScript)) {
        throw new Error(`compare_pdf.py not found in ${scriptDir}`);
    }

    return new Promise((resolve, reject) => {
        const args = [comparePdfScript, resolvedFileA, resolvedFileB, '-o', resolvedOutput];

        const proc = spawn(pythonPath, args, {
            cwd: scriptDir,
            stdio: ['pipe', 'pipe', 'pipe'],
            shell: process.platform === 'win32'
        });

        let stdout = '';
        let stderr = '';
        let timedOut = false;

        // Set timeout
        const timer = setTimeout(() => {
            timedOut = true;
            proc.kill('SIGTERM');
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
                reject(new Error(`Comparison timed out after ${opts.timeout}ms`));
                return;
            }

            const combinedOutput = stdout + stderr;

            if (code !== 0) {
                reject(new Error(`Comparison failed (exit code ${code}): ${combinedOutput}`));
                return;
            }

            // Parse page count from output
            let pageCount = null;
            const pageMatch = combinedOutput.match(/Report generated with (\d+) page/);
            if (pageMatch) {
                pageCount = parseInt(pageMatch[1], 10);
            }

            // Check for "no differences" case
            const noDifferences = combinedOutput.includes('No visual differences found');

            resolve({
                success: true,
                output: combinedOutput.trim(),
                pageCount: noDifferences ? 0 : pageCount,
                reportPath: noDifferences ? null : resolvedOutput
            });
        });

        proc.on('error', (err) => {
            clearTimeout(timer);
            reject(new Error(`Failed to start Python process: ${err.message}`));
        });
    });
}

/**
 * CLI argument parser
 */
function parseArgs(args) {
    const result = {
        fileA: null,
        fileB: null,
        output: 'report.pdf',
        help: false
    };

    const positional = [];

    for (let i = 0; i < args.length; i++) {
        const arg = args[i];

        if (arg === '-h' || arg === '--help') {
            result.help = true;
        } else if (arg === '-o' || arg === '--output') {
            result.output = args[++i];
        } else if (!arg.startsWith('-')) {
            positional.push(arg);
        }
    }

    if (positional.length >= 1) result.fileA = positional[0];
    if (positional.length >= 2) result.fileB = positional[1];

    return result;
}

/**
 * Print CLI usage
 */
function printUsage() {
    console.log(`
PDF Compare - Node.js CLI Wrapper

Usage:
  pdf-compare <file_a> <file_b> [options]

Arguments:
  file_a              Path to the first PDF file (Original)
  file_b              Path to the second PDF file (Modified)

Options:
  -o, --output PATH   Path to save the output report (default: report.pdf)
  -h, --help          Show this help message

Examples:
  pdf-compare original.pdf modified.pdf
  pdf-compare original.pdf modified.pdf -o diff.pdf
  node pdf-compare.js doc1.pdf doc2.pdf --output comparison.pdf

Programmatic Usage:
  const { comparePDFs } = require('./pdf-compare');
  const result = await comparePDFs('original.pdf', 'modified.pdf', 'output.pdf');
`);
}

/**
 * CLI entry point
 */
async function main() {
    const args = parseArgs(process.argv.slice(2));

    if (args.help) {
        printUsage();
        process.exit(0);
    }

    if (!args.fileA || !args.fileB) {
        console.error('Error: Both file_a and file_b are required.\n');
        printUsage();
        process.exit(1);
    }

    try {
        // Validate files exist before starting
        if (!fs.existsSync(args.fileA)) {
            throw new Error(`File not found: ${path.resolve(args.fileA)}`);
        }
        if (!fs.existsSync(args.fileB)) {
            throw new Error(`File not found: ${path.resolve(args.fileB)}`);
        }

        console.log(`Comparing '${args.fileA}' and '${args.fileB}'...`);
        const result = await comparePDFs(args.fileA, args.fileB, args.output);

        if (result.pageCount === 0) {
            console.log('No visual differences found.');
        } else {
            console.log(`Report generated with ${result.pageCount} page(s).`);
            console.log(`Report saved to '${result.reportPath}'`);
        }

        process.exit(0);
    } catch (error) {
        console.error(`Error: ${error.message}`);
        process.exit(1);
    }
}

// Export for programmatic use
module.exports = {
    comparePDFs,
    findPython,
    DEFAULT_OPTIONS
};

// Run CLI if executed directly
if (require.main === module) {
    main();
}
