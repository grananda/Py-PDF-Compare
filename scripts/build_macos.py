#!/usr/bin/env python3
"""
Build script for creating macOS application using PyInstaller.

Usage:
    uv run python scripts/build_macos.py

This creates a standalone .app bundle in the dist/ folder that can be
distributed to users without requiring Python installation.

Note: On macOS, Poppler is typically installed via Homebrew:
    brew install poppler
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path


def check_system_poppler():
    """Check if Poppler is installed system-wide (e.g., via Homebrew)."""
    try:
        result = subprocess.run(
            ["which", "pdftoppm"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        pass
    return None


def get_homebrew_poppler_path():
    """Get the Homebrew Poppler installation path."""
    try:
        result = subprocess.run(
            ["brew", "--prefix", "poppler"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except FileNotFoundError:
        pass
    return None


def find_tcl_tk_libs():
    """Find Tcl/Tk libraries in the Python installation."""
    # Get the Python installation's lib directory
    # Use base_prefix to get the actual Python installation (not the venv)
    python_prefix = Path(sys.base_prefix)
    lib_dir = python_prefix / "lib"

    tcl_tk_binaries = []
    tcl_tk_data = []

    if lib_dir.exists():
        # Find .dylib files for Tcl/Tk (macOS uses .dylib instead of .so)
        for pattern in ["libtcl*.dylib", "libtk*.dylib"]:
            for lib_file in lib_dir.glob(pattern):
                if lib_file.is_file():
                    tcl_tk_binaries.append(lib_file)

        # Find Tcl/Tk data directories (tcl9.0, tk9.0, etc.)
        for dir_pattern in ["tcl[0-9]*", "tk[0-9]*"]:
            for data_dir in lib_dir.glob(dir_pattern):
                if data_dir.is_dir():
                    tcl_tk_data.append(data_dir)

    # Also check in Frameworks (common on macOS)
    frameworks_dir = python_prefix / "Library" / "Frameworks"
    if frameworks_dir.exists():
        for framework in ["Tcl.framework", "Tk.framework"]:
            framework_path = frameworks_dir / framework
            if framework_path.exists():
                # Add framework libraries
                for dylib in framework_path.rglob("*.dylib"):
                    if dylib.is_file():
                        tcl_tk_binaries.append(dylib)

    return tcl_tk_binaries, tcl_tk_data


def main():
    # Get project root (parent of scripts/)
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir.parent
    os.chdir(project_root)

    print("=" * 60)
    print("PDF Compare - macOS Application Builder")
    print("=" * 60)

    # Check for Poppler (bundled or system)
    poppler_dir = project_root / "vendor" / "poppler"
    poppler_bin = poppler_dir / "bin"
    has_bundled_poppler = poppler_bin.exists() and (poppler_bin / "pdftoppm").exists()

    system_poppler = check_system_poppler()
    homebrew_poppler = get_homebrew_poppler_path()

    if has_bundled_poppler:
        print(f"\n[OK] Bundled Poppler found at: {poppler_dir}")
    elif system_poppler:
        print(f"\n[OK] System Poppler found at: {system_poppler}")
        if homebrew_poppler:
            print(f"    Homebrew prefix: {homebrew_poppler}")
        print("    Note: Users will need Poppler installed on their system")
    else:
        print(f"\n[!] Poppler NOT found")
        print("\nTo run the application, users need to install Poppler:")
        print("    brew install poppler")
        print("\nContinuing build without bundled Poppler...")

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

    # Also clean PyInstaller cache to avoid symlink conflicts
    pyinstaller_cache = Path.home() / "Library" / "Application Support" / "pyinstaller"
    if pyinstaller_cache.exists():
        shutil.rmtree(pyinstaller_cache)
        print(f"  Removed PyInstaller cache")

    # PyInstaller arguments
    print("\n[2/4] Configuring PyInstaller...")

    # Runtime hook for Tcl/Tk library paths
    rthook_path = script_dir / "pyinstaller_hooks" / "rthook_tcltk_macos.py"

    pyinstaller_args = [
        "pyinstaller",
        "--windowed",             # No console window (GUI app) - creates .app bundle
        "--name=PDF Compare",     # Application name
        "--clean",                # Clean cache before building
        "--noconfirm",            # Don't ask for confirmation
        # Note: comparator.py and compare_pdf.py are imported as modules by main.py,
        # so PyInstaller will include them automatically. No need for --add-data.
        # Collect all customtkinter and tkinter dependencies
        "--collect-all=customtkinter",
        "--collect-all=tkinter",
        # Runtime hook to set up Tcl/Tk paths before importing
        f"--runtime-hook={rthook_path}",
        # macOS specific: code signing identity (use - for ad-hoc signing)
        "--codesign-identity=-",
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

    # Add Poppler if bundled
    if has_bundled_poppler:
        # Include the entire poppler directory
        pyinstaller_args.append(f"--add-data={poppler_dir}:poppler")
        print(f"  Including bundled Poppler binaries")

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

    # Check for icon file (macOS uses .icns format)
    icon_path = project_root / "assets" / "icon.icns"
    if not icon_path.exists():
        # Fall back to .ico if .icns doesn't exist (PyInstaller will try to convert)
        icon_path = project_root / "assets" / "icon.ico"

    if icon_path.exists():
        pyinstaller_args.append(f"--icon={icon_path}")
        print(f"  Using icon: {icon_path}")
    else:
        print("  No icon found (optional: add assets/icon.icns)")

    # macOS specific: add bundle identifier for proper app behavior
    pyinstaller_args.append("--osx-bundle-identifier=com.pdfcompare.app")

    # Entry point
    entry_point = project_root / "python" / "main.py"
    pyinstaller_args.append(str(entry_point))

    print(f"  Entry point: python/main.py")
    print(f"  Output name: PDF Compare.app")

    # Run PyInstaller
    print("\n[3/4] Building application (this may take a few minutes)...")

    # Workaround for PyInstaller symlink bug with Homebrew Python on macOS
    # The bug causes "FileExistsError: File exists" when creating symlinks
    # during the COLLECT phase. We remove the conflicting file before it fails.
    dist_internal = project_root / "dist" / "PDF Compare" / "_internal"
    python_symlink = dist_internal / "Python"

    def remove_conflicting_symlink():
        """Remove the Python symlink that conflicts with Python.framework symlink."""
        if python_symlink.exists() or python_symlink.is_symlink():
            python_symlink.unlink()

    # Run PyInstaller with retry logic for symlink issue
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Clean up potential symlink conflict before each attempt
            remove_conflicting_symlink()

            result = subprocess.run(
                pyinstaller_args,
                check=True,
                capture_output=False
            )
            break  # Success, exit retry loop
        except subprocess.CalledProcessError as e:
            if attempt < max_retries - 1:
                print(f"\n  Retry {attempt + 1}/{max_retries} - cleaning up symlink conflicts...")
                remove_conflicting_symlink()
                # Also try removing the entire _internal directory
                if dist_internal.exists():
                    shutil.rmtree(dist_internal)
            else:
                print(f"\nError: PyInstaller failed with exit code {e.returncode}")
                sys.exit(1)
        except FileNotFoundError:
            print("\nError: PyInstaller not found. Install with: uv add pyinstaller --dev")
            sys.exit(1)

    # Verify output and re-sign the application
    print("\n[4/4] Verifying build and signing...")
    app_path = project_root / "dist" / "PDF Compare.app"

    if app_path.exists():
        # Re-sign all binaries in the app bundle to fix Team ID mismatch
        # This is required because Homebrew Python has a different signature
        print("  Re-signing application bundle...")
        try:
            # First, remove all existing signatures and re-sign with ad-hoc identity
            # Sign frameworks first, then the main executable
            frameworks_path = app_path / "Contents" / "Frameworks"
            if frameworks_path.exists():
                # Sign all dylibs and frameworks
                for item in frameworks_path.rglob("*"):
                    if item.is_file() and (item.suffix in [".dylib", ".so"] or "Python" in item.name):
                        subprocess.run(
                            ["codesign", "--force", "--sign", "-", "--deep", str(item)],
                            capture_output=True
                        )
                # Sign Python.framework specifically
                python_framework = frameworks_path / "Python.framework"
                if python_framework.exists():
                    subprocess.run(
                        ["codesign", "--force", "--sign", "-", "--deep", str(python_framework)],
                        capture_output=True
                    )

            # Sign the main app bundle
            result = subprocess.run(
                ["codesign", "--force", "--sign", "-", "--deep", str(app_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("  Application signed successfully")
            else:
                print(f"  Warning: Signing may have issues: {result.stderr}")
        except Exception as e:
            print(f"  Warning: Could not re-sign application: {e}")
        # Get size of the entire .app bundle
        total_size = sum(f.stat().st_size for f in app_path.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"  Application created: {app_path}")
        print(f"  Size: {size_mb:.1f} MB")
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print("=" * 60)
        print(f"\nThe application is located at:")
        print(f"  {app_path}")
        print("\nYou can:")
        print("  1. Double-click to run")
        print("  2. Drag to /Applications folder for system-wide access")
        print("  3. Create a DMG for distribution")
        print("  4. Distribute to users")

        if has_bundled_poppler:
            print("\n[OK] Poppler is bundled - fully standalone!")
            print("    Users do NOT need to install anything.")
        else:
            print("\n[!] Poppler NOT bundled")
            print("    Users need to install Poppler via: brew install poppler")

        # Provide optional DMG creation instructions
        print("\n" + "-" * 60)
        print("Optional: Create a DMG for easy distribution")
        print("-" * 60)
        print("To create a DMG installer, you can use create-dmg:")
        print("  brew install create-dmg")
        print("  create-dmg \\")
        print('    --volname "PDF Compare" \\')
        print('    --window-pos 200 120 \\')
        print('    --window-size 600 400 \\')
        print('    --icon-size 100 \\')
        print('    --app-drop-link 450 185 \\')
        print('    "PDF Compare.dmg" \\')
        print('    "dist/PDF Compare.app"')
    else:
        print("\nError: Application not found after build")
        sys.exit(1)


if __name__ == "__main__":
    main()
