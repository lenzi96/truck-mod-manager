"""
Game Log & Crash Analyzer View for Truck Mod Manager.
Parses game.log.txt, highlights errors and warnings, and explains SCS crash reasons.
"""
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QComboBox, QMessageBox, QApplication
)

from truck_mod_manager.core.log_analyzer import LogAnalyzer
from truck_mod_manager.core.models import LogIssue, TruckGame


class LogAnalyzerView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.game: Optional[TruckGame] = None
        self.issues: List[LogIssue] = []
        self.summary: dict = {}
        self.filtered_issues: List[LogIssue] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Diagnostic Banner Card
        self.banner_card = QFrame()
        self.banner_card.setObjectName("toolbarCard")
        banner_layout = QHBoxLayout(self.banner_card)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        banner_layout.setSpacing(16)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        self.title_lbl = QLabel("game.log.txt Analyse & Fehler-Diagnose")
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc;")
        info_col.addWidget(self.title_lbl)

        self.path_lbl = QLabel("Pfad: Nicht geladen")
        self.path_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        info_col.addWidget(self.path_lbl)
        banner_layout.addLayout(info_col, stretch=1)

        # Status Chips
        self.err_chip = QLabel("0 Fehler")
        self.err_chip.setStyleSheet("background-color: #3b1219; color: #fca5a5; border: 1px solid #7f1d1d; padding: 5px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;")
        banner_layout.addWidget(self.err_chip)

        self.warn_chip = QLabel("0 Warnungen")
        self.warn_chip.setStyleSheet("background-color: #3d1c06; color: #fde047; border: 1px solid #d97706; padding: 5px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;")
        banner_layout.addWidget(self.warn_chip)

        self.crash_chip = QLabel("Kein Absturz")
        self.crash_chip.setStyleSheet("background-color: #063726; color: #6ee7b7; border: 1px solid #059669; padding: 5px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;")
        banner_layout.addWidget(self.crash_chip)

        refresh_btn = QPushButton("🔄 Neu analysieren")
        refresh_btn.clicked.connect(self.refresh)
        banner_layout.addWidget(refresh_btn)

        layout.addWidget(self.banner_card)

        # Filter & Search Controls
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Log durchsuchen (z. B. scania, sound, texture, unit)...")
        self.search_input.textChanged.connect(self._apply_filter)
        ctrl_bar.addWidget(self.search_input, stretch=2)

        self.level_filter = QComboBox()
        self.level_filter.addItem("Alle Meldungen (Fehler & Warnungen)", "all")
        self.level_filter.addItem("Nur <ERROR>", "ERROR")
        self.level_filter.addItem("Nur <WARNING>", "WARNING")
        self.level_filter.currentIndexChanged.connect(self._apply_filter)
        ctrl_bar.addWidget(self.level_filter)

        copy_btn = QPushButton("📋 Log kopieren")
        copy_btn.setToolTip("Kopiert die letzten 150 Zeilen bereinigt in die Zwischenablage (für Forum oder Discord)")
        copy_btn.clicked.connect(self._copy_log_snippet)
        ctrl_bar.addWidget(copy_btn)

        layout.addLayout(ctrl_bar)

        # Issues Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Zeile",
            "Level",
            "Subsystem",
            "Fehlermeldung",
            "Empfohlene Lösung / Ursache"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def set_game(self, game: TruckGame):
        self.game = game
        self.refresh()

    def refresh(self):
        if not self.game or not self.game.log_path:
            self.path_lbl.setText("Keine Logdatei gefunden (Spiel noch nicht gestartet?).")
            return

        log_path = self.game.log_path
        self.path_lbl.setText(f"Pfad: {log_path}")

        self.issues, self.summary = LogAnalyzer.analyze_file(log_path)

        # Update chips
        err_count = self.summary.get("error_count", 0)
        warn_count = self.summary.get("warning_count", 0)
        crashed = self.summary.get("crashed", False)
        game_ver = self.summary.get("game_version", "Unbekannt")

        self.err_chip.setText(f"{err_count} Fehler")
        self.warn_chip.setText(f"{warn_count} Warnungen")

        if crashed:
            self.crash_chip.setText("💥 Absturz (Crash)!")
            self.crash_chip.setStyleSheet("background-color: #3b1219; color: #fca5a5; border: 1px solid #7f1d1d; padding: 5px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;")
        else:
            self.crash_chip.setText("✔ Normal beendet")
            self.crash_chip.setStyleSheet("background-color: #063726; color: #6ee7b7; border: 1px solid #059669; padding: 5px 12px; border-radius: 6px; font-weight: bold; font-size: 12px;")

        self.title_lbl.setText(f"game.log.txt Diagnose (Spielversion: {game_ver})")
        self._apply_filter()

    def _apply_filter(self):
        query = self.search_input.text().strip().lower()
        level_sel = self.level_filter.currentData()

        self.filtered_issues = []
        for issue in self.issues:
            if level_sel != "all" and issue.level != level_sel:
                continue

            if query:
                match = (
                    query in issue.message.lower()
                    or query in issue.subsystem.lower()
                    or query in issue.suggestion.lower()
                )
                if not match:
                    continue

            self.filtered_issues.append(issue)

        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(len(self.filtered_issues))
        for row, issue in enumerate(self.filtered_issues):
            line_item = QTableWidgetItem(str(issue.line_number))
            line_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, line_item)

            level_item = QTableWidgetItem(issue.level)
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if issue.level == "ERROR":
                level_item.setForeground(Qt.GlobalColor.red)
            else:
                level_item.setForeground(Qt.GlobalColor.yellow)
            self.table.setItem(row, 1, level_item)

            sub_item = QTableWidgetItem(issue.subsystem)
            sub_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, sub_item)

            msg_item = QTableWidgetItem(issue.message)
            self.table.setItem(row, 3, msg_item)

            sug_item = QTableWidgetItem(issue.suggestion)
            if issue.suggestion:
                sug_item.setForeground(Qt.GlobalColor.cyan)
            self.table.setItem(row, 4, sug_item)

    def _copy_log_snippet(self):
        if not self.game or not self.game.log_path:
            return
        snippet = LogAnalyzer.get_clean_log_snippet(self.game.log_path, max_lines=150)
        clipboard = QApplication.clipboard()
        clipboard.setText(snippet)
        QMessageBox.information(
            self,
            "In die Zwischenablage kopiert",
            "Die relevanten letzten Zeilen der game.log.txt wurden in die Zwischenablage kopiert."
        )
