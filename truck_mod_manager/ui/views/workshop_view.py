"""
Steam Workshop View for Truck Mod Manager.
Displays subscribed Workshop items with Steam links and offline backup options.
"""
import subprocess
import webbrowser
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QFileDialog
)

from truck_mod_manager.core.models import ScsMod, TruckGame
from truck_mod_manager.core.workshop_scanner import WorkshopScanner
from truck_mod_manager.ui.widgets.elided_label import ElidedLabel


class WorkshopItemWidget(QFrame):
    def __init__(self, mod: ScsMod, parent=None):
        super().__init__(parent)
        self.mod = mod
        self.setObjectName("cardFrame")
        self.setMinimumHeight(68)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(14)

        # Icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(56, 38)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background-color: #0f172a; border-radius: 4px; border: 1px solid #334155; font-size: 16px;")
        if self.mod.icon_path and Path(self.mod.icon_path).exists():
            pix = QPixmap(self.mod.icon_path)
            if not pix.isNull():
                icon_lbl.setPixmap(pix.scaled(56, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                icon_lbl.setText("⚙️")
        else:
            icon_lbl.setText("⚙️")
        layout.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Info
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_lbl = ElidedLabel(self.mod.display_name)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #f8fafc;")
        info_col.addWidget(title_lbl)

        size_mb = self.mod.file_size / (1024 * 1024)
        sub_lbl = ElidedLabel(f"Workshop ID: {self.mod.workshop_id or 'N/A'}  •  {size_mb:.1f} MB  •  {self.mod.file_name}")
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        info_col.addWidget(sub_lbl)
        layout.addLayout(info_col, stretch=1)

        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        if self.mod.workshop_id:
            link_btn = QPushButton("🌐 Im Web öffnen")
            link_btn.clicked.connect(self._open_web)
            btn_layout.addWidget(link_btn)

        layout.addLayout(btn_layout)

    def _open_web(self):
        if self.mod.workshop_id:
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={self.mod.workshop_id}"
            webbrowser.open(url)


class WorkshopView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.game: Optional[TruckGame] = None
        self.mods: List[ScsMod] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header
        header = QFrame()
        header.setObjectName("headerFrame")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 8, 10, 8)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        title = QLabel("Steam Workshop Abonnements")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc;")
        info_col.addWidget(title)

        self.sub_lbl = QLabel("0 Workshop-Mods gefunden")
        self.sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        info_col.addWidget(self.sub_lbl)
        h_layout.addLayout(info_col, stretch=1)

        refresh_btn = QPushButton("🔄 Neu scannen")
        refresh_btn.clicked.connect(self.refresh)
        h_layout.addWidget(refresh_btn)

        layout.addWidget(header)

        # List
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(6)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.list_widget)

    def set_game(self, game: TruckGame):
        self.game = game
        self.refresh()

    def refresh(self):
        if not self.game:
            return
        self.mods = WorkshopScanner.scan_workshop(self.game.game_type)
        self.list_widget.clear()

        for mod in self.mods:
            item = QListWidgetItem(self.list_widget)
            widget = WorkshopItemWidget(mod)
            item.setSizeHint(QSize(0, 74))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

        self.sub_lbl.setText(f"{len(self.mods)} Workshop-Elemente auf der Festplatte gefunden.")
