#!/usr/bin/env python3
"""
Build script for creating Windows executable using PyInstaller.

Usage:
    uv run python scripts/build_windows.py

This creates a standalone .exe file in the dist/ folder that can be
distributed to users without requiring Python installation.
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path


def main():
    # Get project root (parent of scripts/)
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    os.chdir(project_root)

    print("=" * 60)
    print("PDF Compare - Windows Executable Builder")
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

    pyinstaller_args = [
        "pyinstaller",
        "--onefile",           # Single executable file
        "--windowed",          # No console window (GUI app)
        "--name=PDF Compare",  # Executable name
        "--clean",             # Clean cache before building
        # Add data files (from pdf_compare/ folder)
        "--add-data=pdf_compare/comparator.py;pdf_compare",
        "--add-data=pdf_compare/cli.py;pdf_compare",
        "--add-data=pdf_compare/config.py;pdf_compare",
    ]

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

    # Check for icon file
    icon_path = project_root / "assets" / "icon.ico"
    if icon_path.exists():
        pyinstaller_args.append(f"--icon={icon_path}")
        print(f"  Using icon: {icon_path}")
    else:
        print("  No icon found (optional: add assets/icon.ico)")

    # Entry point
    entry_point = project_root / "pdf_compare" / "gui.py"
    pyinstaller_args.append(str(entry_point))

    print(f"  Entry point: pdf_compare/gui.py")
    print(f"  Output name: PDF Compare.exe")

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
    exe_path = project_root / "dist" / "PDF Compare.exe"

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
        print("  1. Double-click to run")
        print("  2. Create a desktop shortcut")
        print("  3. Distribute to users")
        print("\n[OK] Fully standalone - no external dependencies required!")
        print("    Users do NOT need to install Python or any other tools.")
    else:
        print("\nError: Executable not found after build")
        sys.exit(1)


if __name__ == "__main__":
    main()
