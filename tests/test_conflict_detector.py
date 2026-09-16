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
            internal_files=["manifest.sii", "description.txt", "mod_icon.png"]
        )
        mod2 = ScsMod(
            file_path="m2.scs", file_name="m2.scs", display_name="M2", is_enabled=True, priority=2,
            internal_files=["manifest.sii", "description.txt", "mod_icon.png"]
        )
        conflicts = ConflictDetector.find_conflicts([mod1, mod2])
        self.assertEqual(len(conflicts), 0)


if __name__ == "__main__":
    unittest.main()
