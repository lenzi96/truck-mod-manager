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
    QButtonGroup, QInputDialog
)

from truck_mod_manager.core.config import config
from truck_mod_manager.core.deployer import ModDeployer
from truck_mod_manager.core.game_scanner import GameScanner
from truck_mod_manager.core.github_updater import GitHubUpdateCheckerWorker, GitHubUpdateInfo
from truck_mod_manager.core.models import GameType, ScsMod, TruckGame
from truck_mod_manager.ui.dialogs import GitHubUpdateDialog
from truck_mod_manager.ui.style import DARK_THEME_QSS
from truck_mod_manager.ui.views import (
    ModsView, LoadOrderView, PresetsView, LogAnalyzerView,
    TelemetryView, WorkshopView, SettingsView, TruckyModsView,
    ProModsView
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
        app_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        title_col.addWidget(app_title)

        app_sub = QLabel("Euro Truck Simulator 2 & American Truck Simulator")
        app_sub.setStyleSheet("font-size: 11px; color: #94a3b8;")
        title_col.addWidget(app_sub)
        brand_layout.addLayout(title_col)
        h_layout.addLayout(brand_layout)

        h_layout.addSpacing(20)

        # Game Switcher (ETS2 vs ATS toggle buttons)
        self.game_btn_group = QButtonGroup(self)
        self.game_btn_group.setExclusive(True)

        self.ets2_btn = QPushButton("🇪🇺 Euro Truck Simulator 2")
        self.ets2_btn.setCheckable(True)
        self.ets2_btn.setFixedHeight(34)
        self.ets2_btn.clicked.connect(lambda: self._switch_game(GameType.ETS2))
        self.game_btn_group.addButton(self.ets2_btn)
        h_layout.addWidget(self.ets2_btn)

        self.ats_btn = QPushButton("🇺🇸 American Truck Simulator")
        self.ats_btn.setCheckable(True)
        self.ats_btn.setFixedHeight(34)
        self.ats_btn.clicked.connect(lambda: self._switch_game(GameType.ATS))
        self.game_btn_group.addButton(self.ats_btn)
        h_layout.addWidget(self.ats_btn)

        h_layout.addStretch()

        # Status indicator
        self.game_status_lbl = QLabel("Wird geladen...")
        self.game_status_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.game_status_lbl.setTextFormat(Qt.TextFormat.RichText)
        self.game_status_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.game_status_lbl.setOpenExternalLinks(False)
        self.game_status_lbl.linkActivated.connect(self._on_status_link_clicked)
        h_layout.addWidget(self.game_status_lbl)

        # Update Button
        self.update_btn = QPushButton("🔄 Updates")
        self.update_btn.setFixedHeight(34)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setToolTip("GitHub Software- & Release-Aktualisierung prüfen")
        self.update_btn.clicked.connect(self._open_update_dialog)
        h_layout.addWidget(self.update_btn)

        # Quick Launch Button
        self.launch_btn = QPushButton("🎮 Spiel starten")
        self.launch_btn.setObjectName("primaryBtn")
        self.launch_btn.setFixedHeight(34)
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
        self.tabs.addTab(self.load_order_view, "⚡ Ladereihenfolge (Load Order)")

        self.presets_view = PresetsView()
        self.presets_view.preset_applied.connect(self._on_preset_applied)
        self.tabs.addTab(self.presets_view, "📁 Presets & Profile")

        self.promods_view = ProModsView()
        self.promods_view.order_applied.connect(self._on_promods_order_applied)
        self.promods_view.mods_imported.connect(self._on_external_mods_added)
        self.tabs.addTab(self.promods_view, "🗺️ ProMods Toolkit")

        self.truckymods_view = TruckyModsView()
        self.truckymods_view.mod_downloaded.connect(self._on_external_mods_added)
        self.tabs.addTab(self.truckymods_view, "🌐 TruckyMods")

        self.log_view = LogAnalyzerView()
        self.tabs.addTab(self.log_view, "📋 Log & Crash Analyse")

        self.telemetry_view = TelemetryView()
        self.tabs.addTab(self.telemetry_view, "🔌 Telemetrie & Plugins")

        self.workshop_view = WorkshopView()
        self.tabs.addTab(self.workshop_view, "🌐 Steam Workshop")

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
        self.current_game_type = game_type
        config.set("active_game", game_type.value)

        # Update buttons
        self.ets2_btn.setChecked(game_type == GameType.ETS2)
        self.ats_btn.setChecked(game_type == GameType.ATS)

        # Style highlight
        if game_type == GameType.ETS2:
            self.ets2_btn.setStyleSheet("background-color: #1e3a8a; color: #ffffff; font-weight: bold; border-color: #3b82f6;")
            self.ats_btn.setStyleSheet("")
        else:
            self.ats_btn.setStyleSheet("background-color: #7f1d1d; color: #ffffff; font-weight: bold; border-color: #ef4444;")
            self.ets2_btn.setStyleSheet("")

        found = self.games.get(game_type) or GameScanner.find_game(game_type)
        if not found:
            info = GameScanner.APP_INFO.get(game_type, {"name": game_type.name, "appid": "", "dir_name": ""})
            found = TruckGame(game_type=game_type, name=info["name"], steam_appid=info["appid"])
        self.current_game = found
        self.games[game_type] = self.current_game

        # Load mods for this game
        self.current_mods = ModDeployer.load_all_mods(self.current_game)

        # Update status
        active_count = sum(1 for m in self.current_mods if m.is_enabled)
        mode_str = "Steam Proton" if self.current_game.is_proton else "Linux Native"
        inst_str = "Installiert" if self.current_game.is_installed else "Pfad nicht gefunden"
        if self.current_game.detected_game_version:
            ver_str = (
                f" • <span style='color: #60a5fa; font-weight: bold;'>v{self.current_game.detected_game_version}</span> "
                f"<a href='set_version' style='color: #94a3b8; text-decoration: underline; font-size: 11px;'>[✏️ Ändern]</a>"
            )
        else:
            ver_str = (
                " • <span style='color: #f87171;'>Version: Unbekannt</span> "
                "<a href='set_version' style='color: #38bdf8; font-weight: bold; text-decoration: underline; font-size: 11px;'>[✏️ Festlegen]</a>"
            )
        self.game_status_lbl.setText(f"Modus: <b>{mode_str}</b> ({inst_str}{ver_str})")

        # Distribute data to views
        self.mods_view.set_game(self.current_game, self.current_mods)
        self.load_order_view.set_game(self.current_game, self.current_mods)
        self.presets_view.set_game(self.current_game, self.current_mods)
        self.promods_view.set_game(self.current_game, self.current_mods)
        self.truckymods_view.set_game(self.current_game)
        self.log_view.set_game(self.current_game)
        self.telemetry_view.set_game(self.current_game)
        self.workshop_view.set_game(self.current_game)

        self.status_bar.showMessage(
            f"{self.current_game.name}: {len(self.current_mods)} Mods ({active_count} aktiv geladen)"
        )

    def _on_mods_changed(self):
        # Sync to load order, presets and promods view
        self.load_order_view.set_game(self.current_game, self.current_mods)
        self.presets_view.set_game(self.current_game, self.current_mods)
        self.promods_view.set_game(self.current_game, self.current_mods)

    def _on_order_changed(self):
        # Sync back to mods view
        self.mods_view.all_mods = self.current_mods
        self.mods_view._refresh_list()
        self.promods_view.set_game(self.current_game, self.current_mods)

    def _on_preset_applied(self):
        self.mods_view.all_mods = self.current_mods
        self.mods_view._refresh_list()
        self.load_order_view.set_game(self.current_game, self.current_mods)
        self.promods_view.set_game(self.current_game, self.current_mods)

    def _on_promods_order_applied(self):
        self.mods_view.all_mods = self.current_mods
        self.mods_view._refresh_list()
        self.load_order_view.set_game(self.current_game, self.current_mods)

    def _on_external_mods_added(self):
        # Reload all mods for current game when a mod is downloaded or imported
        self.current_mods = ModDeployer.load_all_mods(self.current_game)
        self.mods_view.set_game(self.current_game, self.current_mods)
        self.load_order_view.set_game(self.current_game, self.current_mods)
        self.presets_view.set_game(self.current_game, self.current_mods)
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
        preset_versions = ["1.51", "1.50", "1.49", "1.48", "1.47"]
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

