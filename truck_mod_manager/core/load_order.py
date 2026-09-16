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
        """
        # Base score from primary category
        primary_cat = mod.primary_category
        base_score = float(LOAD_ORDER_PRIORITY.get(primary_cat, 5) * 100)

        lower_name = mod.display_name.lower() + " " + mod.file_name.lower()

        # Specific adjustments for Map packages (e.g. ProMods, RusMap, RoEx)
        # Standard SCS Rule: Road Connections / Fixes > Def > Map > Model 3 > Model 2 > Model 1 > Assets > Background Map
        if any(c in mod.categories for c in (ModCategory.MAP, ModCategory.MODELS, ModCategory.PREFABS, ModCategory.DEF)):
            if "connector" in lower_name or "connection" in lower_name or "fix" in lower_name:
                base_score = 3500.0  # Top of maps
            elif "def" in lower_name:
                base_score = 3000.0
            elif "map" in lower_name and not "background" in lower_name:
                base_score = 2500.0
            elif "model 3" in lower_name or "model3" in lower_name or "media" in lower_name:
                base_score = 2300.0
            elif "model 2" in lower_name or "model2" in lower_name:
                base_score = 2200.0
            elif "model 1" in lower_name or "model1" in lower_name or "model" in lower_name:
                base_score = 2100.0
            elif "prefab" in lower_name:
                base_score = 2000.0
            elif "asset" in lower_name:
                base_score = 1900.0
            elif "background" in lower_name:
                base_score = 1500.0  # Below all maps

        # Sub-sort within category: secondary tags
        if "addon" in lower_name or "patch" in lower_name:
            base_score += 15.0

        return base_score

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
