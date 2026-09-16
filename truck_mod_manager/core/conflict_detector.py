"""
Conflict Detector for SCS / ZIP mods.
Identifies duplicate game files across active mods and determines load-order precedence.
"""
from typing import Dict, List, Set, Tuple
from truck_mod_manager.core.models import ConflictFile, ScsMod


# Files that are expected to exist in every mod and do not represent game asset conflicts
IGNORED_CONFLICT_FILES = {
    "manifest.sii",
    "description.txt",
    "mod_icon.png",
    "icon.png",
    "license.txt",
    "readme.txt",
}


class ConflictDetector:
    """Analyzes active mods for file collisions."""

    @classmethod
    def find_conflicts(cls, active_mods: List[ScsMod]) -> List[ConflictFile]:
        """
        Scans all active mods.
        Returns a list of ConflictFile objects for paths existing in > 1 active mod.
        The mod with the lowest priority number (highest priority) is marked as winning_mod.
        """
        # Map: relative_file_path -> list of (priority, mod_file_name)
        file_to_mods: Dict[str, List[Tuple[int, str]]] = {}

        for mod in active_mods:
            if not mod.is_enabled:
                continue

            for file_name in mod.internal_files:
                norm_path = file_name.replace("\\", "/").strip("/")

                # Skip directories and root metadata
                if not norm_path or norm_path.endswith("/"):
                    continue
                basename = norm_path.split("/")[-1].lower()
                if basename in IGNORED_CONFLICT_FILES:
                    continue

                if norm_path not in file_to_mods:
                    file_to_mods[norm_path] = []
                file_to_mods[norm_path].append((mod.priority, mod.display_name))

        conflicts: List[ConflictFile] = []

        for path, mod_list in file_to_mods.items():
            if len(mod_list) > 1:
                # Sort by priority ascending (1 = highest priority)
                mod_list.sort(key=lambda item: item[0] if item[0] > 0 else 999999)
                winning_mod = mod_list[0][1]
                mod_names = [m[1] for m in mod_list]

                conflicts.append(ConflictFile(
                    relative_path=path,
                    mod_files=mod_names,
                    winning_mod=winning_mod
                ))

        # Sort conflicts by path
        conflicts.sort(key=lambda c: c.relative_path)
        return conflicts

    @classmethod
    def get_mod_conflict_counts(cls, active_mods: List[ScsMod]) -> Dict[str, int]:
        """Returns a dict mapping mod display_name to count of conflicting files."""
        conflicts = cls.find_conflicts(active_mods)
        counts: Dict[str, int] = {m.display_name: 0 for m in active_mods}

        for c in conflicts:
            for mod_name in c.mod_files:
                if mod_name in counts:
                    counts[mod_name] += 1

        return counts
