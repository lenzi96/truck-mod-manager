"""
Dialog for inspecting file conflicts between active mods.
Shows conflicting file paths, which mod wins precedence, and which mods are overwritten.
"""
from typing import List
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QFrame
)
from truck_mod_manager.core.models import ConflictFile


class ConflictDialog(QDialog):
    def __init__(self, conflicts: List[ConflictFile], parent=None):
        super().__init__(parent)
        self.conflicts = conflicts
        self.filtered_conflicts = list(conflicts)
        self.setWindowTitle("Dateikonflikte (Kollisionen)")
        self.setMinimumSize(850, 550)
        self.resize(900, 600)
        self._setup_ui()
        self._populate()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Info
        header = QFrame()
        header.setObjectName("cardFrame")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("⚠️ Erkannte Dateikonflikte zwischen aktiven Mods")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f59e0b;")
        h_layout.addWidget(title)

        desc = QLabel(
            "Wenn zwei oder mehr Mods dieselbe Datei (z. B. Definition oder Textur) enthalten, "
            "überschreibt die Mod mit der <b>höheren Priorität (weiter oben in der Ladereihenfolge)</b> die anderen."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Konflikte filtern (z. B. def/vehicle, sound, map)...")
        self.search_input.textChanged.connect(self._filter_conflicts)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Conflict Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "Betroffener Dateipfad",
            "Gewinner (Aktive Mod)",
            "Überschriebene Mods"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Footer
        footer = QHBoxLayout()
        self.count_label = QLabel(f"Gesamt: {len(self.conflicts)} Konflikte")
        self.count_label.setStyleSheet("color: #94a3b8; font-weight: 500;")
        footer.addWidget(self.count_label)
        footer.addStretch()

        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    def _populate(self):
        self.table.setRowCount(len(self.filtered_conflicts))
        for row, conf in enumerate(self.filtered_conflicts):
            # Path Item
            path_item = QTableWidgetItem(conf.relative_path)
            self.table.setItem(row, 0, path_item)

            # Winner Item
            winner_item = QTableWidgetItem(f"✅ {conf.winning_mod}")
            winner_item.setForeground(Qt.GlobalColor.green)
            self.table.setItem(row, 1, winner_item)

            # Overridden Mods
            overridden = [m for m in conf.mod_files if m != conf.winning_mod]
            over_item = QTableWidgetItem(", ".join(overridden))
            over_item.setForeground(Qt.GlobalColor.darkYellow)
            self.table.setItem(row, 2, over_item)

        self.count_label.setText(f"Gesamt: {len(self.filtered_conflicts)} von {len(self.conflicts)} Konflikten angezeigt")

    def _filter_conflicts(self, query: str):
        q = query.strip().lower()
        if not q:
            self.filtered_conflicts = list(self.conflicts)
        else:
            self.filtered_conflicts = [
                c for c in self.conflicts
                if q in c.relative_path.lower()
                or (c.winning_mod and q in c.winning_mod.lower())
                or any(q in m.lower() for m in c.mod_files)
            ]
        self._populate()
