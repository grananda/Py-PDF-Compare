/**
 * PDF-Compare TypeScript Definitions
 */

/**
 * Dependency status returned by checkDependencies()
 */
export interface DependencyStatus {
    /** Whether all dependencies are ready for use */
    ready: boolean;
    /** Whether Python environment is configured */
    python: boolean;
    /** Whether virtual environment exists */
    venv: boolean;
    /** Whether Poppler is available */
    poppler: boolean;
    /** Path to Python executable (null if not configured) */
    pythonPath: string | null;
    /** Path to Poppler binaries (null if not found) */
    popplerPath: string | null;
}

/**
 * Result of a PDF comparison
 */
export interface CompareResult {
    /** Whether comparison completed successfully */
    success: boolean;
    /** Number of pages in the report (0 if no differences, null if error) */
    pageCount: number | null;
    /** Absolute path to the generated report (null if no differences) */
    reportPath: string | null;
    /** Raw output from the comparison process */
    output: string;
}

/**
 * Result of a buffer-based PDF comparison
 */
export interface CompareBufferResult {
    /** Whether comparison completed successfully */
    success: boolean;
    /** Number of pages in the report (0 if no differences, null if error) */
    pageCount: number | null;
    /** The generated report as a Uint8Array (null if no differences) */
    reportBuffer: Uint8Array | null;
    /** Raw output from the comparison process */
    output: string;
}

/**
 * Options for PDF comparison
 */
export interface CompareOptions {
    /** Custom Python executable path (uses venv if not specified) */
    pythonPath?: string;
    /** Timeout in milliseconds (default: 120000) */
    timeout?: number;
    /** Working directory for Python execution */
    cwd?: string;
}

/**
 * Setup options
 */
export interface SetupOptions {
    /** Force reinstall even if environment exists */
    force?: boolean;
    /** Suppress console output */
    quiet?: boolean;
}

/**
 * Result of setup operation
 */
export interface SetupResult {
    /** Whether setup completed successfully */
    success: boolean;
    /** Path to the virtual environment */
    venvPath: string;
    /** Path to Python executable in venv */
    pythonPath: string;
    /** Poppler availability status */
    poppler: {
        available: boolean;
        path: string | null;
    };
}

/**
 * Compare two PDF files and generate a visual diff report
 *
 * @param fileA - Path to the first PDF file (Original)
 * @param fileB - Path to the second PDF file (Modified)
 * @param outputPath - Path to save the output report
 * @param options - Comparison options
 * @returns Promise resolving to comparison result
 *
 * @example
 * ```typescript
 * const result = await comparePDFs('original.pdf', 'modified.pdf', 'diff.pdf');
 * if (result.pageCount === 0) {
 *   console.log('No differences found');
 * } else {
 *   console.log(`Report saved to: ${result.reportPath}`);
 * }
 * ```
 */
export function comparePDFs(
    fileA: string,
    fileB: string,
    outputPath: string,
    options?: CompareOptions
): Promise<CompareResult>;

/**
 * Compare two PDFs from Uint8Array data
 *
 * @param bufferA - First PDF as Uint8Array
 * @param bufferB - Second PDF as Uint8Array
 * @param options - Comparison options
 * @returns Promise resolving to comparison result with Uint8Array output
 *
 * @example
 * ```typescript
 * const pdfA = fs.readFileSync('original.pdf');
 * const pdfB = fs.readFileSync('modified.pdf');
 * const result = await comparePDFsFromBuffer(pdfA, pdfB);
 * if (result.reportBuffer) {
 *   fs.writeFileSync('diff.pdf', result.reportBuffer);
 * }
 * ```
 */
export function comparePDFsFromBuffer(
    bufferA: Uint8Array,
    bufferB: Uint8Array,
    options?: CompareOptions
): Promise<CompareBufferResult>;

/**
 * Check if all dependencies are ready
 *
 * @returns Dependency status object
 *
 * @example
 * ```typescript
 * const status = checkDependencies();
 * if (!status.ready) {
 *   console.log('Please run: npx pdf-compare --setup');
 * }
 * ```
 */
export function checkDependencies(): DependencyStatus;

/**
 * Run setup to configure Python environment
 *
 * @param options - Setup options
 * @returns Promise resolving to setup result
 *
 * @example
 * ```typescript
 * await runSetup({ force: true });
 * ```
 */
export function runSetup(options?: SetupOptions): Promise<SetupResult>;

/**
 * Get package version
 *
 * @returns Version string (e.g., "1.0.0")
 */
export function getVersion(): string;

/**
 * Run Python environment setup (alias for runSetup)
 */
export function setup(options?: SetupOptions): Promise<SetupResult>;

/**
 * Check setup status (alias for checkDependencies)
 */
export function checkSetup(): DependencyStatus;

/**
 * Check Poppler availability
 *
 * @returns Object with available boolean and path
 */
export function checkPoppler(): { available: boolean; path: string | null };

/**
 * Print Poppler installation instructions to console
 */
export function printPopplerInstructions(): void;
