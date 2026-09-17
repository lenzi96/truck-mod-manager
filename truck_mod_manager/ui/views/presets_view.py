"""
Presets View for Truck Mod Manager.
Manages saved loadouts (e.g. ProMods Map Combo, Vanilla, Convoy).
"""
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QFileDialog,
    QSplitter, QTextBrowser
)

from truck_mod_manager.core.models import GameType, ModPreset, ScsMod, TruckGame
from truck_mod_manager.core.preset_manager import PresetManager
from truck_mod_manager.ui.dialogs.preset_dialog import SavePresetDialog


class PresetsView(QWidget):
    preset_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game: Optional[TruckGame] = None
        self.all_mods: List[ScsMod] = []
        self.presets: List[ModPreset] = []
        self.selected_preset: Optional[ModPreset] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Bar
        header = QFrame()
        header.setObjectName("headerFrame")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 8, 10, 8)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        title = QLabel("Mod-Presets & Profile")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc;")
        info_col.addWidget(title)
        desc = QLabel("Speichere verschiedene Mod-Kombinationen (z. B. ProMods, Singleplayer, Convoy) und wechsle mit 1 Klick.")
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        info_col.addWidget(desc)
        h_layout.addLayout(info_col, stretch=1)

        new_preset_btn = QPushButton("💾 Aktuelle Auswahl als Preset speichern")
        new_preset_btn.setObjectName("primaryBtn")
        new_preset_btn.clicked.connect(self._save_current_as_preset)
        h_layout.addWidget(new_preset_btn)

        layout.addWidget(header)

        # Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Column: Presets List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.preset_list = QListWidget()
        self.preset_list.setSpacing(4)
        self.preset_list.setStyleSheet("""
            QListWidget::item {
                padding: 10px 14px;
                border-radius: 6px;
                margin-bottom: 3px;
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #f8fafc;
                font-size: 13px;
                font-weight: 500;
            }
            QListWidget::item:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QListWidget::item:selected {
                background-color: #2563eb;
                border-color: #3b82f6;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        self.preset_list.itemClicked.connect(self._on_preset_selected)
        left_layout.addWidget(self.preset_list)

        # Left actions
        left_btn_row = QHBoxLayout()
        import_btn = QPushButton("📥 Importieren...")
        import_btn.clicked.connect(self._import_preset)
        left_btn_row.addWidget(import_btn)

        export_btn = QPushButton("📤 Exportieren...")
        export_btn.clicked.connect(self._export_preset)
        left_btn_row.addWidget(export_btn)

        del_btn = QPushButton("🗑️ Löschen")
        del_btn.clicked.connect(self._delete_preset)
        left_btn_row.addWidget(del_btn)

        left_layout.addLayout(left_btn_row)
        splitter.addWidget(left_widget)

        # Right Column: Preset Details & Mod Preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        self.detail_card = QFrame()
        self.detail_card.setObjectName("cardFrame")
        detail_layout = QVBoxLayout(self.detail_card)

        self.preset_title = QLabel("Kein Preset ausgewählt")
        self.preset_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        detail_layout.addWidget(self.preset_title)

        self.preset_desc = QLabel("")
        self.preset_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.preset_desc.setWordWrap(True)
        detail_layout.addWidget(self.preset_desc)

        self.apply_btn = QPushButton("▶ Dieses Preset aktivieren")
        self.apply_btn.setObjectName("successBtn")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_preset)
        detail_layout.addWidget(self.apply_btn)

        right_layout.addWidget(self.detail_card)

        right_layout.addWidget(QLabel("Enthaltene Mods in Ladereihenfolge:"))
        self.mods_preview = QTextBrowser()
        right_layout.addWidget(self.mods_preview)

        splitter.addWidget(right_widget)
        splitter.setSizes([350, 550])

        layout.addWidget(splitter)

    def set_game(self, game: TruckGame, all_mods: List[ScsMod]):
        self.game = game
        self.all_mods = all_mods
        self.refresh()

    def refresh(self):
        if not self.game:
            return
        self.presets = PresetManager.list_presets(self.game.game_type)
        self.preset_list.clear()

        for p in self.presets:
            item = QListWidgetItem(f"📁 {p.name} ({len(p.mod_order)} Mods)")
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.preset_list.addItem(item)

        if not self.presets:
            self.preset_title.setText("Keine Presets vorhanden")
            self.preset_desc.setText("Erstelle ein Preset, indem du deine gewünschten Mods aktivierst und auf 'Als Preset speichern' klickst.")
            self.mods_preview.clear()
            self.apply_btn.setEnabled(False)

    def _on_preset_selected(self, item: QListWidgetItem):
        preset: ModPreset = item.data(Qt.ItemDataRole.UserRole)
        self.selected_preset = preset
        self.preset_title.setText(preset.name)
        self.preset_desc.setText(preset.description or "Keine Beschreibung.")
        self.apply_btn.setEnabled(True)

        lines = []
        for idx, mod_file in enumerate(preset.mod_order, start=1):
            # Find matching mod name if installed
            match = next((m for m in self.all_mods if m.file_name == mod_file), None)
            display = f"<b>#{idx}</b>: {match.display_name} <i>({mod_file})</i>" if match else f"<b>#{idx}</b>: {mod_file} <span style='color: #ef4444;'>(fehlt)</span>"
            lines.append(display)

        html = "<ul style='margin-left: -20px;'>" + "".join([f"<li>{l}</li>" for l in lines]) + "</ul>"
        self.mods_preview.setHtml(html)

    def _save_current_as_preset(self):
        if not self.game:
            return
        active = [m for m in self.all_mods if m.is_enabled]
        if not active:
            QMessageBox.warning(self, "Hinweis", "Es sind derzeit keine Mods aktiv. Aktiviere zuerst mindestens eine Mod.")
            return

        # Sort by priority
        active.sort(key=lambda m: m.priority if m.priority > 0 else 99999)

        dlg = SavePresetDialog(self)
        if dlg.exec() == SavePresetDialog.DialogCode.Accepted:
            data = dlg.get_data()
            preset = ModPreset(
                name=data["name"],
                game_type=self.game.game_type,
                description=data["description"],
                mod_order=[m.file_name for m in active],
            )
            PresetManager.save_preset(preset)
            self.refresh()
            QMessageBox.information(self, "Gespeichert", f"Preset '{preset.name}' erfolgreich gespeichert.")

    def _apply_preset(self):
        if not self.selected_preset or not self.game:
            return
        reordered = PresetManager.apply_preset(self.selected_preset, self.all_mods)
        self.all_mods.clear()
        self.all_mods.extend(reordered)
        self.preset_applied.emit()
        QMessageBox.information(
            self,
            "Preset aktiviert",
            f"Preset '{self.selected_preset.name}' wurde geladen. {len(self.selected_preset.mod_order)} Mods aktiviert."
        )

    def _delete_preset(self):
        if not self.selected_preset or not self.game:
            return
        reply = QMessageBox.question(
            self,
            "Löschen bestätigen",
            f"Möchtest du das Preset '{self.selected_preset.name}' wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            PresetManager.delete_preset(self.selected_preset.name, self.game.game_type)
            self.selected_preset = None
            self.refresh()

    def _export_preset(self):
        if not self.selected_preset:
            return
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Preset exportieren",
            f"{self.selected_preset.name}.json",
            "JSON-Dateien (*.json)"
        )
        if target:
            PresetManager.export_preset(self.selected_preset, Path(target))
            QMessageBox.information(self, "Exportiert", f"Preset exportiert nach:\n{target}")

    def _import_preset(self):
        if not self.game:
            return
        src, _ = QFileDialog.getOpenFileName(
            self,
            "Preset importieren",
            "",
            "JSON-Dateien (*.json)"
        )
        if src:
            try:
                preset = PresetManager.import_preset(Path(src))
                self.refresh()
                QMessageBox.information(self, "Importiert", f"Preset '{preset.name}' importiert.")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Konnte Preset nicht importieren: {e}")
