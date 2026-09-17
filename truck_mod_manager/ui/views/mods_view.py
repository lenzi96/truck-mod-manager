"""
Main Mods View for Truck Mod Manager.
Displays installed/staged mods, category filters, enable/disable toggles, and mod actions.
"""
import os
import subprocess
from pathlib import Path
from typing import Callable, List, Optional
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QListWidget, QListWidgetItem, QFrame,
    QFileDialog, QMessageBox, QMenu
)

from truck_mod_manager.core.deployer import ModDeployer
from truck_mod_manager.core.models import ModCategory, ScsMod, TruckGame
from truck_mod_manager.ui.dialogs.mod_detail_dialog import ModDetailDialog
from truck_mod_manager.ui.style import CATEGORY_STYLES, get_category_badge_style
from truck_mod_manager.ui.widgets.elided_label import ElidedLabel


class ModCardWidget(QFrame):
    """Custom widget rendered for each mod in the list."""
    toggled = pyqtSignal(bool)
    delete_requested = pyqtSignal(object)

    def __init__(self, mod: ScsMod, game_version: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.mod = mod
        self.game_version = game_version
        self.setObjectName("cardFrame")
        self.setMinimumHeight(84)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(14)

        # Toggle Active Button / Indicator
        self.toggle_btn = QPushButton("✔ Aktiv" if self.mod.is_enabled else "○ Inaktiv")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(self.mod.is_enabled)
        self.toggle_btn.setFixedSize(88, 36)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_toggle_btn_style()
        self.toggle_btn.clicked.connect(self._on_toggled)
        layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Mod Icon Thumbnail (Larger 100x62 format for rich mod art)
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(100, 62)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background-color: #0b0f19; border-radius: 6px; border: 1px solid #243350; font-size: 24px;")

        if self.mod.icon_path and Path(self.mod.icon_path).exists():
            pix = QPixmap(self.mod.icon_path)
            if not pix.isNull():
                icon_lbl.setPixmap(pix.scaled(100, 62, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                icon_lbl.setText("🚛")
        else:
            icon_lbl.setText("🚛")
        layout.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Mod Details Column
        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_lbl = ElidedLabel(self.mod.display_name)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #f8fafc;")
        title_row.addWidget(title_lbl)

        if self.mod.priority > 0:
            pri_lbl = QLabel(f"#{self.mod.priority}")
            pri_lbl.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8); "
                "color: #ffffff; padding: 2px 7px; border-radius: 5px; font-size: 11px; font-weight: bold;"
            )
            title_row.addWidget(pri_lbl)

        title_row.addStretch()
        info_col.addLayout(title_row)

        sub_parts = []
        if self.mod.package_version:
            sub_parts.append(f"v{self.mod.package_version}")
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

        # Badges & Actions column
        badges_col = QHBoxLayout()
        badges_col.setSpacing(6)
        badges_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Workshop Badge
        if self.mod.is_workshop:
            ws_badge = QLabel("🌐 Workshop")
            ws_badge.setStyleSheet("background-color: #0c2136; color: #38bdf8; border: 1px solid #0284c7; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;")
            badges_col.addWidget(ws_badge)

        # Compatibility Badge
        is_compat, compat_msg = self.mod.check_compatibility(self.game_version)
        if is_compat is False:
            compat_badge = QLabel("❌ Inkompatibel")
            compat_badge.setStyleSheet("background-color: #3b1219; color: #fca5a5; border: 1px solid #7f1d1d; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;")
            compat_badge.setToolTip(compat_msg)
            badges_col.addWidget(compat_badge)
        elif is_compat is True and self.mod.compatible_versions:
            compat_badge = QLabel("✔ Kompatibel")
            compat_badge.setStyleSheet("background-color: #063726; color: #6ee7b7; border: 1px solid #059669; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;")
            compat_badge.setToolTip(compat_msg)
            badges_col.addWidget(compat_badge)

        # Primary Category Badge
        cat = self.mod.primary_category
        cat_info = CATEGORY_STYLES.get(cat, CATEGORY_STYLES[ModCategory.OTHER])
        badge = QLabel(cat_info["label"])
        badge.setStyleSheet(get_category_badge_style(cat))
        badges_col.addWidget(badge)

        if self.mod.mp_mod_optional:
            mp_lbl = QLabel("Convoy")
            mp_lbl.setStyleSheet("background-color: #063726; color: #6ee7b7; border: 1px solid #059669; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;")
            badges_col.addWidget(mp_lbl)

        # Action Button on Card
        if self.mod.is_workshop:
            link_btn = QPushButton("↗")
            link_btn.setObjectName("iconBtn")
            link_btn.setToolTip("Steam-Workshop-Seite im Browser öffnen")
            link_btn.setFixedSize(30, 30)
            link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            link_btn.setStyleSheet(
                "QPushButton { background-color: #0c2136; color: #38bdf8; border: 1px solid #0284c7; "
                "border-radius: 6px; font-weight: bold; font-size: 14px; padding: 0px; text-align: center; } "
                "QPushButton:hover { background-color: #0284c7; color: #ffffff; }"
            )
            if self.mod.workshop_id:
                import webbrowser
                link_btn.clicked.connect(lambda: webbrowser.open(f"https://steamcommunity.com/sharedfiles/filedetails/?id={self.mod.workshop_id}"))
            badges_col.addWidget(link_btn)
        else:
            del_btn = QPushButton("✕")
            del_btn.setObjectName("iconBtn")
            del_btn.setToolTip(f"'{self.mod.display_name}' endgültig löschen")
            del_btn.setFixedSize(30, 30)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet(
                "QPushButton { background-color: #3b1219; color: #fca5a5; border: 1px solid #7f1d1d; "
                "border-radius: 6px; font-weight: bold; font-size: 13px; padding: 0px; text-align: center; } "
                "QPushButton:hover { background-color: #ef4444; color: #ffffff; }"
            )
            del_btn.clicked.connect(lambda: self.delete_requested.emit(self.mod))
            badges_col.addWidget(del_btn)

        layout.addLayout(badges_col)

    def _update_toggle_btn_style(self):
        if self.mod.is_enabled:
            self.toggle_btn.setText("✔ Aktiv")
            self.toggle_btn.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #059669); "
                "color: #ffffff; border: 1px solid #34d399; font-weight: bold; border-radius: 7px; font-size: 12px; } "
                "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34d399, stop:1 #047857); }"
            )
        else:
            self.toggle_btn.setText("○ Inaktiv")
            self.toggle_btn.setStyleSheet(
                "QPushButton { background-color: #141d2d; color: #94a3b8; border: 1px solid #243350; "
                "font-weight: 500; border-radius: 7px; font-size: 12px; } "
                "QPushButton:hover { background-color: #1c2740; color: #f8fafc; border-color: #3b82f6; }"
            )

    def _on_toggled(self):
        new_state = self.toggle_btn.isChecked()
        if new_state:
            is_compat, compat_msg = self.mod.check_compatibility(self.game_version)
            if is_compat is False:
                reply = QMessageBox.warning(
                    self,
                    "Inkompatibilitäts-Warnung",
                    f"Die Mod '{self.mod.display_name}' ist für Spielversion {', '.join(self.mod.compatible_versions)} vorgesehen.\n"
                    f"Dein Spiel läuft auf Version v{self.game_version or 'Unbekannt'}.\n\n"
                    "Das Aktivieren inkompatibler Mods kann zu Abstürzen (CTD) führen.\n\n"
                    "Möchtest du die Mod trotzdem aktivieren?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.toggle_btn.setChecked(False)
                    return

        self.mod.is_enabled = new_state
        self._update_toggle_btn_style()
        self.toggled.emit(self.mod.is_enabled)


class ModsView(QWidget):
    """View displaying all scanned / imported mods for the selected game."""
    mods_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game: Optional[TruckGame] = None
        self.all_mods: List[ScsMod] = []
        self.filtered_mods: List[ScsMod] = []
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Toolbar Card Container
        toolbar_card = QFrame()
        toolbar_card.setObjectName("toolbarCard")
        toolbar_layout = QVBoxLayout(toolbar_card)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(8)

        # Top Control Bar (Search, Filter, Actions)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Suchen nach Mod, Datei oder Autor...")
        self.search_input.textChanged.connect(self._apply_filter)
        top_bar.addWidget(self.search_input, stretch=2)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("Alle Kategorien", "all")
        for cat in ModCategory:
            info = CATEGORY_STYLES.get(cat, CATEGORY_STYLES[ModCategory.OTHER])
            self.cat_filter.addItem(info["label"], cat.value)
        self.cat_filter.currentIndexChanged.connect(self._apply_filter)
        top_bar.addWidget(self.cat_filter)

        # Compatibility filter
        self.compat_filter = QComboBox()
        self.compat_filter.addItem("Alle Mods & Quellen", "all")
        self.compat_filter.addItem("Nur Steam Workshop 🌐", "workshop")
        self.compat_filter.addItem("Nur lokale Mods 💾", "local")
        self.compat_filter.addItem("Nur kompatible Mods ✔", "compat")
        self.compat_filter.addItem("Nur inkompatible Mods ❌", "incompat")
        self.compat_filter.addItem("Universelle Mods 🌐", "universal")
        self.compat_filter.currentIndexChanged.connect(self._apply_filter)
        top_bar.addWidget(self.compat_filter)

        # Add Mod Button
        add_btn = QPushButton("➕ Mod hinzufügen")
        add_btn.setObjectName("primaryBtn")
        add_btn.setToolTip(".scs oder .zip Datei importieren")
        add_btn.clicked.connect(self._on_add_mod)
        top_bar.addWidget(add_btn)

        toolbar_layout.addLayout(top_bar)

        # Secondary action row
        sec_bar = QHBoxLayout()
        sec_bar.setSpacing(8)

        self.status_label = QLabel("0 Mods")
        self.status_label.setStyleSheet(
            "background-color: #0b0f19; color: #94a3b8; border: 1px solid #243350; "
            "padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;"
        )
        sec_bar.addWidget(self.status_label)

        sec_bar.addStretch()

        enable_all_btn = QPushButton("✔ Alle an")
        enable_all_btn.setToolTip("Alle aktuell gefilterten Mods aktivieren")
        enable_all_btn.clicked.connect(self._enable_all)
        sec_bar.addWidget(enable_all_btn)

        disable_all_btn = QPushButton("○ Alle aus")
        disable_all_btn.setToolTip("Alle aktuell gefilterten Mods deaktivieren")
        disable_all_btn.clicked.connect(self._disable_all)
        sec_bar.addWidget(disable_all_btn)

        vanilla_btn = QPushButton("🧹 Vanilla Reset")
        vanilla_btn.setObjectName("dangerBtn")
        vanilla_btn.setToolTip("Entfernt alle Symlinks restlos aus dem Spiel-Mod-Ordner")
        vanilla_btn.clicked.connect(self._vanilla_reset)
        sec_bar.addWidget(vanilla_btn)

        deploy_btn = QPushButton("🚀 Bereitstellen")
        deploy_btn.setObjectName("successBtn")
        deploy_btn.setToolTip("Verlinkt alle aktiven Mods in das Spiel")
        deploy_btn.clicked.connect(self._deploy_mods)
        sec_bar.addWidget(deploy_btn)

        toolbar_layout.addLayout(sec_bar)
        layout.addWidget(toolbar_card)

        # Mod List Widget
        self.mod_list = QListWidget()
        self.mod_list.setSpacing(6)
        self.mod_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.mod_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.mod_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mod_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mod_list.customContextMenuRequested.connect(self._show_context_menu)
        self.mod_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.mod_list)

        # Drop hint banner
        drop_hint = QLabel("💡 Tipp: Ziehe .scs oder .zip Dateien direkt per Drag & Drop hierher!")
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_hint.setStyleSheet("color: #64748b; font-size: 11px; padding: 4px;")
        layout.addWidget(drop_hint)

    def set_game(self, game: TruckGame, mods: List[ScsMod]):
        self.game = game
        self.all_mods = mods
        self._apply_filter()

    def _apply_filter(self):
        query = self.search_input.text().strip().lower()
        selected_cat = self.cat_filter.currentData()
        selected_compat = self.compat_filter.currentData()
        game_ver = self.game.detected_game_version if self.game else None

        self.filtered_mods = []
        for m in self.all_mods:
            # Category match
            if selected_cat != "all" and not any(c.value == selected_cat for c in m.categories):
                continue

            # Compatibility & Source match
            if selected_compat != "all":
                if selected_compat == "workshop" and not m.is_workshop:
                    continue
                elif selected_compat == "local" and m.is_workshop:
                    continue
                elif selected_compat in ("compat", "incompat", "universal"):
                    is_comp, _ = m.check_compatibility(game_ver)
                    if selected_compat == "compat" and is_comp is not True:
                        continue
                    elif selected_compat == "incompat" and is_comp is not False:
                        continue
                    elif selected_compat == "universal" and is_comp is not None:
                        continue

            # Query match
            if query:
                match = (
                    query in m.display_name.lower()
                    or query in m.file_name.lower()
                    or query in m.author.lower()
                    or (m.workshop_id and query in m.workshop_id)
                    or (m.is_workshop and "workshop" in query)
                )
                if not match:
                    continue

            self.filtered_mods.append(m)

        self._refresh_list()

    def _refresh_list(self):
        self.mod_list.clear()
        game_ver = self.game.detected_game_version if self.game else None

        for mod in self.filtered_mods:
            item = QListWidgetItem(self.mod_list)
            card = ModCardWidget(mod, game_version=game_ver)
            card.toggled.connect(self._on_mod_toggled)
            card.delete_requested.connect(self._delete_mod)
            item.setSizeHint(QSize(0, 92))
            self.mod_list.addItem(item)
            self.mod_list.setItemWidget(item, card)

        active_count = sum(1 for m in self.all_mods if m.is_enabled)
        self.status_label.setText(f"📦 {len(self.all_mods)} Mods  •  {active_count} aktiv")

    def _on_mod_toggled(self, is_enabled: bool):
        self.mods_changed.emit()
        active_count = sum(1 for m in self.all_mods if m.is_enabled)
        self.status_label.setText(f"📦 {len(self.all_mods)} Mods  •  {active_count} aktiv")

    def _enable_all(self):
        for m in self.filtered_mods:
            m.is_enabled = True
        self._refresh_list()
        self.mods_changed.emit()

    def _disable_all(self):
        for m in self.filtered_mods:
            m.is_enabled = False
        self._refresh_list()
        self.mods_changed.emit()

    def _on_add_mod(self):
        if not self.game:
            return
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Mods importieren (.scs / .zip)",
            "",
            "SCS Mod-Archive (*.scs *.zip);;Alle Dateien (*)"
        )
        if not files:
            return

        imported_count = 0
        for f in files:
            try:
                mod = ModDeployer.import_mod_archive(self.game, Path(f))
                self.all_mods.append(mod)
                imported_count += 1
            except Exception as e:
                QMessageBox.warning(self, "Import-Fehler", f"Konnte {Path(f).name} nicht importieren: {e}")

        if imported_count > 0:
            self._apply_filter()
            self.mods_changed.emit()
            QMessageBox.information(self, "Erfolg", f"{imported_count} Mod(s) erfolgreich importiert.")

    def _deploy_mods(self):
        if not self.game:
            return
        success, msg = ModDeployer.deploy(self.game, self.all_mods)
        if success:
            QMessageBox.information(self, "Bereitstellung", f"Erfolgreich:\n{msg}")
        else:
            QMessageBox.critical(self, "Fehler", f"Bereitstellung fehlgeschlagen:\n{msg}")

    def _vanilla_reset(self):
        if not self.game:
            return
        reply = QMessageBox.question(
            self,
            "Vanilla Reset bestätigen",
            "Möchtest du wirklich alle aktiven Mod-Verknüpfungen aus dem Spiel entfernen?\n"
            "Deine Original-Mod-Dateien in der Bibliothek bleiben vollständig erhalten.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = ModDeployer.vanilla_reset(self.game)
            for m in self.all_mods:
                m.is_enabled = False
            self._refresh_list()
            self.mods_changed.emit()
            QMessageBox.information(self, "Vanilla Reset", msg)

    def _show_context_menu(self, pos):
        item = self.mod_list.itemAt(pos)
        if not item:
            return
        widget = self.mod_list.itemWidget(item)
        if not isinstance(widget, ModCardWidget):
            return

        mod = widget.mod
        menu = QMenu(self)

        detail_act = menu.addAction("🔍 Details anzeigen")
        open_folder_act = menu.addAction("📂 Ordner im Dateimanager öffnen")
        menu.addSeparator()
        delete_act = menu.addAction("🗑️ Mod löschen")

        action = menu.exec(self.mod_list.mapToGlobal(pos))
        if action == detail_act:
            self._open_details(mod)
        elif action == open_folder_act:
            path = Path(mod.file_path).parent
            subprocess.Popen(["xdg-open", str(path)])
        elif action == delete_act:
            self._delete_mod(mod)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        widget = self.mod_list.itemWidget(item)
        if isinstance(widget, ModCardWidget):
            self._open_details(widget.mod)

    def _open_details(self, mod: ScsMod):
        game_ver = self.game.detected_game_version if self.game else None
        dlg = ModDetailDialog(mod, game_version=game_ver, delete_callback=self._delete_mod, parent=self)
        dlg.exec()

    def _delete_mod(self, mod: ScsMod) -> bool:
        if not self.game:
            return False

        status_str = "Aktiv im Spiel (Verknüpfung wird entfernt)" if mod.is_enabled else "Inaktiv"
        size_mb = mod.file_size / (1024 * 1024)
        msg = (
            f"Möchtest du folgende Mod wirklich endgültig von der Festplatte löschen?\n\n"
            f"• Mod-Name: {mod.display_name}\n"
            f"• Datei: {mod.file_name} ({size_mb:.1f} MB)\n"
            f"• Pfad: {mod.file_path}\n"
            f"• Status: {status_str}\n\n"
            "Dieser Vorgang kann nicht rückgängig gemacht werden."
        )
        reply = QMessageBox.question(
            self,
            "Mod endgültig löschen",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            ModDeployer.delete_mod(self.game, mod)
            if mod in self.all_mods:
                self.all_mods.remove(mod)
            self._apply_filter()
            self.mods_changed.emit()
            return True
        return False

    # Drag & Drop support
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if not self.game:
            return
        urls = event.mimeData().urls()
        imported = 0
        for url in urls:
            path = Path(url.toLocalFile())
            if path.suffix.lower() in (".scs", ".zip") or path.is_dir():
                try:
                    mod = ModDeployer.import_mod_archive(self.game, path)
                    self.all_mods.append(mod)
                    imported += 1
                except Exception as e:
                    print(f"[ModsView] Drop error for {path}: {e}")

        if imported > 0:
            self._apply_filter()
            self.mods_changed.emit()
            QMessageBox.information(self, "Import", f"{imported} Mod(s) via Drag & Drop importiert.")
