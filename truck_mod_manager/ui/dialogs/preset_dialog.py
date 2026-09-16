"""
Dialog for saving a new Mod Preset.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QMessageBox
)


class SavePresetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neues Mod-Preset speichern")
        self.setFixedSize(450, 260)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Name
        layout.addWidget(QLabel("Preset-Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("z. B. ProMods 1.50 + Sound Fixes")
        layout.addWidget(self.name_input)

        # Description
        layout.addWidget(QLabel("Beschreibung (optional):"))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Kurze Notiz zu dieser Mod-Zusammenstellung...")
        self.desc_input.setMaximumHeight(80)
        layout.addWidget(self.desc_input)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Speichern")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Fehler", "Bitte gib einen Namen für das Preset ein.")
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "description": self.desc_input.toPlainText().strip(),
        }
