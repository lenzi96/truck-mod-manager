#!/usr/bin/env python3
"""
Truck Mod Manager - Standalone entry point.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

# 1. Python version check
if sys.version_info < (3, 9):
    msg = f"Python 3.9 oder neuer erforderlich (aktuell: Python {sys.version.split()[0]})."
    print(f"\033[1;31m[FEHLER]\033[0m {msg}", file=sys.stderr)
    sys.exit(1)

# 2. Wayland/X11 safety fallback
if "QT_QPA_PLATFORM" not in os.environ and (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland"):
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

# 3. PyQt6 dependency check
try:
    import PyQt6
    from PyQt6.QtWidgets import QApplication, QMessageBox
except ImportError:
    msg = (
        "PyQt6 ist auf diesem System nicht installiert!\n\n"
        "Bitte installiere PyQt6 über deinen Paketmanager:\n"
        "  • Arch Linux / CachyOS:  sudo pacman -S python-pyqt6\n"
        "  • Ubuntu / Debian / Mint: sudo apt install python3-pyqt6\n"
        "  • Fedora / RHEL:          sudo dnf install python3-pyqt6\n"
        "  • openSUSE:               sudo zypper install python3-PyQt6\n"
        "  • Pip / Wheel:            pip install PyQt6"
    )
    print(f"\033[1;31m[FEHLER]\033[0m {msg}", file=sys.stderr)

    # Show graphical error if running in desktop environment
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        import shutil, subprocess
        if shutil.which("zenity"):
            subprocess.run(["zenity", "--error", "--title=Truck Mod Manager", "--text=" + msg], check=False)
        elif shutil.which("kdialog"):
            subprocess.run(["kdialog", "--error", msg, "--title", "Truck Mod Manager"], check=False)
    sys.exit(1)

# 4. Run application with crash logging
from truck_mod_manager.app import main

if __name__ == "__main__":
    main()
