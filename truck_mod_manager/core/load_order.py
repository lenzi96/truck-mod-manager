"""
Load Order manager and SCS community auto-sorting algorithm.
Provides drag-and-drop ordering, priority reassignment, and smart auto-sorting.
"""
import re
from typing import List, Optional
from truck_mod_manager.core.models import LOAD_ORDER_PRIORITY, ModCategory, ScsMod


class LoadOrderManager:
    """Manages active mod load order, moving items and smart auto-sorting."""

    @staticmethod
    def calculate_mod_sort_score(mod: ScsMod) -> float:
        """
        Calculates a sort score according to SCS community load order rules.
        Higher score = higher priority = top of load order list.
        Order (Top -> Bottom):
          1. Background Maps & Map Crash Fixes (Score ~20000)
          2. UI, Route Advisors, HUD, Mirrors (Score ~18000)
          3. Voice Navigation & GPS (Score ~16500)
          4. Sounds (Score ~16000)
          5. Graphics, Weather & Lighting (Score ~14000)
          6. Physics & Cameras (Score ~12000)
          7. Tuning, Cabin Accessories & Interiors (Score ~10000)
          8. AI Traffic (def > base > jaz) (Score ~8500)
          9. Skins & Paint Jobs (Score ~7500)
          10. Trailers & Cargo (Score ~6500)
          11. Trucks & Engines (Score ~5000)
          12. Road Connections & Map Fixes (Score ~3500)
          13. Map Packages (Def > Map > Models 3/2/1 > Prefabs > Assets > Base) (Score 3000 -> 1800)
          14. Other / General Tweaks (Score ~4000)
        """
        lname = (mod.display_name + " " + mod.file_name).lower()

        # 1. Background Maps & Map Crash Fixes (Top of active mods, Priority 1)
        if "background" in lname and any(k in lname for k in ("map", "ats", "ets", "promods", "desktop", "tempest")):
            return 20000.0
        if "crash" in lname and any(k in lname for k in ("fix", "combo")):
            return 19500.0

        # 2. UI, Route Advisors, HUD & Mirrors
        if any(k in lname for k in ("route advisor", "advisor", "yara", "minimal ui", "fullscreen")):
            return 18500.0
        if any(k in lname for k in ("icon", "icons", "hud", "mirror", "mirrors", "ui_")):
            return 18200.0
        if mod.primary_category == ModCategory.UI:
            return 18000.0

        # 3. Voice Navigation & GPS
        if any(k in lname for k in ("voice", "siri", "tomtom", "navigon", "gps")):
            return 16500.0

        # 4. Sounds
        if mod.primary_category == ModCategory.SOUND or "sound" in lname or ".bank" in lname:
            return 16000.0

        # 5. Graphics, Weather & Lighting
        if "brutal" in lname or "weather" in lname or "autumn" in lname or "winter" in lname:
            return 14500.0
        if mod.primary_category == ModCategory.WEATHER:
            return 14500.0
        if "headlight" in lname or "light" in lname or "xenon" in lname or "led" in lname:
            return 13800.0
        if mod.primary_category == ModCategory.GRAPHICS or "graphic" in lname:
            return 14000.0

        # 6. Physics & Cameras
        if "camera" in lname or "cam" in lname:
            return 12000.0
        if mod.primary_category == ModCategory.PHYSICS or "physic" in lname:
            return 12500.0

        # 7. Tuning, Cabin Accessories & Interiors
        if any(k in lname for k in ("sisl", "accessory", "tuning", "interior", "dog", "wheel")):
            return 10200.0
        if mod.primary_category in (ModCategory.TUNING, ModCategory.INTERIOR):
            return 10000.0

        # 8. AI Traffic (cars, trucks, motorcycles, trains)
        if "traffic" in lname or "train" in lname or mod.primary_category == ModCategory.AI_TRAFFIC:
            # Multi-part packs: def > base > jaz
            score = 8500.0
            if "_def" in lname or " def" in lname:
                score += 100.0
            elif "_jaz" in lname or " jaz" in lname:
                score -= 100.0
            return score

        # 9. Skins & Paint Jobs
        if mod.primary_category == ModCategory.PAINT_JOB or any(k in lname for k in ("skin", "metallic", "paint")):
            return 7500.0

        # 10. Trailers & Cargo
        if "trailer" in lname or "cargo" in lname or mod.primary_category in (ModCategory.TRAILER, ModCategory.CARGO):
            return 6500.0

        # 11. Trucks, Engines & Transmissions
        if any(k in lname for k in ("engine", "transmission", "gearbox", "cummins", "caterpillar", "power")):
            return 5200.0
        if mod.primary_category == ModCategory.TRUCK or any(k in lname for k in (
            "peterbilt", "kenworth", "freightliner", "mack", "volvo", "western", "scania", "man", "daf", "iveco", "renault", "edison"
        )):
            return 5000.0

        # 12. Map Road Connections & Compatibility Fixes (placed directly above Map packs)
        if any(k in lname for k in ("road connection", "connection", "connector", " rc", "_rc", "rc_")):
            return 3500.0
        if "fix" in lname and any(k in lname for k in ("map", "promods", "alaska", "rusmap")):
            return 3400.0

        # 13. Map Packages
        is_map = (
            any(k in lname for k in ("promods", "map", "alaska", "rusmap", "roex", "poland", "southern", "great steppe"))
            or any(c in mod.categories for c in (ModCategory.MAP, ModCategory.MODELS, ModCategory.PREFABS, ModCategory.DEF))
        )
        if is_map:
            if "def" in lname or mod.primary_category == ModCategory.DEF:
                return 3000.0
            if "map" in lname and not any(k in lname for k in ("model", "asset", "prefab")):
                return 2500.0
            if "model 3" in lname or "model3" in lname or "media" in lname:
                return 2300.0
            if "model 2" in lname or "model2" in lname:
                return 2200.0
            if "model 1" in lname or "model1" in lname or "model" in lname:
                return 2100.0
            if "prefab" in lname or mod.primary_category == ModCategory.PREFABS:
                return 2000.0
            if "asset" in lname or mod.primary_category == ModCategory.MODELS:
                return 1900.0
            return 1800.0

        # 14. Other / General Mods (Economy, No Damage, XP, Wheels/Tires)
        return 4000.0

    @classmethod
    def auto_sort(cls, mods: List[ScsMod]) -> List[ScsMod]:
        """
        Sorts active mods using the SCS community load order standard.
        Returns newly ordered list with updated priority indices (1 = highest).
        """
        active_mods = [m for m in mods if m.is_enabled]
        inactive_mods = [m for m in mods if not m.is_enabled]

        # Sort active mods by sort score descending (highest priority first)
        # Secondary sort key: alphabetical by name for determinism
        sorted_active = sorted(
            active_mods,
            key=lambda m: (cls.calculate_mod_sort_score(m), m.display_name.lower()),
            reverse=True
        )

        # Update priorities (1 = highest)
        for idx, mod in enumerate(sorted_active, start=1):
            mod.priority = idx

        for mod in inactive_mods:
            mod.priority = 0

        return sorted_active + inactive_mods

    @classmethod
    def reindex_priorities(cls, active_mods: List[ScsMod]) -> List[ScsMod]:
        """Reassigns 1..N priorities to the active mods in their current sequence."""
        for idx, mod in enumerate(active_mods, start=1):
            mod.priority = idx
        return active_mods

    @classmethod
    def move_up(cls, active_mods: List[ScsMod], index: int) -> bool:
        """Moves mod at index up by one position (higher priority)."""
        if index <= 0 or index >= len(active_mods):
            return False
        active_mods[index - 1], active_mods[index] = active_mods[index], active_mods[index - 1]
        cls.reindex_priorities(active_mods)
        return True

    @classmethod
    def move_down(cls, active_mods: List[ScsMod], index: int) -> bool:
        """Moves mod at index down by one position (lower priority)."""
        if index < 0 or index >= len(active_mods) - 1:
            return False
        active_mods[index], active_mods[index + 1] = active_mods[index + 1], active_mods[index]
        cls.reindex_priorities(active_mods)
        return True

    @classmethod
    def move_to_top(cls, active_mods: List[ScsMod], index: int) -> bool:
        """Moves mod at index to the very top (priority 1)."""
        if index <= 0 or index >= len(active_mods):
            return False
        item = active_mods.pop(index)
        active_mods.insert(0, item)
        cls.reindex_priorities(active_mods)
        return True

    @classmethod
    def move_to_bottom(cls, active_mods: List[ScsMod], index: int) -> bool:
        """Moves mod at index to the very bottom."""
        if index < 0 or index >= len(active_mods) - 1:
            return False
        item = active_mods.pop(index)
        active_mods.append(item)
        cls.reindex_priorities(active_mods)
        return True
