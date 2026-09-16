"""
Unit tests for Mod Compatibility checking with Game Versions.
"""
import unittest
from truck_mod_manager.core.models import ScsMod


class TestCompatibility(unittest.TestCase):
    def test_compatible_wildcard(self):
        mod = ScsMod(
            file_path="promods.scs",
            file_name="promods.scs",
            display_name="ProMods",
            compatible_versions=["1.50.*"]
        )
        is_compat, msg = mod.check_compatibility("1.50.2.3s")
        self.assertTrue(is_compat)
        self.assertIn("Kompatibel mit v1.50.2.3s", msg)

    def test_incompatible_version(self):
        mod = ScsMod(
            file_path="old_mod.scs",
            file_name="old_mod.scs",
            display_name="Old Truck Mod",
            compatible_versions=["1.48.*", "1.49.*"]
        )
        is_compat, msg = mod.check_compatibility("1.50.1s")
        self.assertFalse(is_compat)
        self.assertIn("Inkompatibel", msg)

    def test_universal_no_constraint(self):
        mod = ScsMod(
            file_path="universal.scs",
            file_name="universal.scs",
            display_name="Universal Sound",
            compatible_versions=[]
        )
        is_compat, msg = mod.check_compatibility("1.50.2s")
        self.assertIsNone(is_compat)
        self.assertIn("Universell", msg)

    def test_unknown_game_version(self):
        mod = ScsMod(
            file_path="mod.scs",
            file_name="mod.scs",
            display_name="Mod",
            compatible_versions=["1.50.*"]
        )
        is_compat, msg = mod.check_compatibility(None)
        self.assertIsNone(is_compat)

        is_compat2, msg2 = mod.check_compatibility("Unbekannt")
        self.assertIsNone(is_compat2)


if __name__ == "__main__":
    unittest.main()
