"""
ProMods Manager for ETS2 and ATS.
Detects ProMods packages (Europe, Middle East, The Great Steppe, TCP, Canada),
validates package integrity (missing files), and creates/applies the official load order.
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from truck_mod_manager.core.models import GameType, ScsMod


class ProModsPackType(str, Enum):
    EUROPE = "europe"
    MIDDLE_EAST = "middle_east"
    GREAT_STEPPE = "great_steppe"
    TCP = "tcp"
    CANADA = "canada"


@dataclass
class ProModsComponent:
    role: str
    name: str
    pattern: str  # Regex pattern to match filename
    priority_order: int  # Lower number = higher priority in load order (top of mod manager)
    is_optional: bool = False
    found_mod: Optional[ScsMod] = None


@dataclass
class ProModsPackStatus:
    pack_type: ProModsPackType
    title: str
    game_type: GameType
    components: List[ProModsComponent] = field(default_factory=list)
    version: Optional[str] = None

    @property
    def total_required(self) -> int:
        return sum(1 for c in self.components if not c.is_optional)

    @property
    def total_found(self) -> int:
        return sum(1 for c in self.components if c.found_mod is not None)

    @property
    def is_complete(self) -> bool:
        required_missing = [c for c in self.components if not c.is_optional and c.found_mod is None]
        return len(required_missing) == 0 and self.total_found > 0

    @property
    def is_installed(self) -> bool:
        return self.total_found > 0

    @property
    def missing_names(self) -> List[str]:
        return [c.name for c in self.components if not c.is_optional and c.found_mod is None]


def _build_ets2_definitions() -> Dict[ProModsPackType, List[Tuple[str, str, str, int, bool]]]:
    """
    Returns definitions: (role, name, regex, priority_order, is_optional)
    Priority order: 1 = Topmost priority in Map/Mod load order
    """
    return {
        # Trailer & Company Pack (TCP)
        ProModsPackType.TCP: [
            ("tcp_def_trailers", "ProMods TCP Trailers Def", r"promods[-_]tcp[-_]def[-_]trailers.*\.scs$", 10, False),
            ("tcp_trailers", "ProMods TCP Trailers", r"promods[-_]tcp[-_]trailers.*\.scs$", 11, False),
            ("tcp_def_companies", "ProMods TCP Companies Def", r"promods[-_]tcp[-_]def[-_]companies.*\.scs$", 12, False),
            ("tcp_companies", "ProMods TCP Companies", r"promods[-_]tcp[-_]companies.*\.scs$", 13, False),
        ],
        # Middle East Add-On
        ProModsPackType.MIDDLE_EAST: [
            ("me_def", "ProMods Middle East Def/Map", r"promods[-_]me[-_]def.*\.scs$", 20, False),
            ("me_assets", "ProMods Middle East Assets", r"promods[-_]me[-_]assets.*\.scs$", 21, False),
        ],
        # The Great Steppe
        ProModsPackType.GREAT_STEPPE: [
            ("tgs_def", "ProMods The Great Steppe Def", r"promods[-_]tgs[-_]def.*\.scs$", 30, False),
            ("tgs_map", "ProMods The Great Steppe Map", r"promods[-_]tgs[-_]map.*\.scs$", 31, False),
            ("tgs_assets", "ProMods The Great Steppe Assets", r"promods[-_]tgs[-_]assets.*\.scs$", 32, False),
        ],
        # Europe (The core 7-pack)
        ProModsPackType.EUROPE: [
            ("def", "ProMods Europe Definition", r"promods[-_]def(?:[-_]st|[-_]ip)?[-_]v[0-9.]+\.scs$", 40, False),
            ("map", "ProMods Europe Map", r"promods[-_]map[-_]v[0-9.]+\.scs$", 41, False),
            ("model3", "ProMods Europe Models 3", r"promods[-_]model(?:s)?3[-_]v[0-9.]+\.scs$", 42, False),
            ("model2", "ProMods Europe Models 2", r"promods[-_]model(?:s)?2[-_]v[0-9.]+\.scs$", 43, False),
            ("model1", "ProMods Europe Models 1", r"promods[-_]model(?:s)?1[-_]v[0-9.]+\.scs$", 44, False),
            ("media", "ProMods Europe Media", r"promods[-_]media[-_]v[0-9.]+\.scs$", 45, False),
            ("assets", "ProMods Europe Assets", r"promods[-_]assets[-_]v[0-9.]+\.scs$", 46, False),
        ],
    }


def _build_ats_definitions() -> Dict[ProModsPackType, List[Tuple[str, str, str, int, bool]]]:
    return {
        # ProMods Canada for ATS
        ProModsPackType.CANADA: [
            ("canada_def", "ProMods Canada Definition", r"promods[-_]ats[-_]def.*\.scs$", 10, False),
            ("canada_map", "ProMods Canada Map", r"promods[-_]ats[-_]map.*\.scs$", 11, False),
            ("canada_models", "ProMods Canada Models", r"promods[-_]ats[-_]models.*\.scs$", 12, False),
            ("canada_assets", "ProMods Canada Assets", r"promods[-_]ats[-_]assets.*\.scs$", 13, False),
        ]
    }


class ProModsManager:
    DEF_GENERATOR_URL = "https://promods.net/setup.php"
    PROMODS_SITE_URL = "https://promods.net"

    @classmethod
    def scan_promods(cls, mods: List[ScsMod], game_type: GameType) -> List[ProModsPackStatus]:
        """Scans the given mods list and returns the status of all ProMods packages for this game."""
        definitions = _build_ets2_definitions() if game_type == GameType.ETS2 else _build_ats_definitions()
        results: List[ProModsPackStatus] = []

        # Titles for packs
        titles = {
            ProModsPackType.EUROPE: "ProMods Europe",
            ProModsPackType.MIDDLE_EAST: "ProMods Middle East Add-on",
            ProModsPackType.GREAT_STEPPE: "ProMods The Great Steppe Add-on",
            ProModsPackType.TCP: "ProMods Trailer & Company Pack (TCP)",
            ProModsPackType.CANADA: "ProMods Canada",
        }

        for pack_type, comp_defs in definitions.items():
            components: List[ProModsComponent] = []
            detected_version: Optional[str] = None

            for role, name, pattern, order, opt in comp_defs:
                regex = re.compile(pattern, re.IGNORECASE)
                comp = ProModsComponent(role=role, name=name, pattern=pattern, priority_order=order, is_optional=opt)

                for mod in mods:
                    filename = mod.file_name.lower() if mod.file_name else Path(mod.file_path).name.lower()
                    if regex.search(filename):
                        comp.found_mod = mod
                        # Try to extract version from filename (e.g. v270 -> 2.70 or v2.70)
                        if not detected_version:
                            v_match = re.search(r'v([0-9]+(?:\.[0-9]+)?)', filename)
                            if v_match:
                                raw_v = v_match.group(1)
                                if len(raw_v) == 3 and "." not in raw_v:
                                    detected_version = f"{raw_v[0]}.{raw_v[1:]}"
                                else:
                                    detected_version = raw_v
                        break

                components.append(comp)

            status = ProModsPackStatus(
                pack_type=pack_type,
                title=titles.get(pack_type, pack_type.value),
                game_type=game_type,
                components=components,
                version=detected_version,
            )
            results.append(status)

        return results

    @classmethod
    def get_promods_load_order(cls, mods: List[ScsMod], game_type: GameType) -> List[ScsMod]:
        """
        Returns only the ProMods mods found in `mods`, sorted in the exact official load order:
        Index 0 will be the highest priority (top of Mod Manager).
        """
        statuses = cls.scan_promods(mods, game_type)
        promods_mods_with_order: List[Tuple[int, ScsMod]] = []

        for st in statuses:
            for c in st.components:
                if c.found_mod:
                    promods_mods_with_order.append((c.priority_order, c.found_mod))

        # Sort by priority_order ascending (1 is top priority, 2 is next, etc.)
        promods_mods_with_order.sort(key=lambda x: x[0])
        return [m for _, m in promods_mods_with_order]

    @classmethod
    def apply_promods_order(cls, all_mods: List[ScsMod], game_type: GameType) -> List[ScsMod]:
        """
        Reorders all_mods so that ProMods files follow the official priority hierarchy,
        while maintaining proper SCS community placement relative to other mods.
        Returns the reordered list.
        """
        promods_ordered = cls.get_promods_load_order(all_mods, game_type)
        promods_paths = {str(m.file_path) for m in promods_ordered}

        if not promods_ordered:
            return all_mods

        top_mods: List[ScsMod] = []
        road_connectors: List[ScsMod] = []
        bottom_map_mods: List[ScsMod] = []

        for m in all_mods:
            if str(m.file_path) in promods_paths:
                continue

            fname = m.file_name.lower() if m.file_name else Path(m.file_path).name.lower()
            dname = m.display_name.lower() if m.display_name else ""
            cats = [c.value.lower() if hasattr(c, 'value') else str(c).lower() for c in m.categories]

            # Check if road connector / fix
            if any(k in fname or k in dname for k in ["connector", "rc", "fix", "hybrid", "connection"]):
                road_connectors.append(m)
            # Check if background map
            elif any(k in fname or k in dname for k in ["background", "crash fix", "zoomed map"]):
                top_mods.append(m)
            # Map mods that go below ProMods assets (e.g. other map bases like Southern Region / RusMap Models)
            elif "map" in cats and not any(k in cats for k in ["truck", "sound", "physics", "ui"]):
                bottom_map_mods.append(m)
            else:
                top_mods.append(m)

        # Final ordered sequence:
        # Top non-map mods -> Road connectors -> ProMods in order -> Other map bases / lower mods
        new_order: List[ScsMod] = []
        new_order.extend(top_mods)
        new_order.extend(road_connectors)
        new_order.extend(promods_ordered)
        new_order.extend(bottom_map_mods)

        # Re-assign priority (1 = highest priority, 2 = next...)
        for idx, mod in enumerate(new_order, start=1):
            mod.priority = idx

        return new_order

    @classmethod
    def get_map_combo_guidelines(cls) -> List[Dict[str, str]]:
        """Provides community-approved load order guidelines for major map combos."""
        return [
            {
                "tier": "1. UI & Background Maps",
                "desc": "Karten-Hintergründe, World Maps, Vollbild-Map-Fixes, Crash-Fixes",
                "examples": "ProMods High Quality Background Map, Zoom Crash Fix",
            },
            {
                "tier": "2. Straßenverbindungen (Road Connections)",
                "desc": "Verbindungen zwischen Karten müssen ÜBER den beteiligten Karten stehen!",
                "examples": "ProMods + RusMap Connector, ProMods + RoEx Connector, Poland Rebuilding Fix",
            },
            {
                "tier": "3. ProMods Trailer & Company Pack",
                "desc": "TCP Def-Trailers -> TCP Trailers -> TCP Def-Companies -> TCP Companies",
                "examples": "promods-tcp-def-trailers..., promods-tcp-trailers...",
            },
            {
                "tier": "4. ProMods Middle East & Steppe",
                "desc": "Middle East Def -> Assets -> Steppe Def -> Map -> Assets",
                "examples": "promods-me-def..., promods-tgs-def...",
            },
            {
                "tier": "5. ProMods Europe Hauptpaket",
                "desc": "Def -> Map -> Models 3 -> Models 2 -> Models 1 -> Media -> Assets",
                "examples": "promods-def -> promods-map -> promods-model3 ... promods-assets",
            },
            {
                "tier": "6. Andere Map-Pakete (unter ProMods)",
                "desc": "RusMap (Map -> Models 2 -> Models -> Def), RoEx, Southern Region, Red Sea",
                "examples": "RusMap-map..., RusMap-model..., SRmap...",
            },
        ]
