#!/usr/bin/env python3
"""
Graphical Installer launcher for Truck Mod Manager (ETS2 & ATS).
Run with:
    ./gui-installer.py
or:
    python3 gui-installer.py
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    # 1. Dependency check for PyQt6
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("\033[1;31m[FEHLER]\033[0m PyQt6 ist auf diesem System nicht installiert.")
        print("Um den grafischen Installer auszuführen, installieren Sie bitte python-pyqt6:")
        print("  - Arch / CachyOS:  sudo pacman -S python-pyqt6")
        print("  - Ubuntu / Debian: sudo apt install python3-pyqt6")
        print("  - Fedora:          sudo dnf install python3-pyqt6")
        print("\nAlternativ können Sie die textbasierte Installation starten:")
        print("  ./install.sh --user")
        sys.exit(1)

    # 2. Launch GUI Installer
    from truck_mod_manager.installer.installer_window import InstallerWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Truck Mod Manager Installer")
    app.setApplicationDisplayName("Truck Mod Manager Installation")

    window = InstallerWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
