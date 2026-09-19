"""
Main Window for Truck Mod Manager.
Coordinates game switching (ETS2 <-> ATS), view navigation, and quick launching.
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QStatusBar, QMessageBox, QFrame,
    QButtonGroup, QInputDialog, QComboBox
)

from truck_mod_manager.core.config import config
from truck_mod_manager.core.deployer import ModDeployer
from truck_mod_manager.core.game_scanner import GameScanner
from truck_mod_manager.core.github_updater import GitHubUpdateCheckerWorker, GitHubUpdateInfo
from truck_mod_manager.core.models import GameProfile, GameType, ScsMod, TruckGame
from truck_mod_manager.core.profile_manager import ProfileManager
from truck_mod_manager.ui.dialogs import GitHubUpdateDialog
from truck_mod_manager.ui.style import DARK_THEME_QSS
from truck_mod_manager.ui.views import (
    ModsView, LoadOrderView, LogAnalyzerView,
    TelemetryView, WorkshopView, SettingsView, TruckyModsView,
    ProModsView, TruckToolsView
)


RESOURCE_DIR = Path(__file__).parent.parent / "resources"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Truck Mod Manager - ETS2 & ATS")
        self.resize(1260, 840)
        self.setMinimumSize(980, 640)

        self.current_game_type = GameType(config.get("active_game", GameType.ETS2.value))
        self.games: Dict[GameType, TruckGame] = {}
        self.current_game: Optional[TruckGame] = None
        self.current_mods: List[ScsMod] = []
        self.current_profiles: List[GameProfile] = []
        self.current_profile: Optional[GameProfile] = None
        self._bg_update_checker: Optional[GitHubUpdateCheckerWorker] = None
        self._latest_update_info: Optional[GitHubUpdateInfo] = None

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        self.setStyleSheet(DARK_THEME_QSS)

        # Set Window Icon
        icon_path = RESOURCE_DIR / "icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 1. Header Frame with App Branding & Game Switcher & Launch Button
        header = QFrame()
        header.setObjectName("headerFrame")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 8, 12, 8)
        h_layout.setSpacing(16)

        # Branding (Logo + Title)
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(10)

        app_icon_lbl = QLabel()
        app_icon_lbl.setFixedSize(36, 36)
        if icon_path.exists():
            pix = QPixmap(str(icon_path))
            app_icon_lbl.setPixmap(pix.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        brand_layout.addWidget(app_icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        app_title = QLabel("Truck Mod Manager")
        app_title.setStyleSheet("font-size: 17px; font-weight: bold; color: #ffffff;")
        title_col.addWidget(app_title)

        app_sub = QLabel("ETS 2 & ATS Mod Manager")
        app_sub.setStyleSheet("font-size: 11px; color: #64748b; font-weight: 500;")
        title_col.addWidget(app_sub)
        brand_layout.addLayout(title_col)
        h_layout.addLayout(brand_layout)

        h_layout.addSpacing(16)

        # Game Switcher (ETS2 vs ATS toggle buttons)
        self.game_btn_group = QButtonGroup(self)
        self.game_btn_group.setExclusive(True)

        self.ets2_btn = QPushButton("🇪🇺 ETS 2")
        self.ets2_btn.setCheckable(True)
        self.ets2_btn.setFixedHeight(36)
        self.ets2_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ets2_btn.setToolTip("Euro Truck Simulator 2 auswählen")
        self.ets2_btn.clicked.connect(lambda: self._switch_game(GameType.ETS2))
        self.game_btn_group.addButton(self.ets2_btn)
        h_layout.addWidget(self.ets2_btn)

        self.ats_btn = QPushButton("🇺🇸 ATS")
        self.ats_btn.setCheckable(True)
        self.ats_btn.setFixedHeight(36)
        self.ats_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ats_btn.setToolTip("American Truck Simulator auswählen")
        self.ats_btn.clicked.connect(lambda: self._switch_game(GameType.ATS))
        self.game_btn_group.addButton(self.ats_btn)
        h_layout.addWidget(self.ats_btn)

        h_layout.addSpacing(12)

        # Profile / Spielstand selector
        profile_box = QHBoxLayout()
        profile_box.setSpacing(6)
        profile_lbl = QLabel("👤 Profil:")
        profile_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #94a3b8;")
        profile_box.addWidget(profile_lbl)

        self.profile_combo = QComboBox()
        self.profile_combo.setFixedHeight(36)
        self.profile_combo.setMinimumWidth(180)
        self.profile_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.profile_combo.setToolTip("Aktiver Spielstand / Profil. Jeder Spielstand besitzt eine eigene Mod-Ladeliste und Ladereihenfolge.")
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)
        profile_box.addWidget(self.profile_combo)
        h_layout.addLayout(profile_box)

        h_layout.addStretch()

        # Status indicator
        self.game_status_lbl = QLabel()
        self.game_status_lbl.setStyleSheet(
            "QLabel { background-color: #0b0f19; border: 1px solid #243350; border-radius: 7px; "
            "padding: 6px 14px; font-size: 12px; color: #cbd5e1; }"
        )
        self.game_status_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.game_status_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.game_status_lbl.setOpenExternalLinks(False)
        self.game_status_lbl.linkActivated.connect(self._on_status_link_clicked)
        h_layout.addWidget(self.game_status_lbl)

        # Update Button
        self.update_btn = QPushButton("🔄 Updates")
        self.update_btn.setFixedHeight(36)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setToolTip("GitHub Software- & Release-Aktualisierung prüfen")
        self.update_btn.clicked.connect(self._open_update_dialog)
        h_layout.addWidget(self.update_btn)

        # Quick Launch Button (Prominent Emerald Action Button)
        self.launch_btn = QPushButton("🚀 Spiel starten")
        self.launch_btn.setObjectName("successBtn")
        self.launch_btn.setFixedHeight(36)
        self.launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.launch_btn.setToolTip("Startet das ausgewählte Spiel über Steam")
        self.launch_btn.clicked.connect(self._launch_game)
        h_layout.addWidget(self.launch_btn)

        main_layout.addWidget(header)

        # 2. Main Tab Widget
        self.tabs = QTabWidget()

        self.mods_view = ModsView()
        self.mods_view.mods_changed.connect(self._on_mods_changed)
        self.tabs.addTab(self.mods_view, "📦 Mods")

        self.load_order_view = LoadOrderView()
        self.load_order_view.order_changed.connect(self._on_order_changed)
        self.load_order_view.reload_from_profile_requested.connect(self._on_reload_from_profile_requested)
        self.load_order_view.reload_from_log_requested.connect(self._on_reload_from_log_requested)
        self.tabs.addTab(self.load_order_view, "⚡ Ladereihenfolge")

        self.promods_view = ProModsView()
        self.promods_view.order_applied.connect(self._on_promods_order_applied)
        self.promods_view.mods_imported.connect(self._on_external_mods_added)
        self.tabs.addTab(self.promods_view, "🗺️ ProMods")

        self.truckymods_view = TruckyModsView()
        self.truckymods_view.mod_downloaded.connect(self._on_external_mods_added)
        self.tabs.addTab(self.truckymods_view, "🌐 TruckyMods")

        self.workshop_view = WorkshopView()
        self.tabs.addTab(self.workshop_view, "🛒 Workshop")

        self.truck_tools_view = TruckToolsView()
        self.tabs.addTab(self.truck_tools_view, "🛠️ Truck Tools")

        self.log_view = LogAnalyzerView()
        self.tabs.addTab(self.log_view, "📋 Log-Analyse")

        self.telemetry_view = TelemetryView()
        self.tabs.addTab(self.telemetry_view, "🔌 Plugins")

        self.settings_view = SettingsView()
        self.settings_view.settings_saved.connect(self._on_settings_saved)
        self.tabs.addTab(self.settings_view, "⚙️ Einstellungen")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self.tabs)

        # 3. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Bereit")

    def _load_data(self):
        # Scan games
        self.games = GameScanner.scan_all()
        self._switch_game(self.current_game_type)
        self._start_background_update_check()

    def _switch_game(self, game_type: GameType):
        # Save previous profile state before switching game
        if self.current_game and self.current_profile:
            ProfileManager.save_profile_state(
                self.current_game_type, self.current_profile.id, self.current_mods,
                profile_name=self.current_profile.name
            )

        self.current_game_type = game_type
        config.set("active_game", game_type.value)

        # Update buttons
        self.ets2_btn.setChecked(game_type == GameType.ETS2)
        self.ats_btn.setChecked(game_type == GameType.ATS)

        # Style highlight
        if game_type == GameType.ETS2:
            self.ets2_btn.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1e3a8a); "
                "color: #ffffff; font-weight: bold; border: 1.5px solid #60a5fa; border-radius: 7px; padding: 6px 14px; } "
                "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3b82f6, stop:1 #1e40af); }"
            )
            self.ats_btn.setStyleSheet(
                "QPushButton { background-color: #131b2e; color: #94a3b8; border: 1px solid #243350; border-radius: 7px; padding: 6px 14px; } "
                "QPushButton:hover { background-color: #1c2740; color: #f8fafc; border-color: #475569; }"
            )
        else:
            self.ats_btn.setStyleSheet(
                "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #dc2626, stop:1 #7f1d1d); "
                "color: #ffffff; font-weight: bold; border: 1.5px solid #f87171; border-radius: 7px; padding: 6px 14px; } "
                "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #991b1b); }"
            )
            self.ets2_btn.setStyleSheet(
                "QPushButton { background-color: #131b2e; color: #94a3b8; border: 1px solid #243350; border-radius: 7px; padding: 6px 14px; } "
                "QPushButton:hover { background-color: #1c2740; color: #f8fafc; border-color: #475569; }"
            )

        found = self.games.get(game_type) or GameScanner.find_game(game_type)
        if not found:
            info = GameScanner.APP_INFO.get(game_type, {"name": game_type.name, "appid": "", "dir_name": ""})
            found = TruckGame(game_type=game_type, name=info["name"], steam_appid=info["appid"])
        self.current_game = found
        self.games[game_type] = self.current_game

        # Load all available mods for this game
        self.current_mods = ModDeployer.load_all_mods(self.current_game)

        # Discover profiles for this game
        self.current_profiles = ProfileManager.list_profiles(self.current_game)
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for p in self.current_profiles:
            cloud_badge = "☁️ " if p.is_steam_cloud else ""
            self.profile_combo.addItem(f"{cloud_badge}{p.name}", p.id)

        # Select saved active profile (default to most recently modified profile)
        active_p_id = ProfileManager.get_active_profile_id(game_type)
        selected_idx = 0
        found_active = False
        if active_p_id:
            for idx, p in enumerate(self.current_profiles):
                if p.id == active_p_id:
                    selected_idx = idx
                    found_active = True
                    break

        if not found_active:
            most_recent = ProfileManager.get_most_recent_profile(self.current_profiles)
            if most_recent:
                for idx, p in enumerate(self.current_profiles):
                    if p.id == most_recent.id:
                        selected_idx = idx
                        break

        self.profile_combo.setCurrentIndex(selected_idx)
        self.current_profile = self.current_profiles[selected_idx]
        ProfileManager.set_active_profile_id(game_type, self.current_profile.id)
        self.profile_combo.blockSignals(False)

        # Apply profile-specific mod state
        self.current_mods = ProfileManager.apply_profile_state(
            game_type, self.current_profile, self.current_mods
        )

        # Update status
        active_count = sum(1 for m in self.current_mods if m.is_enabled)
        mode_str = "Proton" if self.current_game.is_proton else "Native"
        if self.current_game.detected_game_version:
            ver_html = (
                f"<span style='color: #60a5fa; font-weight: bold;'>v{self.current_game.detected_game_version}</span> "
                f"<a href='set_version' style='color: #94a3b8; text-decoration: none; font-size: 12px;'>✎</a>"
            )
        else:
            ver_html = (
                "<span style='color: #f87171; font-weight: bold;'>v?</span> "
                "<a href='set_version' style='color: #38bdf8; text-decoration: underline; font-size: 12px;'>✎</a>"
            )

        inst_badge = "Installiert" if self.current_game.is_installed else "Nicht installiert"
        self.game_status_lbl.setText(f"<b>{mode_str}</b> &nbsp;•&nbsp; {ver_html}")
        self.status_bar.showMessage(
            f"{self.current_game.name} ({mode_str} • {inst_badge})  |  Profil: {self.current_profile.name} ({active_count}/{len(self.current_mods)} Mods aktiv)  |  Mod-Ordner: {self.current_game.mod_dir or 'Nicht konfiguriert'}"
        )

        # Distribute data to views
        self.mods_view.set_game(self.current_game, self.current_mods)
        self.load_order_view.set_game(self.current_game, self.current_mods)
        self.promods_view.set_game(self.current_game, self.current_mods)
        self.truckymods_view.set_game(self.current_game)
        self.log_view.set_game(self.current_game)
        self.telemetry_view.set_game(self.current_game)
        self.workshop_view.set_game(self.current_game)
        self.truck_tools_view.set_game_and_profile(self.current_game, self.current_profile)

        self.status_bar.showMessage(
            f"{self.current_game.name} [{self.current_profile.name}]: {len(self.current_mods)} Mods ({active_count} aktiv geladen)"
        )

    def _on_profile_changed(self, index: int):
        if index < 0 or index >= len(self.current_profiles) or not self.current_game:
            return

        new_profile = self.current_profiles[index]
        if self.current_profile and self.current_profile.id == new_profile.id:
            return

        # 1. Save previous profile's state
        if self.current_profile:
            ProfileManager.save_profile_state(
                self.current_game_type, self.current_profile.id, self.current_mods,
                profile_name=self.current_profile.name
            )

        # 2. Switch to new profile
        self.current_profile = new_profile
        ProfileManager.set_active_profile_id(self.current_game_type, new_profile.id)

        # 3. Apply new profile's active mods & order
        self.current_mods = ProfileManager.apply_profile_state(
            self.current_game_type, new_profile, self.current_mods
        )

        # 4. Auto-deploy to game mod dir if staging is enabled
        if config.get("zero_pollution_staging", True):
            ModDeployer.deploy(self.current_game, self.current_mods)

        # 5. Refresh all views
        self.mods_view.set_game(self.current_game, self.current_mods)
        self.load_order_view.set_game(self.current_game, self.current_mods)
        self.promods_view.set_game(self.current_game, self.current_mods)
        self.truck_tools_view.set_game_and_profile(self.current_game, self.current_profile)

        active_count = sum(1 for m in self.current_mods if m.is_enabled)
        self.status_bar.showMessage(
            f"Spielstand gewechselt: {new_profile.name} ({active_count} Mods aktiv)"
        )

    def _on_reload_from_profile_requested(self):
        if not self.current_game or not self.current_profile:
            return
        self.current_mods = ProfileManager.apply_profile_state(
            self.current_game_type, self.current_profile, self.current_mods,
            force_reload_sii=True
        )
        if config.get("zero_pollution_staging", True):
            ModDeployer.deploy(self.current_game, self.current_mods)

        self.mods_view.set_game(self.current_game, self.current_mods)
        self.load_order_view.set_game(self.current_game, self.current_mods)
        self.promods_view.set_game(self.current_game, self.current_mods)

        active_count = sum(1 for m in self.current_mods if m.is_enabled)
        self.status_bar.showMessage(
            f"Spielstand '{self.current_profile.name}': Ladereihenfolge aus Spielstand geladen ({active_count} Mods aktiv)"
        )
        QMessageBox.information(
            self,
            "Spielstand eingelesen",
            f"Die Mod-Ladereihenfolge für '{self.current_profile.name}' wurde erfolgreich direkt aus dem Spielstand (profile.sii / save) eingelesen!\n\n"
            f"Aktive Mods: {active_count} von {len(self.current_mods)}"
        )

    def _on_reload_from_log_requested(self):
        if not self.current_game or not self.current_profile:
            return
        log_path = Path(self.current_game.log_path) if self.current_game.log_path else None
        if not log_path or not log_path.is_file():
            QMessageBox.warning(
                self,
                "game.log.txt nicht gefunden",
                f"Die Log-Datei für {self.current_game.name} konnte unter folgendem Pfad nicht gefunden werden:\n{self.current_game.log_path or 'Nicht konfiguriert'}\n\nBitte starte das Spiel einmal, damit eine Log-Datei erzeugt wird."
            )
            return

        log_tuples = ProfileManager.read_log_active_mods(log_path)
        if not log_tuples:
            QMessageBox.warning(
                self,
                "Keine gemounteten Mods im Log",
                f"In der Datei {log_path.name} wurden keine gemounteten Mod-Einträge ([mod_package_manager] Mod ...) gefunden."
            )
            return

        reordered = ProfileManager.match_sii_active_mods_to_scs_mods(log_tuples, self.current_mods)
        self.current_mods = reordered

        ProfileManager.save_profile_state(
            self.current_game_type, self.current_profile.id, self.current_mods,
            profile_name=self.current_profile.name,
            user_modified=True
        )

        if config.get("zero_pollution_staging", True):
            ModDeployer.deploy(self.current_game, self.current_mods)

        self.mods_view.set_game(self.current_game, self.current_mods)
        self.load_order_view.set_game(self.current_game, self.current_mods)
        self.promods_view.set_game(self.current_game, self.current_mods)

        active_count = sum(1 for m in self.current_mods if m.is_enabled)
        self.status_bar.showMessage(
            f"Spielstand '{self.current_profile.name}': {active_count} Mods aus game.log.txt eingelesen"
        )
        QMessageBox.information(
            self,
            "Aus game.log.txt eingelesen",
            f"Die Mod-Ladereihenfolge für '{self.current_profile.name}' wurde erfolgreich direkt aus {log_path.name} eingelesen!\n\n"
            f"Aktive Mods: {active_count} von {len(self.current_mods)}"
        )

    def _on_mods_changed(self):
        # Save to active profile immediately
        if self.current_game and self.current_profile:
            ProfileManager.save_profile_state(
                self.current_game_type, self.current_profile.id, self.current_mods,
                profile_name=self.current_profile.name
            )
        # Sync to load order and promods view
        self.load_order_view.set_game(self.current_game, self.current_mods)
        self.promods_view.set_game(self.current_game, self.current_mods)

    def _on_order_changed(self):
        # Save to active profile immediately
        if self.current_game and self.current_profile:
            ProfileManager.save_profile_state(
                self.current_game_type, self.current_profile.id, self.current_mods,
                profile_name=self.current_profile.name
            )
        # Sync back to mods view
        self.mods_view.all_mods = self.current_mods
        self.mods_view._refresh_list()
        self.promods_view.set_game(self.current_game, self.current_mods)

    def _on_promods_order_applied(self):
        if self.current_game and self.current_profile:
            ProfileManager.save_profile_state(
                self.current_game_type, self.current_profile.id, self.current_mods,
                profile_name=self.current_profile.name
            )
        self.mods_view.all_mods = self.current_mods
        self.mods_view._refresh_list()
        self.load_order_view.set_game(self.current_game, self.current_mods)

    def _on_external_mods_added(self):
        # Reload all mods for current game when a mod is downloaded or imported
        self.current_mods = ModDeployer.load_all_mods(self.current_game)
        if self.current_profile:
            self.current_mods = ProfileManager.apply_profile_state(
                self.current_game_type, self.current_profile, self.current_mods
            )
        self.mods_view.set_game(self.current_game, self.current_mods)
        self.load_order_view.set_game(self.current_game, self.current_mods)
        self.promods_view.set_game(self.current_game, self.current_mods)
        active_count = sum(1 for m in self.current_mods if m.is_enabled)
        self.status_bar.showMessage(
            f"{self.current_game.name}: {len(self.current_mods)} Mods ({active_count} aktiv geladen) — Neue Mod hinzugefügt!"
        )

    def _on_settings_saved(self):
        self._load_data()

    def _on_tab_changed(self, index: int):
        # Refresh current tab view if needed
        tab_text = self.tabs.tabText(index)
        if "Log" in tab_text:
            self.log_view.refresh()
        elif "Ladereihenfolge" in tab_text:
            self.load_order_view.refresh()
        elif "ProMods" in tab_text:
            self.promods_view.refresh()
        elif "TruckyMods" in tab_text:
            self.truckymods_view.ensure_loaded()
        elif "Telemetrie" in tab_text:
            self.telemetry_view.refresh()
        elif "Workshop" in tab_text:
            self.workshop_view.refresh()
        elif "Truck Tools" in tab_text:
            self.truck_tools_view.refresh_savegames()

    def _start_background_update_check(self):
        if not config.get("auto_check_updates", True):
            return
        self._bg_update_checker = GitHubUpdateCheckerWorker()
        self._bg_update_checker.finished.connect(self._on_bg_update_checked)
        self._bg_update_checker.start()

    def _on_bg_update_checked(self, info: GitHubUpdateInfo):
        self._latest_update_info = info
        if info.has_update:
            self.update_btn.setText(f"⚡ Update v{info.remote_version}!")
            self.update_btn.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1d4ed8); "
                "color: #ffffff; font-weight: bold; border: 1px solid #60a5fa;"
            )
            self.update_btn.setToolTip(
                f"Neue Version v{info.remote_version} auf GitHub verfügbar! Klicken zum Aktualisieren."
            )
            self.status_bar.showMessage(
                f"Update verfügbar: v{info.remote_version} (Aktuell: v{info.installed_version})", 8000
            )

    def _open_update_dialog(self):
        dlg = GitHubUpdateDialog(self)
        dlg.exec()

    def closeEvent(self, event):
        if self.current_game and self.current_profile:
            ProfileManager.save_profile_state(
                self.current_game_type, self.current_profile.id, self.current_mods,
                profile_name=self.current_profile.name
            )
        self.truckymods_view.stop_workers()
        if self._bg_update_checker and self._bg_update_checker.isRunning():
            self._bg_update_checker.wait(500)
        super().closeEvent(event)

    def _launch_game(self):
        if not self.current_game:
            return

        appid = self.current_game.steam_appid
        args = self.current_game.custom_launch_args.strip()

        # Try steam launch
        try:
            cmd = ["steam", f"steam://rungameid/{appid}"]
            if args:
                cmd.extend(["//", args])
            subprocess.Popen(cmd)
            self.status_bar.showMessage(f"Spiel gestartet: {self.current_game.name} (AppID {appid})")
        except Exception as e:
            QMessageBox.critical(self, "Startfehler", f"Konnte Spiel nicht über Steam starten: {e}")

    def _on_status_link_clicked(self, link: str):
        if link == "set_version":
            self._prompt_set_game_version()

    def _prompt_set_game_version(self):
        if not self.current_game:
            return

        current_val = self.current_game.detected_game_version or "1.51"
        preset_versions = ["1.61", "1.60", "1.51", "1.50", "1.49", "1.48", "1.47"]
        options = list(preset_versions)
        if current_val and current_val not in preset_versions:
            options.insert(0, current_val)
        options.append("Benutzerdefiniert / Manuell eingeben...")
        options.append("Automatische Erkennung zurücksetzen")

        initial_idx = 0
        if current_val in options:
            initial_idx = options.index(current_val)

        choice, ok = QInputDialog.getItem(
            self,
            f"Spielversion festlegen - {self.current_game.name}",
            f"Wählen Sie die Spielversion für {self.current_game.name}:\n"
            "(Wird für Kompatibilitätsfilter und Mod-Warnungen verwendet)",
            options,
            initial_idx,
            False
        )
        if not ok or not choice:
            return

        game_key = self.current_game_type.value

        if choice == "Automatische Erkennung zurücksetzen":
            config.set_game_config(game_key, "game_version_override", "")
            self.games[self.current_game_type] = GameScanner.find_game(self.current_game_type)
            self._switch_game(self.current_game_type)
            self.status_bar.showMessage("Spielversion auf automatische Erkennung zurückgesetzt.", 5000)
            return

        final_version = choice
        if "Benutzerdefiniert" in choice:
            custom_val, ok2 = QInputDialog.getText(
                self,
                "Benutzerdefinierte Spielversion",
                "Geben Sie die Versionsnummer ein (z.B. 1.51 oder 1.51.1):",
                text=current_val
            )
            if not ok2 or not custom_val.strip():
                return
            final_version = custom_val.strip()

        config.set_game_config(game_key, "game_version_override", final_version)

        # Update in-memory game & switch game to refresh UI and mod compatibility
        self.games[self.current_game_type] = GameScanner.find_game(self.current_game_type)
        self._switch_game(self.current_game_type)
        self.status_bar.showMessage(
            f"Spielversion für {self.current_game.name} auf v{final_version} gesetzt.", 5000
        )

