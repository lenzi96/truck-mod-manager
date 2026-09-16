"""
URL Download Dialog for Truck Mod Manager.
Allows users to paste any direct download link (ProMods, Google Drive, ShareMods, CDN)
and download & extract it directly into the mod library.
"""
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout
)

from truck_mod_manager.core.models import GameType, TruckGame
from truck_mod_manager.ui.dialogs.download_dialog import DownloadDialog


class UrlDownloadDialog(QDialog):
    download_success = pyqtSignal(list)

    def __init__(self, current_game: TruckGame, parent=None):
        super().__init__(parent)
        self.current_game = current_game
        self.setWindowTitle("Mod über Direktlink herunterladen")
        self.resize(560, 260)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QLineEdit, QComboBox {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f8fafc;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #3b82f6;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title
        title_lbl = QLabel("🔗 Mod / ProMods über Direktlink herunterladen")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(
            "Füge einen beliebigen Download-Link (z. B. ProMods-Bezahllink, Google Drive, TruckyMods, "
            "Mediafire oder direkte .scs / .zip / .7z URL) ein. Das Archiv wird automatisch heruntergeladen, "
            "entpackt und in die Mod-Bibliothek integriert."
        )
        desc_lbl.setStyleSheet("font-size: 11px; color: #94a3b8;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        # URL Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://.../promods-v270.7z oder https://.../mod.scs")
        layout.addWidget(self.url_input)

        # Optional custom filename
        fn_row = QHBoxLayout()
        fn_lbl = QLabel("Dateiname (optional):")
        fn_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        fn_row.addWidget(fn_lbl)

        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("Automatisch aus URL ermitteln")
        fn_row.addWidget(self.filename_input, 1)
        layout.addLayout(fn_row)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.setFixedHeight(32)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        start_btn = QPushButton("⬇️ Herunterladen & Installieren")
        start_btn.setObjectName("primaryBtn")
        start_btn.setFixedHeight(34)
        start_btn.clicked.connect(self._start_download)
        btn_layout.addWidget(start_btn)

        layout.addLayout(btn_layout)

    def _start_download(self):
        url = self.url_input.text().strip()
        if not url or not url.startswith("http"):
            QMessageBox.warning(self, "Ungültige URL", "Bitte gib eine gültige Web-Adresse (http:// oder https://) ein.")
            return

        target_dir = Path(self.current_game.mod_dir) if self.current_game.mod_dir else Path.home() / ".local/share/truck-mod-manager/mods"
        filename = self.filename_input.text().strip()

        # Open download progress dialog
        dl_dialog = DownloadDialog(
            title="Direkt-Download",
            target_dir=target_dir,
            direct_url=url,
            suggested_filename=filename,
            parent=self
        )
        dl_dialog.download_completed.connect(self._on_completed)
        dl_dialog.exec()

    def _on_completed(self, deployed_files):
        self.download_success.emit(deployed_files)
        self.accept()
