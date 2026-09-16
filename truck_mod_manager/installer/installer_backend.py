"""
Backend logic and asynchronous workers for Truck Mod Manager graphical installer.
"""
import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from truck_mod_manager import __version__


APP_NAME = "Truck Mod Manager"
BIN_NAME = "truck-mod-manager"


class InstallerDetector:
    """Detects system status, dependencies, and existing installations."""

    @staticmethod
    def get_source_dir() -> Path:
        """Find the root directory containing the project source code."""
        return Path(__file__).resolve().parent.parent.parent

    @classmethod
    def check_existing_installations(cls) -> Dict[str, Any]:
        """Check if truck-mod-manager is already installed (user and/or system)."""
        home = Path.home()
        user_bin = home / ".local" / "bin" / BIN_NAME
        user_share = home / ".local" / "share" / BIN_NAME
        user_desktop = home / ".local" / "share" / "applications" / f"{BIN_NAME}.desktop"

        sys_bin1 = Path(f"/usr/local/bin/{BIN_NAME}")
        sys_bin2 = Path(f"/usr/bin/{BIN_NAME}")
        sys_share1 = Path(f"/usr/local/share/{BIN_NAME}")
        sys_share2 = Path(f"/usr/share/{BIN_NAME}")

        user_installed = user_bin.exists() or user_share.exists()
        sys_installed = sys_bin1.exists() or sys_bin2.exists() or sys_share1.exists() or sys_share2.exists()

        installed_version = None
        if user_installed or sys_installed:
            try:
                bin_path = str(user_bin if user_installed else (sys_bin1 if sys_bin1.exists() else sys_bin2))
                res = subprocess.run([bin_path, "--version"], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    installed_version = res.stdout.strip()
            except Exception:
                installed_version = __version__

        return {
            "is_installed": user_installed or sys_installed,
            "user_installed": user_installed,
            "system_installed": sys_installed,
            "user_bin": str(user_bin) if user_bin.exists() else None,
            "sys_bin": str(sys_bin1 if sys_bin1.exists() else sys_bin2) if sys_installed else None,
            "version": installed_version or __version__,
        }

    @classmethod
    def check_prerequisites(cls) -> Dict[str, Any]:
        """Verify Python, PyQt6, storage, and system compatibility."""
        py_version = platform.python_version()
        py_ok = sys.version_info >= (3, 9)

        pyqt6_ok = True
        try:
            import PyQt6
        except ImportError:
            pyqt6_ok = False

        # Free disk space in user home
        home = Path.home()
        try:
            usage = shutil.disk_usage(home)
            free_bytes = usage.free
            free_mb = free_bytes / (1024 * 1024)
            space_ok = free_mb >= 50
        except Exception:
            free_mb = 0
            space_ok = True

        # OS Information
        distro_name = "Linux"
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            distro_name = line.split("=", 1)[1].strip().strip('"')
                            break
            except Exception:
                pass

        # Steam & Game quick check
        ets2_detected = False
        ats_detected = False
        native_ets2 = home / ".local" / "share" / "Euro Truck Simulator 2"
        native_ats = home / ".local" / "share" / "American Truck Simulator"
        if native_ets2.exists():
            ets2_detected = True
        if native_ats.exists():
            ats_detected = True

        return {
            "python_version": py_version,
            "python_ok": py_ok,
            "pyqt6_ok": pyqt6_ok,
            "free_space_mb": free_mb,
            "space_ok": space_ok,
            "distro_name": distro_name,
            "ets2_detected": ets2_detected,
            "ats_detected": ats_detected,
        }


class InstallWorker(QThread):
    """Asynchronous worker executing the installation steps."""

    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, mode: str = "user", create_desktop_shortcut: bool = True, prepare_dirs: bool = True):
        super().__init__()
        self.mode = mode  # "user" or "system"
        self.create_desktop_shortcut = create_desktop_shortcut
        self.prepare_dirs = prepare_dirs

    def run(self):
        try:
            self.progress.emit(5)
            self.log_message.emit("Initialisiere Installationsassistenten...")

            src_root = InstallerDetector.get_source_dir()

            if self.mode == "user":
                prefix = Path.home() / ".local"
            else:
                prefix = Path("/usr")

            bin_dir = prefix / "bin"
            share_dir = prefix / "share" / BIN_NAME
            app_dir = prefix / "share" / "applications"
            icon_dir = prefix / "share" / "icons" / "hicolor" / "scalable" / "apps"

            self.progress.emit(15)
            self.log_message.emit(f"Erstelle Zielverzeichnisse in {prefix}...")
            bin_dir.mkdir(parents=True, exist_ok=True)
            share_dir.mkdir(parents=True, exist_ok=True)
            app_dir.mkdir(parents=True, exist_ok=True)
            icon_dir.mkdir(parents=True, exist_ok=True)

            self.progress.emit(30)
            self.log_message.emit("Kopiere Programmdateien...")

            # Copy package
            target_pkg = share_dir / "truck_mod_manager"
            if target_pkg.exists():
                shutil.rmtree(target_pkg)
            shutil.copytree(src_root / "truck_mod_manager", target_pkg)

            # Copy main.py
            shutil.copy2(src_root / "main.py", share_dir / "main.py")

            self.progress.emit(50)
            self.log_message.emit("Erstelle Starter-Skript...")

            launcher_path = bin_dir / BIN_NAME
            launcher_content = f"""#!/usr/bin/env bash
# Truck Mod Manager launcher

if [ -z "$QT_QPA_PLATFORM" ] && [ -n "$WAYLAND_DISPLAY" ]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi

SHARE_PATH="{share_dir}"
if [ ! -d "$SHARE_PATH" ]; then
    if [ -d "$HOME/.local/share/truck-mod-manager" ]; then
        SHARE_PATH="$HOME/.local/share/truck-mod-manager"
    elif [ -d "/usr/share/truck-mod-manager" ]; then
        SHARE_PATH="/usr/share/truck-mod-manager"
    fi
fi

exec python3 "$SHARE_PATH/main.py" "$@"
"""
            launcher_path.write_text(launcher_content, encoding="utf-8")
            launcher_path.chmod(0o755)

            self.progress.emit(70)
            self.log_message.emit("Installiere Desktop-Starter und Anwendungs-Icon...")

            # Install Icon
            src_icon = src_root / "truck_mod_manager" / "resources" / "icon.svg"
            if src_icon.exists():
                shutil.copy2(src_icon, icon_dir / f"{BIN_NAME}.svg")

            # Install Desktop file with absolute Exec path
            src_desktop = src_root / f"{BIN_NAME}.desktop"
            if src_desktop.exists():
                content = src_desktop.read_text(encoding="utf-8")
                content = re.sub(r"^Exec=.*", f"Exec={bin_dir / BIN_NAME}", content, flags=re.MULTILINE)
                content = re.sub(r"^Icon=.*", f"Icon={BIN_NAME}", content, flags=re.MULTILINE)
                (app_dir / f"{BIN_NAME}.desktop").write_text(content, encoding="utf-8")
                (app_dir / f"{BIN_NAME}.desktop").chmod(0o755)

                # Desktop shortcut if enabled
                if self.create_desktop_shortcut:
                    for dt_dir in [Path.home() / "Desktop", Path.home() / "Schreibtisch"]:
                        if dt_dir.is_dir():
                            dt_file = dt_dir / f"{BIN_NAME}.desktop"
                            dt_file.write_text(content, encoding="utf-8")
                            dt_file.chmod(0o755)
                            try:
                                subprocess.run(["gio", "set", str(dt_file), "metadata::trusted", "true"], check=False, capture_output=True)
                            except Exception:
                                pass
                            break


            if self.prepare_dirs:
                self.progress.emit(85)
                self.log_message.emit("Bereite Verzeichnisse für ETS2 und ATS vor...")
                home = Path.home()
                (home / ".config" / "truck-mod-manager").mkdir(parents=True, exist_ok=True)
                (home / ".local" / "share" / "truck-mod-manager" / "mods" / "ets2").mkdir(parents=True, exist_ok=True)
                (home / ".local" / "share" / "truck-mod-manager" / "mods" / "ats").mkdir(parents=True, exist_ok=True)
                (home / ".local" / "share" / "truck-mod-manager" / "presets" / "ets2").mkdir(parents=True, exist_ok=True)
                (home / ".local" / "share" / "truck-mod-manager" / "presets" / "ats").mkdir(parents=True, exist_ok=True)

            self.progress.emit(95)
            self.log_message.emit("Aktualisiere System-Caches...")
            try:
                subprocess.run(["update-desktop-database", str(app_dir)], check=False, capture_output=True)
            except Exception:
                pass
            try:
                subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(prefix / "share" / "icons" / "hicolor")], check=False, capture_output=True)
            except Exception:
                pass

            self.progress.emit(100)
            self.log_message.emit("Installation erfolgreich abgeschlossen!")
            self.finished.emit(True, f"Truck Mod Manager wurde erfolgreich in {prefix} installiert.")

        except Exception as e:
            self.finished.emit(False, f"Fehler bei der Installation: {e}")


class UninstallWorker(QThread):
    """Asynchronous worker executing uninstallation."""

    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, keep_mods: bool = True):
        super().__init__()
        self.keep_mods = keep_mods

    def run(self):
        try:
            self.progress.emit(10)
            self.log_message.emit("Ermittle installierte Dateien...")

            home = Path.home()
            is_user = (home / ".local" / "bin" / BIN_NAME).exists()
            prefix = home / ".local" if is_user else Path("/usr")

            bin_file = prefix / "bin" / BIN_NAME
            share_dir = prefix / "share" / BIN_NAME
            desktop_file = prefix / "share" / "applications" / f"{BIN_NAME}.desktop"
            icon_file = prefix / "share" / "icons" / "hicolor" / "scalable" / "apps" / f"{BIN_NAME}.svg"

            self.progress.emit(30)
            if bin_file.exists():
                self.log_message.emit(f"Entferne {bin_file}...")
                bin_file.unlink()

            self.progress.emit(50)
            if desktop_file.exists():
                self.log_message.emit(f"Entferne Desktop-Starter...")
                desktop_file.unlink()

            if icon_file.exists():
                self.log_message.emit(f"Entferne Icon...")
                icon_file.unlink()

            self.progress.emit(70)
            if share_dir.exists():
                self.log_message.emit(f"Entferne Programmverzeichnis {share_dir}...")
                shutil.rmtree(share_dir)

            if not self.keep_mods:
                data_dir = home / ".local" / "share" / "truck-mod-manager"
                if data_dir.exists():
                    self.log_message.emit("Entferne Mod-Daten und Presets...")
                    shutil.rmtree(data_dir)

            self.progress.emit(90)
            self.log_message.emit("Aktualisiere Desktop-Datenbank...")
            try:
                subprocess.run(["update-desktop-database", str(prefix / "share" / "applications")], check=False, capture_output=True)
            except Exception:
                pass

            self.progress.emit(100)
            self.log_message.emit("Deinstallation erfolgreich abgeschlossen!")
            self.finished.emit(True, "Truck Mod Manager wurde erfolgreich deinstalliert.")

        except Exception as e:
            self.finished.emit(False, f"Fehler bei der Deinstallation: {e}")
