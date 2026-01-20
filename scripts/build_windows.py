#!/usr/bin/env python3
"""
Build script for creating Windows executable using PyInstaller.

Usage:
    uv run python scripts/build_windows.py

This creates a standalone .exe file in the dist/ folder that can be
distributed to users without requiring Python or Poppler installation.

Before building, run:
    uv run python scripts/download_poppler.py
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

    # Check for Poppler
    poppler_dir = project_root / "vendor" / "poppler"
    poppler_bin = poppler_dir / "Library" / "bin"
    has_poppler = poppler_bin.exists() and (poppler_bin / "pdftoppm.exe").exists()

    if has_poppler:
        print(f"\n[OK] Poppler found at: {poppler_dir}")
    else:
        print(f"\n[!] Poppler NOT found at: {poppler_dir}")
        print("\nTo create a fully standalone executable, first download Poppler:")
        print("    uv run python scripts/download_poppler.py")
        print("\nContinuing without bundled Poppler...")
        print("(Users will need to install Poppler separately)")

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
        # Add data files (from python/ folder)
        "--add-data=python/comparator.py;python",
        "--add-data=python/compare_pdf.py;python",
    ]

    # Add Poppler if available
    if has_poppler:
        # Include the entire poppler directory
        pyinstaller_args.append(f"--add-data={poppler_dir};poppler")
        print(f"  Including Poppler binaries")

    # Hidden imports that PyInstaller might miss
    hidden_imports = [
        "PIL",
        "PIL.Image",
        "customtkinter",
        "cv2",
        "numpy",
        "pdf2image",
        "pdfplumber",
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
    entry_point = project_root / "python" / "main.py"
    pyinstaller_args.append(str(entry_point))

    print(f"  Entry point: python/main.py")
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

        if has_poppler:
            print("\n[OK] Poppler is bundled - fully standalone!")
            print("    Users do NOT need to install anything.")
        else:
            print("\n[!] Poppler NOT bundled")
            print("    Users need to install Poppler separately.")
    else:
        print("\nError: Executable not found after build")
        sys.exit(1)


if __name__ == "__main__":
    main()
