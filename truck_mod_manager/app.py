"""
Application entry and lifecycle for Truck Mod Manager.
"""
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from truck_mod_manager.ui.main_window import MainWindow

__version__ = "1.0.2"


def main():

    crash_dir = Path.home() / ".local" / "share" / "truck-mod-manager"
    crash_log = crash_dir / "startup_crash.log"

    try:
        # Enable High DPI scaling
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Safe platform plugin fallback (e.g. Wayland without qt6-wayland fallback to xcb)
        if "QT_QPA_PLATFORM" not in os.environ and (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland"):
            os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

        app = QApplication(sys.argv)
        app.setApplicationName("Truck Mod Manager")
        app.setApplicationDisplayName("Truck Mod Manager (ETS2 & ATS)")
        app.setOrganizationName("Julian")
        app.setApplicationVersion(__version__)

        # Set icon
        icon_path = Path(__file__).parent / "resources" / "icon.svg"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        crash_dir.mkdir(parents=True, exist_ok=True)
        tb = traceback.format_exc()
        crash_text = (
            f"=== Truck Mod Manager Crash Report ({datetime.now().isoformat()}) ===\n"
            f"Python: {sys.version}\n"
            f"Platform: {sys.platform}\n"
            f"Error: {e}\n\n"
            f"Traceback:\n{tb}\n"
        )
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write(crash_text)
        print(crash_text, file=sys.stderr)

        # Try to show GUI message if possible
        try:
            app_inst = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "Truck Mod Manager - Startfehler",
                f"Beim Starten von Truck Mod Manager ist ein Fehler aufgetreten:\n\n{e}\n\n"
                f"Ein detaillierter Absturzbericht wurde gespeichert unter:\n{crash_log}"
            )
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
