"""
Truck Tools View for Truck Mod Manager.
Provides an integrated savegame editor for ETS2 & ATS:
- Money, Level, XP & Driver Skills customization
- Fleet and Truck repair (0% wear), refuel, odometer & license plate editing
- Engine and Transmission swaps
- Trailer repair, cargo mass modifier (0 kg for Convoy / heavy haul)
- Automatic backups and 1-click restore
"""
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from truck_mod_manager.core.models import GameProfile, GameType, TruckGame
from truck_mod_manager.core.truck_tools import SaveGameInfo, TruckToolsEngine


class TruckToolsView(QWidget):
    """View providing savegame editing and maintenance tools (port of Truck Tools)."""
    save_modified = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game: Optional[TruckGame] = None
        self.profile: Optional[GameProfile] = None
        self.engine = TruckToolsEngine()
        self.saves: List[SaveGameInfo] = []
        self.current_save: Optional[SaveGameInfo] = None

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ---------------------------------------------------------------------
        # Top Toolbar Card: Savegame selection, reload, backup, save
        # ---------------------------------------------------------------------
        toolbar_card = QFrame()
        toolbar_card.setObjectName("toolbarCard")
        tb_layout = QHBoxLayout(toolbar_card)
        tb_layout.setContentsMargins(12, 8, 12, 8)
        tb_layout.setSpacing(10)

        lbl_save = QLabel("📁 Spielstand:")
        lbl_save.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 12px;")
        tb_layout.addWidget(lbl_save)

        self.save_combo = QComboBox()
        self.save_combo.setMinimumWidth(320)
        self.save_combo.currentIndexChanged.connect(self._on_save_selected)
        tb_layout.addWidget(self.save_combo, stretch=2)

        self.reload_btn = QPushButton("🔄 Neu laden")
        self.reload_btn.setToolTip("Aktuellen Spielstand neu von der Festplatte einlesen")
        self.reload_btn.clicked.connect(self._reload_current_save)
        tb_layout.addWidget(self.reload_btn)

        self.backup_btn = QPushButton("🛡️ Backup erstellen")
        self.backup_btn.setToolTip("Erstellt eine Sicherheitskopie des gewählten Spielstands")
        self.backup_btn.clicked.connect(self._create_backup)
        tb_layout.addWidget(self.backup_btn)

        tb_layout.addStretch(1)

        self.save_btn = QPushButton("💾 Spielstand speichern")
        self.save_btn.setObjectName("successBtn")
        self.save_btn.setStyleSheet(
            "QPushButton#successBtn { font-weight: bold; padding: 7px 18px; font-size: 13px; }"
        )
        self.save_btn.setToolTip("Schreibt alle vorgenommenen Änderungen direkt in die game.sii (inkl. Auto-Backup)")
        self.save_btn.clicked.connect(self._save_changes)
        tb_layout.addWidget(self.save_btn)

        main_layout.addWidget(toolbar_card)

        # Status banner when no save is loaded
        self.status_banner = QLabel("Bitte wähle oben einen Spielstand aus, um Daten zu laden.")
        self.status_banner.setStyleSheet(
            "background-color: #1e293b; color: #94a3b8; padding: 6px 12px; border-radius: 6px; font-size: 12px;"
        )
        main_layout.addWidget(self.status_banner)

        # ---------------------------------------------------------------------
        # Sub-Tabs for Truck Tools Options
        # ---------------------------------------------------------------------
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #1e293b; border-radius: 8px; }")

        # Tab 1: Profile & Finances
        self.profile_tab = self._create_profile_tab()
        self.sub_tabs.addTab(self.profile_tab, "👤 Profil && Finanzen")

        # Tab 2: Trucks & Fleet
        self.truck_tab = self._create_truck_tab()
        self.sub_tabs.addTab(self.truck_tab, "🚚 LKW && Fuhrpark")

        # Tab 3: Trailers & Cargo
        self.trailer_tab = self._create_trailer_tab()
        self.sub_tabs.addTab(self.trailer_tab, "🚛 Auflieger && Fracht")

        # Tab 4: Backups
        self.backup_tab = self._create_backup_tab()
        self.sub_tabs.addTab(self.backup_tab, "💾 Sicherungen")

        main_layout.addWidget(self.sub_tabs, stretch=1)

    # -------------------------------------------------------------------------
    # Tab 1: Profile & Finances UI
    # -------------------------------------------------------------------------

    def _create_profile_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(14)

        # 1. Money Card
        money_box = QGroupBox("💰 Bankkonto && Vermögen")
        money_layout = QGridLayout(money_box)
        money_layout.setSpacing(10)

        money_layout.addWidget(QLabel("Aktueller Kontostand:"), 0, 0)
        self.money_spin = QSpinBox()
        self.money_spin.setRange(-2000000000, 2000000000)
        self.money_spin.setSingleStep(100000)
        self.money_spin.setSuffix(" € / $")
        money_layout.addWidget(self.money_spin, 0, 1)

        btn_add_1m = QPushButton("+ 1.000.000")
        btn_add_1m.clicked.connect(lambda: self.money_spin.setValue(self.money_spin.value() + 1000000))
        money_layout.addWidget(btn_add_1m, 0, 2)

        btn_add_5m = QPushButton("+ 5.000.000")
        btn_add_5m.clicked.connect(lambda: self.money_spin.setValue(self.money_spin.value() + 5000000))
        money_layout.addWidget(btn_add_5m, 0, 3)

        btn_set_10m = QPushButton("Setze 10.000.000")
        btn_set_10m.clicked.connect(lambda: self.money_spin.setValue(10000000))
        money_layout.addWidget(btn_set_10m, 0, 4)

        c_layout.addWidget(money_box)

        # 2. XP & Level Card
        xp_box = QGroupBox("⭐ Level && Erfahrungspunkte (XP)")
        xp_layout = QGridLayout(xp_box)
        xp_layout.setSpacing(10)

        xp_layout.addWidget(QLabel("Erfahrungspunkte (XP):"), 0, 0)
        self.xp_spin = QSpinBox()
        self.xp_spin.setRange(0, 50000000)
        self.xp_spin.setSingleStep(10000)
        self.xp_spin.setSuffix(" XP")
        xp_layout.addWidget(self.xp_spin, 0, 1)

        btn_xp_lvl30 = QPushButton("Level 30 (100.000 XP)")
        btn_xp_lvl30.clicked.connect(lambda: self.xp_spin.setValue(100000))
        xp_layout.addWidget(btn_xp_lvl30, 0, 2)

        btn_xp_lvl50 = QPushButton("Level 50 (200.000 XP)")
        btn_xp_lvl50.clicked.connect(lambda: self.xp_spin.setValue(200000))
        xp_layout.addWidget(btn_xp_lvl50, 0, 3)

        btn_xp_lvl100 = QPushButton("Level 100 (500.000 XP)")
        btn_xp_lvl100.clicked.connect(lambda: self.xp_spin.setValue(500000))
        xp_layout.addWidget(btn_xp_lvl100, 0, 4)

        c_layout.addWidget(xp_box)

        # 3. Skills Card
        skills_box = QGroupBox("🎓 Fahrer-Fertigkeiten (Skills)")
        skills_layout = QVBoxLayout(skills_box)
        skills_layout.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(8)

        grid.addWidget(QLabel("Gefahrgut (ADR):"), 0, 0)
        self.skill_adr_spin = QSpinBox()
        self.skill_adr_spin.setRange(0, 63)
        self.skill_adr_spin.setToolTip("Bitmask für ADR-Klassen 1-6 (63 = Alle Klassen freigeschaltet)")
        grid.addWidget(self.skill_adr_spin, 0, 1)

        grid.addWidget(QLabel("Fernfahrt:"), 0, 2)
        self.skill_dist_spin = QSpinBox()
        self.skill_dist_spin.setRange(0, 6)
        grid.addWidget(self.skill_dist_spin, 0, 3)

        grid.addWidget(QLabel("Schwertransport:"), 1, 0)
        self.skill_heavy_spin = QSpinBox()
        self.skill_heavy_spin.setRange(0, 6)
        grid.addWidget(self.skill_heavy_spin, 1, 1)

        grid.addWidget(QLabel("Zerbrechliche Fracht:"), 1, 2)
        self.skill_fragile_spin = QSpinBox()
        self.skill_fragile_spin.setRange(0, 6)
        grid.addWidget(self.skill_fragile_spin, 1, 3)

        grid.addWidget(QLabel("Eilzustellung:"), 2, 0)
        self.skill_urgent_spin = QSpinBox()
        self.skill_urgent_spin.setRange(0, 6)
        grid.addWidget(self.skill_urgent_spin, 2, 1)

        grid.addWidget(QLabel("Sparsames Fahren:"), 2, 2)
        self.skill_mech_spin = QSpinBox()
        self.skill_mech_spin.setRange(0, 6)
        grid.addWidget(self.skill_mech_spin, 2, 3)

        skills_layout.addLayout(grid)

        btn_max_skills = QPushButton("⭐ Alle Fertigkeiten maximieren (Max Skills)")
        btn_max_skills.setStyleSheet("font-weight: bold; background-color: #1e3a8a; color: #ffffff;")
        btn_max_skills.clicked.connect(self._on_max_skills_clicked)
        skills_layout.addWidget(btn_max_skills)

        c_layout.addWidget(skills_box)

        # 4. Garages & Exploration Card
        explore_box = QGroupBox("🏢 Garagen && Kartenerkundung")
        explore_layout = QHBoxLayout(explore_box)
        explore_layout.setSpacing(12)

        self.btn_garages = QPushButton("🏢 Alle Garagen freischalten && voll ausbauen")
        self.btn_garages.setToolTip("Setzt den Status aller Garagen im Spielstand auf Stufe 3 (5 Stellplätze)")
        self.btn_garages.clicked.connect(self._on_unlock_garages_clicked)
        explore_layout.addWidget(self.btn_garages)

        self.btn_cities = QPushButton("🗺️ 100% Städte && alle Händler entdecken")
        self.btn_cities.setToolTip("Schaltet alle Städte und LKW-Händler auf der Weltkarte frei")
        self.btn_cities.clicked.connect(self._on_unlock_cities_clicked)
        explore_layout.addWidget(self.btn_cities)

        c_layout.addWidget(explore_box)
        c_layout.addStretch(1)

        scroll.setWidget(container)
        layout.addWidget(scroll)
        return widget

    # -------------------------------------------------------------------------
    # Tab 2: Trucks & Fleet UI
    # -------------------------------------------------------------------------

    def _create_truck_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(14)

        # 1. Active Truck Info
        info_box = QGroupBox("🚛 Aktiver Spieler-LKW")
        info_layout = QGridLayout(info_box)
        info_layout.setSpacing(8)

        self.lbl_truck_model = QLabel("Modell: Lädt...")
        self.lbl_truck_model.setStyleSheet("font-weight: bold; font-size: 13px; color: #38bdf8;")
        info_layout.addWidget(self.lbl_truck_model, 0, 0, 1, 2)

        self.lbl_truck_engine = QLabel("Motor: -")
        info_layout.addWidget(self.lbl_truck_engine, 1, 0)

        self.lbl_truck_trans = QLabel("Getriebe: -")
        info_layout.addWidget(self.lbl_truck_trans, 1, 1)

        self.lbl_truck_plate = QLabel("Kennzeichen: -")
        info_layout.addWidget(self.lbl_truck_plate, 2, 0)

        self.lbl_truck_fuel = QLabel("Tank: 100%")
        info_layout.addWidget(self.lbl_truck_fuel, 2, 1)

        c_layout.addWidget(info_box)

        # 2. Instant Fleet Maintenance Actions
        maint_box = QGroupBox("⚡ Sofort-Wartung (Fuhrpark && Spieler-LKW)")
        maint_layout = QHBoxLayout(maint_box)
        maint_layout.setSpacing(10)

        btn_repair = QPushButton("🔧 Komplett reparieren (0% Verschleiß)")
        btn_repair.setStyleSheet("background-color: #064e3b; color: #6ee7b7; font-weight: bold;")
        btn_repair.setToolTip("Setzt sämtlichen Verschleiß (Motor, Getriebe, Fahrwerk, Räder, Kabine) bei allen LKW auf 0")
        btn_repair.clicked.connect(self._on_repair_trucks_clicked)
        maint_layout.addWidget(btn_repair)

        btn_refuel = QPushButton("⛽ Voll tanken (100%)")
        btn_refuel.clicked.connect(self._on_refuel_trucks_clicked)
        maint_layout.addWidget(btn_refuel)

        btn_inf_fuel = QPushButton("♾️ Unendlich Kraftstoff")
        btn_inf_fuel.setToolTip("Setzt den Tankwert auf den unendlichen Gleitkommawert (&4f000000)")
        btn_inf_fuel.clicked.connect(self._on_infinite_fuel_clicked)
        maint_layout.addWidget(btn_inf_fuel)

        c_layout.addWidget(maint_box)

        # 3. Odometer & License Plate
        custom_box = QGroupBox("📝 Kilometerstand && Kennzeichen anpassen")
        custom_layout = QGridLayout(custom_box)
        custom_layout.setSpacing(10)

        custom_layout.addWidget(QLabel("Kilometerstand:"), 0, 0)
        self.mileage_spin = QSpinBox()
        self.mileage_spin.setRange(0, 99999999)
        self.mileage_spin.setSingleStep(1000)
        self.mileage_spin.setSuffix(" km")
        custom_layout.addWidget(self.mileage_spin, 0, 1)

        btn_set_km = QPushButton("Kilometerstand übernehmen")
        btn_set_km.clicked.connect(self._on_set_mileage_clicked)
        custom_layout.addWidget(btn_set_km, 0, 2)

        custom_layout.addWidget(QLabel("Wunsch-Kennzeichen:"), 1, 0)
        self.plate_text = QLineEdit()
        self.plate_text.setPlaceholderText("z. B. M-TK 730")
        custom_layout.addWidget(self.plate_text, 1, 1)

        btn_set_plate = QPushButton("Kennzeichen übernehmen")
        btn_set_plate.clicked.connect(self._on_set_plate_clicked)
        custom_layout.addWidget(btn_set_plate, 1, 2)

        c_layout.addWidget(custom_box)

        # 4. Engine & Transmission Swap
        swap_box = QGroupBox("⚙️ Motor- && Getriebetausch (Engine && Transmission Swap)")
        swap_layout = QGridLayout(swap_box)
        swap_layout.setSpacing(10)

        swap_layout.addWidget(QLabel("Marke:"), 0, 0)
        self.swap_brand_combo = QComboBox()
        self.swap_brand_combo.currentIndexChanged.connect(self._on_swap_brand_changed)
        swap_layout.addWidget(self.swap_brand_combo, 0, 1)

        swap_layout.addWidget(QLabel("Modell:"), 0, 2)
        self.swap_model_combo = QComboBox()
        self.swap_model_combo.currentIndexChanged.connect(self._on_swap_model_changed)
        swap_layout.addWidget(self.swap_model_combo, 0, 3)

        swap_layout.addWidget(QLabel("Wunsch-Motor:"), 1, 0)
        self.swap_engine_combo = QComboBox()
        swap_layout.addWidget(self.swap_engine_combo, 1, 1)

        btn_swap_engine = QPushButton("Motor einbauen")
        btn_swap_engine.setStyleSheet("font-weight: bold;")
        btn_swap_engine.clicked.connect(self._on_swap_engine_clicked)
        swap_layout.addWidget(btn_swap_engine, 1, 2)

        swap_layout.addWidget(QLabel("Wunsch-Getriebe:"), 2, 0)
        self.swap_trans_combo = QComboBox()
        swap_layout.addWidget(self.swap_trans_combo, 2, 1)

        btn_swap_trans = QPushButton("Getriebe einbauen")
        btn_swap_trans.setStyleSheet("font-weight: bold;")
        btn_swap_trans.clicked.connect(self._on_swap_trans_clicked)
        swap_layout.addWidget(btn_swap_trans, 2, 2)

        c_layout.addWidget(swap_box)
        c_layout.addStretch(1)

        scroll.setWidget(container)
        layout.addWidget(scroll)
        return widget

    # -------------------------------------------------------------------------
    # Tab 3: Trailers & Cargo UI
    # -------------------------------------------------------------------------

    def _create_trailer_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(14)

        # 1. Trailer Status
        info_box = QGroupBox("🚛 Aktiver Auflieger && Fracht")
        info_layout = QGridLayout(info_box)
        info_layout.setSpacing(8)

        self.lbl_trailer_id = QLabel("Auflieger: Lädt...")
        self.lbl_trailer_id.setStyleSheet("font-weight: bold; font-size: 13px; color: #38bdf8;")
        info_layout.addWidget(self.lbl_trailer_id, 0, 0)

        self.lbl_cargo_mass = QLabel("Frachtgewicht: 0 kg")
        info_layout.addWidget(self.lbl_cargo_mass, 0, 1)

        c_layout.addWidget(info_box)

        # 2. Trailer Repair
        maint_box = QGroupBox("⚡ Auflieger-Wartung")
        maint_layout = QHBoxLayout(maint_box)

        btn_repair_trailers = QPushButton("🔧 Alle Auflieger reparieren (0% Schaden)")
        btn_repair_trailers.setStyleSheet("background-color: #064e3b; color: #6ee7b7; font-weight: bold;")
        btn_repair_trailers.clicked.connect(self._on_repair_trailers_clicked)
        maint_layout.addWidget(btn_repair_trailers)

        c_layout.addWidget(maint_box)

        # 3. Cargo Mass Modifier
        cargo_box = QGroupBox("⚖️ Frachtgewicht-Modifikator (Cargo Mass)")
        cargo_layout = QGridLayout(cargo_box)
        cargo_layout.setSpacing(10)

        cargo_layout.addWidget(QLabel("Frachtgewicht (kg):"), 0, 0)
        self.cargo_spin = QSpinBox()
        self.cargo_spin.setRange(0, 500000)
        self.cargo_spin.setSingleStep(1000)
        self.cargo_spin.setSuffix(" kg")
        cargo_layout.addWidget(self.cargo_spin, 0, 1)

        btn_set_cargo = QPushButton("Gewicht anwenden")
        btn_set_cargo.clicked.connect(self._on_set_cargo_clicked)
        cargo_layout.addWidget(btn_set_cargo, 0, 2)

        btn_cargo_0 = QPushButton("0 kg (Convoy No-Weight)")
        btn_cargo_0.setToolTip("Entfernt jegliches Frachtgewicht – maximale Beschleunigung und Höchstgeschwindigkeit")
        btn_cargo_0.clicked.connect(lambda: self.cargo_spin.setValue(0))
        cargo_layout.addWidget(btn_cargo_0, 1, 0)

        btn_cargo_20k = QPushButton("Standard (20.000 kg)")
        btn_cargo_20k.clicked.connect(lambda: self.cargo_spin.setValue(20000))
        cargo_layout.addWidget(btn_cargo_20k, 1, 1)

        btn_cargo_60k = QPushButton("Schwerlast (60.000 kg)")
        btn_cargo_60k.clicked.connect(lambda: self.cargo_spin.setValue(60000))
        cargo_layout.addWidget(btn_cargo_60k, 1, 2)

        c_layout.addWidget(cargo_box)

        # 4. Trailer License Plate
        plate_box = QGroupBox("📝 Auflieger-Kennzeichen")
        plate_layout = QHBoxLayout(plate_box)
        plate_layout.setSpacing(10)

        self.trailer_plate_text = QLineEdit()
        self.trailer_plate_text.setPlaceholderText("z. B. HH-TL 900")
        plate_layout.addWidget(self.trailer_plate_text)

        btn_set_t_plate = QPushButton("Kennzeichen anwenden")
        btn_set_t_plate.clicked.connect(self._on_set_trailer_plate_clicked)
        plate_layout.addWidget(btn_set_t_plate)

        c_layout.addWidget(plate_box)
        c_layout.addStretch(1)

        scroll.setWidget(container)
        layout.addWidget(scroll)
        return widget

    # -------------------------------------------------------------------------
    # Tab 4: Backups UI
    # -------------------------------------------------------------------------

    def _create_backup_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        lbl = QLabel("Sicherheitskopien für den ausgewählten Spielstand:")
        lbl.setStyleSheet("font-weight: bold; color: #94a3b8;")
        layout.addWidget(lbl)

        self.backup_list = QListWidget()
        layout.addWidget(self.backup_list, stretch=1)

        btn_layout = QHBoxLayout()
        btn_restore = QPushButton("↩️ Ausgewähltes Backup wiederherstellen")
        btn_restore.setStyleSheet("background-color: #1e3a8a; color: #ffffff; font-weight: bold;")
        btn_restore.clicked.connect(self._on_restore_backup_clicked)
        btn_layout.addWidget(btn_restore)

        btn_refresh_bak = QPushButton("🔄 Liste aktualisieren")
        btn_refresh_bak.clicked.connect(self._refresh_backup_list)
        btn_layout.addWidget(btn_refresh_bak)

        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)
        return widget

    # -------------------------------------------------------------------------
    # Public Controller API: Profile & Game selection
    # -------------------------------------------------------------------------

    def set_game_and_profile(self, game: Optional[TruckGame], profile: Optional[GameProfile]):
        """Called by MainWindow when game or active profile changes."""
        self.game = game
        self.profile = profile
        self._populate_swap_brands()
        self.refresh_savegames()

    def refresh_savegames(self):
        """Discovers and populates savegames for the currently active profile."""
        self.save_combo.blockSignals(True)
        self.save_combo.clear()
        self.saves = []

        if not self.profile:
            self.status_banner.setText("Kein Spielstand-Profil ausgewählt.")
            self.save_combo.blockSignals(False)
            return

        self.saves = self.engine.list_savegames(self.profile)
        if not self.saves:
            self.status_banner.setText(f"Keine Spielstände im Profil '{self.profile.name}' gefunden.")
            self.save_combo.blockSignals(False)
            return

        for save in self.saves:
            dt_str = save.save_time.strftime("%d.%m.%Y %H:%M") if save.save_time else ""
            item_text = f"{save.display_name}  [{dt_str}]"
            self.save_combo.addItem(item_text, save)

        self.save_combo.blockSignals(False)
        self._on_save_selected(0)

    def _on_save_selected(self, index: int):
        if index < 0 or index >= len(self.saves):
            return
        self.current_save = self.saves[index]
        self._load_save_data(self.current_save)

    def _reload_current_save(self):
        if self.current_save:
            self._load_save_data(self.current_save)

    def _load_save_data(self, save: SaveGameInfo):
        """Loads savegame into engine and populates all UI controls."""
        success = self.engine.load_save(save)
        if not success:
            self.status_banner.setText(f"❌ Fehler beim Entschlüsseln von {save.folder_name}/game.sii")
            return

        dt_str = save.save_time.strftime("%d.%m.%Y %H:%M") if save.save_time else ""
        self.status_banner.setText(f"✔ Spielstand geladen: {save.display_name} ({dt_str})")

        # 1. Money & XP
        money = self.engine.get_money() or 0
        self.money_spin.setValue(money)

        xp = self.engine.get_experience() or 0
        self.xp_spin.setValue(xp)

        # 2. Skills
        skills = self.engine.get_skills()
        self.skill_adr_spin.setValue(skills.get("adr", 0))
        self.skill_dist_spin.setValue(skills.get("long_dist", 0))
        self.skill_heavy_spin.setValue(skills.get("heavy", 0))
        self.skill_fragile_spin.setValue(skills.get("fragile", 0))
        self.skill_urgent_spin.setValue(skills.get("urgent", 0))
        self.skill_mech_spin.setValue(skills.get("mechanical", 0))

        # 3. Truck Summary
        truck = self.engine.get_player_truck_summary()
        self.lbl_truck_model.setText(f"Modell: {truck['model_name']}")
        self.lbl_truck_engine.setText(f"Motor: {truck['engine_name']}")
        self.lbl_truck_trans.setText(f"Getriebe: {truck['transmission_name']}")
        self.lbl_truck_plate.setText(f"Kennzeichen: {truck['license_plate'] or 'Keines'}")
        fuel_str = "♾️ Unendlich" if truck['has_infinite_fuel'] else f"{truck['fuel_percent']:.1f}%"
        self.lbl_truck_fuel.setText(f"Tank: {fuel_str}")
        self.mileage_spin.setValue(truck.get("mileage_km", 0))
        self.plate_text.setText(truck.get("license_plate", ""))

        # 4. Trailer Summary
        trailer = self.engine.get_player_trailer_summary()
        self.lbl_trailer_id.setText(f"Auflieger: {trailer['trailer_id']}")
        self.lbl_cargo_mass.setText(f"Frachtgewicht: {trailer['cargo_mass_kg']:.0f} kg")
        self.cargo_spin.setValue(int(trailer["cargo_mass_kg"]))

        # 5. Backups
        self._refresh_backup_list()

    def _refresh_backup_list(self):
        self.backup_list.clear()
        if not self.current_save:
            return
        baks = self.engine.list_backups(self.current_save.save_dir)
        for b in baks:
            mtime = datetime.datetime.fromtimestamp(b.stat().st_mtime)
            size_kb = b.stat().st_size / 1024
            item = QListWidgetItem(f"💾 {b.name}  ({size_kb:.1f} KB, {mtime.strftime('%d.%m.%Y %H:%M:%S')})")
            item.setData(Qt.ItemDataRole.UserRole, str(b))
            self.backup_list.addItem(item)

    # -------------------------------------------------------------------------
    # Action Handlers
    # -------------------------------------------------------------------------

    def _create_backup(self):
        if not self.current_save:
            return
        bak = self.engine.create_backup(self.current_save)
        if bak:
            QMessageBox.information(
                self, "Backup erstellt",
                f"Sicherheitskopie erfolgreich erstellt:\n{bak.name}"
            )
            self._refresh_backup_list()

    def _on_restore_backup_clicked(self):
        curr_item = self.backup_list.currentItem()
        if not curr_item or not self.current_save:
            QMessageBox.warning(self, "Hinweis", "Bitte wähle eine Sicherung aus der Liste aus.")
            return

        bak_path = Path(curr_item.data(Qt.ItemDataRole.UserRole))
        if not bak_path.is_file():
            return

        reply = QMessageBox.question(
            self, "Backup wiederherstellen",
            f"Möchtest du das Backup '{bak_path.name}' wirklich wiederherstellen?\n"
            "Der aktuelle Spielstand wird dabei überschrieben.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = self.engine.restore_backup(bak_path, self.current_save.save_dir)
            if success:
                QMessageBox.information(self, "Wiederhergestellt", "Spielstand erfolgreich aus Backup wiederhergestellt!")
                self._load_save_data(self.current_save)
            else:
                QMessageBox.critical(self, "Fehler", "Wiederherstellung fehlgeschlagen.")

    def _save_changes(self):
        """Applies all form values to memory and writes back to game.sii."""
        if not self.engine.is_loaded() or not self.current_save:
            return

        # 1. Update Profile & Finances
        self.engine.set_money(self.money_spin.value())
        self.engine.set_experience(self.xp_spin.value())
        self.engine.set_skills({
            "adr": self.skill_adr_spin.value(),
            "long_dist": self.skill_dist_spin.value(),
            "heavy": self.skill_heavy_spin.value(),
            "fragile": self.skill_fragile_spin.value(),
            "urgent": self.skill_urgent_spin.value(),
            "mechanical": self.skill_mech_spin.value(),
        })

        # 2. Write save to disk with auto-backup
        success = self.engine.save_changes(create_auto_backup=True)
        if success:
            QMessageBox.information(
                self, "Gespeichert",
                f"Alle Änderungen wurden erfolgreich in '{self.current_save.folder_name}/game.sii' gespeichert!\n"
                "Eine automatische Sicherheitskopie (.bak) wurde vorab angelegt."
            )
            self.save_modified.emit(self.current_save.folder_name)
            self._load_save_data(self.current_save)
        else:
            QMessageBox.critical(self, "Fehler", "Fehler beim Speichern des Spielstands.")

    def _on_max_skills_clicked(self):
        self.skill_adr_spin.setValue(63)
        self.skill_dist_spin.setValue(6)
        self.skill_heavy_spin.setValue(6)
        self.skill_fragile_spin.setValue(6)
        self.skill_urgent_spin.setValue(6)
        self.skill_mech_spin.setValue(6)
        QMessageBox.information(
            self, "Fertigkeiten maximiert",
            "Alle Fertigkeiten (ADR 1-6 & alle Spezialisierungen auf Stufe 6) wurden im Editor maximiert.\n"
            "Klicke auf '💾 Spielstand speichern', um die Änderungen dauerhaft zu übernehmen."
        )

    def _on_unlock_garages_clicked(self):
        count = self.engine.unlock_all_garages()
        QMessageBox.information(
            self, "Garagen ausgebaut",
            f"{count} Garagen im Spielstand wurden auf Maximalstufe (5 Stellplätze) ausgebaut!\n"
            "Klicke auf '💾 Spielstand speichern', um die Änderungen zu sichern."
        )

    def _on_unlock_cities_clicked(self):
        cities, dealers = self.engine.unlock_all_cities_and_dealers()
        QMessageBox.information(
            self, "Erkundung freigeschaltet",
            f"{cities} Städte und {dealers} LKW-Händler wurden auf der Karte als entdeckt markiert!\n"
            "Klicke auf '💾 Spielstand speichern', um die Änderungen zu sichern."
        )

    def _on_repair_trucks_clicked(self):
        count = self.engine.repair_all_trucks()
        QMessageBox.information(
            self, "LKW repariert",
            f"Komplettreparatur durchgeführt: {count} Verschleißwerte aller LKW und Komponenten wurden auf 0% gesetzt!"
        )
        self._load_save_data(self.current_save)

    def _on_refuel_trucks_clicked(self):
        count = self.engine.refuel_all_trucks(infinite=False)
        QMessageBox.information(self, "Vollgetankt", f"{count} LKW-Tanks wurden auf 100% gefüllt!")
        self._load_save_data(self.current_save)

    def _on_infinite_fuel_clicked(self):
        count = self.engine.refuel_all_trucks(infinite=True)
        QMessageBox.information(
            self, "Unendlich Kraftstoff",
            f"Unendlicher Tankmodus für {count} LKW aktiviert!\n"
            "Klicke auf '💾 Spielstand speichern', um die Änderung zu sichern."
        )
        self._load_save_data(self.current_save)

    def _on_set_mileage_clicked(self):
        km = self.mileage_spin.value()
        count = self.engine.set_truck_mileage(km)
        QMessageBox.information(self, "Kilometerstand", f"Kilometerstand von {count} LKW auf {km:,} km gesetzt!")

    def _on_set_plate_clicked(self):
        text = self.plate_text.text().strip()
        if text:
            count = self.engine.set_truck_license_plate(text)
            QMessageBox.information(self, "Kennzeichen", f"Kennzeichen '{text}' für {count} LKW zugewiesen!")

    def _on_repair_trailers_clicked(self):
        count = self.engine.repair_all_trailers()
        QMessageBox.information(self, "Auflieger repariert", f"{count} Auflieger wurden auf 0% Schaden repariert!")

    def _on_set_cargo_clicked(self):
        mass = self.cargo_spin.value()
        count = self.engine.set_cargo_mass(mass)
        QMessageBox.information(self, "Frachtgewicht", f"Frachtgewicht auf {mass:,} kg gesetzt ({count} Auflieger)!")

    def _on_set_trailer_plate_clicked(self):
        text = self.trailer_plate_text.text().strip()
        if text:
            count = self.engine.set_trailer_license_plate(text)
            QMessageBox.information(self, "Auflieger-Kennzeichen", f"Kennzeichen '{text}' für {count} Auflieger gesetzt!")

    # -------------------------------------------------------------------------
    # Engine & Transmission Swap Helpers
    # -------------------------------------------------------------------------

    def _get_active_trucks_db(self) -> Dict[str, Any]:
        if self.game and self.game.game_type == GameType.ATS:
            return self.engine.trucks_data_ats
        return self.engine.trucks_data_ets2

    def _populate_swap_brands(self):
        self.swap_brand_combo.blockSignals(True)
        self.swap_brand_combo.clear()
        db = self._get_active_trucks_db()
        for brand in sorted(list(db.keys())):
            self.swap_brand_combo.addItem(brand.upper(), brand)
        self.swap_brand_combo.blockSignals(False)
        self._on_swap_brand_changed(0)

    def _on_swap_brand_changed(self, index: int):
        self.swap_model_combo.blockSignals(True)
        self.swap_model_combo.clear()
        db = self._get_active_trucks_db()
        brand_key = self.swap_brand_combo.currentData()
        models = db.get(brand_key, [])
        for m in models:
            m_name = str(m.get("model", "Standard")).title()
            self.swap_model_combo.addItem(m_name, m)
        self.swap_model_combo.blockSignals(False)
        self._on_swap_model_changed(0)

    def _on_swap_model_changed(self, index: int):
        self.swap_engine_combo.clear()
        self.swap_trans_combo.clear()
        model_data = self.swap_model_combo.currentData()
        if not model_data:
            return

        for eng in model_data.get("engines", []):
            name = eng.get("name", "Motor")
            hp = eng.get("hp", "")
            label = f"{name} ({hp} PS)" if hp else name
            self.swap_engine_combo.addItem(label, eng.get("data_path", ""))

        for trans in model_data.get("transmissions", []):
            name = trans.get("name", "Getriebe")
            ret = "mit Retarder" if trans.get("retarder", False) else "ohne Retarder"
            label = f"{name} ({ret})"
            self.swap_trans_combo.addItem(label, trans.get("data_path", ""))

    def _on_swap_engine_clicked(self):
        path = self.swap_engine_combo.currentData()
        if not path:
            return
        success = self.engine.swap_player_truck_engine(path)
        if success:
            eng_lbl = self.swap_engine_combo.currentText()
            QMessageBox.information(
                self, "Motor getauscht",
                f"Motor '{eng_lbl}' wurde erfolgreich in den LKW eingebaut!\n"
                "Klicke auf '💾 Spielstand speichern', um die Änderung zu sichern."
            )
            self._load_save_data(self.current_save)
        else:
            QMessageBox.warning(self, "Hinweis", "Kein aktiver Motorblock im Spielstand gefunden.")

    def _on_swap_trans_clicked(self):
        path = self.swap_trans_combo.currentData()
        if not path:
            return
        success = self.engine.swap_player_truck_transmission(path)
        if success:
            trans_lbl = self.swap_trans_combo.currentText()
            QMessageBox.information(
                self, "Getriebe getauscht",
                f"Getriebe '{trans_lbl}' wurde erfolgreich in den LKW eingebaut!\n"
                "Klicke auf '💾 Spielstand speichern', um die Änderung zu sichern."
            )
            self._load_save_data(self.current_save)
        else:
            QMessageBox.warning(self, "Hinweis", "Kein aktiver Getriebeblock im Spielstand gefunden.")
