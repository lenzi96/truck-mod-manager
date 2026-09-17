"""
Dialog for inspecting file conflicts between active mods.
Shows conflicting file paths, risk severity (Critical, Warning, Info),
precedence winners, and actionable impact explanations.
"""
from typing import List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QButtonGroup
)
from truck_mod_manager.core.models import ConflictFile, ConflictSeverity


class ConflictDialog(QDialog):
    def __init__(self, conflicts: List[ConflictFile], parent=None):
        super().__init__(parent)
        self.conflicts = conflicts
        self.filtered_conflicts = list(conflicts)
        self.current_severity_filter: Optional[str] = "all"  # "all", "critical", "warning", "info", "genuine"
        self.search_query: str = ""

        self.setWindowTitle("Mod-Konflikte & Kollisionsdiagnose")
        self.setMinimumSize(950, 620)
        self.resize(1050, 680)
        self._setup_ui()
        self._apply_filters()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Summary Cards Header
        crit_count = sum(1 for c in self.conflicts if c.severity == ConflictSeverity.CRITICAL)
        warn_count = sum(1 for c in self.conflicts if c.severity == ConflictSeverity.WARNING)
        info_count = sum(1 for c in self.conflicts if c.severity == ConflictSeverity.INFO)

        stat_layout = QHBoxLayout()
        stat_layout.setSpacing(10)

        # Card: Critical
        crit_card = QFrame()
        crit_card.setStyleSheet("background-color: #2a1215; border: 1px solid #7f1d1d; border-radius: 6px; padding: 6px;")
        c_layout = QVBoxLayout(crit_card)
        c_layout.setContentsMargins(8, 6, 8, 6)
        c_layout.setSpacing(2)
        c_title = QLabel(f"🔴 {crit_count} Kritische Konflikte")
        c_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #fca5a5;")
        c_desc = QLabel("Spieldaten, Wirtschaft, Fahrphysik, unverbundene Map-Sektoren")
        c_desc.setStyleSheet("color: #f87171; font-size: 11px;")
        c_layout.addWidget(c_title)
        c_layout.addWidget(c_desc)
        stat_layout.addWidget(crit_card, stretch=1)

        # Card: Warning
        warn_card = QFrame()
        warn_card.setStyleSheet("background-color: #2b1d0c; border: 1px solid #78350f; border-radius: 6px; padding: 6px;")
        w_layout = QVBoxLayout(warn_card)
        w_layout.setContentsMargins(8, 6, 8, 6)
        w_layout.setSpacing(2)
        w_title = QLabel(f"🟡 {warn_count} Warnungen")
        w_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #fef08a;")
        w_desc = QLabel("LKW-Tuning, Motoren, Sounds, Benutzeroberfläche / HUD")
        w_desc.setStyleSheet("color: #fde047; font-size: 11px;")
        w_layout.addWidget(w_title)
        w_layout.addWidget(w_desc)
        stat_layout.addWidget(warn_card, stretch=1)

        # Card: Info / Benign
        info_card = QFrame()
        info_card.setStyleSheet("background-color: #0c2136; border: 1px solid #0369a1; border-radius: 6px; padding: 6px;")
        i_layout = QVBoxLayout(info_card)
        i_layout.setContentsMargins(8, 6, 8, 6)
        i_layout.setSpacing(2)
        i_title = QLabel(f"🔵 {info_count} Unkritisch / Assets")
        i_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #7dd3fc;")
        i_desc = QLabel("Texturen, 3D-Modelle, Road Connections & Mod-Pakete")
        i_desc.setStyleSheet("color: #38bdf8; font-size: 11px;")
        i_layout.addWidget(i_title)
        i_layout.addWidget(i_desc)
        stat_layout.addWidget(info_card, stretch=1)

        layout.addLayout(stat_layout)

        # 2. Filter Bar & Search
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.btn_all = QPushButton(f"Alle ({len(self.conflicts)})")
        self.btn_all.setCheckable(True)
        self.btn_all.setChecked(True)
        self.btn_all.clicked.connect(lambda: self._set_severity_filter("all"))
        self.btn_group.addButton(self.btn_all)
        filter_bar.addWidget(self.btn_all)

        self.btn_crit = QPushButton(f"🔴 Nur Kritische ({crit_count})")
        self.btn_crit.setCheckable(True)
        self.btn_crit.clicked.connect(lambda: self._set_severity_filter("critical"))
        self.btn_group.addButton(self.btn_crit)
        filter_bar.addWidget(self.btn_crit)

        self.btn_warn = QPushButton(f"🟡 Warnungen ({warn_count})")
        self.btn_warn.setCheckable(True)
        self.btn_warn.clicked.connect(lambda: self._set_severity_filter("warning"))
        self.btn_group.addButton(self.btn_warn)
        filter_bar.addWidget(self.btn_warn)

        self.btn_info = QPushButton(f"🔵 Unkritisch ({info_count})")
        self.btn_info.setCheckable(True)
        self.btn_info.clicked.connect(lambda: self._set_severity_filter("info"))
        self.btn_group.addButton(self.btn_info)
        filter_bar.addWidget(self.btn_info)

        self.btn_genuine = QPushButton("🧩 Ohne Road Connections")
        self.btn_genuine.setCheckable(True)
        self.btn_genuine.setToolTip("Blendet beabsichtigte Kartenverbindungen und interne Paket-Overrides aus.")
        self.btn_genuine.clicked.connect(lambda: self._set_severity_filter("genuine"))
        self.btn_group.addButton(self.btn_genuine)
        filter_bar.addWidget(self.btn_genuine)

        filter_bar.addSpacing(10)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtern nach Pfad, Mod-Name oder Kategorie...")
        self.search_input.textChanged.connect(self._on_search_changed)
        filter_bar.addWidget(self.search_input, stretch=1)

        layout.addLayout(filter_bar)

        # 3. Conflict Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Schweregrad",
            "Kategorie",
            "Dateipfad",
            "Gewinner (Priorität oben)",
            "Überschriebene Mods",
            "Mögliche Auswirkung & Empfehlung"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().resizeSection(2, 260)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(32)
        layout.addWidget(self.table)

        # 4. Footer
        footer = QHBoxLayout()
        self.count_label = QLabel(f"Gesamt: {len(self.conflicts)} Konflikte")
        self.count_label.setStyleSheet("color: #94a3b8; font-weight: 500;")
        footer.addWidget(self.count_label)
        footer.addStretch()

        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    def _set_severity_filter(self, filter_name: str):
        self.current_severity_filter = filter_name
        self._apply_filters()

    def _on_search_changed(self, text: str):
        self.search_query = text.strip().lower()
        self._apply_filters()

    def _apply_filters(self):
        filtered = []
        for c in self.conflicts:
            # Severity / mode filter
            if self.current_severity_filter == "critical" and c.severity != ConflictSeverity.CRITICAL:
                continue
            if self.current_severity_filter == "warning" and c.severity != ConflictSeverity.WARNING:
                continue
            if self.current_severity_filter == "info" and c.severity != ConflictSeverity.INFO:
                continue
            if self.current_severity_filter == "genuine" and c.is_intended_override:
                continue

            # Search query filter
            if self.search_query:
                q = self.search_query
                match = (
                    q in c.relative_path.lower()
                    or q in (c.winning_mod or "").lower()
                    or q in c.category_label.lower()
                    or q in c.impact.lower()
                    or any(q in m.lower() for m in c.mod_files)
                )
                if not match:
                    continue

            filtered.append(c)

        self.filtered_conflicts = filtered
        self._populate()

    def _populate(self):
        self.table.setRowCount(len(self.filtered_conflicts))
        for row, conf in enumerate(self.filtered_conflicts):
            # 0. Severity Item
            if conf.severity == ConflictSeverity.CRITICAL:
                sev_item = QTableWidgetItem("🔴 Kritisch")
                sev_item.setForeground(QColor("#f87171"))
            elif conf.severity == ConflictSeverity.WARNING:
                sev_item = QTableWidgetItem("🟡 Warnung")
                sev_item.setForeground(QColor("#facc15"))
            else:
                if conf.is_intended_override:
                    sev_item = QTableWidgetItem("🔵 Gewollt")
                else:
                    sev_item = QTableWidgetItem("🔵 Info")
                sev_item.setForeground(QColor("#38bdf8"))

            bold_font = QFont()
            bold_font.setBold(True)
            sev_item.setFont(bold_font)
            self.table.setItem(row, 0, sev_item)

            # 1. Category Item
            cat_item = QTableWidgetItem(conf.category_label)
            self.table.setItem(row, 1, cat_item)

            # 2. Relative Path
            path_item = QTableWidgetItem(conf.relative_path)
            path_item.setToolTip(conf.relative_path)
            self.table.setItem(row, 2, path_item)

            # 3. Winning Mod
            winner_item = QTableWidgetItem(f"✅ {conf.winning_mod or 'Unbekannt'}")
            winner_item.setForeground(QColor("#4ade80"))
            self.table.setItem(row, 3, winner_item)

            # 4. Overridden Mods
            overridden = [m for m in conf.mod_files if m != conf.winning_mod]
            over_item = QTableWidgetItem(", ".join(overridden))
            over_item.setForeground(QColor("#fbbf24"))
            self.table.setItem(row, 4, over_item)

            # 5. Impact & Recommendation
            impact_item = QTableWidgetItem(conf.impact)
            impact_item.setToolTip(conf.impact)
            if conf.severity == ConflictSeverity.CRITICAL:
                impact_item.setForeground(QColor("#fca5a5"))
            elif conf.severity == ConflictSeverity.WARNING:
                impact_item.setForeground(QColor("#fef08a"))
            else:
                impact_item.setForeground(QColor("#94a3b8"))
            self.table.setItem(row, 5, impact_item)

        self.count_label.setText(
            f"Zeige {len(self.filtered_conflicts)} von {len(self.conflicts)} Konflikten"
        )

