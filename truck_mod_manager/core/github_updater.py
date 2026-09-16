"""
GitHub Update Manager for Truck Mod Manager (Euro Truck Simulator 2 & American Truck Simulator).
Adapted from Cachy Security Suite and AMD Control Center.
Provides release detection, version comparison, background checking, and self-updating.
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Ensure package root is in sys.path when invoked directly as standalone script
_core_dir = Path(__file__).resolve().parent
_pkg_root = _core_dir.parent   # .../truck_mod_manager
_app_root = _pkg_root.parent   # .../truck-mod-manager
for _p in (str(_app_root), str(_pkg_root)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from PyQt6.QtCore import QSettings, QThread, pyqtSignal
except ImportError:
    class QThread:  # type: ignore
        pass
    def pyqtSignal(*args, **kwargs):  # type: ignore
        class _Signal:
            def connect(self, *a, **kw): pass
            def emit(self, *a, **kw): pass
        return _Signal()
    class QSettings:  # type: ignore
        def __init__(self, *args, **kwargs): pass
        def value(self, key, default=None): return default
        def setValue(self, key, val): pass
        def sync(self): pass

try:
    from truck_mod_manager import __version__
except (ImportError, ValueError):
    try:
        from .. import __version__
    except Exception:
        __version__ = "1.0.0"

DEFAULT_GITHUB_REPO = "lenzi96/truck-mod-manager"
CONFIG_FILE = Path.home() / ".config" / "truck-mod-manager" / "updater_config.json"


def get_repo_dir() -> Path:
    """Returns the root directory of the application repository."""
    return Path(__file__).resolve().parent.parent.parent


def get_github_repo() -> str:
    """Gets the currently configured GitHub repository (owner/repo)."""
    # 1. Check saved config file / QSettings
    settings = QSettings("Julian", "TruckModManager")
    custom = settings.value("updater/github_repo", "").strip()
    if custom:
        return custom

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("github_repo"):
                    return cfg["github_repo"]
        except Exception:
            pass

    # 2. Check git remote origin if in git repository
    repo_dir = get_repo_dir()
    if (repo_dir / ".git").is_dir() and shutil.which("git"):
        try:
            res = subprocess.run(
                ["git", "-C", str(repo_dir), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                url = res.stdout.strip()
                m = re.search(r"github\.com[:/]([^/]+)/([^/\.]+)", url)
                if m:
                    r = f"{m.group(1)}/{m.group(2)}"
                    return r[:-4] if r.endswith(".git") else r
        except Exception:
            pass

    return DEFAULT_GITHUB_REPO


def set_github_repo(repo_str: str) -> None:
    """Saves configured GitHub repository and updates git origin if in git repo."""
    repo_clean = repo_str.strip()
    m = re.search(r"github\.com[:/]([^/]+)/([^/\.]+)", repo_clean)
    if m:
        repo_clean = f"{m.group(1)}/{m.group(2)}"
        if repo_clean.endswith(".git"):
            repo_clean = repo_clean[:-4]

    # Save to QSettings
    settings = QSettings("Julian", "TruckModManager")
    settings.setValue("updater/github_repo", repo_clean)

    # Save to config file
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["github_repo"] = repo_clean
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

    # Update git remote if in git repo
    repo_dir = get_repo_dir()
    if (repo_dir / ".git").is_dir() and shutil.which("git") and repo_clean:
        target_url = f"https://github.com/{repo_clean}.git"
        check_rem = subprocess.run(["git", "-C", str(repo_dir), "remote"], capture_output=True, text=True, check=False)
        if "origin" in check_rem.stdout:
            subprocess.run(["git", "-C", str(repo_dir), "remote", "set-url", "origin", target_url], check=False)
        else:
            subprocess.run(["git", "-C", str(repo_dir), "remote", "add", "origin", target_url], check=False)


def get_github_token() -> Optional[str]:
    """Retrieves GitHub personal access token from QSettings, env, or ~/.git-credentials."""
    settings = QSettings("Julian", "TruckModManager")
    token = settings.value("updater/github_token", "").strip()
    if token:
        return token
    env_token = os.environ.get("GITHUB_TOKEN", "").strip() or os.environ.get("GH_TOKEN", "").strip()
    if env_token:
        return env_token
    git_cred_path = os.path.expanduser("~/.git-credentials")
    if os.path.exists(git_cred_path):
        try:
            with open(git_cred_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "github.com" in line:
                        m = re.search(r":([^@:]+)@github\.com", line)
                        if m:
                            tok = m.group(1).strip()
                            if tok.startswith("github_pat_") or tok.startswith("ghp_"):
                                return tok
        except Exception:
            pass
    cfg_token_path = os.path.expanduser("~/.config/truck-mod-manager/token")
    if os.path.exists(cfg_token_path):
        try:
            with open(cfg_token_path, "r", encoding="utf-8") as f:
                t = f.read().strip()
                if t:
                    return t
        except Exception:
            pass
    return None


def set_github_token(token_str: str) -> None:
    """Saves configured GitHub personal access token in QSettings."""
    settings = QSettings("Julian", "TruckModManager")
    settings.setValue("updater/github_token", token_str.strip())


def compare_versions(v1: str, v2: str) -> int:
    """
    Compares two version strings.
    Returns:
       < 0 if v1 < v2 (newer version available)
       0   if v1 == v2
       > 0 if v1 > v2
    Uses vercmp if available, otherwise fallback numeric tuple comparison.
    """
    v1_clean = v1.lstrip("v").strip()
    v2_clean = v2.lstrip("v").strip()

    if shutil.which("vercmp"):
        try:
            res = subprocess.run(["vercmp", v1_clean, v2_clean], capture_output=True, text=True, check=False)
            return int(res.stdout.strip())
        except Exception:
            pass

    parts1 = [int(p) for p in re.findall(r"\d+", v1_clean)]
    parts2 = [int(p) for p in re.findall(r"\d+", v2_clean)]
    return (parts1 > parts2) - (parts1 < parts2)


@dataclass
class GitHubUpdateInfo:
    installed_version: str = __version__
    remote_version: str = "Unbekannt"
    has_update: bool = False
    github_repo: str = DEFAULT_GITHUB_REPO
    release_url: str = ""
    release_notes: str = ""
    tarball_url: str = ""
    asset_api_url: str = ""
    github_auth_error: bool = False
    checked_at: Optional[datetime.datetime] = None
    check_error: Optional[str] = None


class GitHubUpdateCheckerWorker(QThread):
    """Background worker that queries the GitHub API for latest releases or tags."""
    finished = pyqtSignal(GitHubUpdateInfo)

    def run(self):
        info = GitHubUpdateInfo()
        info.installed_version = __version__
        info.checked_at = datetime.datetime.now()
        repo = get_github_repo()
        info.github_repo = repo
        token = get_github_token()

        try:
            # 1. Check GitHub Releases API
            url = f"https://api.github.com/repos/{repo}/releases/latest"
            headers = {
                "User-Agent": f"Truck-Mod-Manager/{info.installed_version}",
                "Accept": "application/vnd.github+json",
            }
            if token:
                headers["Authorization"] = f"Bearer {token}"

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    tag = data.get("tag_name", "").lstrip("v").strip()
                    if tag:
                        info.remote_version = tag
                        info.release_url = data.get("html_url", "")
                        info.release_notes = data.get("body", "")
                        for asset in data.get("assets", []):
                            if asset.get("name", "").endswith((".tar.gz", ".zip")):
                                info.tarball_url = asset.get("browser_download_url", "")
                                info.asset_api_url = asset.get("url", "")
                                break

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # No release published yet, check tags
                info = self._fallback_check_tags(info, repo, token)
            elif e.code in (401, 403):
                info.github_auth_error = True
                if not token:
                    info.check_error = "Repository ist privat oder Rate-Limit erreicht. Bitte GitHub-Token hinterlegen."
                else:
                    info.check_error = f"GitHub-Fehler {e.code}: Token ungültig oder unzureichende Rechte."
                info.remote_version = info.installed_version
            else:
                info.check_error = f"GitHub API Fehler ({e.code}): {e.reason}"
                info.remote_version = info.installed_version
        except Exception as exc:
            info.check_error = f"Verbindung zu GitHub nicht möglich: {exc}"
            info.remote_version = info.installed_version

        # Compare versions
        if info.installed_version and info.remote_version and info.remote_version != "Unbekannt":
            cmp_res = compare_versions(info.installed_version, info.remote_version)
            info.has_update = cmp_res < 0

        self.finished.emit(info)

    def _fallback_check_tags(self, info: GitHubUpdateInfo, repo: str, token: Optional[str]) -> GitHubUpdateInfo:
        """Fallback to check tags if no release exists."""
        try:
            url = f"https://api.github.com/repos/{repo}/tags"
            headers = {"User-Agent": f"Truck-Mod-Manager/{info.installed_version}"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    tags = json.loads(resp.read().decode("utf-8"))
                    if tags and isinstance(tags, list):
                        latest_tag = tags[0].get("name", "").lstrip("v").strip()
                        if latest_tag:
                            info.remote_version = latest_tag
                            info.release_url = f"https://github.com/{repo}/releases/tag/v{latest_tag}"
                            info.release_notes = f"Tag v{latest_tag} auf GitHub verfügbar."
                            return info
        except Exception:
            pass
        info.remote_version = info.installed_version
        return info


@dataclass
class UpdateStep:
    name: str
    command: List[str]
    description: str


class GitHubUpdateExecWorker(QThread):
    """Executes update steps with real-time log output."""
    step_started = pyqtSignal(int, int, str)  # current, total, name
    output_line = pyqtSignal(str)
    completed = pyqtSignal(bool, str)

    def __init__(self, steps: List[UpdateStep]):
        super().__init__()
        self.steps = steps
        self.process: Optional[subprocess.Popen] = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=1)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

    def run(self):
        total = len(self.steps)
        if total == 0:
            self.completed.emit(True, "Keine Schritte auszuführen.")
            return

        for idx, step in enumerate(self.steps, start=1):
            if self._is_cancelled:
                self.output_line.emit("\n[!] Vorgang vom Benutzer abgebrochen.")
                self.completed.emit(False, "Aktualisierung abgebrochen.")
                return

            self.step_started.emit(idx, total, step.name)
            self.output_line.emit("==================================================")
            self.output_line.emit(f"[{idx}/{total}] {step.name}")
            self.output_line.emit(f"Befehl: {' '.join(step.command)}")
            self.output_line.emit("==================================================\n")

            env = os.environ.copy()
            repo_root = str(get_repo_dir())
            env["PYTHONPATH"] = f"{repo_root}:{env.get('PYTHONPATH', '')}"

            try:
                self.process = subprocess.Popen(
                    step.command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env,
                )

                if self.process.stdout:
                    for line in iter(self.process.stdout.readline, ""):
                        if self._is_cancelled:
                            break
                        self.output_line.emit(line.rstrip())

                self.process.wait()
                ret = self.process.returncode if self.process else 1

                if ret != 0:
                    self.output_line.emit(f"\n❌ Schritt '{step.name}' mit Fehlercode {ret} beendet.")
                    self.completed.emit(False, f"Fehler bei Schritt '{step.name}' (Code {ret})")
                    return
                else:
                    self.output_line.emit(f"\n✅ Schritt '{step.name}' erfolgreich abgeschlossen.\n")

            except Exception as e:
                self.output_line.emit(f"\n❌ Fehler bei Ausführung: {e}")
                self.completed.emit(False, str(e))
                return

        self.completed.emit(True, "Truck Mod Manager wurde erfolgreich auf die neueste Version aktualisiert!")


def is_valid_archive(path: str) -> Optional[str]:
    """Checks if the file at path is a valid tar or zip archive."""
    if not os.path.exists(path) or os.path.getsize(path) < 500:
        return None
    try:
        import tarfile
        if tarfile.is_tarfile(path):
            return "tar"
    except Exception:
        pass
    try:
        import zipfile
        if zipfile.is_zipfile(path):
            return "zip"
    except Exception:
        pass
    return None


def download_and_install_release(version: str = "", asset_url: str = "", tarball_url: str = "", token: str = "") -> int:
    """Standalone downloader and installer for GitHub releases (used when not running from git)."""
    repo = get_github_repo()
    token = token or get_github_token() or ""

    if not version or version == "Unbekannt" or (not asset_url and not tarball_url):
        try:
            gh_url = f"https://api.github.com/repos/{repo}/releases/latest"
            headers = {"User-Agent": "Truck-Mod-Manager", "Accept": "application/vnd.github+json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(gh_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                if not version or version == "Unbekannt":
                    version = data.get("tag_name", "").lstrip("v").strip()
                if not tarball_url:
                    tarball_url = data.get("tarball_url", "")
                for asset in data.get("assets", []):
                    if asset.get("name", "").endswith((".tar.gz", ".zip")):
                        tarball_url = asset.get("browser_download_url", "")
                        asset_url = asset.get("url", "")
                        break
        except Exception:
            pass

    if not version or version == "Unbekannt":
        version = __version__

    print("=======================================================")
    print("      Truck Mod Manager - GitHub Updater               ")
    print("=======================================================")
    print(f"Ziel-Version : v{version}")
    print(f"Repository   : https://github.com/{repo}")
    print(f"Token aktiv  : {'Ja (hinterlegt)' if token else 'Nein (Öffentlicher Zugriff)'}")
    print("-------------------------------------------------------")

    tmp_dir = tempfile.mkdtemp(prefix="truck_mm_update_")
    archive_path = os.path.join(tmp_dir, f"truck-mod-manager-v{version}.archive")
    unpack_dir = os.path.join(tmp_dir, "unpacked")

    try:
        # Build prioritized list of candidate URLs
        candidates = []
        if token and asset_url:
            candidates.append(("asset_api", asset_url))
        if tarball_url:
            candidates.append(("tarball_url", tarball_url))
        if version:
            v_clean = version.lstrip("v").strip()
            candidates.append(("api_tarball", f"https://api.github.com/repos/{repo}/tarball/v{v_clean}"))
            candidates.append(("api_tarball", f"https://api.github.com/repos/{repo}/tarball/{v_clean}"))
            candidates.append(("tag_archive", f"https://github.com/{repo}/archive/refs/tags/v{v_clean}.tar.gz"))
            candidates.append(("tag_archive", f"https://github.com/{repo}/archive/refs/tags/{v_clean}.tar.gz"))
            candidates.append(("api_zipball", f"https://api.github.com/repos/{repo}/zipball/v{v_clean}"))
            candidates.append(("tag_zip", f"https://github.com/{repo}/archive/refs/tags/v{v_clean}.zip"))
        candidates.append(("api_main", f"https://api.github.com/repos/{repo}/tarball/main"))
        candidates.append(("branch_main", f"https://github.com/{repo}/archive/refs/heads/main.tar.gz"))
        candidates.append(("branch_master", f"https://github.com/{repo}/archive/refs/heads/master.tar.gz"))

        print("[1/4] Lade Release-Paket herunter...")
        curl_bin = shutil.which("curl")
        download_ok = False
        archive_format = "tar"
        seen_urls = set()

        class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
                if new_req and "Authorization" in new_req.headers:
                    # Strip Authorization header when GitHub redirects to AWS S3/CDN
                    del new_req.headers["Authorization"]
                return new_req

        opener = urllib.request.build_opener(NoAuthRedirect)

        for kind, dl_url in candidates:
            if not dl_url or dl_url in seen_urls:
                continue
            seen_urls.add(dl_url)

            if os.path.exists(archive_path):
                try:
                    os.remove(archive_path)
                except Exception:
                    pass

            # Try curl first if available
            if curl_bin:
                curl_cmd = [curl_bin, "-sSL", "-f"]
                if token and ("api.github.com" in dl_url or kind == "asset_api"):
                    curl_cmd.extend(["-H", f"Authorization: Bearer {token}"])
                    if kind == "asset_api":
                        curl_cmd.extend(["-H", "Accept: application/octet-stream"])
                    else:
                        curl_cmd.extend(["-H", "Accept: application/vnd.github+json"])
                curl_cmd.extend([dl_url, "-o", archive_path])
                res = subprocess.run(curl_cmd, capture_output=True, check=False)
                fmt = is_valid_archive(archive_path)
                if res.returncode == 0 and fmt:
                    download_ok = True
                    archive_format = fmt
                    break

            # Fallback to urllib
            headers = {"User-Agent": "Truck-Mod-Manager"}
            if token and ("api.github.com" in dl_url or kind == "asset_api"):
                headers["Authorization"] = f"Bearer {token}"
                if kind == "asset_api":
                    headers["Accept"] = "application/octet-stream"
                else:
                    headers["Accept"] = "application/vnd.github+json"
            try:
                req = urllib.request.Request(dl_url, headers=headers)
                with opener.open(req, timeout=20) as resp, open(archive_path, "wb") as out_f:
                    shutil.copyfileobj(resp, out_f)
                fmt = is_valid_archive(archive_path)
                if fmt:
                    download_ok = True
                    archive_format = fmt
                    break
            except Exception:
                pass

        if not download_ok or not os.path.exists(archive_path):
            print("[FEHLER] Release-Paket konnte nicht heruntergeladen werden.")
            print(f"Repository: https://github.com/{repo}")
            if token:
                print("Hinweis: Bitte prüfen Sie, ob das Repository existiert und Ihr GitHub-Token")
                print(f"Leserechte ('Contents: Read') für '{repo}' besitzt.")
            else:
                print("Hinweis: Bei privaten Repositories muss ein Personal Access Token (PAT) hinterlegt sein.")
            return 1

        size_mb = os.path.getsize(archive_path) / (1024 * 1024)
        print(f"✓ Download erfolgreich ({size_mb:.2f} MB, Format: {archive_format.upper()})")

        print("[2/4] Entpacke Archiv...")
        os.makedirs(unpack_dir, exist_ok=True)
        if archive_format == "zip":
            res_unpack = subprocess.run(["unzip", "-q", archive_path, "-d", unpack_dir], check=False)
        else:
            res_unpack = subprocess.run(["tar", "-xzf", archive_path, "-C", unpack_dir], check=False)

        if res_unpack.returncode != 0:
            print("[FEHLER] Archiv konnte nicht entpackt werden.")
            return 1
        print("✓ Entpacken abgeschlossen.")

        # Find install.sh inside unpacked folder
        installer_path = None
        for root, dirs, files in os.walk(unpack_dir):
            if "install.sh" in files:
                installer_path = os.path.join(root, "install.sh")
                break

        if not installer_path:
            print("[FEHLER] install.sh im entpackten Release-Archiv nicht gefunden.")
            return 1

        print(f"[3/4] Führe Installation aus ({installer_path})...")
        os.chmod(installer_path, 0o755)
        # Determine install mode: use --user if not root
        inst_args = ["bash", installer_path]
        if os.geteuid() != 0:
            inst_args.append("--user")
        res_inst = subprocess.run(inst_args, cwd=os.path.dirname(installer_path), check=False)
        if res_inst.returncode != 0:
            print(f"[FEHLER] Installation schlug fehl mit Exit-Code {res_inst.returncode}")
            return res_inst.returncode

        print("[4/4] Bereinige temporäre Dateien...")
        print(f"✓ Truck Mod Manager wurde erfolgreich auf v{version} aktualisiert!")
        return 0

    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass


if __name__ == "__main__":
    if any(arg in sys.argv for arg in ("--download-and-install", "-h", "--help")):
        import argparse
        parser = argparse.ArgumentParser(description="Truck Mod Manager Standalone Release Installer")
        parser.add_argument("--download-and-install", action="store_true")
        parser.add_argument("--version", default="")
        parser.add_argument("--asset-url", default="")
        parser.add_argument("--tarball-url", default="")
        parser.add_argument("--token", default="")
        args, _ = parser.parse_known_args()
        if args.download_and_install:
            sys.exit(download_and_install_release(args.version, args.asset_url, args.tarball_url, args.token))
