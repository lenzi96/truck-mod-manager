"""
Data models for Truck Mod Manager (ETS2 & ATS).
"""
import fnmatch
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class GameType(str, Enum):
    ETS2 = "ets2"
    ATS = "ats"


class ModCategory(str, Enum):
    MAP = "map"
    MODELS = "models"
    PREFABS = "prefabs"
    DEF = "def"
    TRUCK = "truck"
    TRAILER = "trailer"
    TUNING = "tuning"
    INTERIOR = "interior"
    SOUND = "sound"
    PHYSICS = "physics"
    AI_TRAFFIC = "ai_traffic"
    PAINT_JOB = "paint_job"
    CARGO = "cargo"
    GRAPHICS = "graphics"
    WEATHER = "weather"
    UI = "ui"
    OTHER = "other"


# Community-recommended load order ranking (higher number = loaded higher = higher priority in SCS)
# In SCS Mod Manager, top of the list has highest priority and overrides bottom of list.
LOAD_ORDER_PRIORITY: Dict[ModCategory, int] = {
    ModCategory.UI: 140,
    ModCategory.PHYSICS: 130,
    ModCategory.WEATHER: 120,
    ModCategory.GRAPHICS: 110,
    ModCategory.SOUND: 100,
    ModCategory.AI_TRAFFIC: 90,
    ModCategory.PAINT_JOB: 80,
    ModCategory.TUNING: 70,
    ModCategory.INTERIOR: 65,
    ModCategory.TRUCK: 60,
    ModCategory.TRAILER: 50,
    ModCategory.CARGO: 40,
    ModCategory.DEF: 30,          # Map road connections / Map Def
    ModCategory.MAP: 20,          # Map files
    ModCategory.PREFABS: 15,      # Map Prefabs
    ModCategory.MODELS: 10,       # Map Models / Assets
    ModCategory.OTHER: 5,
}


@dataclass
class TruckGame:
    game_type: GameType
    name: str
    steam_appid: str
    install_dir: Optional[str] = None
    user_dir: Optional[str] = None         # e.g. ~/.local/share/Euro Truck Simulator 2/
    mod_dir: Optional[str] = None          # e.g. ~/.local/share/Euro Truck Simulator 2/mod/
    proton_prefix: Optional[str] = None    # e.g. steamapps/compatdata/227300/pfx
    is_proton: bool = False
    custom_launch_args: str = ""
    is_installed: bool = False
    detected_game_version: Optional[str] = None

    @property
    def log_path(self) -> Optional[Path]:
        if not self.user_dir:
            return None
        return Path(self.user_dir) / "game.log.txt"

    @property
    def crash_path(self) -> Optional[Path]:
        if not self.user_dir:
            return None
        return Path(self.user_dir) / "game.crash.txt"

    @property
    def config_path(self) -> Optional[Path]:
        if not self.user_dir:
            return None
        return Path(self.user_dir) / "config.cfg"

    @property
    def plugins_dir(self) -> Optional[Path]:
        if not self.install_dir:
            return None
        install = Path(self.install_dir)
        if self.is_proton:
            return install / "bin" / "win_x64" / "plugins"
        return install / "bin" / "linux_x64" / "plugins"


@dataclass
class ScsMod:
    file_path: str                         # Full path to .scs, .zip, or folder
    file_name: str                         # Basename
    display_name: str                      # From manifest.sii or fallback
    package_version: str = "1.0"
    author: str = "Unknown"
    categories: List[ModCategory] = field(default_factory=lambda: [ModCategory.OTHER])
    icon_path: Optional[str] = None        # Extracted thumbnail path
    description: str = ""
    mp_mod_optional: bool = False
    is_enabled: bool = False
    priority: int = 0                      # 1 is highest priority
    file_size: int = 0
    internal_files: List[str] = field(default_factory=list)
    has_manifest: bool = False
    compatible_versions: List[str] = field(default_factory=list)
    is_workshop: bool = False
    workshop_id: Optional[str] = None

    @property
    def primary_category(self) -> ModCategory:
        if self.categories:
            return self.categories[0]
        return ModCategory.OTHER

    def check_compatibility(self, game_version: Optional[str]) -> Tuple[Optional[bool], str]:
        """
        Checks if this mod is compatible with the detected game_version.
        Returns:
            (True, msg): Explicitly compatible
            (False, msg): Incompatible version mismatch
            (None, msg): No version restriction defined (Universal) or game version unknown
        """
        if not self.compatible_versions:
            return None, "Universell (Keine Einschränkung im Manifest)"

        if not game_version or game_version.lower() in ("unbekannt", "unknown", ""):
            return None, f"Erfordert {', '.join(self.compatible_versions)} (Spielversion unbekannt)"

        clean_game_ver = game_version.rstrip("s").strip()

        for pattern in self.compatible_versions:
            pat = pattern.strip()
            # 1. Exact or wildcard match on original version e.g. 1.50.* matches 1.50.2.3s
            if fnmatch.fnmatch(game_version, pat):
                return True, f"Kompatibel mit v{game_version} ({pat})"
            # 2. Match on stripped version e.g. 1.50.* matches 1.50.2.3
            if fnmatch.fnmatch(clean_game_ver, pat):
                return True, f"Kompatibel mit v{game_version} ({pat})"
            # 3. Starts-with check e.g. pat '1.50' matches '1.50.2.3'
            if clean_game_ver.startswith(pat):
                return True, f"Kompatibel mit v{game_version} ({pat})"
            # 4. Try wildcard expansion if not present
            if not pat.endswith("*"):
                if fnmatch.fnmatch(clean_game_ver, pat + "*") or fnmatch.fnmatch(clean_game_ver, pat + ".*"):
                    return True, f"Kompatibel mit v{game_version} ({pat})"

        return False, f"Inkompatibel! Erfordert {', '.join(self.compatible_versions)}, installiert ist v{game_version}"


@dataclass
class ConflictFile:
    relative_path: str
    mod_files: List[str] = field(default_factory=list)     # File names of mods containing this file
    winning_mod: Optional[str] = None                      # Mod with highest priority


@dataclass
class ModPreset:
    name: str
    game_type: GameType
    description: str = ""
    mod_order: List[str] = field(default_factory=list)     # Ordered list of mod filenames / IDs
    created_at: str = ""


@dataclass
class LogIssue:
    level: str                             # "ERROR", "WARNING", "CRITICAL"
    subsystem: str                         # e.g. "sound", "unit", "model", "fs", "dx11"
    message: str
    line_number: int
    suggestion: str = ""
