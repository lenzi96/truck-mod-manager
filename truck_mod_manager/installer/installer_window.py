"""
Graphical Installer Wizard for Truck Mod Manager.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QRadioButton, QCheckBox,
    QProgressBar, QPlainTextEdit, QMessageBox, QButtonGroup, QApplication
)

from truck_mod_manager import __version__
from truck_mod_manager.installer.installer_backend import (
    APP_NAME, BIN_NAME, InstallerDetector, InstallWorker, UninstallWorker
)
from truck_mod_manager.ui.style import DARK_THEME_QSS


class InstallerWindow(QMainWindow):
    """Modern dark graphical installer wizard for Truck Mod Manager."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Installation: {APP_NAME} v{__version__}")
        self.resize(840, 560)
        self.setMinimumSize(760, 500)
        self.setStyleSheet(DARK_THEME_QSS)

        src_dir = InstallerDetector.get_source_dir()
        icon_path = src_dir / "truck_mod_manager" / "resources" / "icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.install_worker: Optional[InstallWorker] = None
        self.uninstall_worker: Optional[UninstallWorker] = None

        self._init_ui()
        self._check_prerequisites()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar (Steps)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("cardFrame")
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet("background-color: #1e293b; border-right: 1px solid #334155; border-radius: 0px;")

        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(20, 24, 20, 20)
        side_layout.setSpacing(16)

        # Brand header
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        logo_lbl = QLabel()
        src_dir = InstallerDetector.get_source_dir()
        icon_path = src_dir / "truck_mod_manager" / "resources" / "icon.svg"
        if icon_path.exists():
            pix = QPixmap(str(icon_path))
            logo_lbl.setPixmap(pix.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        brand_row.addWidget(logo_lbl)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(1)
        lbl_name = QLabel("Truck Mod")
        lbl_name.setStyleSheet("font-size: 15px; font-weight: 800; color: #f8fafc;")
        lbl_sub = QLabel("INSTALLER")
        lbl_sub.setStyleSheet("font-size: 10px; font-weight: 700; color: #38bdf8; letter-spacing: 1px;")
        brand_col.addWidget(lbl_name)
        brand_col.addWidget(lbl_sub)
        brand_row.addLayout(brand_col)
        side_layout.addLayout(brand_row)

        side_layout.addSpacing(15)

        # Step Labels
        self.step_labels = []
        steps = [
            ("1", "Systemprüfung"),
            ("2", "Installationsmodus"),
            ("3", "Optionen"),
            ("4", "Installation"),
            ("5", "Fertigstellung"),
        ]

        for num, title in steps:
            row = QHBoxLayout()
            row.setSpacing(10)

            num_lbl = QLabel(num)
            num_lbl.setFixedSize(24, 24)
            num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_lbl.setStyleSheet("background-color: #334155; color: #cbd5e1; border-radius: 12px; font-weight: bold; font-size: 11px;")

            text_lbl = QLabel(title)
            text_lbl.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: 500;")

            row.addWidget(num_lbl)
            row.addWidget(text_lbl)
            row.addStretch()
            side_layout.addLayout(row)
            self.step_labels.append((num_lbl, text_lbl))

        side_layout.addStretch()

        version_lbl = QLabel(f"Version {__version__}")
        version_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        side_layout.addWidget(version_lbl)

        root_layout.addWidget(self.sidebar)

        # 2. Right Content Area (QStackedWidget)
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(28, 28, 28, 24)
        content_layout.setSpacing(16)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, stretch=1)

        # Step Pages
        self.page_check = self._create_page_check()
        self.page_mode = self._create_page_mode()
        self.page_options = self._create_page_options()
        self.page_install = self._create_page_install()
        self.page_finish = self._create_page_finish()

        self.stack.addWidget(self.page_check)    # 0
        self.stack.addWidget(self.page_mode)     # 1
        self.stack.addWidget(self.page_options)  # 2
        self.stack.addWidget(self.page_install)  # 3
        self.stack.addWidget(self.page_finish)   # 4

        # Navigation Bar
        self.nav_bar = QHBoxLayout()
        self.nav_bar.setSpacing(10)

        self.btn_cancel = QPushButton("Abbrechen")
        self.btn_cancel.clicked.connect(self.close)
        self.nav_bar.addWidget(self.btn_cancel)

        self.nav_bar.addStretch()

        self.btn_back = QPushButton("◄ Zurück")
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setEnabled(False)
        self.nav_bar.addWidget(self.btn_back)

        self.btn_next = QPushButton("Weiter ►")
        self.btn_next.setObjectName("primaryBtn")
        self.btn_next.clicked.connect(self._go_next)
        self.nav_bar.addWidget(self.btn_next)

        content_layout.addLayout(self.nav_bar)
        root_layout.addWidget(content_frame, stretch=1)

        self._update_step_visuals(0)

    def _create_page_check(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("Willkommen bei der Installation des Truck Mod Managers")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")
        layout.addWidget(title)

        desc = QLabel(
            "Dieser Assistent installiert den Truck Mod Manager für Euro Truck Simulator 2 & "
            "American Truck Simulator auf deinem Linux-System."
        )
        desc.setStyleSheet("color: #cbd5e1; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Status box
        status_box = QFrame()
        status_box.setObjectName("cardFrame")
        box_layout = QVBoxLayout(status_box)
        box_layout.setContentsMargins(14, 12, 14, 12)
        box_layout.setSpacing(10)

        lbl_check_title = QLabel("Systemvoraussetzungen & Diagnose:")
        lbl_check_title.setStyleSheet("font-weight: bold; color: #f8fafc; font-size: 13px;")
        box_layout.addWidget(lbl_check_title)

        self.lbl_python = QLabel("Prüfe Python...")
        box_layout.addWidget(self.lbl_python)

        self.lbl_pyqt6 = QLabel("Prüfe PyQt6...")
        box_layout.addWidget(self.lbl_pyqt6)

        self.lbl_space = QLabel("Prüfe Speicherplatz...")
        box_layout.addWidget(self.lbl_space)

        self.lbl_games = QLabel("Prüfe Spiele-Installationen...")
        box_layout.addWidget(self.lbl_games)

        layout.addWidget(status_box)

        # Existing install note
        self.existing_box = QFrame()
        self.existing_box.setObjectName("cardFrame")
        self.existing_box.setStyleSheet("background-color: #1e3a8a; border: 1px solid #3b82f6;")
        ex_layout = QHBoxLayout(self.existing_box)
        self.lbl_existing = QLabel()
        self.lbl_existing.setStyleSheet("color: #ffffff; font-size: 12px;")
        ex_layout.addWidget(self.lbl_existing, stretch=1)

        self.btn_uninstall_existing = QPushButton("🗑️ Deinstallieren...")
        self.btn_uninstall_existing.setObjectName("dangerBtn")
        self.btn_uninstall_existing.clicked.connect(self._start_uninstall)
        ex_layout.addWidget(self.btn_uninstall_existing)
        self.existing_box.setVisible(False)
        layout.addWidget(self.existing_box)

        layout.addStretch()
        return page

    def _create_page_mode(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("Installationsmodus auswählen")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")
        layout.addWidget(title)

        self.mode_group = QButtonGroup(self)

        # User Mode Card
        card_user = QFrame()
        card_user.setObjectName("cardFrame")
        u_layout = QVBoxLayout(card_user)
        self.rb_user = QRadioButton("Benutzer-Installation (Empfohlen)")
        self.rb_user.setChecked(True)
        self.rb_user.setStyleSheet("font-weight: bold; font-size: 14px; color: #f8fafc;")
        self.mode_group.addButton(self.rb_user)
        u_layout.addWidget(self.rb_user)

        desc_user = QLabel(
            "Installiert nach <code>~/.local/bin</code> und <code>~/.local/share</code>. "
            "Erfordert keine Root-/Sudo-Rechte und ist optimal für Desktop-Gamer geeignet."
        )
        desc_user.setStyleSheet("color: #94a3b8; font-size: 12px; margin-left: 24px;")
        desc_user.setWordWrap(True)
        u_layout.addWidget(desc_user)
        layout.addWidget(card_user)

        # System Mode Card
        card_sys = QFrame()
        card_sys.setObjectName("cardFrame")
        s_layout = QVBoxLayout(card_sys)
        self.rb_system = QRadioButton("Systemweite Installation")
        self.rb_system.setStyleSheet("font-weight: bold; font-size: 14px; color: #f8fafc;")
        self.mode_group.addButton(self.rb_system)
        s_layout.addWidget(self.rb_system)

        desc_sys = QLabel(
            "Installiert nach <code>/usr/bin</code> und <code>/usr/share</code>. "
            "Für alle Benutzer verfügbar. (Erfordert Root-Berechtigung)."
        )
        desc_sys.setStyleSheet("color: #94a3b8; font-size: 12px; margin-left: 24px;")
        desc_sys.setWordWrap(True)
        s_layout.addWidget(desc_sys)
        layout.addWidget(card_sys)

        layout.addStretch()
        return page

    def _create_page_options(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("Zusätzliche Optionen")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("cardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        self.cb_desktop = QCheckBox("Desktop-Starter & Startmenü-Eintrag erstellen (.desktop)")
        self.cb_desktop.setChecked(True)
        c_layout.addWidget(self.cb_desktop)

        self.cb_prep_dirs = QCheckBox("Staging- und Preset-Ordner für ETS2 & ATS vorbereiten")
        self.cb_prep_dirs.setChecked(True)
        c_layout.addWidget(self.cb_prep_dirs)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _create_page_install(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.lbl_install_status = QLabel("Installation wird vorbereitet...")
        self.lbl_install_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        layout.addWidget(self.lbl_install_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setStyleSheet("QProgressBar { background-color: #1e293b; border: 1px solid #334155; border-radius: 4px; text-align: center; } QProgressBar::chunk { background-color: #2563eb; }")
        layout.addWidget(self.progress_bar)

        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("background-color: #0f172a; font-family: monospace; font-size: 11px; color: #94a3b8;")
        layout.addWidget(self.log_console)

        return page

    def _create_page_finish(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.lbl_finish_title = QLabel("Installation erfolgreich!")
        self.lbl_finish_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #10b981;")
        layout.addWidget(self.lbl_finish_title)

        self.lbl_finish_msg = QLabel("Truck Mod Manager ist jetzt einsatzbereit.")
        self.lbl_finish_msg.setStyleSheet("color: #cbd5e1; font-size: 13px;")
        layout.addWidget(self.lbl_finish_msg)

        card = QFrame()
        card.setObjectName("cardFrame")
        c_layout = QVBoxLayout(card)

        btn_launch = QPushButton("🚀 Truck Mod Manager jetzt starten")
        btn_launch.setObjectName("primaryBtn")
        btn_launch.setFixedHeight(38)
        btn_launch.clicked.connect(self._launch_app)
        c_layout.addWidget(btn_launch)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _check_prerequisites(self):
        pre = InstallerDetector.check_prerequisites()
        ext = InstallerDetector.check_existing_installations()

        if pre["python_ok"]:
            self.lbl_python.setText(f"✔ Python: {pre['python_version']} (Kompatibel)")
            self.lbl_python.setStyleSheet("color: #10b981;")
        else:
            self.lbl_python.setText(f"❌ Python {pre['python_version']} ist zu alt (>= 3.9 erforderlich)")
            self.lbl_python.setStyleSheet("color: #ef4444;")

        if pre["pyqt6_ok"]:
            self.lbl_pyqt6.setText("✔ GUI-Framework: PyQt6 ist installiert")
            self.lbl_pyqt6.setStyleSheet("color: #10b981;")
        else:
            self.lbl_pyqt6.setText("❌ PyQt6 nicht gefunden!")
            self.lbl_pyqt6.setStyleSheet("color: #ef4444;")

        self.lbl_space.setText(f"✔ Verfügbarer Speicherplatz: {pre['free_space_mb']:.0f} MB")
        self.lbl_space.setStyleSheet("color: #10b981;")

        game_status = []
        if pre["ets2_detected"]:
            game_status.append("Euro Truck Simulator 2 erkannt")
        if pre["ats_detected"]:
            game_status.append("American Truck Simulator erkannt")

        if game_status:
            self.lbl_games.setText(f"✔ Spiele: {', '.join(game_status)}")
            self.lbl_games.setStyleSheet("color: #10b981;")
        else:
            self.lbl_games.setText("ℹ️ Keine aktiven Spielverzeichnisse in ~/.local/share (werden bei Bedarf angelegt)")
            self.lbl_games.setStyleSheet("color: #94a3b8;")

        # Existing check
        if ext["is_installed"]:
            self.existing_box.setVisible(True)
            mode_str = "Benutzer-Installation" if ext["user_installed"] else "Systemweit"
            self.lbl_existing.setText(f"ℹ️ Bereits installiert: <b>v{ext['version']}</b> ({mode_str})")

    def _update_step_visuals(self, step_idx: int):
        for idx, (num_lbl, text_lbl) in enumerate(self.step_labels):
            if idx == step_idx:
                num_lbl.setStyleSheet("background-color: #2563eb; color: #ffffff; border-radius: 12px; font-weight: bold; font-size: 11px;")
                text_lbl.setStyleSheet("color: #f8fafc; font-size: 13px; font-weight: bold;")
            elif idx < step_idx:
                num_lbl.setStyleSheet("background-color: #059669; color: #ffffff; border-radius: 12px; font-weight: bold; font-size: 11px;")
                text_lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")
            else:
                num_lbl.setStyleSheet("background-color: #334155; color: #cbd5e1; border-radius: 12px; font-weight: bold; font-size: 11px;")
                text_lbl.setStyleSheet("color: #64748b; font-size: 13px;")

    def _go_next(self):
        curr = self.stack.currentIndex()
        if curr == 0:
            self.stack.setCurrentIndex(1)
            self.btn_back.setEnabled(True)
            self._update_step_visuals(1)
        elif curr == 1:
            self.stack.setCurrentIndex(2)
            self.btn_back.setEnabled(True)
            self._update_step_visuals(2)
        elif curr == 2:
            self.stack.setCurrentIndex(3)
            self.btn_back.setEnabled(False)
            self.btn_next.setEnabled(False)
            self._update_step_visuals(3)
            self._start_install()
        elif curr == 4:
            self.close()

    def _go_back(self):
        curr = self.stack.currentIndex()
        if curr > 0:
            self.stack.setCurrentIndex(curr - 1)
            self.btn_back.setEnabled(curr - 1 > 0)
            self._update_step_visuals(curr - 1)

    def _start_install(self):
        mode = "user" if self.rb_user.isChecked() else "system"
        self.install_worker = InstallWorker(
            mode=mode,
            create_desktop_shortcut=self.cb_desktop.isChecked(),
            prepare_dirs=self.cb_prep_dirs.isChecked()
        )
        self.install_worker.progress.connect(self.progress_bar.setValue)
        self.install_worker.log_message.connect(self.log_console.appendPlainText)
        self.install_worker.finished.connect(self._on_install_finished)
        self.install_worker.start()

    def _on_install_finished(self, success: bool, msg: str):
        if success:
            self.stack.setCurrentIndex(4)
            self._update_step_visuals(4)
            self.btn_next.setText("Fertigstellen")
            self.btn_next.setEnabled(True)
            self.btn_cancel.setVisible(False)
        else:
            QMessageBox.critical(self, "Installationsfehler", msg)
            self.btn_back.setEnabled(True)
            self.btn_next.setEnabled(True)

    def _start_uninstall(self):
        reply = QMessageBox.question(
            self,
            "Deinstallation bestätigen",
            "Möchtest du Truck Mod Manager wirklich deinstallieren?\n"
            "(Deine Mod-Dateien und Presets bleiben erhalten.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.stack.setCurrentIndex(3)
            self.btn_back.setEnabled(False)
            self.btn_next.setEnabled(False)
            self.lbl_install_status.setText("Deinstallation läuft...")
            self.uninstall_worker = UninstallWorker(keep_mods=True)
            self.uninstall_worker.progress.connect(self.progress_bar.setValue)
            self.uninstall_worker.log_message.connect(self.log_console.appendPlainText)
            self.uninstall_worker.finished.connect(self._on_uninstall_finished)
            self.uninstall_worker.start()

    def _on_uninstall_finished(self, success: bool, msg: str):
        if success:
            QMessageBox.information(self, "Deinstalliert", msg)
            self.close()
        else:
            QMessageBox.critical(self, "Fehler", msg)

    def _launch_app(self):
        home = Path.home()
        user_bin = home / ".local" / "bin" / BIN_NAME
        target = str(user_bin) if user_bin.exists() else BIN_NAME
        subprocess.Popen([target])
        self.close()
