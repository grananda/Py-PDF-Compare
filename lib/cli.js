#!/usr/bin/env node

/**
 * PDF-Compare CLI
 *
 * Command-line interface for comparing PDF files.
 *
 * Usage:
 *   pdf-compare <file_a> <file_b> [-o output.pdf]
 *   pdf-compare --check
 *   pdf-compare --setup
 *   pdf-compare --version
 */

const path = require('path');
const fs = require('fs');
const { comparePDFs, checkDependencies, runSetup, getVersion, printPopplerInstructions } = require('./index');

/**
 * Parse command line arguments
 */
function parseArgs(argv) {
    const args = {
        fileA: null,
        fileB: null,
        output: 'report.pdf',
        help: false,
        version: false,
        check: false,
        setup: false,
        force: false
    };

    const positional = [];

    for (let i = 0; i < argv.length; i++) {
        const arg = argv[i];

        switch (arg) {
            case '-h':
            case '--help':
                args.help = true;
                break;
            case '-v':
            case '--version':
                args.version = true;
                break;
            case '-o':
            case '--output':
                args.output = argv[++i];
                break;
            case '--check':
                args.check = true;
                break;
            case '--setup':
                args.setup = true;
                break;
            case '--force':
                args.force = true;
                break;
            default:
                if (!arg.startsWith('-')) {
                    positional.push(arg);
                }
        }
    }

    if (positional.length >= 1) args.fileA = positional[0];
    if (positional.length >= 2) args.fileB = positional[1];

    return args;
}

/**
 * Print help message
 */
function printHelp() {
    console.log(`
PDF-Compare v${getVersion()}
Compare two PDF files and generate a visual diff report.

USAGE:
  pdf-compare <file_a> <file_b> [options]
  pdf-compare --check
  pdf-compare --setup [--force]

ARGUMENTS:
  file_a              Path to the first PDF file (Original)
  file_b              Path to the second PDF file (Modified)

OPTIONS:
  -o, --output PATH   Output report path (default: report.pdf)
  -h, --help          Show this help message
  -v, --version       Show version number
  --check             Check if dependencies are installed
  --setup             Run Python environment setup
  --force             Force reinstall (with --setup)

EXAMPLES:
  # Compare two PDFs
  pdf-compare original.pdf modified.pdf -o diff.pdf

  # Check dependencies
  pdf-compare --check

  # Run setup manually
  pdf-compare --setup

REQUIREMENTS:
  - Python 3.12 or higher
  - Poppler (for PDF to image conversion)

For more information, visit: https://github.com/grananda/PDF-Compare
`);
}

/**
 * Check and display dependency status
 */
function checkAndDisplay() {
    const status = checkDependencies();

    console.log('\nPDF-Compare Dependency Status:\n');
    console.log(`  Python environment: ${status.python ? '✓ Ready' : '✗ Not configured'}`);
    if (status.pythonPath) {
        console.log(`    Path: ${status.pythonPath}`);
    }
    console.log(`  Poppler:            ${status.poppler ? '✓ Found' : '✗ Not found'}`);
    if (status.popplerPath) {
        console.log(`    Path: ${status.popplerPath}`);
    }
    console.log('');

    if (status.ready) {
        console.log('✅ All dependencies are ready!\n');
        return true;
    } else {
        if (!status.python) {
            console.log('Run "pdf-compare --setup" to configure Python environment.\n');
        }
        if (!status.poppler) {
            printPopplerInstructions();
        }
        return false;
    }
}

/**
 * Main CLI entry point
 */
async function main() {
    const args = parseArgs(process.argv.slice(2));

    // Handle version
    if (args.version) {
        console.log(getVersion());
        process.exit(0);
    }

    // Handle help
    if (args.help) {
        printHelp();
        process.exit(0);
    }

    // Handle check
    if (args.check) {
        const ready = checkAndDisplay();
        process.exit(ready ? 0 : 1);
    }

    // Handle setup
    if (args.setup) {
        try {
            console.log('\nRunning PDF-Compare setup...\n');
            await runSetup({ force: args.force, quiet: false });
            console.log('\n✅ Setup complete!\n');
            process.exit(0);
        } catch (error) {
            console.error(`\n❌ Setup failed: ${error.message}\n`);
            process.exit(1);
        }
    }

    // Require files for comparison
    if (!args.fileA || !args.fileB) {
        console.error('Error: Both file_a and file_b are required.\n');
        console.error('Usage: pdf-compare <file_a> <file_b> [-o output.pdf]');
        console.error('       pdf-compare --help for more information\n');
        process.exit(1);
    }

    // Check dependencies before comparison
    const status = checkDependencies();
    if (!status.ready) {
        console.error('Error: Dependencies not configured.\n');
        checkAndDisplay();
        process.exit(1);
    }

    // Validate input files
    if (!fs.existsSync(args.fileA)) {
        console.error(`Error: File not found: ${path.resolve(args.fileA)}`);
        process.exit(1);
    }
    if (!fs.existsSync(args.fileB)) {
        console.error(`Error: File not found: ${path.resolve(args.fileB)}`);
        process.exit(1);
    }

    // Run comparison
    try {
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

// Run CLI if executed directly
if (require.main === module) {
    main().catch((error) => {
        console.error(`Fatal error: ${error.message}`);
        process.exit(1);
    });
}

module.exports = { main, parseArgs };
