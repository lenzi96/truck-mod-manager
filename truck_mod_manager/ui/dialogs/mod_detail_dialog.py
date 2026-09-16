"""
Dialog for viewing detailed information about an SCS mod.
Shows manifest metadata, icon, categories, description, and internal archive files.
"""
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QTreeWidget, QTreeWidgetItem, QTabWidget,
    QWidget, QFrame
)
from truck_mod_manager.core.models import ScsMod
from truck_mod_manager.ui.style import CATEGORY_STYLES, get_category_badge_style


class ModDetailDialog(QDialog):
    def __init__(self, mod: ScsMod, game_version: Optional[str] = None, delete_callback=None, parent=None):
        super().__init__(parent)
        self.mod = mod
        self.game_version = game_version
        self.delete_callback = delete_callback
        self.setWindowTitle(f"Mod Details: {mod.display_name}")
        self.setMinimumSize(720, 580)
        self.resize(760, 620)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header section (Icon + Title + Meta)
        header = QFrame()
        header.setObjectName("cardFrame")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 12, 12, 12)
        header_layout.setSpacing(16)

        # Thumbnail / Icon
        icon_label = QLabel()
        icon_label.setFixedSize(140, 82)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background-color: #0f172a; border-radius: 6px; border: 1px solid #334155;")

        if self.mod.icon_path and Path(self.mod.icon_path).exists():
            pix = QPixmap(self.mod.icon_path)
            if not pix.isNull():
                icon_label.setPixmap(pix.scaled(140, 82, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                icon_label.setText("🚛 Mod")
        else:
            icon_label.setText("🚛 Mod")

        header_layout.addWidget(icon_label)

        # Info column
        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        title_lbl = QLabel(self.mod.display_name)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        info_col.addWidget(title_lbl)

        author_lbl = QLabel(f"Autor: <b>{self.mod.author}</b> | Mod-Version: <b>{self.mod.package_version}</b>")
        author_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        info_col.addWidget(author_lbl)

        # File path & size
        size_mb = self.mod.file_size / (1024 * 1024)
        file_lbl = QLabel(f"Datei: {self.mod.file_name} ({size_mb:.1f} MB)")
        file_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        info_col.addWidget(file_lbl)

        # Compatibility info line
        is_compat, compat_msg = self.mod.check_compatibility(self.game_version)
        compat_layout = QHBoxLayout()
        compat_layout.setSpacing(6)
        compat_title = QLabel("Spielversion-Kompatibilität:")
        compat_title.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: bold;")
        compat_layout.addWidget(compat_title)

        if is_compat is False:
            compat_badge = QLabel(f"❌ Inkompatibel ({compat_msg})")
            compat_badge.setStyleSheet("background-color: #7f1d1d; color: #fca5a5; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;")
        elif is_compat is True:
            compat_badge = QLabel(f"✔ Kompatibel ({compat_msg})")
            compat_badge.setStyleSheet("background-color: #064e3b; color: #6ee7b7; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;")
        else:
            compat_badge = QLabel(f"🌐 {compat_msg}")
            compat_badge.setStyleSheet("background-color: #334155; color: #cbd5e1; padding: 2px 8px; border-radius: 4px; font-size: 11px;")

        compat_layout.addWidget(compat_badge)
        compat_layout.addStretch()
        info_col.addLayout(compat_layout)

        # Badges row (Categories & Convoy)
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(6)

        for cat in self.mod.categories:
            cat_info = CATEGORY_STYLES.get(cat, CATEGORY_STYLES[cat.OTHER])
            lbl = QLabel(cat_info["label"])
            lbl.setStyleSheet(get_category_badge_style(cat))
            badges_layout.addWidget(lbl)

        if self.mod.mp_mod_optional:
            mp_lbl = QLabel("Convoy Optional")
            mp_lbl.setStyleSheet("background-color: #065f46; color: #6ee7b7; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;")
            badges_layout.addWidget(mp_lbl)

        badges_layout.addStretch()
        info_col.addLayout(badges_layout)

        header_layout.addLayout(info_col)
        layout.addWidget(header)

        # Tabs for Description & Contained Files
        tabs = QTabWidget()

        # Tab 1: Description
        desc_widget = QWidget()
        desc_layout = QVBoxLayout(desc_widget)
        desc_layout.setContentsMargins(8, 8, 8, 8)

        text_browser = QTextBrowser()
        if self.mod.description:
            text_browser.setPlainText(self.mod.description)
        else:
            text_browser.setHtml("<p style='color: #64748b; font-style: italic;'>Keine Beschreibung im Mod-Archiv gefunden.</p>")
        desc_layout.addWidget(text_browser)
        tabs.addTab(desc_widget, "Beschreibung")

        # Tab 2: Internal Files Tree
        files_widget = QWidget()
        files_layout = QVBoxLayout(files_widget)
        files_layout.setContentsMargins(8, 8, 8, 8)

        files_tree = QTreeWidget()
        files_tree.setHeaderLabels(["Enthaltene Datei / Pfad"])
        files_tree.setAlternatingRowColors(True)

        for fpath in sorted(self.mod.internal_files):
            QTreeWidgetItem(files_tree, [fpath])

        files_info = QLabel(f"Gesamt: {len(self.mod.internal_files)} Dateien im Archiv")
        files_info.setStyleSheet("color: #94a3b8; font-size: 11px; margin-top: 4px;")

        files_layout.addWidget(files_tree)
        files_layout.addWidget(files_info)
        tabs.addTab(files_widget, f"Dateien ({len(self.mod.internal_files)})")

        layout.addWidget(tabs)

        # Footer Buttons
        btn_layout = QHBoxLayout()

        if self.delete_callback:
            del_btn = QPushButton("🗑️ Mod löschen")
            del_btn.setObjectName("dangerBtn")
            del_btn.clicked.connect(self._on_delete)
            btn_layout.addWidget(del_btn)

        btn_layout.addStretch()
        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _on_delete(self):
        if self.delete_callback:
            if self.delete_callback(self.mod):
                self.accept()
