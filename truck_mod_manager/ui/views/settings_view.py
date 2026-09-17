"""
Settings View for Truck Mod Manager.
Manages paths, Proton toggles, launch parameters, and staging mode.
"""
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QFrame, QFileDialog, QMessageBox,
    QTabWidget, QScrollArea
)

from truck_mod_manager import __version__
from truck_mod_manager.core.config import config
from truck_mod_manager.core.github_updater import get_github_repo
from truck_mod_manager.core.models import GameType, TruckGame


class SettingsView(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game: Optional[TruckGame] = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Header
        header = QFrame()
        header.setObjectName("toolbarCard")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 8, 10, 8)
        title = QLabel("⚙️ Einstellungen & Pfadkonfiguration")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        save_btn = QPushButton("💾 Speichern")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save_settings)
        h_layout.addWidget(save_btn)
        main_layout.addWidget(header)

        # Tabs for Global, ETS2, ATS
        tabs = QTabWidget()

        # Tab 1: Global Settings
        global_widget = QWidget()
        g_layout = QVBoxLayout(global_widget)
        g_layout.setContentsMargins(16, 16, 16, 16)
        g_layout.setSpacing(14)

        self.zero_pollution_cb = QCheckBox("Zero-Pollution Staging aktivieren (Empfohlen)")
        self.zero_pollution_cb.setChecked(config.get("zero_pollution_staging", True))
        self.zero_pollution_cb.setToolTip(
            "Mods bleiben isoliert in der Manager-Bibliothek und werden per Symlinks in das Spiel verlinkt.\n"
            "Verhindert jegliche Verschmutzung des Originalordners und erlaubt blitzschnellen Vanilla-Reset."
        )
        g_layout.addWidget(self.zero_pollution_cb)

        self.auto_sort_cb = QCheckBox("Automatisch sortieren beim Aktivieren einer Mod")
        self.auto_sort_cb.setChecked(config.get("auto_sort_on_enable", False))
        g_layout.addWidget(self.auto_sort_cb)

        g_layout.addWidget(QLabel("Zusätzliche Steam-Bibliothekspfade (optional, getrennt durch Komma):"))
        self.extra_steam_input = QLineEdit()
        self.extra_steam_input.setText(", ".join(config.get("extra_steam_paths", [])))
        self.extra_steam_input.setPlaceholderText("/pfad/zu/externer/steam/bibliothek")
        g_layout.addWidget(self.extra_steam_input)

        # Update Settings Group
        update_card = QFrame()
        update_card.setObjectName("cardFrame")
        uc_layout = QVBoxLayout(update_card)
        uc_layout.setContentsMargins(14, 12, 14, 12)
        uc_layout.setSpacing(10)

        uc_title = QLabel("🔄 Software-Updates & GitHub")
        uc_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
        uc_layout.addWidget(uc_title)

        self.auto_check_cb = QCheckBox("Beim Start automatisch im Hintergrund auf GitHub-Updates prüfen")
        self.auto_check_cb.setChecked(config.get("auto_check_updates", True))
        uc_layout.addWidget(self.auto_check_cb)

        repo_info_layout = QHBoxLayout()
        repo_lbl = QLabel(f"Aktuelle Version: <b>v{__version__}</b>  │  Quell-Repository: <code>https://github.com/{get_github_repo()}</code>")
        repo_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        repo_info_layout.addWidget(repo_lbl, 1)

        open_updater_btn = QPushButton("🚀 Update-Manager öffnen")
        open_updater_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_updater_btn.clicked.connect(self._open_updater_dialog)
        repo_info_layout.addWidget(open_updater_btn)
        uc_layout.addLayout(repo_info_layout)

        g_layout.addWidget(update_card)

        g_layout.addStretch()
        tabs.addTab(global_widget, "Allgemein")

        # Tab 2: ETS2
        tabs.addTab(self._create_game_tab("ets2", "Euro Truck Simulator 2"), "Euro Truck Simulator 2")

        # Tab 3: ATS
        tabs.addTab(self._create_game_tab("ats", "American Truck Simulator"), "American Truck Simulator")

        main_layout.addWidget(tabs)

    def _create_game_tab(self, game_key: str, game_name: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        cfg = config.get_game_config(game_key)

        # Proton toggle
        proton_cb = QCheckBox(f"{game_name} über Steam Proton (Wine) ausführen")
        proton_cb.setChecked(cfg.get("is_proton", False))
        layout.addWidget(proton_cb)
        setattr(self, f"{game_key}_proton_cb", proton_cb)

        # Custom Install Dir
        layout.addWidget(QLabel("Benutzerdefinierter Installationsordner (Spiel-Hauptverzeichnis):"))
        inst_row = QHBoxLayout()
        inst_input = QLineEdit(cfg.get("custom_install_dir", ""))
        inst_input.setPlaceholderText("z. B. .../Steam/steamapps/common/Euro Truck Simulator 2")
        inst_browse = QPushButton("Durchsuchen...")
        inst_browse.clicked.connect(lambda: self._browse_dir(inst_input))
        inst_row.addWidget(inst_input)
        inst_row.addWidget(inst_browse)
        layout.addLayout(inst_row)
        setattr(self, f"{game_key}_install_input", inst_input)

        # Custom User Dir
        layout.addWidget(QLabel("Benutzer-Datenverzeichnis (wo config.cfg & game.log.txt liegen):"))
        user_row = QHBoxLayout()
        user_input = QLineEdit(cfg.get("custom_user_dir", ""))
        user_input.setPlaceholderText("z. B. ~/.local/share/Euro Truck Simulator 2 oder Proton Documents-Ordner")
        user_browse = QPushButton("Durchsuchen...")
        user_browse.clicked.connect(lambda: self._browse_dir(user_input))
        user_row.addWidget(user_input)
        user_row.addWidget(user_browse)
        layout.addLayout(user_row)
        setattr(self, f"{game_key}_user_input", user_input)

        # Launch Args
        layout.addWidget(QLabel("Startparameter (Launch Arguments):"))
        args_input = QLineEdit(cfg.get("launch_args", "-nointro -mm_pool_size 4096"))
        args_input.setPlaceholderText("-nointro -mm_pool_size 4096")
        layout.addWidget(args_input)
        setattr(self, f"{game_key}_args_input", args_input)

        # Game Version Override
        layout.addWidget(QLabel("Spielversion manuell festlegen / überschreiben (optional, z. B. 1.50 oder 1.51):"))
        ver_input = QLineEdit(cfg.get("game_version_override", ""))
        ver_input.setPlaceholderText("Leer lassen für automatische Erkennung aus game.log.txt")
        layout.addWidget(ver_input)
        setattr(self, f"{game_key}_ver_input", ver_input)

        layout.addStretch()
        return widget

    def _browse_dir(self, target_input: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "Verzeichnis auswählen", target_input.text() or "")
        if path:
            target_input.setText(path)

    def _save_settings(self):
        # Save global
        config.set("zero_pollution_staging", self.zero_pollution_cb.isChecked())
        config.set("auto_sort_on_enable", self.auto_sort_cb.isChecked())
        config.set("auto_check_updates", self.auto_check_cb.isChecked())

        extra_paths = [p.strip() for p in self.extra_steam_input.text().split(",") if p.strip()]
        config.set("extra_steam_paths", extra_paths)

        # Save ETS2
        config.set_game_config("ets2", "is_proton", self.ets2_proton_cb.isChecked())
        config.set_game_config("ets2", "custom_install_dir", self.ets2_install_input.text().strip())
        config.set_game_config("ets2", "custom_user_dir", self.ets2_user_input.text().strip())
        config.set_game_config("ets2", "launch_args", self.ets2_args_input.text().strip())
        config.set_game_config("ets2", "game_version_override", self.ets2_ver_input.text().strip())

        # Save ATS
        config.set_game_config("ats", "is_proton", self.ats_proton_cb.isChecked())
        config.set_game_config("ats", "custom_install_dir", self.ats_install_input.text().strip())
        config.set_game_config("ats", "custom_user_dir", self.ats_user_input.text().strip())
        config.set_game_config("ats", "launch_args", self.ats_args_input.text().strip())
        config.set_game_config("ats", "game_version_override", self.ats_ver_input.text().strip())

        self.settings_saved.emit()
        QMessageBox.information(self, "Gespeichert", "Einstellungen wurden erfolgreich gespeichert.")

    def _open_updater_dialog(self):
        from truck_mod_manager.ui.dialogs import GitHubUpdateDialog
        dlg = GitHubUpdateDialog(self)
        dlg.exec()

