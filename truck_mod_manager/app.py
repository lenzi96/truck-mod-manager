"""
Application entry and lifecycle for Truck Mod Manager.
"""
import sys
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from truck_mod_manager.ui.main_window import MainWindow


__version__ = "1.0.0"


def main():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

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


if __name__ == "__main__":
    main()
