#!/usr/bin/env python3
"""
Build script for creating Linux executable using PyInstaller.

Usage:
    uv run python scripts/build_linux.py

This creates a standalone executable file in the dist/ folder that can be
distributed to users without requiring Python installation.

Uses PyMuPDF for vector-based PDF processing (no external dependencies needed).
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path


def find_tcl_tk_libs():
    """Find Tcl/Tk libraries in the Python installation."""
    # Get the Python installation's lib directory
    # Use base_prefix to get the actual Python installation (not the venv)
    python_prefix = Path(sys.base_prefix)
    lib_dir = python_prefix / "lib"

    tcl_tk_binaries = []
    tcl_tk_data = []

    if lib_dir.exists():
        # Find .so files for Tcl/Tk
        for pattern in ["libtcl*.so*", "libtk*.so*"]:
            for lib_file in lib_dir.glob(pattern):
                if lib_file.is_file():
                    tcl_tk_binaries.append(lib_file)

        # Find Tcl/Tk data directories (tcl9.0, tk9.0, etc.)
        for dir_pattern in ["tcl[0-9]*", "tk[0-9]*"]:
            for data_dir in lib_dir.glob(dir_pattern):
                if data_dir.is_dir():
                    tcl_tk_data.append(data_dir)

    return tcl_tk_binaries, tcl_tk_data


def main():
    # Get project root (parent of scripts/)
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    os.chdir(project_root)

    print("=" * 60)
    print("PDF Compare - Linux Executable Builder")
    print("=" * 60)
    print("\nUsing PyMuPDF for vector-based PDF processing (no external dependencies needed)")

    # Clean previous builds
    print("\n[1/4] Cleaning previous builds...")
    for folder in ["build", "dist"]:
        folder_path = project_root / folder
        if folder_path.exists():
            shutil.rmtree(folder_path)
            print(f"  Removed {folder}/")

    for spec_file in project_root.glob("*.spec"):
        spec_file.unlink()
        print(f"  Removed {spec_file.name}")

    # PyInstaller arguments
    print("\n[2/4] Configuring PyInstaller...")

    # Runtime hook for Tcl/Tk library paths
    rthook_path = script_dir / "pyinstaller_hooks" / "rthook_tcltk_linux.py"

    pyinstaller_args = [
        "pyinstaller",
        "--onefile",           # Single executable file
        "--name=pdf-compare",  # Executable name (lowercase for Linux convention)
        "--clean",             # Clean cache before building
        # Add data files (from pdf_compare/ folder) - Linux uses : as separator
        "--add-data=pdf_compare/comparator.py:pdf_compare",
        "--add-data=pdf_compare/cli.py:pdf_compare",
        "--add-data=pdf_compare/config.py:pdf_compare",
        # Collect all customtkinter and tkinter dependencies
        "--collect-all=customtkinter",
        "--collect-all=tkinter",
        # Runtime hook to set up Tcl/Tk paths before importing
        f"--runtime-hook={rthook_path}",
    ]

    # Find and add Tcl/Tk libraries (required for tkinter on standalone Python)
    tcl_tk_binaries, tcl_tk_data = find_tcl_tk_libs()

    if tcl_tk_binaries:
        print(f"  Found {len(tcl_tk_binaries)} Tcl/Tk binary libraries")
        for lib in tcl_tk_binaries:
            # Add binary to root of bundle (where _tkinter looks for them)
            pyinstaller_args.append(f"--add-binary={lib}:.")

    if tcl_tk_data:
        print(f"  Found {len(tcl_tk_data)} Tcl/Tk data directories")
        for data_dir in tcl_tk_data:
            # Add data directories preserving their names
            pyinstaller_args.append(f"--add-data={data_dir}:{data_dir.name}")

    # Hidden imports that PyInstaller might miss
    hidden_imports = [
        "customtkinter",
        "fitz",
        "pymupdf",
        "PIL",
        "PIL.Image",
        "pdf_compare.comparator",
        "pdf_compare.config",
    ]

    for imp in hidden_imports:
        pyinstaller_args.append(f"--hidden-import={imp}")

    # Check for icon file (Linux supports .png for icons)
    icon_path = project_root / "assets" / "icon.png"
    if not icon_path.exists():
        # Fall back to .ico if .png doesn't exist
        icon_path = project_root / "assets" / "icon.ico"

    if icon_path.exists():
        pyinstaller_args.append(f"--icon={icon_path}")
        print(f"  Using icon: {icon_path}")
    else:
        print("  No icon found (optional: add assets/icon.png)")

    # Entry point
    entry_point = project_root / "pdf_compare" / "gui.py"
    pyinstaller_args.append(str(entry_point))

    print(f"  Entry point: pdf_compare/gui.py")
    print(f"  Output name: pdf-compare")

    # Run PyInstaller
    print("\n[3/4] Building executable (this may take a few minutes)...")
    try:
        result = subprocess.run(
            pyinstaller_args,
            check=True,
            capture_output=False
        )
    except subprocess.CalledProcessError as e:
        print(f"\nError: PyInstaller failed with exit code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("\nError: PyInstaller not found. Install with: uv add pyinstaller --dev")
        sys.exit(1)

    # Verify output
    print("\n[4/4] Verifying build...")
    exe_path = project_root / "dist" / "pdf-compare"

    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"  Executable created: {exe_path}")
        print(f"  Size: {size_mb:.1f} MB")
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print("=" * 60)
        print(f"\nThe executable is located at:")
        print(f"  {exe_path}")
        print("\nYou can:")
        print("  1. Run directly: ./dist/pdf-compare")
        print("  2. Copy to /usr/local/bin for system-wide access")
        print("  3. Create a .desktop file for application menu")
        print("  4. Distribute to users")
        print("\n[OK] Fully standalone - no external dependencies required!")
        print("    Users do NOT need to install Python or any other tools.")
    else:
        print("\nError: Executable not found after build")
        sys.exit(1)


if __name__ == "__main__":
    main()
