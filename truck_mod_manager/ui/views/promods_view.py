"""
ProMods Toolkit View for Truck Mod Manager.
Provides status validation for ProMods packs (Europe, Middle East, Steppe, TCP, Canada),
missing component detection, 1-click official load order application, and combo guides.
"""
from typing import Dict, List, Optional
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget
)

from truck_mod_manager.core.deployer import ModDeployer
from truck_mod_manager.core.downloader import ArchiveExtractor
from truck_mod_manager.core.models import GameType, ScsMod, TruckGame
from truck_mod_manager.core.promods_manager import (
    ProModsManager, ProModsPackStatus, ProModsPackType
)
from truck_mod_manager.ui.dialogs.promods_download_dialog import ProModsDownloadDialog
from truck_mod_manager.ui.dialogs.url_download_dialog import UrlDownloadDialog
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget
)


class ProModsPackCard(QFrame):
    download_requested = pyqtSignal(object)

    def __init__(self, pack_status: ProModsPackStatus, parent=None):
        super().__init__(parent)
        self.pack_status = pack_status
        self.setObjectName("promodsCard")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header: Title + Installed/Web Versions + Status Badge + Download Button
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        title_lbl = QLabel(self.pack_status.title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")
        top_row.addWidget(title_lbl)

        # Installed version badge
        if self.pack_status.version:
            ver_lbl = QLabel(f"v{self.pack_status.version}")
            ver_lbl.setStyleSheet("""
                font-size: 11px;
                color: #60a5fa;
                background-color: #1e3a8a;
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: bold;
            """)
            ver_lbl.setToolTip(f"Installierte Version: v{self.pack_status.version}")
            top_row.addWidget(ver_lbl)

        # Latest web version badge
        if self.pack_status.latest_version:
            web_lbl = QLabel(f"Web: v{self.pack_status.latest_version}")
            web_lbl.setStyleSheet("""
                font-size: 11px;
                color: #94a3b8;
                background-color: #1e293b;
                padding: 2px 8px;
                border: 1px solid #334155;
                border-radius: 4px;
                font-weight: 500;
            """)
            web_lbl.setToolTip(f"Offizielle Version auf promods.net: v{self.pack_status.latest_version} ({self.pack_status.game_compatibility})")
            top_row.addWidget(web_lbl)

        top_row.addStretch()

        # Status badge (Aktuell vs Update vs Unvollständig vs Nicht installiert)
        badge = QLabel()
        badge.setStyleSheet("font-size: 11px; font-weight: bold; padding: 4px 10px; border-radius: 6px;")

        if self.pack_status.is_complete:
            if self.pack_status.is_update_available:
                badge.setText(f"🔄 Update auf v{self.pack_status.latest_version} verfügbar")
                badge.setStyleSheet(badge.styleSheet() + "background-color: #431407; color: #fb923c; border: 1px solid #c2410c;")
                self.setStyleSheet("QFrame#promodsCard { background-color: #241611; border: 1px solid #c2410c; border-radius: 8px; }")
            else:
                badge.setText(f"✅ Aktuell (v{self.pack_status.version or self.pack_status.latest_version})")
                badge.setStyleSheet(badge.styleSheet() + "background-color: #064e3b; color: #34d399; border: 1px solid #059669;")
                self.setStyleSheet("QFrame#promodsCard { background-color: #13271d; border: 1px solid #059669; border-radius: 8px; }")
        elif self.pack_status.is_installed:
            if self.pack_status.is_update_available:
                badge.setText(f"⚠️ Unvollständig (Update v{self.pack_status.latest_version})")
                badge.setStyleSheet(badge.styleSheet() + "background-color: #451a03; color: #fbbf24; border: 1px solid #d97706;")
            else:
                badge.setText(f"⚠️ {self.pack_status.total_found}/{self.pack_status.total_required} Unvollständig")
                badge.setStyleSheet(badge.styleSheet() + "background-color: #451a03; color: #fbbf24; border: 1px solid #d97706;")
            self.setStyleSheet("QFrame#promodsCard { background-color: #261e14; border: 1px solid #d97706; border-radius: 8px; }")
        else:
            badge.setText(f"⚪ Nicht installiert (v{self.pack_status.latest_version or '?'})")
            badge.setStyleSheet(badge.styleSheet() + "background-color: #141d2d; color: #64748b; border: 1px solid #243350;")
            self.setStyleSheet("QFrame#promodsCard { background-color: #131b2e; border: 1px solid #243350; border-radius: 8px; }")

        top_row.addWidget(badge)

        # Dedicated Download button on the card
        dl_btn = QPushButton("⬇️ Download")
        dl_btn.setFixedHeight(28)
        if not self.pack_status.is_installed or self.pack_status.is_update_available:
            dl_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2563eb;
                    color: #ffffff;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 5px;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    background-color: #1d4ed8;
                }
            """)
        else:
            dl_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #cbd5e1;
                    font-size: 11px;
                    border: 1px solid #334155;
                    border-radius: 5px;
                    padding: 0 10px;
                }
                QPushButton:hover {
                    background-color: #334155;
                    color: #ffffff;
                }
            """)
        dl_btn.setToolTip(f"Download-Optionen für {self.pack_status.title} (Offizielle Seite / Schnelldownload-Direktlink)")
        dl_btn.clicked.connect(lambda: self.download_requested.emit(self.pack_status))
        top_row.addWidget(dl_btn)

        layout.addLayout(top_row)

        # Missing components warning if incomplete
        if self.pack_status.is_installed and not self.pack_status.is_complete:
            missing_text = "Fehlende Dateien: " + ", ".join(self.pack_status.missing_names)
            warn_lbl = QLabel(missing_text)
            warn_lbl.setWordWrap(True)
            warn_lbl.setStyleSheet("color: #f87171; font-size: 11px; font-weight: bold; padding: 4px; background-color: #450a0a; border-radius: 4px;")
            layout.addWidget(warn_lbl)

        # Component List
        comp_frame = QFrame()
        comp_frame.setStyleSheet("background-color: rgba(0, 0, 0, 0.2); border-radius: 6px; padding: 4px;")
        comp_layout = QVBoxLayout(comp_frame)
        comp_layout.setContentsMargins(6, 6, 6, 6)
        comp_layout.setSpacing(4)

        for comp in self.pack_status.components:
            row = QHBoxLayout()
            row.setSpacing(8)

            if comp.found_mod:
                icon_lbl = QLabel("✔️")
                icon_lbl.setStyleSheet("color: #34d399; font-weight: bold;")
                name_lbl = QLabel(f"<b>{comp.name}</b> <span style='color: #94a3b8;'>({comp.found_mod.file_name})</span>")
                name_lbl.setStyleSheet("color: #e2e8f0; font-size: 12px;")

            else:
                icon_lbl = QLabel("❌" if not comp.is_optional else "➖")
                icon_lbl.setStyleSheet("color: #f87171;" if not comp.is_optional else "color: #94a3b8;")
                opt_str = " [Optional]" if comp.is_optional else " [Erforderlich]"
                name_lbl = QLabel(f"{comp.name}{opt_str}")
                name_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")

            row.addWidget(icon_lbl)
            row.addWidget(name_lbl, 1)

            order_lbl = QLabel(f"Priorität: #{comp.priority_order}")
            order_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
            row.addWidget(order_lbl)

            comp_layout.addLayout(row)

        layout.addWidget(comp_frame)


class ProModsView(QWidget):
    order_applied = pyqtSignal()
    mods_imported = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_game: Optional[TruckGame] = None
        self.current_mods: List[ScsMod] = []
        self.pack_statuses: List[ProModsPackStatus] = []

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. Header Frame & Action Buttons
        header_frame = QFrame()
        header_frame.setObjectName("toolbarCard")
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(10, 8, 10, 8)
        h_layout.setSpacing(10)

        # Title & Subtitle
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        h_title = QLabel("🗺️ ProMods Toolkit & Paket-Inspektor")
        h_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc;")
        title_col.addWidget(h_title)

        h_sub = QLabel("Automatische Erkennung, Integritäts-Check und offizielle Ladereihenfolge")
        h_sub.setStyleSheet("font-size: 11px; color: #94a3b8;")
        title_col.addWidget(h_sub)
        h_layout.addLayout(title_col, 1)

        # Action Buttons
        self.check_updates_btn = QPushButton("🔄 Versionen prüfen")
        self.check_updates_btn.setFixedHeight(34)
        self.check_updates_btn.setToolTip("Prüft den Status aller Pakete gegen die neuesten offiziellen Versionen auf promods.net")
        self.check_updates_btn.clicked.connect(self._check_version_updates)
        h_layout.addWidget(self.check_updates_btn)

        self.import_btn = QPushButton("📦 Entpacken")
        self.import_btn.setFixedHeight(34)
        self.import_btn.setStyleSheet("""
            background-color: #059669;
            color: #ffffff;
            font-weight: bold;
            border: 1px solid #10b981;
            border-radius: 6px;
            padding: 4px 12px;
        """)
        self.import_btn.setToolTip("Findet heruntergeladene ProMods-Archive (z. B. .7z.001) in Downloads und entpackt sie automatisch")
        self.import_btn.clicked.connect(self._import_promods_archives)
        h_layout.addWidget(self.import_btn)

        self.url_dl_btn = QPushButton("🔗 Direkt-Download")
        self.url_dl_btn.setFixedHeight(34)
        self.url_dl_btn.setToolTip("ProMods oder beliebige Mods über einen direkten Web-Link herunterladen")
        self.url_dl_btn.clicked.connect(self._open_url_download_dialog)
        h_layout.addWidget(self.url_dl_btn)

        self.apply_btn = QPushButton("⚡ Sortieren")
        self.apply_btn.setObjectName("primaryBtn")
        self.apply_btn.setFixedHeight(34)
        self.apply_btn.setToolTip("Ordnet alle ProMods-Komponenten und Road-Connectors nach den offiziellen Vorgaben")
        self.apply_btn.clicked.connect(self._apply_load_order)
        h_layout.addWidget(self.apply_btn)

        self.def_btn = QPushButton("⚙️ Def-Gen")
        self.def_btn.setFixedHeight(34)
        self.def_btn.setToolTip("Öffnet den offiziellen ProMods Definition-File Generator auf promods.net")
        self.def_btn.clicked.connect(self._open_def_generator)
        h_layout.addWidget(self.def_btn)

        main_layout.addWidget(header_frame)

        # 2. Scrollable Body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        body_widget = QWidget()
        self.body_layout = QVBoxLayout(body_widget)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(12)

        # Summary Info Label
        self.summary_lbl = QLabel()
        self.summary_lbl.setStyleSheet("color: #cbd5e1; font-size: 13px; font-weight: 500; margin-left: 4px;")
        self.body_layout.addWidget(self.summary_lbl)

        # Container for Pack Cards
        self.packs_container = QWidget()
        self.packs_layout = QVBoxLayout(self.packs_container)
        self.packs_layout.setContentsMargins(0, 0, 0, 0)
        self.packs_layout.setSpacing(10)
        self.body_layout.addWidget(self.packs_container)

        # Map Combo Guidelines Box
        combo_group = QGroupBox("📖 Offizielle Ladereihenfolge && Kartenkombinationen (Guide)")
        combo_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                color: #f8fafc;
                border: 1px solid #243350;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 4px;
            }
        """)
        combo_layout = QVBoxLayout(combo_group)
        combo_layout.setContentsMargins(10, 10, 10, 10)
        combo_layout.setSpacing(6)

        guidelines = ProModsManager.get_map_combo_guidelines()
        for g in guidelines:
            g_row = QHBoxLayout()
            tier_lbl = QLabel(g["tier"])
            tier_lbl.setFixedWidth(260)
            tier_lbl.setStyleSheet("font-weight: bold; color: #38bdf8; font-size: 12px;")
            g_row.addWidget(tier_lbl)

            desc_lbl = QLabel(f"{g['desc']} — <span style='color: #94a3b8; font-style: italic;'>z. B. {g['examples']}</span>")
            desc_lbl.setStyleSheet("color: #e2e8f0; font-size: 12px;")
            desc_lbl.setWordWrap(True)
            g_row.addWidget(desc_lbl, 1)

            combo_layout.addLayout(g_row)

        self.body_layout.addWidget(combo_group)
        self.body_layout.addStretch()

        scroll.setWidget(body_widget)
        main_layout.addWidget(scroll, 1)

    def set_game(self, game: TruckGame, mods: List[ScsMod]):
        self.current_game = game
        self.current_mods = mods
        self.refresh()

    def refresh(self):
        if not self.current_game:
            return

        # Scan for ProMods components
        self.pack_statuses = ProModsManager.scan_promods(self.current_mods, self.current_game.game_type)

        # Clear previous pack cards
        while self.packs_layout.count() > 0:
            item = self.packs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        installed_packs = [p for p in self.pack_statuses if p.is_installed]
        complete_packs = [p for p in self.pack_statuses if p.is_complete]

        game_name = "Euro Truck Simulator 2" if self.current_game.game_type == GameType.ETS2 else "American Truck Simulator"
        self.summary_lbl.setText(
            f"Gefundene ProMods-Pakete für {game_name}: <b>{len(installed_packs)} erkannt</b> ({len(complete_packs)} vollständig)"
        )

        for pack in self.pack_statuses:
            card = ProModsPackCard(pack)
            card.download_requested.connect(self._open_pack_download_dialog)
            self.packs_layout.addWidget(card)

        # Enable / disable action buttons based on presence of ProMods mods
        has_promods = any(p.is_installed for p in self.pack_statuses)
        self.apply_btn.setEnabled(has_promods)

    def _open_pack_download_dialog(self, pack: ProModsPackStatus):
        if not self.current_game:
            return
        dlg = ProModsDownloadDialog(pack, self.current_game, parent=self)
        dlg.download_success.connect(lambda files: (self.mods_imported.emit(), self.refresh()))
        dlg.exec()

    def _check_version_updates(self):
        self.refresh()
        updates_count = sum(1 for p in self.pack_statuses if p.is_update_available)
        installed_count = sum(1 for p in self.pack_statuses if p.is_installed)
        if updates_count > 0:
            msg = (
                f"Versionsprüfung abgeschlossen!\n\n"
                f"Für {updates_count} deiner installierten ProMods-Pakete ist ein Update auf promods.net verfügbar."
            )
        else:
            msg = (
                f"Versionsprüfung abgeschlossen!\n\n"
                f"Alle {installed_count} installierten ProMods-Pakete entsprechen den neuesten offiziellen Web-Versionen (promods.net)."
            )
        QMessageBox.information(self, "ProMods Versionsprüfung", msg)

    def _apply_load_order(self):
        if not self.current_mods or not self.current_game:
            return

        # Apply official ordering
        ordered_mods = ProModsManager.apply_promods_order(self.current_mods, self.current_game.game_type)
        self.current_mods.clear()
        self.current_mods.extend(ordered_mods)

        # Save to load order file
        ModDeployer.save_load_order(self.current_game, self.current_mods)

        self.order_applied.emit()
        QMessageBox.information(
            self,
            "Ladereihenfolge angewendet",
            "Die offizielle ProMods-Ladereihenfolge wurde erfolgreich auf deine Mods angewendet!\n\n"
            "Die Definitionen, Modelle und Road Connectors wurden nach Priorität einsortiert."
        )

    def _import_promods_archives(self):
        if not self.current_game:
            return

        target_dir = Path(self.current_game.mod_dir) if self.current_game.mod_dir else Path.home() / ".local/share/truck-mod-manager/mods"
        downloads_dir = Path.home() / "Downloads"

        # Check for promods archives in Downloads
        found_in_downloads: List[Path] = []
        if downloads_dir.exists():
            for f in downloads_dir.iterdir():
                if f.is_file() and "promods" in f.name.lower():
                    if any(f.name.lower().endswith(ext) for ext in [".7z", ".7z.001", ".zip", ".scs"]):
                        found_in_downloads.append(f)

        files_to_import: List[Path] = []
        if found_in_downloads:
            flist_str = "\n".join(f"• {f.name}" for f in found_in_downloads[:8])
            reply = QMessageBox.question(
                self,
                "ProMods-Dateien in Downloads gefunden",
                f"Folgende {len(found_in_downloads)} ProMods-Dateien wurden in deinem Downloads-Ordner gefunden:\n\n"
                f"{flist_str}\n\n"
                f"Möchtest du diese jetzt automatisch entpacken und in deine Mod-Bibliothek importieren?\n\n"
                f"(Klicke auf 'Nein', um andere Dateien manuell auszuwählen.)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                files_to_import = found_in_downloads
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        if not files_to_import:
            selected, _ = QFileDialog.getOpenFileNames(
                self,
                "ProMods-Archive zum Entpacken & Importieren auswählen",
                str(downloads_dir),
                "ProMods Archive (*.7z* *.zip *.scs);;Alle Dateien (*)"
            )
            if not selected:
                return
            files_to_import = [Path(p) for p in selected]

        total_deployed = []
        for src in files_to_import:
            # Skip secondary multipart archives (.7z.002, .003, etc.) as 7z x .001 extracts the entire set
            if any(src.name.lower().endswith(f".7z.{i:03d}") for i in range(2, 20)):
                continue
            deployed = ArchiveExtractor.deploy_or_extract(src, target_dir)
            total_deployed.extend(deployed)

        if total_deployed:
            QMessageBox.information(
                self,
                "Import erfolgreich",
                f"Es wurden {len(total_deployed)} Dateien erfolgreich entpackt und in die Mod-Bibliothek importiert!\n\n"
                f"Der Paket-Status und die Ladereihenfolge werden nun aktualisiert."
            )
            self.mods_imported.emit()
            self.refresh()
        else:
            QMessageBox.warning(
                self,
                "Keine SCS-Dateien entpackt",
                "Aus den ausgewählten Archiven konnten keine .scs-Moddateien extrahiert werden.\n"
                "Bitte stelle sicher, dass '7z' installiert ist und alle Archiv-Teile vorhanden sind."
            )

    def _open_url_download_dialog(self):
        if not self.current_game:
            return
        dlg = UrlDownloadDialog(self.current_game, parent=self)
        dlg.download_success.connect(lambda files: (self.mods_imported.emit(), self.refresh()))
        dlg.exec()

    def _open_def_generator(self):
        QDesktopServices.openUrl(QUrl(ProModsManager.DEF_GENERATOR_URL))
