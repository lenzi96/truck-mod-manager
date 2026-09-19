"""
ProMods Download Dialog for Truck Mod Manager.
Provides official website links and direct fast-download handling
with automatic extraction into the active game's mod directory.
"""
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout
)

from truck_mod_manager.core.downloader import ArchiveExtractor
from truck_mod_manager.core.models import GameType, TruckGame
from truck_mod_manager.core.promods_manager import ProModsPackStatus
from truck_mod_manager.ui.dialogs.download_dialog import DownloadDialog


class ProModsDownloadDialog(QDialog):
    download_success = pyqtSignal(list)

    def __init__(self, pack_status: ProModsPackStatus, current_game: TruckGame, parent=None):
        super().__init__(parent)
        self.pack = pack_status
        self.current_game = current_game

        self.setWindowTitle(f"ProMods Download: {self.pack.title}")
        self.resize(620, 480)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QLineEdit {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 10px;
                color: #f8fafc;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Box
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header_frame)
        h_layout.setSpacing(6)

        title_lbl = QLabel(f"🗺️ {self.pack.title}")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        h_layout.addWidget(title_lbl)

        # Versions info
        inst_ver = f"v{self.pack.version}" if self.pack.version else "Nicht installiert"
        latest_ver = f"v{self.pack.latest_version}" if self.pack.latest_version else "Unbekannt"
        compat = self.pack.game_compatibility or "Aktuelle ETS2/ATS Version"

        status_text = f"<b>Installiert:</b> {inst_ver} &nbsp;|&nbsp; <b>Website / Aktuell:</b> {latest_ver} &nbsp;|&nbsp; <b>Kompatibilität:</b> {compat}"
        info_lbl = QLabel(status_text)
        info_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
        h_layout.addWidget(info_lbl)

        layout.addWidget(header_frame)

        # Option 1: Official Website
        opt1_frame = QFrame()
        opt1_frame.setStyleSheet("QFrame { background-color: #162032; border: 1px solid #25334d; border-radius: 8px; }")
        opt1_layout = QVBoxLayout(opt1_frame)
        opt1_layout.setContentsMargins(14, 12, 14, 14)
        opt1_layout.setSpacing(8)

        opt1_title = QLabel("1. Offizielle ProMods-Downloadseite")
        opt1_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #38bdf8; border: none;")
        opt1_layout.addWidget(opt1_title)

        opt1_desc = QLabel(
            "Öffnet die offizielle Download-Seite auf promods.net im Webbrowser. "
            "Dort kannst du deine individuelle Def-Datei generieren und die Pack-Archive herunterladen."
        )
        opt1_desc.setStyleSheet("font-size: 11px; color: #cbd5e1; border: none;")
        opt1_desc.setWordWrap(True)
        opt1_layout.addWidget(opt1_desc)

        btn_open_web = QPushButton("🌐 Offizielle Downloadseite öffnen")
        btn_open_web.setFixedHeight(34)
        btn_open_web.setStyleSheet("""
            background-color: #2563eb;
            color: #ffffff;
            font-weight: bold;
            border-radius: 6px;
            border: 1px solid #3b82f6;
        """)
        btn_open_web.clicked.connect(self._open_web)
        opt1_layout.addWidget(btn_open_web)

        layout.addWidget(opt1_frame)

        # Option 2: Direct URL Download & Auto-Extract
        opt2_frame = QFrame()
        opt2_frame.setStyleSheet("QFrame { background-color: #162032; border: 1px solid #25334d; border-radius: 8px; }")
        opt2_layout = QVBoxLayout(opt2_frame)
        opt2_layout.setContentsMargins(14, 12, 14, 14)
        opt2_layout.setSpacing(8)

        opt2_title = QLabel("2. Direkt-Download / Fast-Link (Automatischer Download & Entpacken)")
        opt2_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #34d399; border: none;")
        opt2_layout.addWidget(opt2_title)

        opt2_desc = QLabel(
            "Füge deinen direkten Download-Link (z. B. ProMods Fast-Download-Link von Payloadz, "
            "CDN-Direktlink oder Mirror) ein. Der Mod Manager lädt die Datei im Hintergrund herunter "
            "und entpackt sie automatisch in dein aktives Mod-Verzeichnis."
        )
        opt2_desc.setStyleSheet("font-size: 11px; color: #cbd5e1; border: none;")
        opt2_desc.setWordWrap(True)
        opt2_layout.addWidget(opt2_desc)

        dl_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://... (Direkt-Link hier einfügen)")
        dl_row.addWidget(self.url_input, 1)

        self.btn_download = QPushButton("⬇️ Herunterladen && Installieren")
        self.btn_download.setFixedHeight(34)
        self.btn_download.setStyleSheet("""
            background-color: #059669;
            color: #ffffff;
            font-weight: bold;
            border-radius: 6px;
            border: 1px solid #10b981;
            padding: 0 14px;
        """)
        self.btn_download.clicked.connect(self._start_direct_download)
        dl_row.addWidget(self.btn_download)

        opt2_layout.addLayout(dl_row)
        layout.addWidget(opt2_frame)

        # Bottom buttons (Close / Local Extract)
        bottom_row = QHBoxLayout()

        btn_local = QPushButton("📦 Heruntergeladene Archive aus Downloads entpacken...")
        btn_local.setFixedHeight(32)
        btn_local.clicked.connect(self._extract_local)
        bottom_row.addWidget(btn_local)

        bottom_row.addStretch()

        btn_close = QPushButton("Schließen")
        btn_close.setFixedHeight(32)
        btn_close.clicked.connect(self.reject)
        bottom_row.addWidget(btn_close)

        layout.addLayout(bottom_row)

    def _open_web(self):
        url = self.pack.download_url or "https://promods.net"
        QDesktopServices.openUrl(QUrl(url))

    def _start_direct_download(self):
        url = self.url_input.text().strip()
        if not url or not url.startswith("http"):
            QMessageBox.warning(self, "Ungültige URL", "Bitte gib eine gültige Download-Webadresse (http:// oder https://) ein.")
            return

        target_dir = Path(self.current_game.mod_dir) if self.current_game.mod_dir else Path.home() / ".local/share/truck-mod-manager/mods"

        dl_dialog = DownloadDialog(
            title=self.pack.title,
            target_dir=target_dir,
            direct_url=url,
            suggested_filename="",
            parent=self
        )
        dl_dialog.download_completed.connect(self._on_download_completed)
        dl_dialog.exec()

    def _on_download_completed(self, deployed_files):
        self.download_success.emit(deployed_files)
        self.accept()

    def _extract_local(self):
        target_dir = Path(self.current_game.mod_dir) if self.current_game.mod_dir else Path.home() / ".local/share/truck-mod-manager/mods"
        downloads_dir = Path.home() / "Downloads"

        selected, _ = QFileDialog.getOpenFileNames(
            self,
            f"Heruntergeladene Archive für {self.pack.title} auswählen",
            str(downloads_dir),
            "ProMods Archive (*.7z* *.zip *.scs);;Alle Dateien (*)"
        )
        if not selected:
            return

        deployed_total = []
        for p in selected:
            src = Path(p)
            # Skip secondary multipart archives (.7z.002, .003, etc.) as .001 unpacks the full set
            if any(src.name.lower().endswith(f".7z.{i:03d}") for i in range(2, 30)):
                continue
            dep = ArchiveExtractor.deploy_or_extract(src, target_dir)
            deployed_total.extend(dep)

        if deployed_total:
            QMessageBox.information(
                self,
                "Entpacken erfolgreich",
                f"Es wurden {len(deployed_total)} Dateien für {self.pack.title} erfolgreich entpackt und in den Mod-Ordner importiert!"
            )
            self.download_success.emit(deployed_total)
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Keine Dateien entpackt",
                "Aus den ausgewählten Dateien konnten keine Mod-Dateien entpackt werden."
            )
