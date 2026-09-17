"""
Unit tests for ConflictDetector.
"""
import unittest
from truck_mod_manager.core.conflict_detector import ConflictDetector
from truck_mod_manager.core.models import ScsMod


class TestConflictDetector(unittest.TestCase):
    def test_conflict_detection(self):
        mod1 = ScsMod(
            file_path="mod1.scs",
            file_name="mod1.scs",
            display_name="Engine Tuning",
            is_enabled=True,
            priority=1,
            internal_files=[
                "manifest.sii",  # should be ignored
                "def/vehicle/truck/scania.r/engine/dc16_730.sii",
                "sound/truck/engine.bank"
            ]
        )

        mod2 = ScsMod(
            file_path="mod2.scs",
            file_name="mod2.scs",
            display_name="Sound Overhaul",
            is_enabled=True,
            priority=2,
            internal_files=[
                "manifest.sii",  # should be ignored
                "sound/truck/engine.bank",  # Conflict!
                "sound/truck/horn.bank"
            ]
        )

        conflicts = ConflictDetector.find_conflicts([mod1, mod2])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].relative_path, "sound/truck/engine.bank")
        self.assertEqual(conflicts[0].winning_mod, "Engine Tuning")
        self.assertIn("Sound Overhaul", conflicts[0].mod_files)

    def test_no_conflicts_for_metadata(self):
        mod1 = ScsMod(
            file_path="m1.scs", file_name="m1.scs", display_name="M1", is_enabled=True, priority=1,
            internal_files=["manifest.sii", "description.txt", "mod_icon.png", "versions.sii", "changelog.txt", ".DS_Store"]
        )
        mod2 = ScsMod(
            file_path="m2.scs", file_name="m2.scs", display_name="M2", is_enabled=True, priority=2,
            internal_files=["manifest.sii", "description.txt", "mod_icon.png", "versions.sii", "metadata.sii", "thumbs.db"]
        )
        conflicts = ConflictDetector.find_conflicts([mod1, mod2])
        self.assertEqual(len(conflicts), 0)

    def test_case_insensitive_matching(self):
        from truck_mod_manager.core.models import ConflictSeverity

        mod1 = ScsMod(
            file_path="m1.scs", file_name="m1.scs", display_name="Mod A", is_enabled=True, priority=1,
            internal_files=["def/Game_Data.sii"]
        )
        mod2 = ScsMod(
            file_path="m2.scs", file_name="m2.scs", display_name="Mod B", is_enabled=True, priority=2,
            internal_files=["def/game_data.sii"]
        )
        conflicts = ConflictDetector.find_conflicts([mod1, mod2])
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].severity, ConflictSeverity.CRITICAL)
        self.assertEqual(conflicts[0].category_label, "Spieldaten (Core)")
        self.assertEqual(conflicts[0].winning_mod, "Mod A")

    def test_critical_severity_classification(self):
        from truck_mod_manager.core.models import ConflictSeverity

        mod1 = ScsMod(
            file_path="m1.scs", file_name="m1.scs", display_name="Physics Mod", is_enabled=True, priority=1,
            internal_files=["def/vehicle/physics.sii", "def/economy_data.sii", "map/europe/sec+0001-0002.base"]
        )
        mod2 = ScsMod(
            file_path="m2.scs", file_name="m2.scs", display_name="Map Mod", is_enabled=True, priority=2,
            internal_files=["def/vehicle/physics.sii", "def/economy_data.sii", "map/europe/sec+0001-0002.base"]
        )
        conflicts = ConflictDetector.find_conflicts([mod1, mod2])
        self.assertEqual(len(conflicts), 3)
        for c in conflicts:
            self.assertEqual(c.severity, ConflictSeverity.CRITICAL)

    def test_road_connection_and_same_family(self):
        from truck_mod_manager.core.models import ConflictSeverity

        # ProMods Map and ProMods Def (Same family)
        pm_def = ScsMod(
            file_path="promods-def.scs", file_name="promods-def.scs", display_name="ProMods Definition Package",
            is_enabled=True, priority=1, internal_files=["material/road.mat", "def/world/road.promods.sii"]
        )
        pm_map = ScsMod(
            file_path="promods-map.scs", file_name="promods-map.scs", display_name="ProMods Map Package",
            is_enabled=True, priority=2, internal_files=["material/road.mat", "def/world/road.promods.sii"]
        )
        conflicts = ConflictDetector.find_conflicts([pm_def, pm_map])
        self.assertEqual(len(conflicts), 2)
        for c in conflicts:
            self.assertTrue(c.is_intended_override)
            self.assertEqual(c.severity, ConflictSeverity.INFO)
            self.assertEqual(c.category_label, "Mod-Paket (Intern)")

        # Road connection overwriting map sector
        rc = ScsMod(
            file_path="promods_poland_rc.scs", file_name="promods_poland_rc.scs",
            display_name="ProMods Poland Rebuilding Road Connection",
            is_enabled=True, priority=1, internal_files=["map/europe/sec+0005-0003.base"]
        )
        map_mod = ScsMod(
            file_path="poland.scs", file_name="poland.scs", display_name="Poland Rebuilding",
            is_enabled=True, priority=2, internal_files=["map/europe/sec+0005-0003.base"]
        )
        rc_conflicts = ConflictDetector.find_conflicts([rc, map_mod])
        self.assertEqual(len(rc_conflicts), 1)
        self.assertTrue(rc_conflicts[0].is_intended_override)
        self.assertEqual(rc_conflicts[0].severity, ConflictSeverity.INFO)
        self.assertEqual(rc_conflicts[0].category_label, "Kartensektor (RC)")

    def test_conflict_summary_and_critical_counts(self):
        mod1 = ScsMod(
            file_path="m1.scs", file_name="m1.scs", display_name="Mod 1", is_enabled=True, priority=1,
            internal_files=["def/game_data.sii", "sound/engine.bank", "material/sign.mat"]
        )
        mod2 = ScsMod(
            file_path="m2.scs", file_name="m2.scs", display_name="Mod 2", is_enabled=True, priority=2,
            internal_files=["def/game_data.sii", "sound/engine.bank", "material/sign.mat"]
        )
        summary = ConflictDetector.get_conflict_summary([mod1, mod2])
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["critical"], 1)  # game_data.sii
        self.assertEqual(summary["warning"], 1)   # sound/engine.bank
        self.assertEqual(summary["info"], 1)      # material/sign.mat

        crit_counts = ConflictDetector.get_mod_critical_conflict_counts([mod1, mod2])
        self.assertEqual(crit_counts["Mod 1"], 1)
        self.assertEqual(crit_counts["Mod 2"], 1)


if __name__ == "__main__":
    unittest.main()
