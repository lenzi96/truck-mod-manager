"""
Modern Download Progress Dialog for Truck Mod Manager.
Handles link resolution, chunked streaming downloads with speed/ETA, and automatic archive extraction.
"""
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QVBoxLayout, QWidget
)

from truck_mod_manager.core.downloader import (
    ArchiveExtractor, ModDownloadWorker, format_size
)
from truck_mod_manager.core.models import GameType, TruckGame
from truck_mod_manager.core.trucky_api import TruckyClient


class TruckyResolveWorker(QThread):
    resolved = pyqtSignal(str, str)  # direct_url, filename
    error = pyqtSignal(str)

    def __init__(self, mod_url: str, parent=None):
        super().__init__(parent)
        self.mod_url = mod_url

    def run(self):
        success, url, filename, err = TruckyClient.resolve_direct_download(self.mod_url)
        if success and url:
            self.resolved.emit(url, filename or "mod.scs")
        else:
            self.error.emit(err or "Konnte Download-Link nicht abrufen.")


class DownloadDialog(QDialog):
    download_completed = pyqtSignal(list)  # List of deployed Path objects

    def __init__(
        self,
        title: str,
        target_dir: Path,
        direct_url: Optional[str] = None,
        trucky_mod_url: Optional[str] = None,
        suggested_filename: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.mod_title = title
        self.target_dir = Path(target_dir)
        self.direct_url = direct_url
        self.trucky_mod_url = trucky_mod_url
        self.suggested_filename = suggested_filename

        self.resolve_worker: Optional[TruckyResolveWorker] = None
        self.download_worker: Optional[ModDownloadWorker] = None
        self.deployed_files: List[Path] = []

        self.setWindowTitle(f"Download: {self.mod_title}")
        self.resize(500, 220)
        self.setModal(True)

        self._init_ui()
        self._start_process()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                background-color: #1e293b;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
                height: 22px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #38bdf8);
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title & Filename
        title_lbl = QLabel(f"📦 {self.mod_title}")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc;")
        layout.addWidget(title_lbl)

        self.filename_lbl = QLabel("Ermittle Download-Link...")
        self.filename_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(self.filename_lbl)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status & Stats label
        self.stats_lbl = QLabel("Verbindung wird aufgebaut...")
        self.stats_lbl.setStyleSheet("font-size: 12px; color: #cbd5e1;")
        layout.addWidget(self.stats_lbl)

        layout.addStretch()

        # Action button (Cancel / Close)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Abbrechen")
        self.cancel_btn.setFixedHeight(32)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

    def _start_process(self):
        if self.trucky_mod_url:
            self.stats_lbl.setText("Generiere autorisierten Direkt-Link von TruckyMods...")
            self.resolve_worker = TruckyResolveWorker(self.trucky_mod_url, parent=self)
            self.resolve_worker.resolved.connect(self._on_url_resolved)
            self.resolve_worker.error.connect(self._on_resolve_error)
            self.resolve_worker.start()
        elif self.direct_url:
            self._start_download(self.direct_url, self.suggested_filename)
        else:
            self._on_resolve_error("Keine gültige Download-URL angegeben.")

    def _on_url_resolved(self, direct_url: str, filename: str):
        self.direct_url = direct_url
        self.suggested_filename = filename
        self._start_download(direct_url, filename)

    def _on_resolve_error(self, error_msg: str):
        self.stats_lbl.setText(f"❌ Fehler: {error_msg}")
        self.stats_lbl.setStyleSheet("color: #f87171; font-size: 12px; font-weight: bold;")
        self.cancel_btn.setText("Schließen")
        QMessageBox.warning(self, "Download-Fehler", f"Konnte Download nicht starten:\n\n{error_msg}")

    def _start_download(self, url: str, filename: str):
        self.filename_lbl.setText(f"Datei: <b>{filename}</b>")
        self.stats_lbl.setText("Download gestartet...")

        self.download_worker = ModDownloadWorker(
            url=url,
            target_dir=self.target_dir,
            suggested_filename=filename,
            parent=self
        )
        self.download_worker.progress_updated.connect(self._on_progress_updated)
        self.download_worker.download_finished.connect(self._on_download_finished)
        self.download_worker.download_error.connect(self._on_download_error)
        self.download_worker.start()

    def _on_progress_updated(self, downloaded: int, total: int, speed_str: str, eta_str: str):
        if total > 0:
            pct = int((downloaded / total) * 100)
            self.progress_bar.setValue(pct)
            total_str = format_size(total)
            dl_str = format_size(downloaded)
            stats = f"{dl_str} / {total_str} • {speed_str}"
            if eta_str:
                stats += f" • {eta_str}"
            self.stats_lbl.setText(stats)
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.stats_lbl.setText(f"{format_size(downloaded)} heruntergeladen • {speed_str}")

    def _on_download_finished(self, local_path_str: str, filename: str):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.stats_lbl.setText("📦 Entpacke und installiere Mod...")

        local_path = Path(local_path_str)
        deployed = ArchiveExtractor.deploy_or_extract(local_path, self.target_dir)
        self.deployed_files = deployed

        count = len(deployed)
        if count > 0:
            names = ", ".join(f.name for f in deployed[:3])
            if count > 3:
                names += f" (+ {count - 3} weitere)"
            self.stats_lbl.setText(f"✅ Erfolgreich installiert: {names}")
            self.stats_lbl.setStyleSheet("color: #34d399; font-size: 12px; font-weight: bold;")
        else:
            self.stats_lbl.setText(f"✅ Heruntergeladen nach {local_path.name}")

        self.cancel_btn.setText("Fertig")
        self.download_completed.emit(deployed)

    def _on_download_error(self, error_msg: str):
        self.stats_lbl.setText(f"❌ Download fehlgeschlagen: {error_msg}")
        self.stats_lbl.setStyleSheet("color: #f87171; font-size: 12px; font-weight: bold;")
        self.cancel_btn.setText("Schließen")
        QMessageBox.critical(self, "Download-Fehler", f"Download abgebrochen:\n\n{error_msg}")

    def _on_cancel(self):
        if self.cancel_btn.text() in ["Fertig", "Schließen"]:
            self.accept()
            return

        # Cancel workers if active
        if self.resolve_worker and self.resolve_worker.isRunning():
            self.resolve_worker.requestInterruption()
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.requestInterruption()
            self.download_worker.wait(500)

        self.reject()
