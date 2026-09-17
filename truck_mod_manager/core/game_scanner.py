"""
Game Scanner for Euro Truck Simulator 2 and American Truck Simulator.
Detects Steam installations, Native Linux binaries, and Proton Wine prefixes.
"""
import os
import re
import struct
from pathlib import Path
from typing import Dict, List, Optional

from truck_mod_manager.core.config import config
from truck_mod_manager.core.models import GameType, TruckGame


COMMON_STEAM_ROOTS = [
    Path(os.path.expanduser("~/.local/share/Steam")),
    Path(os.path.expanduser("~/.steam/root")),
    Path(os.path.expanduser("~/.steam/steam")),
    Path(os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam")),  # Flatpak
]


class GameScanner:
    """Scans for ETS2 and ATS installations and data directories."""

    APP_INFO: Dict[GameType, Dict[str, str]] = {
        GameType.ETS2: {
            "name": "Euro Truck Simulator 2",
            "appid": "227300",
            "dir_name": "Euro Truck Simulator 2",
            "native_exe": "bin/linux_x64/eurotrucks2",
            "win_exe": "bin/win_x64/eurotrucks2.exe",
        },
        GameType.ATS: {
            "name": "American Truck Simulator",
            "appid": "270880",
            "dir_name": "American Truck Simulator",
            "native_exe": "bin/linux_x64/amtrucks",
            "win_exe": "bin/win_x64/amtrucks.exe",
        },
    }

    @staticmethod
    def parse_vdf(text: str) -> dict:
        """Simple tokenizer for Valve VDF format."""
        lines = [l.split("//")[0].strip() for l in text.splitlines()]
        clean = "\n".join([l for l in lines if l])
        tokens = re.findall(r'"([^"]*)"|(\{)|(\})', clean)
        token_list = []
        for s, o, c in tokens:
            if s:
                token_list.append(s)
            elif o:
                token_list.append("{")
            elif c:
                token_list.append("}")

        idx = 0

        def parse():
            nonlocal idx
            res = {}
            while idx < len(token_list):
                token = token_list[idx]
                if token == "}":
                    idx += 1
                    return res
                idx += 1
                if idx >= len(token_list):
                    break
                next_t = token_list[idx]
                if next_t == "{":
                    idx += 1
                    res[token] = parse()
                else:
                    res[token] = next_t
                    idx += 1
            return res

        return parse()

    @classmethod
    def get_steam_libraries(cls) -> List[Path]:
        """Finds all Steam library folders."""
        libs = set()

        search_roots = list(COMMON_STEAM_ROOTS)
        extra = config.get("extra_steam_paths", [])
        for p in extra:
            if p:
                search_roots.append(Path(p))

        for root in search_roots:
            if not root.exists():
                continue

            vdfs = [
                root / "steamapps" / "libraryfolders.vdf",
                root / "config" / "libraryfolders.vdf",
            ]
            for vdf in vdfs:
                if vdf.exists():
                    try:
                        content = vdf.read_text(encoding="utf-8", errors="ignore")
                        data = cls.parse_vdf(content)
                        root_dict = data.get("libraryfolders", data)
                        for _, folder_info in root_dict.items():
                            if isinstance(folder_info, dict) and "path" in folder_info:
                                lib_path = Path(folder_info["path"])
                                if lib_path.exists():
                                    libs.add(lib_path)
                    except Exception as e:
                        print(f"[GameScanner] Failed parsing {vdf}: {e}")

            if (root / "steamapps" / "common").exists():
                libs.add(root)

        return sorted(list(libs))

    @staticmethod
    def _extract_pe_version(exe_path: Path) -> Optional[str]:
        """Extracts FileVersion/ProductVersion from a Windows PE executable header or string table."""
        if not exe_path.is_file():
            return None
        try:
            with open(exe_path, "rb") as f:
                data = f.read(128 * 1024 * 1024)
            sig = b"\xbd\x04\xef\xfe"  # VS_FIXEDFILEINFO magic (0xFEEF04BD)
            idx = 0
            while True:
                pos = data.find(sig, idx)
                if pos == -1:
                    break
                if len(data) >= pos + 52:
                    unp = struct.unpack("<IIIIIIIIIIIII", data[pos:pos + 52])
                    magic, struc_ver, f_ms, f_ls = unp[0], unp[1], unp[2], unp[3]
                    # Microsoft specification: magic == 0xFEEF04BD and struc_ver == 0x00010000
                    if magic == 0xFEEF04BD and struc_ver == 0x00010000:
                        f_major = f_ms >> 16
                        f_minor = f_ms & 0xFFFF
                        f_build = f_ls >> 16
                        f_rev = f_ls & 0xFFFF
                        if 1 <= f_major <= 10:
                            if f_rev > 0:
                                return f"{f_major}.{f_minor}.{f_build}.{f_rev}"
                            elif f_build > 0:
                                return f"{f_major}.{f_minor}.{f_build}"
                            else:
                                return f"{f_major}.{f_minor}"
                idx = pos + 4

            # Fallback regex search on binary bytes
            m = re.search(rb"init ver\.?\s*([1-9]\.[0-9]+(?:\.[0-9]+)*[a-z]?)", data)
            if m:
                return m.group(1).decode("ascii", errors="ignore").strip()
        except Exception as e:
            print(f"[GameScanner] Error extracting PE version from {exe_path}: {e}")
        return None

    @staticmethod
    def _extract_elf_version(bin_path: Path) -> Optional[str]:
        """Extracts version string from a Linux ELF binary."""
        if not bin_path.is_file():
            return None
        try:
            with open(bin_path, "rb") as f:
                data = f.read(128 * 1024 * 1024)
            m = re.search(rb"init ver\.?\s*([1-9]\.[0-9]+(?:\.[0-9]+)*[a-z]?)", data)
            if m:
                return m.group(1).decode("ascii", errors="ignore").strip()
            m2 = re.search(rb"(?:Euro Truck Simulator 2|American Truck Simulator)\s+v?([1-9]\.[0-9]+(?:\.[0-9]+)*[a-z]?)", data)
            if m2:
                return m2.group(1).decode("ascii", errors="ignore").strip()
        except Exception as e:
            print(f"[GameScanner] Error extracting ELF version from {bin_path}: {e}")
        return None

    @classmethod
    def detect_version_from_binaries(cls, install_path: Path, game_type: GameType) -> Optional[str]:
        """Checks executable binaries in the game install directory for version info."""
        if not install_path or not install_path.exists():
            return None

        is_ets2 = (game_type == GameType.ETS2)
        candidates = [
            install_path / "bin" / "win_x64" / ("eurotrucks2.exe" if is_ets2 else "amtrucks.exe"),
            install_path / "bin" / "linux_x64" / ("eurotrucks2" if is_ets2 else "amtrucks"),
            install_path / "bin" / "win_x86" / ("eurotrucks2.exe" if is_ets2 else "amtrucks.exe"),
            install_path / "bin" / "linux_x86" / ("eurotrucks2" if is_ets2 else "amtrucks"),
        ]

        for exe in candidates:
            if not exe.is_file():
                continue
            if exe.suffix.lower() == ".exe":
                ver = cls._extract_pe_version(exe)
                if ver:
                    return ver
            else:
                ver = cls._extract_elf_version(exe)
                if ver:
                    return ver
        return None

    @classmethod
    def detect_version_from_logs(cls, candidate_dirs: List[Path]) -> Optional[str]:
        """Scans candidate directories for game.log.txt or game.log.bak.txt and extracts version."""
        for cdir in candidate_dirs:
            if not cdir or not cdir.exists():
                continue
            for log_name in ("game.log.txt", "game.log.bak.txt"):
                log_file = cdir / log_name
                if not log_file.is_file():
                    continue
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f):
                            if idx > 1000:
                                break
                            m = re.search(r"init ver\.?\s*([1-9]\.[0-9]+(?:\.[0-9]+)*\w*)", line, re.IGNORECASE)
                            if m:
                                return m.group(1).strip()
                            m2 = re.search(r"(?:Euro Truck Simulator 2|American Truck Simulator)\s+init\s+ver\.?\s*([1-9]\.[0-9]+(?:\.[0-9]+)*\w*)", line, re.IGNORECASE)
                            if m2:
                                return m2.group(1).strip()
                            m3 = re.search(r"\[sys\]\s+(?:game\s+)?version[:\s]+([1-9]\.[0-9]+(?:\.[0-9]+)*\w*)", line, re.IGNORECASE)
                            if m3:
                                return m3.group(1).strip()
                            m4 = re.search(r"\[ufs\]\s+Loaded pack set version\s+([1-9]\.[0-9]+(?:\.[0-9]+)*\w*)", line, re.IGNORECASE)
                            if m4:
                                return m4.group(1).strip()
                except Exception as e:
                    print(f"[GameScanner] Error reading version from {log_file}: {e}")
        return None

    @classmethod
    def find_game(cls, game_type: GameType) -> TruckGame:
        """Locates game install dir, user data directory, and mod folder."""
        info = cls.APP_INFO[game_type]
        game_cfg = config.get_game_config(game_type.value)

        # 1. Check custom overrides first
        custom_install = game_cfg.get("custom_install_dir", "").strip()
        custom_user = game_cfg.get("custom_user_dir", "").strip()
        custom_mod = game_cfg.get("custom_mod_dir", "").strip()
        is_proton_pref = game_cfg.get("is_proton", False)

        install_path: Optional[Path] = Path(custom_install) if custom_install else None
        user_path: Optional[Path] = Path(custom_user) if custom_user else None
        mod_path: Optional[Path] = Path(custom_mod) if custom_mod else None
        proton_pfx: Optional[Path] = None

        # 2. If not manually set, scan Steam libraries
        libraries = cls.get_steam_libraries()
        appid = info["appid"]

        if not install_path or not install_path.exists():
            for lib in libraries:
                steamapps = lib / "steamapps"
                # Check appmanifest
                acf = steamapps / f"appmanifest_{appid}.acf"
                if acf.exists():
                    try:
                        acf_data = cls.parse_vdf(acf.read_text(encoding="utf-8", errors="ignore"))
                        app_state = acf_data.get("AppState", acf_data)
                        installdir = app_state.get("installdir", info["dir_name"])
                        candidate = steamapps / "common" / installdir
                        if candidate.exists():
                            install_path = candidate
                            break
                    except Exception:
                        pass

                # Fallback: check common directly
                candidate2 = steamapps / "common" / info["dir_name"]
                if candidate2.exists():
                    install_path = candidate2
                    break

        # Check Proton prefix
        for lib in libraries:
            pfx = lib / "steamapps" / "compatdata" / appid / "pfx"
            if pfx.exists():
                proton_pfx = pfx
                break

        # 3. Detect User Directory (~/.local/share/... for native, or Wine pfx Documents)
        if not user_path or not user_path.exists():
            native_user = Path(os.path.expanduser(f"~/.local/share/{info['dir_name']}"))
            proton_user = None
            if proton_pfx:
                proton_user = proton_pfx / "drive_c" / "users" / "steamuser" / "Documents" / info["dir_name"]

            if is_proton_pref and proton_user and proton_user.exists():
                user_path = proton_user
            elif native_user.exists():
                user_path = native_user
            elif proton_user and proton_user.exists():
                user_path = proton_user
                is_proton_pref = True
            else:
                # Default to native path even if not created yet
                user_path = native_user

        # 4. Mod directory
        if not mod_path or not mod_path.exists():
            if user_path:
                mod_path = user_path / "mod"

        # Check if actual game binaries or archives exist (avoid false positive on empty folders)
        is_installed = False
        if install_path and install_path.exists():
            is_installed = any(
                (install_path / sub).exists()
                for sub in ("bin", "base.scs", "def.scs", "core.scs")
            )

        # Collect candidate directories for log searching
        candidate_user_dirs: List[Path] = []
        if user_path:
            candidate_user_dirs.append(user_path)
        if proton_pfx:
            candidate_user_dirs.append(proton_pfx / "drive_c" / "users" / "steamuser" / "Documents" / info["dir_name"])
            candidate_user_dirs.append(proton_pfx / "drive_c" / "users" / "steamuser" / "My Documents" / info["dir_name"])

        # Native Linux and Flatpak standard paths
        candidate_user_dirs.append(Path(os.path.expanduser(f"~/.local/share/{info['dir_name']}")))
        candidate_user_dirs.append(Path(os.path.expanduser(f"~/.var/app/com.valvesoftware.Steam/.local/share/{info['dir_name']}")))
        candidate_user_dirs.append(Path(os.path.expanduser(f"~/Documents/{info['dir_name']}")))

        # Check compatdata in all Steam libraries
        for lib in libraries:
            pfx_c = lib / "steamapps" / "compatdata" / appid / "pfx"
            if pfx_c.exists():
                candidate_user_dirs.append(pfx_c / "drive_c" / "users" / "steamuser" / "Documents" / info["dir_name"])

        # 5. Detect Game Version (Multi-Tier)
        # Tier 1: User override in settings
        detected_version = game_cfg.get("game_version_override", "").strip()

        # Tier 2: Scan game.log.txt across candidate locations (most accurate, includes live build & revision)
        if not detected_version:
            detected_version = cls.detect_version_from_logs(candidate_user_dirs) or ""

        # Tier 3: Directly inspect game executable binaries (fallback if game was never run yet)
        if not detected_version and install_path:
            detected_version = cls.detect_version_from_binaries(install_path, game_type) or ""

        return TruckGame(
            game_type=game_type,
            name=info["name"],
            steam_appid=appid,
            install_dir=str(install_path) if install_path else None,
            user_dir=str(user_path) if user_path else None,
            mod_dir=str(mod_path) if mod_path else None,
            proton_prefix=str(proton_pfx) if proton_pfx else None,
            is_proton=is_proton_pref,
            custom_launch_args=game_cfg.get("launch_args", "-nointro -mm_pool_size 4096"),
            is_installed=is_installed,
            detected_game_version=detected_version or None,
        )

    @classmethod
    def scan_all(cls) -> Dict[GameType, TruckGame]:
        """Scans both ETS2 and ATS."""
        return {
            GameType.ETS2: cls.find_game(GameType.ETS2),
            GameType.ATS: cls.find_game(GameType.ATS),
        }
