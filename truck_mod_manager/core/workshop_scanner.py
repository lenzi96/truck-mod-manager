"""
Steam Workshop mod scanner for Euro Truck Simulator 2 and American Truck Simulator.
Locates subscribed workshop items in steamapps/workshop/content/<appid>/.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from truck_mod_manager.core.game_scanner import GameScanner
from truck_mod_manager.core.models import GameType, ScsMod
from truck_mod_manager.core.scs_parser import ScsParser


class WorkshopScanner:
    """Scans and parses subscribed Steam Workshop items."""

    @classmethod
    def get_workshop_title_cache(cls, game_type: GameType) -> Dict[str, str]:
        """
        Extracts human-readable workshop item titles cached in local profile.sii files.
        Maps decimal workshop_id -> title.
        """
        titles: Dict[str, str] = {}
        try:
            from truck_mod_manager.core.profile_manager import read_sii_active_mods
            game = GameScanner.find_game(game_type)
            if game and game.user_dir:
                user_dir = Path(game.user_dir)
                for sub in ("profiles", "steam_profiles"):
                    p_dir = user_dir / sub
                    if not p_dir.is_dir():
                        continue
                    for entry in p_dir.iterdir():
                        if not entry.is_dir() or entry.name.endswith(".bak") or entry.name.startswith("."):
                            continue
                        sii = entry / "profile.sii"
                        if sii.is_file():
                            for pkg, name in read_sii_active_mods(sii):
                                if name and pkg.startswith("mod_workshop_package."):
                                    hex_id = pkg.split(".")[-1]
                                    try:
                                        dec_id = str(int(hex_id, 16))
                                        titles[dec_id] = name
                                    except ValueError:
                                        pass
        except Exception:
            pass
        return titles

    @classmethod
    def _find_best_mod_candidate(cls, item_dir: Path) -> Optional[ScsMod]:
        """
        Finds and parses the best mod content inside a workshop item directory.
        Checks versions.sii, universal/latest folders, zip/scs archives.
        """
        item_id = item_dir.name
        zips = list(item_dir.glob("*.zip")) + list(item_dir.glob("*.scs"))

        preferred_names = []
        vf = item_dir / "versions.sii"
        if vf.exists():
            try:
                content = vf.read_text(encoding="utf-8", errors="ignore")
                pkgs = re.findall(r'package_name:\s*\"([^\"]+)\"', content)
                for p in pkgs:
                    p_clean = p.strip()
                    if p_clean.lower() in ("universal", "latest") or "content" in p_clean.lower() or not preferred_names:
                        preferred_names.append(p_clean)
            except Exception:
                pass

        candidates: List[Path] = []

        # 1. Preferred names from versions.sii
        for pref in preferred_names:
            for ext in ("", ".zip", ".scs"):
                cand = item_dir / f"{pref}{ext}"
                if cand.exists() and cand not in candidates:
                    candidates.append(cand)

        # 2. Universal / Latest candidates
        for name in ("universal", "latest"):
            for ext in ("", ".zip", ".scs"):
                cand = item_dir / f"{name}{ext}"
                if cand.exists() and cand not in candidates:
                    candidates.append(cand)

        # 3. Any other archive files
        for z in zips:
            if z not in candidates:
                candidates.append(z)

        # 4. Any other subdirectories
        for d in item_dir.iterdir():
            if d.is_dir() and d not in candidates and d.name.lower() not in ("info", "compatibility_info", "incompatible"):
                candidates.append(d)

        if not candidates:
            candidates = [item_dir]

        best_mod: Optional[ScsMod] = None
        for cand in candidates:
            mod = ScsParser.parse_mod_file(cand)
            if mod.has_manifest:
                best_mod = mod
                break
            if best_mod is None:
                best_mod = mod

        if best_mod is None:
            return None

        # Look for icon if not found
        if not best_mod.icon_path:
            icon_candidates = (
                list(item_dir.glob("*icon*.png")) +
                list(item_dir.glob("*icon*.jpg")) +
                list(item_dir.glob("logo.jpg")) +
                list(item_dir.glob("logo.png")) +
                list(item_dir.glob("**/*icon*.png")) +
                list(item_dir.glob("**/*icon*.jpg"))
            )
            if icon_candidates:
                best_mod.icon_path = str(icon_candidates[0].resolve())

        return best_mod

    @classmethod
    def scan_workshop(cls, game_type: GameType) -> List[ScsMod]:
        """Scans workshop folders for the specified game."""
        info = GameScanner.APP_INFO.get(game_type)
        if not info:
            return []
        appid = info["appid"]
        libraries = GameScanner.get_steam_libraries()
        workshop_mods: List[ScsMod] = []
        seen_ids: Set[str] = set()

        title_cache = cls.get_workshop_title_cache(game_type)

        generic_names = {
            "universal", "latest", "compatibility info", "compatibility_info",
            "info", "157", "158", "159", "160"
        }

        for lib in libraries:
            workshop_content = lib / "steamapps" / "workshop" / "content" / appid
            if not workshop_content.exists():
                continue

            for item_dir in workshop_content.iterdir():
                if not item_dir.is_dir():
                    continue

                item_id = item_dir.name
                if item_id in seen_ids:
                    continue

                mod = cls._find_best_mod_candidate(item_dir)
                if not mod:
                    continue

                seen_ids.add(item_id)
                mod.is_workshop = True
                mod.workshop_id = item_id

                try:
                    mod.file_name = f"mod_workshop_package.{int(item_id):016X}"
                except ValueError:
                    mod.file_name = f"mod_workshop_package.{item_id}"

                # Improve display name using cached profile titles or cleaning
                current_name = mod.display_name.strip()
                if item_id in title_cache:
                    mod.display_name = title_cache[item_id]
                elif (
                    not current_name
                    or current_name.lower() in generic_names
                    or "content" in current_name.lower()
                    or current_name.startswith("Workshop Mod #")
                    or current_name == item_dir.name
                ):
                    mod.display_name = f"Workshop Mod #{item_id}"

                workshop_mods.append(mod)

        workshop_mods.sort(key=lambda m: m.display_name.lower())
        return workshop_mods
