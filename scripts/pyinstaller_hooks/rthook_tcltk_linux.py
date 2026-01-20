"""
Runtime hook for PyInstaller to set up Tcl/Tk library paths.
This ensures the Tcl/Tk shared libraries can be found at runtime.
"""
import os
import sys
import ctypes

# Get the directory where PyInstaller extracts files
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    bundle_dir = sys._MEIPASS

    # Set TCL/TK library paths BEFORE importing tkinter
    tcl_dir = os.path.join(bundle_dir, 'tcl9.0')
    tk_dir = os.path.join(bundle_dir, 'tk9.0')

    if os.path.isdir(tcl_dir):
        os.environ['TCL_LIBRARY'] = tcl_dir
    if os.path.isdir(tk_dir):
        os.environ['TK_LIBRARY'] = tk_dir

    # Preload Tcl/Tk shared libraries using ctypes
    # This makes them available before _tkinter tries to load them
    tcl_lib = os.path.join(bundle_dir, 'libtcl9.0.so')
    tk_lib = os.path.join(bundle_dir, 'libtcl9tk9.0.so')

    if os.path.exists(tcl_lib):
        ctypes.CDLL(tcl_lib, mode=ctypes.RTLD_GLOBAL)
    if os.path.exists(tk_lib):
        ctypes.CDLL(tk_lib, mode=ctypes.RTLD_GLOBAL)
