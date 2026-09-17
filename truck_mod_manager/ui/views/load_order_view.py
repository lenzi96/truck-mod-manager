"""
Dedicated Load Order view for Truck Mod Manager.
Manages priority ordering (1 = highest), SCS community auto-sorting, and conflict diagnostics.
"""
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QMenu
)

from truck_mod_manager.core.conflict_detector import ConflictDetector
from truck_mod_manager.core.deployer import ModDeployer
from truck_mod_manager.core.load_order import LoadOrderManager
from truck_mod_manager.core.models import ConflictFile, ConflictSeverity, ModCategory, ScsMod, TruckGame
from truck_mod_manager.ui.dialogs.conflict_dialog import ConflictDialog
from truck_mod_manager.ui.dialogs.mod_detail_dialog import ModDetailDialog
from truck_mod_manager.ui.style import CATEGORY_STYLES, get_category_badge_style
from truck_mod_manager.ui.widgets.elided_label import ElidedLabel


class LoadOrderItemWidget(QFrame):
    """Row item in the load order list."""

    def __init__(
        self,
        mod: ScsMod,
        conflict_count: int = 0,
        critical_conflict_count: int = 0,
        game_version: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.mod = mod
        self.setObjectName("cardFrame")
        self.setMinimumHeight(78)
        self.conflict_count = conflict_count
        self.critical_conflict_count = critical_conflict_count
        self.game_version = game_version
        if self.mod.is_missing:
            self.setStyleSheet(
                "#cardFrame { background-color: #2b1219; border: 1px dashed #ef4444; border-radius: 8px; }"
            )
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(14)

        # Priority badge (#1, #2, ...)
        prio_lbl = QLabel(f"#{self.mod.priority}")
        prio_lbl.setFixedSize(50, 36)
        prio_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prio_lbl.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8); "
            "color: #ffffff; border-radius: 6px; border: 1px solid #3b82f6; "
            "font-weight: bold; font-size: 13px; padding: 4px;"
        )
        layout.addWidget(prio_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Thumbnail (Enlarged 86x54)
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(86, 54)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background-color: #0b0f19; border-radius: 6px; border: 1px solid #243350; font-size: 20px;")
        if self.mod.icon_path and Path(self.mod.icon_path).exists():
            pix = QPixmap(self.mod.icon_path)
            if not pix.isNull():
                icon_lbl.setPixmap(pix.scaled(86, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                icon_lbl.setText("🚛")
        else:
            icon_lbl.setText("🚛")
        layout.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Title & filename
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_lbl = ElidedLabel(self.mod.display_name)
        if self.mod.is_missing:
            title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #f87171;")
        else:
            title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #f8fafc;")
        info_col.addWidget(title_lbl)

        sub_parts = []
        if self.mod.is_missing:
            sub_parts.append("⚠️ Mod-Datei nicht auf Festplatte gefunden")
        if self.mod.author and self.mod.author.lower() != "unknown":
            sub_parts.append(f"von {self.mod.author}")
        if self.mod.is_workshop:
            sub_parts.append(f"Workshop #{self.mod.workshop_id or 'Abo'}")
        else:
            sub_parts.append(self.mod.file_name)

        sub_lbl = ElidedLabel("  •  ".join(sub_parts))
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        info_col.addWidget(sub_lbl)
        layout.addLayout(info_col, stretch=1)

        # Badges column
        badges_col = QHBoxLayout()
        badges_col.setSpacing(6)
        badges_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Missing Mod Badge
        if self.mod.is_missing:
            missing_badge = QLabel("⚠️ Nicht installiert")
            missing_badge.setStyleSheet(
                "background-color: #3b1219; color: #fecaca; border: 1px solid #ef4444; "
                "padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;"
            )
            missing_badge.setToolTip("Diese Mod ist im Spielstand/Profil aktiviert, die .scs/.zip-Datei wurde jedoch nicht im Mod-Verzeichnis gefunden.")
            badges_col.addWidget(missing_badge)

        # Workshop Badge
        if self.mod.is_workshop:
            ws_badge = QLabel("🌐 Workshop")
            ws_badge.setStyleSheet("background-color: #0c2136; color: #38bdf8; border: 1px solid #0284c7; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;")
            badges_col.addWidget(ws_badge)

        # Compatibility Badge if incompatible
        is_compat, compat_msg = self.mod.check_compatibility(self.game_version)
        if is_compat is False:
            compat_badge = QLabel("❌ Inkompatibel")
            compat_badge.setStyleSheet("background-color: #3b1219; color: #fca5a5; border: 1px solid #7f1d1d; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;")
            compat_badge.setToolTip(compat_msg)
            badges_col.addWidget(compat_badge)

        # Category Badge
        cat = self.mod.primary_category
        cat_info = CATEGORY_STYLES.get(cat, CATEGORY_STYLES[ModCategory.OTHER])
        cat_badge = QLabel(cat_info["label"])
        cat_badge.setStyleSheet(get_category_badge_style(cat))
        badges_col.addWidget(cat_badge)

        # Conflict Badge (if any)
        if self.critical_conflict_count > 0:
            conf_badge = QLabel(f"🔴 {self.critical_conflict_count} kritisch")
            conf_badge.setStyleSheet(
                "background-color: #3b1219; color: #fecaca; padding: 3px 8px; "
                "border-radius: 6px; font-size: 11px; font-weight: bold; border: 1px solid #ef4444;"
            )
            conf_badge.setToolTip(f"Diese Mod enthält {self.critical_conflict_count} kritische Kollision(en) (z. B. Spieldaten, Fahrphysik oder Kartensektoren). Gesamt: {self.conflict_count} Kollision(en).")
            badges_col.addWidget(conf_badge)
        elif self.conflict_count > 0:
            conf_badge = QLabel(f"⚠️ {self.conflict_count} Kollision(en)")
            conf_badge.setStyleSheet(
                "background-color: #3d1c06; color: #fef08a; padding: 3px 8px; "
                "border-radius: 6px; font-size: 11px; font-weight: bold; border: 1px solid #d97706;"
            )
            conf_badge.setToolTip(f"Diese Mod enthält {self.conflict_count} Datei-Kollision(en), die von anderen Mods überschrieben werden oder diese überschreiben.")
            badges_col.addWidget(conf_badge)

        layout.addLayout(badges_col)


class LoadOrderView(QWidget):
    """Interactive Load Order manager with Smart Auto-Sort."""
    order_changed = pyqtSignal()
    reload_from_profile_requested = pyqtSignal()
    reload_from_log_requested = pyqtSignal()

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
        header_card.setObjectName("toolbarCard")
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

        # Reload from profile button
        self.reload_sii_btn = QPushButton("🔄 Spielstand")
        self.reload_sii_btn.setToolTip("Liest die originale Mod-Ladereihenfolge direkt aus der Spielstand-Datei (profile.sii / save) des ausgewählten Profils ein.")
        self.reload_sii_btn.clicked.connect(lambda: self.reload_from_profile_requested.emit())
        header_layout.addWidget(self.reload_sii_btn)

        # Reload from log button
        self.reload_log_btn = QPushButton("📄 game.log")
        self.reload_log_btn.setToolTip("Liest die zuletzt im Spiel geladenen Mods direkt aus der game.log.txt ein (exakte In-Game-Reihenfolge).")
        self.reload_log_btn.clicked.connect(lambda: self.reload_from_log_requested.emit())
        header_layout.addWidget(self.reload_log_btn)

        # Auto-Sort Button
        auto_sort_btn = QPushButton("⚡ Auto-Sort")
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
        self.list_widget.setSpacing(6)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        content_layout.addWidget(self.list_widget, stretch=1)

        # Right Side Control Buttons
        btn_col = QVBoxLayout()
        btn_col.setSpacing(8)

        top_btn = QPushButton("▲▲ Ganz oben")
        top_btn.setFixedWidth(130)
        top_btn.clicked.connect(self._move_top)
        btn_col.addWidget(top_btn)

        up_btn = QPushButton("▲ Nach oben")
        up_btn.setFixedWidth(130)
        up_btn.clicked.connect(self._move_up)
        btn_col.addWidget(up_btn)

        down_btn = QPushButton("▼ Nach unten")
        down_btn.setFixedWidth(130)
        down_btn.clicked.connect(self._move_down)
        btn_col.addWidget(down_btn)

        bottom_btn = QPushButton("▼▼ Ganz unten")
        bottom_btn.setFixedWidth(130)
        bottom_btn.clicked.connect(self._move_bottom)
        btn_col.addWidget(bottom_btn)

        btn_col.addSpacing(16)

        detail_btn = QPushButton("🔍 Details")
        detail_btn.setFixedWidth(130)
        detail_btn.clicked.connect(self._view_selected_detail)
        btn_col.addWidget(detail_btn)

        deactivate_btn = QPushButton("○ Deaktivieren")
        deactivate_btn.setFixedWidth(130)
        deactivate_btn.clicked.connect(self._deactivate_selected)
        btn_col.addWidget(deactivate_btn)

        btn_col.addStretch()

        deploy_btn = QPushButton("🚀 Bereitstellen")
        deploy_btn.setObjectName("successBtn")
        deploy_btn.setFixedWidth(130)
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
        crit_counts = ConflictDetector.get_mod_critical_conflict_counts(self.active_mods)
        crit_total = sum(1 for c in self.current_conflicts if c.severity == ConflictSeverity.CRITICAL)
        warn_total = sum(1 for c in self.current_conflicts if c.severity == ConflictSeverity.WARNING)

        if crit_total > 0:
            self.conflicts_btn.setText(f"🔴 {crit_total} Kritisch ({len(self.current_conflicts)})")
            self.conflicts_btn.setStyleSheet(
                "background-color: #7f1d1d; color: #fecaca; font-weight: bold; border: 1px solid #ef4444; border-radius: 6px; padding: 5px 12px;"
            )
        elif warn_total > 0:
            self.conflicts_btn.setText(f"🟡 {warn_total} Warnungen ({len(self.current_conflicts)})")
            self.conflicts_btn.setStyleSheet(
                "background-color: #78350f; color: #fef08a; font-weight: bold; border: 1px solid #f59e0b; border-radius: 6px; padding: 5px 12px;"
            )
        elif self.current_conflicts:
            self.conflicts_btn.setText(f"🔵 {len(self.current_conflicts)} Kollisionen")
            self.conflicts_btn.setStyleSheet(
                "background-color: #0c4a6e; color: #bae6fd; font-weight: bold; border: 1px solid #0284c7; border-radius: 6px; padding: 5px 12px;"
            )
        else:
            self.conflicts_btn.setText("✔ 0 Konflikte")
            self.conflicts_btn.setStyleSheet(
                "background-color: #064e3b; color: #a7f3d0; font-weight: bold; border: 1px solid #10b981; border-radius: 6px; padding: 5px 12px;"
            )

        self.list_widget.clear()
        game_ver = self.game.detected_game_version if self.game else None
        for mod in self.active_mods:
            item = QListWidgetItem(self.list_widget)
            item_widget = LoadOrderItemWidget(
                mod,
                conflict_count=conflict_counts.get(mod.display_name, 0),
                critical_conflict_count=crit_counts.get(mod.display_name, 0),
                game_version=game_ver
            )
            item.setSizeHint(QSize(0, 86))
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
