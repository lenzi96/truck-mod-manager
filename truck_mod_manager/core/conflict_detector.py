"""
Conflict Detector for SCS / ZIP mods.
Identifies duplicate game files across active mods and determines load-order precedence,
risk levels (Critical, Warning, Info), and in-game impact.
"""
from typing import Dict, List, Optional, Set, Tuple
from truck_mod_manager.core.models import ConflictFile, ConflictSeverity, ScsMod


# Files that are expected to exist in mods and do not represent game asset conflicts
IGNORED_CONFLICT_FILES = {
    "manifest.sii",
    "description.txt",
    "mod_icon.png",
    "icon.png",
    "icon.jpg",
    "license.txt",
    "readme.txt",
    "versions.sii",
    "metadata.sii",
    "changelog.txt",
    "changelog.md",
    "credits.txt",
    "info.txt",
    ".ds_store",
    "thumbs.db",
    "desktop.ini",
}


def is_road_connection(mod: ScsMod) -> bool:
    """Checks whether a mod is a Road Connection or compatibility fix pack."""
    lname = (mod.display_name + " " + mod.file_name).lower()
    return any(k in lname for k in (
        "road connection", "road_connection", "roadconnection",
        "_rc", " rc", " connector", "connector", "fix", "patch"
    ))


def are_same_family(mod1: ScsMod, mod2: ScsMod) -> bool:
    """Checks whether two mods belong to the same package family (e.g. ProMods Map + Def)."""
    name1 = (mod1.display_name + " " + mod1.file_name).lower()
    name2 = (mod2.display_name + " " + mod2.file_name).lower()

    # Known mod families
    for prefix in (
        "promods", "rusmap", "roex", "poland rebuilding", "jazzycat",
        "great steppe", "middle east", "siberia", "srteam", "volga", "red sea"
    ):
        if prefix in name1 and prefix in name2:
            return True

    # Same author match
    if (
        mod1.author
        and mod2.author
        and mod1.author.lower() != "unknown"
        and mod1.author.strip().lower() == mod2.author.strip().lower()
    ):
        return True

    return False


class ConflictDetector:
    """Analyzes active mods for file collisions and evaluates operational risk."""

    @classmethod
    def classify_conflict(
        cls,
        path: str,
        winning_mod: ScsMod,
        other_mods: List[ScsMod]
    ) -> Tuple[ConflictSeverity, str, str, bool]:
        """
        Classifies a conflict's severity, category label, impact description,
        and whether it's an intended override (Road Connection / Multi-Part pack).
        """
        p_lower = path.lower()
        all_involved = [winning_mod] + other_mods

        # 1. Check for intentional Road Connection / Patch override
        has_rc = any(is_road_connection(m) for m in all_involved)
        if has_rc and (p_lower.startswith("map/") or p_lower.startswith("def/world/") or "sector" in p_lower):
            return (
                ConflictSeverity.INFO,
                "Kartensektor (RC)",
                "Beabsichtigte Verbindung: Road Connection überschreibt Basiskarte wie vorgesehen.",
                True
            )

        # 2. Check for multi-part mod from same family
        if len(all_involved) >= 2 and all(are_same_family(all_involved[0], m) for m in all_involved[1:]):
            return (
                ConflictSeverity.INFO,
                "Mod-Paket (Intern)",
                "Zusammengehöriges Paket: Geteilte Datei innerhalb derselben Mod-Familie (harmlos).",
                True
            )

        # 3. Critical core game files
        if p_lower == "def/game_data.sii":
            return (
                ConflictSeverity.CRITICAL,
                "Spieldaten (Core)",
                "Kritisch: Überschreibt Basis-Kamera, Kartenzoom und Renderwerte. Kann Kartennavigation stören.",
                False
            )

        if p_lower == "def/economy_data.sii":
            return (
                ConflictSeverity.CRITICAL,
                "Wirtschaft / XP",
                "Kritisch: Beeinflusst Auftragsvergütung, Kredite, Strafen und Level-XP. Obere Mod bestimmt Werte.",
                False
            )

        if p_lower in ("def/map_data.sii", "def/world/road.sii") or p_lower.startswith("def/world/road."):
            return (
                ConflictSeverity.CRITICAL,
                "Welt & Straßen",
                "Kritisch: Definiert Straßeneigenschaften und Geländematerialien. Kann unsichtbare Straßen verursachen.",
                False
            )

        if p_lower == "def/climate.sii" or p_lower.startswith("def/climate/"):
            return (
                ConflictSeverity.CRITICAL,
                "Klima & Wetter",
                "Kritisch: Klimazonen-Kollision kann zu Grafikfehlern oder Abstürzen bei Wetterwechseln führen.",
                False
            )

        if p_lower == "def/vehicle/physics.sii" or ("physics" in p_lower and p_lower.startswith("def/vehicle/")):
            return (
                ConflictSeverity.CRITICAL,
                "Fahrphysik",
                "Kritisch: LKW-Fahrphysik, Bremskraft und Kabinenneigung werden von der oberen Mod bestimmt.",
                False
            )

        if p_lower.startswith("def/traffic_rules") or p_lower == "def/traffic_data.sii":
            return (
                ConflictSeverity.CRITICAL,
                "KI-Verkehrsregeln",
                "Kritisch: Spawn-Regeln und Vorfahrtsregeln kollidieren. Kann KI-Stillstand auslösen.",
                False
            )

        if p_lower.startswith("map/") and (p_lower.endswith(".base") or p_lower.endswith(".data")):
            return (
                ConflictSeverity.CRITICAL,
                "Kartensektor",
                "Kritisch: Unabhängige Karten überschreiben denselben Sektor! Ohne Road Connection drohen Abstürze.",
                False
            )

        # 4. Warnings (Functional overrides)
        if p_lower.startswith("def/vehicle/truck/"):
            return (
                ConflictSeverity.WARNING,
                "LKW & Zubehör",
                "Fahrzeug-Konfiguration: Chassis, Motoren oder Anbauteile werden von oberer Mod überschrieben.",
                False
            )

        if p_lower.startswith("sound/") or "sound.sii" in p_lower:
            return (
                ConflictSeverity.WARNING,
                "Sound",
                "Sound-Kollision: Motor-, Innenraum- oder Umgebungsgeräusch wird von oberer Mod ersetzt.",
                False
            )

        if p_lower.startswith("ui/") or p_lower.startswith("ui_"):
            return (
                ConflictSeverity.WARNING,
                "Benutzeroberfläche",
                "UI-Konflikt: HUD-, Route-Advisor- oder Menüelemente überschreiben sich gegenseitig.",
                False
            )

        if p_lower.startswith("def/city/") or p_lower == "def/city.sii":
            return (
                ConflictSeverity.WARNING,
                "Stadtdaten",
                "Stadteinstellungen: Firmenzuordnung oder Kennzeichen werden von oberer Mod bestimmt.",
                False
            )

        if p_lower.startswith("def/cargo") or p_lower.startswith("def/vehicle/trailer"):
            return (
                ConflictSeverity.WARNING,
                "Frachten & Trailer",
                "Frachtdaten: Frachtgewichte, Trailer oder Vergütungsboni werden überschrieben.",
                False
            )

        # 5. Info / Benign (Visual assets, materials, models)
        if (
            p_lower.startswith("material/")
            or p_lower.startswith("model/")
            or p_lower.startswith("model2/")
            or p_lower.startswith("prefab/")
            or p_lower.startswith("unit/hookup/")
        ):
            return (
                ConflictSeverity.INFO,
                "Textur / Modell",
                "Optisches Asset: Textur oder 3D-Modell wird ersetzt. In der Regel unkritisch (gewollter Re-Skin).",
                False
            )

        if p_lower.startswith("vehicle/") and (p_lower.endswith(".dds") or p_lower.endswith(".tobj")):
            return (
                ConflictSeverity.INFO,
                "Fahrzeug-Asset",
                "Fahrzeug-Textur/Lackierung: Höher platzierte Mod bestimmt die Textur.",
                False
            )

        if p_lower.startswith("def/"):
            return (
                ConflictSeverity.WARNING,
                "Definition",
                "SCS-Definition wird durch die höher priorisierte Mod überschrieben.",
                False
            )

        return (
            ConflictSeverity.INFO,
            "Sonstiges",
            "Datei wird durch die höher priorisierte Mod ersetzt.",
            False
        )

    @classmethod
    def find_conflicts(cls, active_mods: List[ScsMod]) -> List[ConflictFile]:
        """
        Scans all active mods for file collisions.
        Returns a list of ConflictFile objects with severity and impact analysis.
        """
        # Map: lower_path -> (canonical_path, list of (priority, mod_object))
        file_to_mods: Dict[str, Tuple[str, List[Tuple[int, ScsMod]]]] = {}

        for mod in active_mods:
            if not mod.is_enabled:
                continue

            for file_name in mod.internal_files:
                norm_path = file_name.replace("\\", "/").strip("/")

                # Skip directories and root metadata
                if not norm_path or norm_path.endswith("/"):
                    continue
                basename = norm_path.split("/")[-1].lower()
                if basename in IGNORED_CONFLICT_FILES or basename.startswith("."):
                    continue

                lower_path = norm_path.lower()
                if lower_path not in file_to_mods:
                    file_to_mods[lower_path] = (norm_path, [])
                file_to_mods[lower_path][1].append((mod.priority, mod))

        conflicts: List[ConflictFile] = []

        for lower_path, (canonical_path, mod_tuples) in file_to_mods.items():
            if len(mod_tuples) > 1:
                # Sort by priority ascending (1 = highest priority)
                mod_tuples.sort(key=lambda item: item[0] if item[0] > 0 else 999999)
                winning_mod = mod_tuples[0][1]
                other_mods = [m[1] for m in mod_tuples[1:]]
                mod_names = [m[1].display_name for m in mod_tuples]

                severity, cat_label, impact, is_intended = cls.classify_conflict(
                    canonical_path, winning_mod, other_mods
                )

                conflicts.append(ConflictFile(
                    relative_path=canonical_path,
                    mod_files=mod_names,
                    winning_mod=winning_mod.display_name,
                    severity=severity,
                    category_label=cat_label,
                    impact=impact,
                    is_intended_override=is_intended,
                ))

        # Sort conflicts: Critical first, then Warning, then Info, then alphabetically
        severity_order = {
            ConflictSeverity.CRITICAL: 0,
            ConflictSeverity.WARNING: 1,
            ConflictSeverity.INFO: 2,
        }
        conflicts.sort(key=lambda c: (severity_order.get(c.severity, 99), c.relative_path.lower()))
        return conflicts

    @classmethod
    def get_conflict_summary(cls, active_mods: List[ScsMod]) -> Dict[str, int]:
        """
        Returns a dictionary with overall conflict statistics:
        'total': total count
        'critical': critical high-risk count
        'warning': functional warning count
        'info': info / benign count
        """
        conflicts = cls.find_conflicts(active_mods)
        summary = {
            "total": len(conflicts),
            "critical": sum(1 for c in conflicts if c.severity == ConflictSeverity.CRITICAL),
            "warning": sum(1 for c in conflicts if c.severity == ConflictSeverity.WARNING),
            "info": sum(1 for c in conflicts if c.severity == ConflictSeverity.INFO),
        }
        return summary

    @classmethod
    def get_mod_conflict_counts(cls, active_mods: List[ScsMod]) -> Dict[str, int]:
        """Returns a dict mapping mod display_name to total count of conflicting files."""
        conflicts = cls.find_conflicts(active_mods)
        counts: Dict[str, int] = {m.display_name: 0 for m in active_mods}

        for c in conflicts:
            for mod_name in c.mod_files:
                if mod_name in counts:
                    counts[mod_name] += 1

        return counts

    @classmethod
    def get_mod_critical_conflict_counts(cls, active_mods: List[ScsMod]) -> Dict[str, int]:
        """Returns a dict mapping mod display_name to count of CRITICAL conflicts."""
        conflicts = cls.find_conflicts(active_mods)
        counts: Dict[str, int] = {m.display_name: 0 for m in active_mods}

        for c in conflicts:
            if c.severity == ConflictSeverity.CRITICAL:
                for mod_name in c.mod_files:
                    if mod_name in counts:
                        counts[mod_name] += 1

        return counts
