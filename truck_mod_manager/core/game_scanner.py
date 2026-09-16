"""
Game Scanner for Euro Truck Simulator 2 and American Truck Simulator.
Detects Steam installations, Native Linux binaries, and Proton Wine prefixes.
"""
import os
import re
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

        is_installed = bool(install_path and install_path.exists())

        # 5. Detect Game Version from game.log.txt or config override
        detected_version = game_cfg.get("game_version_override", "").strip()
        if not detected_version and user_path:
            log_p = user_path / "game.log.txt"
            if log_p.exists():
                try:
                    with open(log_p, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f):
                            if idx > 35:
                                break
                            if "init ver." in line:
                                m = re.search(r"init ver\.([0-9\.\w]+)", line)
                                if m:
                                    detected_version = m.group(1)
                                    break
                except Exception as e:
                    print(f"[GameScanner] Error reading version from log: {e}")

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
