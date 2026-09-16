"""
Steam Workshop mod scanner for Euro Truck Simulator 2 and American Truck Simulator.
Locates subscribed workshop items in steamapps/workshop/content/<appid>/.
"""
from pathlib import Path
from typing import List, Optional

from truck_mod_manager.core.game_scanner import GameScanner
from truck_mod_manager.core.models import GameType, ScsMod
from truck_mod_manager.core.scs_parser import ScsParser


class WorkshopScanner:
    """Scans and parses subscribed Steam Workshop items."""

    @classmethod
    def scan_workshop(cls, game_type: GameType) -> List[ScsMod]:
        """Scans workshop folders for the specified game."""
        info = GameScanner.APP_INFO[game_type]
        appid = info["appid"]
        libraries = GameScanner.get_steam_libraries()
        workshop_mods: List[ScsMod] = []

        for lib in libraries:
            workshop_content = lib / "steamapps" / "workshop" / "content" / appid
            if not workshop_content.exists():
                continue

            for item_dir in workshop_content.iterdir():
                if not item_dir.is_dir():
                    continue

                item_id = item_dir.name

                # Look for .zip or .scs inside
                archive_candidates = list(item_dir.glob("*.zip")) + list(item_dir.glob("*.scs"))

                if archive_candidates:
                    for archive in archive_candidates:
                        mod = ScsParser.parse_mod_file(archive)
                        mod.is_workshop = True
                        mod.workshop_id = item_id
                        if mod.display_name == archive.stem:
                            mod.display_name = f"Workshop Mod #{item_id}"
                        workshop_mods.append(mod)
                else:
                    # Treat directory itself as mod
                    mod = ScsParser.parse_mod_file(item_dir)
                    mod.is_workshop = True
                    mod.workshop_id = item_id
                    if mod.display_name == item_dir.name:
                        mod.display_name = f"Workshop Mod #{item_id}"
                    workshop_mods.append(mod)

        return workshop_mods
