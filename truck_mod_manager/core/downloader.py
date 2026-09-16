"""
Asynchronous Download Manager and Archive Extractor for Truck Mod Manager.
Supports chunked streaming downloads with speed/ETA calculation and safe multi-part archive unpacking.
"""
import os
import shutil
import subprocess
import time
import urllib.request
import urllib.error
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from truck_mod_manager.core.config import config



DOWNLOADS_CACHE_DIR = Path(config.get("cache_dir", Path.home() / ".cache" / "truck-mod-manager")) / "downloads"
DOWNLOADS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def format_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"


class ModDownloadWorker(QThread):
    progress_updated = pyqtSignal(int, int, str, str)  # downloaded_bytes, total_bytes, speed_str, eta_str
    download_finished = pyqtSignal(str, str)  # local_path, file_name
    download_error = pyqtSignal(str)

    def __init__(self, url: str, target_dir: Path, suggested_filename: str = "", parent=None):
        super().__init__(parent)
        self.url = url
        self.target_dir = Path(target_dir)
        self.suggested_filename = suggested_filename

    def run(self):
        try:
            self.target_dir.mkdir(parents=True, exist_ok=True)

            req = urllib.request.Request(self.url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            })

            with urllib.request.urlopen(req, timeout=15) as resp:
                status_code = getattr(resp, "status", 200)
                if status_code != 200:
                    self.download_error.emit(f"Server antwortete mit HTTP {status_code}")
                    return

                # Determine filename
                filename = self.suggested_filename
                if not filename:
                    cd = resp.headers.get("Content-Disposition", "")
                    if "filename=" in cd:
                        filename = cd.split("filename=")[-1].strip("\"' ")
                    else:
                        filename = self.url.split("?")[0].split("/")[-1] or "mod_download.scs"

                # Clean filename
                filename = os.path.basename(filename)
                temp_path = DOWNLOADS_CACHE_DIR / f"tmp_{filename}"
                final_download_path = DOWNLOADS_CACHE_DIR / filename

                total_bytes = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                start_time = time.time()
                last_emit_time = start_time

                with open(temp_path, "wb") as f:
                    while True:
                        if self.isInterruptionRequested():
                            if temp_path.exists():
                                temp_path.unlink()
                            return

                        chunk = resp.read(65536)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if now - last_emit_time >= 0.2:
                            elapsed = now - start_time
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            speed_str = f"{format_size(int(speed))}/s"

                            eta_str = ""
                            if total_bytes > 0 and speed > 0:
                                rem_bytes = total_bytes - downloaded
                                rem_seconds = int(rem_bytes / speed)
                                if rem_seconds < 60:
                                    eta_str = f"Noch {rem_seconds}s"
                                else:
                                    eta_str = f"Noch {rem_seconds // 60}m {rem_seconds % 60}s"

                            self.progress_updated.emit(downloaded, total_bytes, speed_str, eta_str)
                            last_emit_time = now


            if temp_path.exists():
                temp_path.replace(final_download_path)

            self.download_finished.emit(str(final_download_path), filename)

        except Exception as e:
            self.download_error.emit(str(e))


class ArchiveExtractor:
    @classmethod
    def deploy_or_extract(cls, source_file: Path, target_mod_dir: Path) -> List[Path]:
        """
        Deploys or extracts the downloaded file into target_mod_dir:
        - If .scs: moves/copies directly into target_mod_dir.
        - If .zip: checks if it contains internal .scs files. If yes, extracts .scs files. If it has manifest.sii directly, copies .zip.
        - If .7z or .7z.001: extracts all files into target_mod_dir using 7z.
        Returns the list of final .scs / .zip files deployed in target_mod_dir.
        """
        source = Path(source_file)
        target = Path(target_mod_dir)
        target.mkdir(parents=True, exist_ok=True)
        deployed: List[Path] = []

        filename_lower = source.name.lower()

        # 1. Pure SCS file
        if filename_lower.endswith(".scs"):
            dest = target / source.name
            shutil.copy2(source, dest)
            deployed.append(dest)
            return deployed

        # 2. ZIP Archive
        if filename_lower.endswith(".zip"):
            try:
                with zipfile.ZipFile(source, 'r') as zf:
                    namelist = zf.namelist()
                    # Check if archive contains nested .scs files
                    scs_entries = [n for n in namelist if n.lower().endswith(".scs") and not n.startswith("__MACOSX")]
                    if scs_entries:
                        for entry in scs_entries:
                            zf.extract(entry, target)
                            extracted = target / entry
                            # Flatten if nested in subfolder
                            flat_dest = target / Path(entry).name
                            if flat_dest != extracted:
                                shutil.move(extracted, flat_dest)
                            deployed.append(flat_dest)
                    else:
                        # Direct zip mod
                        dest = target / source.name
                        shutil.copy2(source, dest)
                        deployed.append(dest)
                return deployed
            except Exception as e:
                print(f"[ArchiveExtractor] Fehler beim Zip-Entpacken von {source}: {e}")

        # 3. 7Z Archive (e.g. .7z, .7z.001, ProMods packages)
        if any(filename_lower.endswith(ext) for ext in [".7z", ".7z.001", ".rar"]):
            cmd_7z = shutil.which("7z") or shutil.which("7za")
            if cmd_7z:
                # Extract into a temp subfolder first, then pick .scs files
                temp_extract = target / "_temp_extract"
                temp_extract.mkdir(parents=True, exist_ok=True)
                try:
                    res = subprocess.run([cmd_7z, "x", "-y", f"-o{temp_extract}", str(source)], capture_output=True, text=True)
                    if res.returncode == 0:
                        # Find all extracted .scs and .zip files
                        for root, _, files in os.walk(temp_extract):
                            for f in files:
                                f_lower = f.lower()
                                if f_lower.endswith(".scs") or f_lower.endswith(".zip"):
                                    src_f = Path(root) / f
                                    dest_f = target / f
                                    shutil.copy2(src_f, dest_f)
                                    deployed.append(dest_f)
                finally:
                    if temp_extract.exists():
                        shutil.rmtree(temp_extract, ignore_errors=True)

        return deployed
