"""
Dedicated Load Order view for Truck Mod Manager.
Manages priority ordering (1 = highest), SCS community auto-sorting, and conflict diagnostics.
"""
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QMenu
)

from truck_mod_manager.core.conflict_detector import ConflictDetector
from truck_mod_manager.core.deployer import ModDeployer
from truck_mod_manager.core.load_order import LoadOrderManager
from truck_mod_manager.core.models import ConflictFile, ModCategory, ScsMod, TruckGame
from truck_mod_manager.ui.dialogs.conflict_dialog import ConflictDialog
from truck_mod_manager.ui.dialogs.mod_detail_dialog import ModDetailDialog
from truck_mod_manager.ui.style import CATEGORY_STYLES, get_category_badge_style


class LoadOrderItemWidget(QFrame):
    """Row item in the load order list."""

    def __init__(self, mod: ScsMod, conflict_count: int = 0, game_version: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.mod = mod
        self.setObjectName("cardFrame")
        self.conflict_count = conflict_count
        self.game_version = game_version
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        # Priority badge (#1, #2, ...)
        prio_lbl = QLabel(f"#{self.mod.priority}")
        prio_lbl.setFixedWidth(42)
        prio_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prio_lbl.setStyleSheet(
            "background-color: #2563eb; color: #ffffff; border-radius: 4px; "
            "font-weight: bold; font-size: 13px; padding: 4px;"
        )
        layout.addWidget(prio_lbl)

        # Small thumbnail
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(50, 30)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background-color: #0f172a; border-radius: 3px; border: 1px solid #334155;")
        if self.mod.icon_path and Path(self.mod.icon_path).exists():
            pix = QPixmap(self.mod.icon_path)
            if not pix.isNull():
                icon_lbl.setPixmap(pix.scaled(50, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                icon_lbl.setText("🚛")
        else:
            icon_lbl.setText("🚛")
        layout.addWidget(icon_lbl)

        # Title & filename
        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        title_lbl = QLabel(self.mod.display_name)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #f8fafc;")
        info_col.addWidget(title_lbl)

        sub_lbl = QLabel(f"{self.mod.file_name} • von {self.mod.author}")
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        info_col.addWidget(sub_lbl)
        layout.addLayout(info_col, stretch=1)

        # Compatibility Badge if incompatible
        is_compat, compat_msg = self.mod.check_compatibility(self.game_version)
        if is_compat is False:
            compat_badge = QLabel("❌ Inkompatibel")
            compat_badge.setStyleSheet("background-color: #7f1d1d; color: #fca5a5; padding: 3px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;")
            compat_badge.setToolTip(compat_msg)
            layout.addWidget(compat_badge)

        # Category Badge
        cat = self.mod.primary_category
        cat_info = CATEGORY_STYLES.get(cat, CATEGORY_STYLES[ModCategory.OTHER])
        cat_badge = QLabel(cat_info["label"])
        cat_badge.setStyleSheet(get_category_badge_style(cat))
        layout.addWidget(cat_badge)

        # Conflict Badge (if any)
        if self.conflict_count > 0:
            conf_badge = QLabel(f"⚠️ {self.conflict_count} Kollision(en)")
            conf_badge.setStyleSheet(
                "background-color: #78350f; color: #fef08a; padding: 3px 8px; "
                "border-radius: 4px; font-size: 11px; font-weight: bold;"
            )
            conf_badge.setToolTip("Diese Mod enthält Dateien, die auch in anderen aktiven Mods vorkommen.")
            layout.addWidget(conf_badge)


class LoadOrderView(QWidget):
    """Interactive Load Order manager with Smart Auto-Sort."""
    order_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game: Optional[TruckGame] = None
        self.all_mods: List[ScsMod] = []
        self.active_mods: List[ScsMod] = []
        self.current_conflicts: List[ConflictFile] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Info & Action Toolbar
        header_card = QFrame()
        header_card.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(10)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        title = QLabel("Ladereihenfolge & Priorität (Load Order)")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc;")
        info_col.addWidget(title)

        desc = QLabel("Position 1 (oben) hat die höchste Priorität und überschreibt darunterliegende Mods.")
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        info_col.addWidget(desc)
        header_layout.addLayout(info_col, stretch=1)

        # Auto-Sort Button
        auto_sort_btn = QPushButton("⚡ SCS Community Auto-Sort")
        auto_sort_btn.setObjectName("primaryBtn")
        auto_sort_btn.setToolTip("Sortiert aktive Mods automatisch nach der bewährten SCS-Modding-Hierarchie (Maps, Modelle, Sounds, LKWs, Physik, UI).")
        auto_sort_btn.clicked.connect(self._on_auto_sort)
        header_layout.addWidget(auto_sort_btn)

        # Conflict Inspector Button
        self.conflicts_btn = QPushButton("⚠️ 0 Konflikte")
        self.conflicts_btn.clicked.connect(self._show_conflicts)
        header_layout.addWidget(self.conflicts_btn)

        layout.addWidget(header_card)

        # Main Central Area (List on Left, Control Buttons on Right)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        content_layout.addWidget(self.list_widget, stretch=1)

        # Right Side Control Buttons
        btn_col = QVBoxLayout()
        btn_col.setSpacing(8)

        top_btn = QPushButton("⏫ Nach ganz oben")
        top_btn.clicked.connect(self._move_top)
        btn_col.addWidget(top_btn)

        up_btn = QPushButton("▲ Eins nach oben")
        up_btn.clicked.connect(self._move_up)
        btn_col.addWidget(up_btn)

        down_btn = QPushButton("▼ Eins nach unten")
        down_btn.clicked.connect(self._move_down)
        btn_col.addWidget(down_btn)

        bottom_btn = QPushButton("⏬ Nach ganz unten")
        bottom_btn.clicked.connect(self._move_bottom)
        btn_col.addWidget(bottom_btn)

        btn_col.addSpacing(16)

        detail_btn = QPushButton("🔍 Details")
        detail_btn.clicked.connect(self._view_selected_detail)
        btn_col.addWidget(detail_btn)

        deactivate_btn = QPushButton("○ Deaktivieren")
        deactivate_btn.clicked.connect(self._deactivate_selected)
        btn_col.addWidget(deactivate_btn)

        btn_col.addStretch()

        deploy_btn = QPushButton("🚀 Bereitstellen")
        deploy_btn.setObjectName("successBtn")
        deploy_btn.clicked.connect(self._deploy)
        btn_col.addWidget(deploy_btn)

        content_layout.addLayout(btn_col)
        layout.addLayout(content_layout)

    def set_game(self, game: TruckGame, all_mods: List[ScsMod]):
        self.game = game
        self.all_mods = all_mods
        self.refresh()

    def refresh(self):
        # Extract active mods
        self.active_mods = [m for m in self.all_mods if m.is_enabled]
        # Sort by priority ascending (1 = highest)
        self.active_mods.sort(key=lambda m: m.priority if m.priority > 0 else 99999)
        LoadOrderManager.reindex_priorities(self.active_mods)

        # Check conflicts
        self.current_conflicts = ConflictDetector.find_conflicts(self.active_mods)
        conflict_counts = ConflictDetector.get_mod_conflict_counts(self.active_mods)

        if self.current_conflicts:
            self.conflicts_btn.setText(f"⚠️ {len(self.current_conflicts)} Konflikte")
            self.conflicts_btn.setObjectName("warningBtn")
        else:
            self.conflicts_btn.setText("✔ Keine Konflikte")
            self.conflicts_btn.setObjectName("")
        self.conflicts_btn.setStyleSheet(self.conflicts_btn.styleSheet())

        self.list_widget.clear()
        game_ver = self.game.detected_game_version if self.game else None
        for mod in self.active_mods:
            item = QListWidgetItem(self.list_widget)
            item_widget = LoadOrderItemWidget(mod, conflict_counts.get(mod.display_name, 0), game_version=game_ver)
            item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, item_widget)

    def _on_rows_moved(self, parent, start, end, destination, row):
        # Re-construct active_mods from the new sequence in list_widget
        new_active = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            w = self.list_widget.itemWidget(item)
            if isinstance(w, LoadOrderItemWidget):
                new_active.append(w.mod)

        self.active_mods = new_active
        LoadOrderManager.reindex_priorities(self.active_mods)
        self.refresh()
        self.order_changed.emit()

    def _on_auto_sort(self):
        if not self.active_mods:
            return
        sorted_mods = LoadOrderManager.auto_sort(self.all_mods)
        # Update self.all_mods
        self.all_mods.clear()
        self.all_mods.extend(sorted_mods)
        self.refresh()
        self.order_changed.emit()
        QMessageBox.information(
            self,
            "Auto-Sort abgeschlossen",
            "Die aktiven Mods wurden erfolgreich nach der SCS-Community-Hierarchie sortiert."
        )

    def _move_up(self):
        idx = self.list_widget.currentRow()
        if idx > 0:
            LoadOrderManager.move_up(self.active_mods, idx)
            self.refresh()
            self.list_widget.setCurrentRow(idx - 1)
            self.order_changed.emit()

    def _move_down(self):
        idx = self.list_widget.currentRow()
        if 0 <= idx < len(self.active_mods) - 1:
            LoadOrderManager.move_down(self.active_mods, idx)
            self.refresh()
            self.list_widget.setCurrentRow(idx + 1)
            self.order_changed.emit()

    def _move_top(self):
        idx = self.list_widget.currentRow()
        if idx > 0:
            LoadOrderManager.move_to_top(self.active_mods, idx)
            self.refresh()
            self.list_widget.setCurrentRow(0)
            self.order_changed.emit()

    def _move_bottom(self):
        idx = self.list_widget.currentRow()
        if 0 <= idx < len(self.active_mods) - 1:
            LoadOrderManager.move_to_bottom(self.active_mods, idx)
            self.refresh()
            self.list_widget.setCurrentRow(len(self.active_mods) - 1)
            self.order_changed.emit()

    def _deactivate_selected(self):
        idx = self.list_widget.currentRow()
        if 0 <= idx < len(self.active_mods):
            mod = self.active_mods[idx]
            mod.is_enabled = False
            mod.priority = 0
            self.refresh()
            self.order_changed.emit()

    def _view_selected_detail(self):
        idx = self.list_widget.currentRow()
        if 0 <= idx < len(self.active_mods):
            game_ver = self.game.detected_game_version if self.game else None
            dlg = ModDetailDialog(self.active_mods[idx], game_version=game_ver, parent=self)
            dlg.exec()

    def _on_double_click(self, item):
        w = self.list_widget.itemWidget(item)
        if isinstance(w, LoadOrderItemWidget):
            game_ver = self.game.detected_game_version if self.game else None
            dlg = ModDetailDialog(w.mod, game_version=game_ver, parent=self)
            dlg.exec()

    def _show_conflicts(self):
        dlg = ConflictDialog(self.current_conflicts, self)
        dlg.exec()

    def _deploy(self):
        if not self.game:
            return
        success, msg = ModDeployer.deploy(self.game, self.all_mods)
        if success:
            QMessageBox.information(self, "Bereitstellung", f"Erfolgreich:\n{msg}")
        else:
            QMessageBox.critical(self, "Fehler", f"Bereitstellung fehlgeschlagen:\n{msg}")
