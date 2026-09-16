"""
Telemetry and Plugins View for Truck Mod Manager.
Manages plugins in bin/linux_x64/plugins or bin/win_x64/plugins.
"""
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QFileDialog, QMessageBox
)

from truck_mod_manager.core.models import TruckGame
from truck_mod_manager.core.telemetry_manager import TelemetryManager


class TelemetryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.game: Optional[TruckGame] = None
        self.plugins = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Info Card
        header = QFrame()
        header.setObjectName("headerFrame")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 8, 10, 8)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        title = QLabel("🔌 Telemetrie & Spiel-Plugins")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc;")
        info_col.addWidget(title)
        self.path_lbl = QLabel("Plugin-Verzeichnis: Nicht geladen")
        self.path_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        info_col.addWidget(self.path_lbl)
        h_layout.addLayout(info_col, stretch=1)

        install_btn = QPushButton("➕ Plugin installieren...")
        install_btn.setObjectName("primaryBtn")
        install_btn.clicked.connect(self._install_plugin)
        h_layout.addWidget(install_btn)

        layout.addWidget(header)

        # Proton Note / Diagnostic Card
        self.pfx_card = QFrame()
        self.pfx_card.setObjectName("cardFrame")
        pfx_layout = QVBoxLayout(self.pfx_card)
        pfx_layout.setContentsMargins(10, 8, 10, 8)
        self.pfx_text = QLabel()
        self.pfx_text.setWordWrap(True)
        self.pfx_text.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        pfx_layout.addWidget(self.pfx_text)
        layout.addWidget(self.pfx_card)

        # Plugins Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Status",
            "Plugin-Name",
            "Typ",
            "Aktionen"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def set_game(self, game: TruckGame):
        self.game = game
        self.refresh()

    def refresh(self):
        if not self.game or not self.game.plugins_dir:
            self.path_lbl.setText("Plugin-Verzeichnis nicht verfügbar (Spielpfad prüfen).")
            self.table.setRowCount(0)
            return

        pdir = self.game.plugins_dir
        self.path_lbl.setText(f"Plugin-Ordner: {pdir}")

        if self.game.is_proton:
            self.pfx_text.setText(
                "💡 <b>Steam Proton Modus aktiv</b>: Plugins werden als Windows <code>.dll</code> geladen "
                "(z. B. für ETS2 Telemetry Server, SimHub). Falls eine DLL nicht geladen wird, stelle sicher, "
                "dass Wine-DLL-Overrides konfiguriert sind."
            )
        else:
            self.pfx_text.setText(
                "💡 <b>Linux Native Modus aktiv</b>: Plugins werden als native <code>.so</code> Bibliotheken "
                "in <code>bin/linux_x64/plugins/</code> geladen."
            )

        self.plugins = TelemetryManager.list_plugins(self.game)
        self.table.setRowCount(len(self.plugins))

        for row, p in enumerate(self.plugins):
            # Status
            status_item = QTableWidgetItem("✔ Aktiv" if p["is_enabled"] else "○ Deaktiviert")
            if p["is_enabled"]:
                status_item.setForeground(Qt.GlobalColor.green)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, status_item)

            # Name
            name_item = QTableWidgetItem(p["name"])
            self.table.setItem(row, 1, name_item)

            # Type
            type_str = "Native .so" if p["is_native"] else ("Windows .dll" if p["is_dll"] else "Plugin")
            type_item = QTableWidgetItem(type_str)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, type_item)

            # Action Buttons Widget
            btn_frame = QWidget()
            btn_layout = QHBoxLayout(btn_frame)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(6)

            toggle_btn = QPushButton("Deaktivieren" if p["is_enabled"] else "Aktivieren")
            toggle_btn.clicked.connect(lambda _, path=Path(p["file_path"]): self._toggle(path))
            btn_layout.addWidget(toggle_btn)

            del_btn = QPushButton("🗑️")
            del_btn.setObjectName("dangerBtn")
            del_btn.setToolTip("Plugin löschen")
            del_btn.clicked.connect(lambda _, path=Path(p["file_path"]): self._delete(path))
            btn_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 3, btn_frame)

    def _toggle(self, path: Path):
        TelemetryManager.toggle_plugin(path)
        self.refresh()

    def _delete(self, path: Path):
        reply = QMessageBox.question(
            self,
            "Plugin löschen",
            f"Plugin '{path.name}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            TelemetryManager.remove_plugin(path)
            self.refresh()

    def _install_plugin(self):
        if not self.game:
            return
        ext_filter = "Plugins (*.dll *.so);;Alle Dateien (*)" if self.game.is_proton else "Native Plugins (*.so);;Alle Dateien (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Plugin auswählen", "", ext_filter)
        if files:
            count = 0
            for f in files:
                try:
                    TelemetryManager.install_plugin(self.game, Path(f))
                    count += 1
                except Exception as e:
                    QMessageBox.critical(self, "Fehler", f"Konnte Plugin nicht installieren: {e}")
            if count > 0:
                self.refresh()
                QMessageBox.information(self, "Installiert", f"{count} Plugin(s) installiert.")
