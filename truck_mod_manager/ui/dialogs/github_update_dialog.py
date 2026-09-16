"""
GitHub Program Update Dialog for Truck Mod Manager (ETS2 & ATS).
Adapted from Cachy Security Suite and AMD Control Center.
Provides automated version checking against GitHub, changelog display, and 1-click self-update.
"""

import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QProcess
from PyQt6.QtGui import QColor, QFont, QIcon, QTextCursor, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from truck_mod_manager.core.github_updater import (
    GitHubUpdateCheckerWorker,
    GitHubUpdateExecWorker,
    GitHubUpdateInfo,
    UpdateStep,
    get_github_repo,
    get_github_token,
    get_repo_dir,
    set_github_repo,
    set_github_token,
)


RESOURCE_DIR = Path(__file__).resolve().parent.parent.parent / "resources"


class GitHubUpdateDialog(QDialog):
    """Modern modal dialog for updating Truck Mod Manager from GitHub."""

    app_restarted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Software-Aktualisierung – Truck Mod Manager")
        self.resize(780, 580)
        self.setMinimumSize(700, 500)

        icon_path = RESOURCE_DIR / "icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.checker_worker: Optional[GitHubUpdateCheckerWorker] = None
        self.exec_worker: Optional[GitHubUpdateExecWorker] = None
        self.latest_info: Optional[GitHubUpdateInfo] = None
        self.app_was_updated: bool = False

        self.init_ui()
        self.start_check()

    def init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f1f5f9;
            }
            QLabel {
                color: #f1f5f9;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QPushButton#primaryBlue {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1d4ed8);
                color: #ffffff;
                border: 1px solid #3b82f6;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QPushButton#primaryBlue:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
                border: 1px solid #60a5fa;
            }
            QPushButton#primaryBlue:disabled {
                background-color: #1e293b;
                color: #64748b;
                border-color: #334155;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(22, 20, 22, 20)
        root_layout.setSpacing(14)

        # ----------------------------------------------------------------------
        # Top Header Banner
        # ----------------------------------------------------------------------
        header_layout = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(2)

        title_lbl = QLabel("TRUCK MOD MANAGER")
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 900; color: #38bdf8; letter-spacing: 1.5px;")
        sub_lbl = QLabel("Software- & Release-Aktualisierung (GitHub)")
        sub_lbl.setStyleSheet("font-size: 17px; font-weight: 800; color: #f8fafc;")
        desc_lbl = QLabel("Prüfe auf neue Versionen, installiere Updates direkt per 1-Klick und verfolge Changelogs.")
        desc_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
        desc_lbl.setWordWrap(True)

        header_text.addWidget(title_lbl)
        header_text.addWidget(sub_lbl)
        header_text.addWidget(desc_lbl)
        header_layout.addLayout(header_text, 1)

        # Header Action Buttons
        self.btn_refresh = QPushButton("↻  Auf Updates prüfen")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.start_check)
        header_layout.addWidget(self.btn_refresh)

        self.btn_update_now = QPushButton("⚡  JETZT AKTUALISIEREN")
        self.btn_update_now.setObjectName("primaryBlue")
        self.btn_update_now.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update_now.setEnabled(False)
        self.btn_update_now.clicked.connect(self.run_github_update)
        header_layout.addWidget(self.btn_update_now)

        root_layout.addLayout(header_layout)

        # Progress bar (indeterminate while checking or updating)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #0f172a;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
                border-radius: 1px;
            }
        """)
        root_layout.addWidget(self.progress_bar)

        # ----------------------------------------------------------------------
        # Tab Navigation
        # ----------------------------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 8px;
                background-color: #0f172a;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 9px 20px;
                border: 1px solid #334155;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: 700;
                font-size: 12px;
                letter-spacing: 0.5px;
            }
            QTabBar::tab:selected {
                background-color: #2563eb;
                color: #ffffff;
                border-color: #3b82f6;
            }
            QTabBar::tab:hover:!selected {
                background-color: #334155;
                color: #f8fafc;
            }
        """)

        # Tab 1: Status & Versions
        self.tab_status = QWidget()
        self._init_status_tab()
        self.tabs.addTab(self.tab_status, "STATUS && VERSIONEN")

        # Tab 2: Changelog / Release Notes
        self.tab_changelog = QWidget()
        self._init_changelog_tab()
        self.tabs.addTab(self.tab_changelog, "RELEASE-NOTIZEN && CHANGELOG")

        # Tab 3: Terminal Output
        self.tab_log = QWidget()
        self._init_log_tab()
        self.tabs.addTab(self.tab_log, "TERMINAL-PROTOKOLL")

        root_layout.addWidget(self.tabs, 1)

        # ----------------------------------------------------------------------
        # Bottom Bar
        # ----------------------------------------------------------------------
        bottom_layout = QHBoxLayout()
        self.lbl_status = QLabel("Bereit.")
        self.lbl_status.setStyleSheet("font-size: 12px; color: #94a3b8;")
        self.lbl_status.setWordWrap(True)
        bottom_layout.addWidget(self.lbl_status, 1)

        self.btn_restart = QPushButton("🔄 Anwendung neu starten")
        self.btn_restart.setObjectName("primaryBlue")
        self.btn_restart.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restart.setVisible(False)
        self.btn_restart.clicked.connect(self.restart_application)
        bottom_layout.addWidget(self.btn_restart)

        self.btn_close = QPushButton("Schließen")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close)
        bottom_layout.addWidget(self.btn_close)

        root_layout.addLayout(bottom_layout)

    def _init_status_tab(self):
        layout = QVBoxLayout(self.tab_status)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Card 1: Version Comparison
        card_ver = QFrame()
        card_ver.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        cv_layout = QHBoxLayout(card_ver)
        cv_layout.setSpacing(16)

        icon_lbl = QLabel("🚚")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setFixedSize(46, 46)
        icon_lbl.setStyleSheet("""
            background: rgba(37, 99, 235, 0.2);
            border: 1px solid #3b82f6;
            border-radius: 23px;
            font-size: 22px;
        """)
        cv_layout.addWidget(icon_lbl)

        ver_text = QVBoxLayout()
        ver_text.setSpacing(4)
        t_lbl = QLabel("Truck Mod Manager für Linux (ETS2 & ATS)")
        t_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff;")

        self.lbl_versions = QLabel("Installiert: v...  │  Auf GitHub: v...")
        self.lbl_versions.setStyleSheet("font-size: 12px; color: #94a3b8;")
        ver_text.addWidget(t_lbl)
        ver_text.addWidget(self.lbl_versions)
        cv_layout.addLayout(ver_text, 1)

        self.badge_status = QLabel("Wird geprüft...")
        self.badge_status.setStyleSheet("""
            background-color: #0f172a;
            color: #94a3b8;
            padding: 6px 14px;
            border-radius: 6px;
            font-weight: 800;
            font-size: 11px;
            border: 1px solid #334155;
        """)
        cv_layout.addWidget(self.badge_status)
        layout.addWidget(card_ver)

        # Card 2: GitHub Repository Config
        card_repo = QFrame()
        card_repo.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        cr_layout = QVBoxLayout(card_repo)
        cr_layout.setSpacing(10)

        lbl_head_repo = QLabel("GITHUB QUELL-REPOSITORY")
        lbl_head_repo.setStyleSheet("font-size: 11px; font-weight: 800; color: #38bdf8; letter-spacing: 1.5px;")
        cr_layout.addWidget(lbl_head_repo)

        row_repo = QHBoxLayout()
        self.lbl_repo_name = QLabel(f"https://github.com/{get_github_repo()}")
        self.lbl_repo_name.setStyleSheet("font-family: monospace; font-size: 12px; color: #60a5fa; font-weight: 600;")
        row_repo.addWidget(self.lbl_repo_name, 1)

        btn_edit_repo = QPushButton("Repository ändern")
        btn_edit_repo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit_repo.clicked.connect(self.edit_github_repo)
        row_repo.addWidget(btn_edit_repo)

        btn_token = QPushButton("GitHub Token (PAT)")
        btn_token.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_token.clicked.connect(self.edit_github_token)
        row_repo.addWidget(btn_token)

        cr_layout.addLayout(row_repo)

        info_lbl = QLabel("Standardmäßig wird das offizielle Release-Repository von GitHub abgefragt. Bei privaten Repositories oder API-Rate-Limits kann ein Personal Access Token (PAT) hinterlegt werden.")
        info_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; line-height: 1.4;")
        info_lbl.setWordWrap(True)
        cr_layout.addWidget(info_lbl)

        layout.addWidget(card_repo)
        layout.addStretch()

    def _init_changelog_tab(self):
        layout = QVBoxLayout(self.tab_changelog)
        layout.setContentsMargins(14, 14, 14, 14)

        self.txt_changelog = QTextBrowser()
        self.txt_changelog.setOpenExternalLinks(True)
        self.txt_changelog.setStyleSheet("""
            QTextBrowser {
                background-color: #0b0f19;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #e2e8f0;
                padding: 14px;
                font-size: 12px;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.txt_changelog)

    def _init_log_tab(self):
        layout = QVBoxLayout(self.tab_log)
        layout.setContentsMargins(14, 14, 14, 14)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("""
            QTextEdit {
                background-color: #07090c;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #22c55e;
                font-family: monospace;
                font-size: 11px;
                padding: 12px;
            }
        """)
        layout.addWidget(self.txt_log)

    def start_check(self):
        self.btn_refresh.setEnabled(False)
        self.btn_update_now.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.badge_status.setText("● Prüfe GitHub...")
        self.badge_status.setStyleSheet("""
            background-color: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            padding: 6px 14px;
            border-radius: 6px;
            font-weight: 800;
            font-size: 11px;
            border: 1px solid #38bdf8;
        """)
        self.lbl_status.setText("Frage GitHub Releases API ab...")

        self.checker_worker = GitHubUpdateCheckerWorker()
        self.checker_worker.finished.connect(self._on_check_finished)
        self.checker_worker.start()

    def _on_check_finished(self, info: GitHubUpdateInfo):
        self.latest_info = info
        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)

        self.lbl_versions.setText(
            f"Installiert: v{info.installed_version}  │  Auf GitHub: v{info.remote_version}"
        )
        self.lbl_repo_name.setText(f"https://github.com/{info.github_repo}")

        if info.has_update:
            self.badge_status.setText(f"⬆ Update verfügbar: v{info.remote_version}")
            self.badge_status.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1d4ed8);
                color: #ffffff;
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: 800;
                font-size: 11px;
            """)
            self.btn_update_now.setEnabled(True)
            self.btn_update_now.setText("⚡  JETZT AKTUALISIEREN")
            self.lbl_status.setText(f"Eine neue Version (v{info.remote_version}) ist auf GitHub verfügbar!")
        else:
            self.badge_status.setText("✓ Auf neuestem Stand")
            self.badge_status.setStyleSheet("""
                background-color: rgba(34, 197, 94, 0.12);
                color: #22c55e;
                border: 1px solid #22c55e;
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: 800;
                font-size: 11px;
            """)
            self.btn_update_now.setEnabled(True)
            self.btn_update_now.setText("🔄  Neu installieren")
            self.lbl_status.setText(f"Truck Mod Manager ist auf dem neuesten Stand (v{info.installed_version}).")

        # Update changelog tab
        if info.release_notes:
            self.txt_changelog.setMarkdown(f"## Version v{info.remote_version}\n\n{info.release_notes}")
        else:
            self.txt_changelog.setMarkdown(
                f"### Truck Mod Manager v{info.installed_version}\n\n"
                "- Vollständige Mod-Verwaltung für Euro Truck Simulator 2 & American Truck Simulator\n"
                "- Zero-Pollution Staging-Architektur via Symlinks\n"
                "- TruckyMods.io Direkt-Browser, Suche, Filter & Cloudflare R2 Direktdownloader\n"
                "- ProMods Toolkit mit automatischer Archivprüfung & offizieller Ladereihenfolge\n"
                "- Integrierter game.log.txt Crash-Analyzer & Mod-Konflikt-Detektor\n"
                "- Steam Workshop Synchronisation & Telemetrie-Plugin-Manager"
            )

        if info.check_error:
            self.txt_log.append(f"[Hinweis] {info.check_error}\n")

    def edit_github_repo(self):
        curr = get_github_repo()
        repo, ok = QInputDialog.getText(
            self,
            "GitHub-Repository verknüpfen",
            "Gib dein GitHub-Repository im Format 'Benutzername/Repository' ein:\n"
            "(z. B. lenzi96/truck-mod-manager):",
            text=curr,
        )
        if ok and repo.strip():
            set_github_repo(repo.strip())
            self.lbl_repo_name.setText(f"https://github.com/{get_github_repo()}")
            QMessageBox.information(
                self,
                "GitHub verknüpft",
                f"Repository erfolgreich verknüpft:\nhttps://github.com/{get_github_repo()}",
            )
            self.start_check()

    def edit_github_token(self):
        curr_token = get_github_token() or ""
        masked = (curr_token[:8] + "..." + curr_token[-4:]) if len(curr_token) > 12 else curr_token
        tok, ok = QInputDialog.getText(
            self,
            "GitHub Access Token (PAT)",
            "Gib dein GitHub Personal Access Token ein\n"
            "(Erforderlich bei privaten Repositories oder API-Rate-Limits):\n"
            f"Aktuell hinterlegt: {masked if masked else 'Keins'}",
            text=curr_token,
        )
        if ok:
            set_github_token(tok.strip())
            QMessageBox.information(self, "Token gespeichert", "Das GitHub Token wurde aktualisiert.")
            self.start_check()

    def run_github_update(self):
        """Executes git pull or source update + install.sh."""
        repo_dir = get_repo_dir()
        installer = repo_dir / "install.sh"
        is_git = (repo_dir / ".git").is_dir() and shutil.which("git")

        steps: List[UpdateStep] = []

        if is_git and installer.exists():
            # In developer git repo: pull and reinstall
            steps.append(
                UpdateStep(
                    name="GitHub Quellcode synchronisieren (git pull --rebase)",
                    command=["git", "-C", str(repo_dir), "pull", "--rebase"],
                    description="Holt die neuesten Code-Änderungen von GitHub",
                )
            )
            inst_cmd = ["bash", str(installer)]
            if os.geteuid() != 0:
                inst_cmd.append("--user")
            steps.append(
                UpdateStep(
                    name="Truck Mod Manager neu installieren",
                    command=inst_cmd,
                    description="Kopiert Core-Dateien, aktualisiert Starter und Desktop-Caches",
                )
            )
        else:
            # Standalone installation: download release tarball and install
            ver = self.latest_info.remote_version if self.latest_info else ""
            asset_url = self.latest_info.asset_api_url if self.latest_info else ""
            tarball_url = self.latest_info.tarball_url if self.latest_info else ""
            updater_script = Path(__file__).resolve().parent.parent.parent / "core" / "github_updater.py"
            tok = get_github_token()
            cmd = [
                sys.executable,
                str(updater_script),
                "--download-and-install",
            ]
            if ver and ver != "Unbekannt":
                cmd.extend(["--version", ver])
            if asset_url:
                cmd.extend(["--asset-url", asset_url])
            if tarball_url:
                cmd.extend(["--tarball-url", tarball_url])
            if tok:
                cmd.extend(["--token", tok])
            steps.append(
                UpdateStep(
                    name=f"Truck Mod Manager v{ver if ver and ver != 'Unbekannt' else 'neueste Version'} herunterladen & installieren",
                    command=cmd,
                    description="Lädt das offizielle GitHub Release-Archiv herunter und installiert die neue Version",
                )
            )

        # Switch to terminal tab
        self.tabs.setCurrentIndex(2)
        self.btn_refresh.setEnabled(False)
        self.btn_update_now.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText("Aktualisiere Programm über GitHub...")

        self.exec_worker = GitHubUpdateExecWorker(steps)
        self.exec_worker.output_line.connect(self._on_log_line)
        self.exec_worker.completed.connect(self._on_update_completed)
        self.exec_worker.start()

    def _on_log_line(self, line: str):
        cursor = self.txt_log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(line + "\n")
        self.txt_log.setTextCursor(cursor)
        self.txt_log.ensureCursorVisible()

    def _on_update_completed(self, success: bool, msg: str):
        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)

        if success:
            self.app_was_updated = True
            self.lbl_status.setText("Aktualisierung erfolgreich!")
            self.btn_restart.setVisible(True)
            QMessageBox.information(
                self,
                "Update abgeschlossen",
                "Truck Mod Manager wurde erfolgreich über GitHub aktualisiert!\n\n"
                "Klicke auf 'Anwendung neu starten', um die aktualisierte Version zu laden.",
            )
        else:
            self.lbl_status.setText(f"Fehler beim Update: {msg}")
            self.btn_update_now.setEnabled(True)
            QMessageBox.warning(self, "Update fehlgeschlagen", f"Aktualisierung konnte nicht abgeschlossen werden:\n{msg}")

    def restart_application(self):
        """Restarts the running application."""
        self.close()
        python = sys.executable
        try:
            QProcess.startDetached(python, sys.argv)
            QApplication.quit()
        except Exception:
            os.execl(python, python, *sys.argv)
