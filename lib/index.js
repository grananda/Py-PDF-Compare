/**
 * PDF-Compare - Node.js API
 *
 * Compare two PDF files and generate a visual diff report.
 *
 * @example
 * const pdfCompare = require('pdf-compare');
 *
 * // Check dependencies
 * const status = pdfCompare.checkDependencies();
 * console.log(status.ready); // true if everything is set up
 *
 * // Compare PDFs
 * const result = await pdfCompare.comparePDFs('a.pdf', 'b.pdf', 'output.pdf');
 */

const { comparePDFs, comparePDFsFromBuffer } = require('./python-bridge');
const { setup, checkSetup, checkPoppler, printPopplerInstructions } = require('./setup');
const path = require('path');
const fs = require('fs');

/**
 * Package version
 */
const version = (() => {
    try {
        const pkg = require('../package.json');
        return pkg.version;
    } catch {
        return '0.0.0';
    }
})();

/**
 * Check if all dependencies are ready
 * @returns {{ready: boolean, python: boolean, poppler: boolean, pythonPath: string|null, popplerPath: string|null}}
 */
function checkDependencies() {
    return checkSetup();
}

/**
 * Get package version
 * @returns {string}
 */
function getVersion() {
    return version;
}

/**
 * Run setup to configure Python environment
 * @param {Object} options
 * @param {boolean} options.force - Force reinstall
 * @param {boolean} options.quiet - Suppress output
 * @returns {Promise<{success: boolean, venvPath: string, pythonPath: string, poppler: {available: boolean, path: string|null}}>}
 */
async function runSetup(options = {}) {
    return setup(options);
}

module.exports = {
    // Core comparison functions
    comparePDFs,
    comparePDFsFromBuffer,

    // Setup and utilities
    checkDependencies,
    runSetup,
    getVersion,

    // Re-export for advanced usage
    setup,
    checkSetup,
    checkPoppler,
    printPopplerInstructions
};
