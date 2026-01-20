/**
 * Python Environment Setup Module
 *
 * Handles automatic Python virtual environment creation and dependency installation
 * for the pdf-compare npm package.
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Package root directory (where node_modules/pdf-compare lives after install)
const PACKAGE_ROOT = path.resolve(__dirname, '..');
const VENV_DIR = path.join(PACKAGE_ROOT, '.venv');
const PYTHON_DIR = path.join(PACKAGE_ROOT, 'python');
const REQUIREMENTS_FILE = path.join(PYTHON_DIR, 'requirements.txt');

// Minimum Python version required
const MIN_PYTHON_VERSION = { major: 3, minor: 12 };

/**
 * Parse Python version string into components
 * @param {string} versionStr - Version string like "Python 3.12.0"
 * @returns {{major: number, minor: number, patch: number} | null}
 */
function parsePythonVersion(versionStr) {
    const match = versionStr.match(/Python\s+(\d+)\.(\d+)\.(\d+)/i);
    if (!match) return null;
    return {
        major: parseInt(match[1], 10),
        minor: parseInt(match[2], 10),
        patch: parseInt(match[3], 10)
    };
}

/**
 * Check if Python version meets minimum requirements
 * @param {{major: number, minor: number}} version
 * @returns {boolean}
 */
function isVersionSufficient(version) {
    if (version.major > MIN_PYTHON_VERSION.major) return true;
    if (version.major < MIN_PYTHON_VERSION.major) return false;
    return version.minor >= MIN_PYTHON_VERSION.minor;
}

/**
 * Find Python executable that meets version requirements
 * @returns {Promise<{path: string, version: string} | null>}
 */
async function findPython() {
    const isWindows = process.platform === 'win32';
    const candidates = isWindows
        ? ['python', 'python3', 'py -3']
        : ['python3', 'python'];

    for (const candidate of candidates) {
        try {
            const versionOutput = execSync(`${candidate} --version`, {
                encoding: 'utf8',
                stdio: ['pipe', 'pipe', 'pipe']
            }).trim();

            const version = parsePythonVersion(versionOutput);
            if (version && isVersionSufficient(version)) {
                // For 'py -3', we need to return just 'py' with args later
                const pythonPath = candidate === 'py -3' ? 'py' : candidate;
                return {
                    path: pythonPath,
                    version: versionOutput,
                    usePyLauncher: candidate === 'py -3'
                };
            }
        } catch {
            // Candidate not found or errored, try next
            continue;
        }
    }

    return null;
}

/**
 * Get the Python executable path within the virtual environment
 * @returns {string}
 */
function getVenvPython() {
    const isWindows = process.platform === 'win32';
    return isWindows
        ? path.join(VENV_DIR, 'Scripts', 'python.exe')
        : path.join(VENV_DIR, 'bin', 'python');
}

/**
 * Get the pip executable path within the virtual environment
 * @returns {string}
 */
function getVenvPip() {
    const isWindows = process.platform === 'win32';
    return isWindows
        ? path.join(VENV_DIR, 'Scripts', 'pip.exe')
        : path.join(VENV_DIR, 'bin', 'pip');
}

/**
 * Check if virtualenv already exists and is valid
 * @returns {boolean}
 */
function isVenvValid() {
    const venvPython = getVenvPython();
    if (!fs.existsSync(venvPython)) return false;

    try {
        execSync(`"${venvPython}" --version`, {
            encoding: 'utf8',
            stdio: ['pipe', 'pipe', 'pipe']
        });
        return true;
    } catch {
        return false;
    }
}

/**
 * Create Python virtual environment
 * @param {string} pythonPath - Path to system Python
 * @param {boolean} usePyLauncher - Whether to use py launcher
 * @returns {Promise<void>}
 */
async function createVenv(pythonPath, usePyLauncher = false) {
    return new Promise((resolve, reject) => {
        const args = usePyLauncher
            ? ['-3', '-m', 'venv', VENV_DIR]
            : ['-m', 'venv', VENV_DIR];

        console.log(`Creating virtual environment in ${VENV_DIR}...`);

        const proc = spawn(pythonPath, args, {
            stdio: 'inherit',
            shell: process.platform === 'win32'
        });

        proc.on('close', (code) => {
            if (code === 0) {
                resolve();
            } else {
                reject(new Error(`Failed to create virtual environment (exit code ${code})`));
            }
        });

        proc.on('error', reject);
    });
}

/**
 * Install Python dependencies from requirements.txt
 * @returns {Promise<void>}
 */
async function installDependencies() {
    return new Promise((resolve, reject) => {
        const venvPython = getVenvPython();

        if (!fs.existsSync(REQUIREMENTS_FILE)) {
            reject(new Error(`requirements.txt not found at ${REQUIREMENTS_FILE}`));
            return;
        }

        console.log('Installing Python dependencies...');

        const proc = spawn(venvPython, ['-m', 'pip', 'install', '-r', REQUIREMENTS_FILE, '--quiet'], {
            stdio: 'inherit',
            shell: process.platform === 'win32'
        });

        proc.on('close', (code) => {
            if (code === 0) {
                resolve();
            } else {
                reject(new Error(`Failed to install dependencies (exit code ${code})`));
            }
        });

        proc.on('error', reject);
    });
}

/**
 * Check if Poppler is available
 * @returns {{available: boolean, path: string | null}}
 */
function checkPoppler() {
    const isWindows = process.platform === 'win32';
    const pdftoppm = isWindows ? 'pdftoppm.exe' : 'pdftoppm';

    // Check common paths
    const commonPaths = isWindows
        ? [
            'C:\\poppler-25.11.0\\Library\\bin',
            'C:\\poppler-24.08.0\\Library\\bin',
            'C:\\Program Files\\poppler\\Library\\bin',
            'C:\\Program Files (x86)\\poppler\\Library\\bin'
        ]
        : process.platform === 'darwin'
            ? ['/opt/homebrew/bin', '/usr/local/bin']
            : ['/usr/bin', '/usr/local/bin'];

    for (const dir of commonPaths) {
        const fullPath = path.join(dir, pdftoppm);
        if (fs.existsSync(fullPath)) {
            return { available: true, path: dir };
        }
    }

    // Check PATH
    try {
        const which = isWindows ? 'where' : 'which';
        const result = execSync(`${which} pdftoppm`, {
            encoding: 'utf8',
            stdio: ['pipe', 'pipe', 'pipe']
        }).trim();

        if (result) {
            return { available: true, path: path.dirname(result.split('\n')[0]) };
        }
    } catch {
        // Not in PATH
    }

    return { available: false, path: null };
}

/**
 * Print Poppler installation instructions
 */
function printPopplerInstructions() {
    console.log('\n⚠️  Poppler is not installed or not in PATH.');
    console.log('Poppler is required for PDF to image conversion.\n');

    switch (process.platform) {
        case 'win32':
            console.log('Windows installation:');
            console.log('  1. Download from: https://github.com/oschwartz10612/poppler-windows/releases');
            console.log('  2. Extract to C:\\poppler-xx.xx.x\\');
            console.log('  3. Add C:\\poppler-xx.xx.x\\Library\\bin to your PATH');
            break;
        case 'darwin':
            console.log('macOS installation:');
            console.log('  brew install poppler');
            break;
        default:
            console.log('Linux installation:');
            console.log('  Ubuntu/Debian: sudo apt install poppler-utils');
            console.log('  Fedora/RHEL:   sudo dnf install poppler-utils');
            console.log('  Arch:          sudo pacman -S poppler');
    }
    console.log('');
}

/**
 * Full setup process - creates venv and installs dependencies
 * @param {Object} options
 * @param {boolean} options.force - Force reinstall even if venv exists
 * @param {boolean} options.quiet - Suppress output
 * @returns {Promise<{success: boolean, venvPath: string, pythonPath: string, poppler: {available: boolean, path: string | null}}>}
 */
async function setup(options = {}) {
    const { force = false, quiet = false } = options;

    const log = quiet ? () => {} : console.log;

    // Check for existing valid venv
    if (!force && isVenvValid()) {
        const poppler = checkPoppler();
        log('✓ Virtual environment already exists and is valid.');

        if (!poppler.available) {
            printPopplerInstructions();
        }

        return {
            success: true,
            venvPath: VENV_DIR,
            pythonPath: getVenvPython(),
            poppler
        };
    }

    // Find system Python
    log('Checking Python installation...');
    const python = await findPython();

    if (!python) {
        const error = new Error(
            `Python ${MIN_PYTHON_VERSION.major}.${MIN_PYTHON_VERSION.minor}+ is required but not found.\n` +
            'Please install Python from https://www.python.org/downloads/'
        );
        error.code = 'PYTHON_NOT_FOUND';
        throw error;
    }

    log(`✓ Found ${python.version}`);

    // Remove existing venv if force
    if (force && fs.existsSync(VENV_DIR)) {
        log('Removing existing virtual environment...');
        fs.rmSync(VENV_DIR, { recursive: true, force: true });
    }

    // Create virtual environment
    await createVenv(python.path, python.usePyLauncher);
    log('✓ Virtual environment created.');

    // Install dependencies
    await installDependencies();
    log('✓ Python dependencies installed.');

    // Check Poppler
    const poppler = checkPoppler();
    if (poppler.available) {
        log(`✓ Poppler found at ${poppler.path}`);
    } else {
        printPopplerInstructions();
    }

    return {
        success: true,
        venvPath: VENV_DIR,
        pythonPath: getVenvPython(),
        poppler
    };
}

/**
 * Check if setup is complete
 * @returns {{ready: boolean, python: boolean, venv: boolean, poppler: boolean, pythonPath: string | null}}
 */
function checkSetup() {
    const venvValid = isVenvValid();
    const poppler = checkPoppler();

    return {
        ready: venvValid && poppler.available,
        python: venvValid,
        venv: venvValid,
        poppler: poppler.available,
        pythonPath: venvValid ? getVenvPython() : null,
        popplerPath: poppler.path
    };
}

module.exports = {
    setup,
    checkSetup,
    findPython,
    isVenvValid,
    getVenvPython,
    getVenvPip,
    checkPoppler,
    printPopplerInstructions,
    PACKAGE_ROOT,
    VENV_DIR,
    PYTHON_DIR,
    MIN_PYTHON_VERSION
};
