"""
Unit tests for ProModsManager.
"""
from pathlib import Path
import unittest

from truck_mod_manager.core.models import GameType, ModCategory, ScsMod
from truck_mod_manager.core.promods_manager import (
    ProModsManager, ProModsPackStatus, ProModsPackType
)


def _make_mod(filename: str, display_name: str, categories=None) -> ScsMod:
    cats = categories or [ModCategory.MAP]
    return ScsMod(
        file_path=f"/mods/{filename}",
        file_name=filename,
        display_name=display_name,
        categories=cats,
        is_enabled=True
    )


class TestProModsManager(unittest.TestCase):
    def test_promods_europe_complete(self):
        mods = [
            _make_mod("promods-assets-v270.scs", "ProMods Assets"),
            _make_mod("promods-def-v270.scs", "ProMods Def"),
            _make_mod("promods-map-v270.scs", "ProMods Map"),
            _make_mod("promods-media-v270.scs", "ProMods Media"),
            _make_mod("promods-model1-v270.scs", "ProMods Model 1"),
            _make_mod("promods-model2-v270.scs", "ProMods Model 2"),
            _make_mod("promods-model3-v270.scs", "ProMods Model 3"),
        ]

        statuses = ProModsManager.scan_promods(mods, GameType.ETS2)
        europe = next(s for s in statuses if s.pack_type == ProModsPackType.EUROPE)

        self.assertTrue(europe.is_installed)
        self.assertTrue(europe.is_complete)
        self.assertEqual(europe.total_found, 7)
        self.assertEqual(europe.total_required, 7)
        self.assertEqual(europe.version, "2.70")
        self.assertEqual(len(europe.missing_names), 0)

    def test_promods_europe_incomplete(self):
        # Missing model2 and media
        mods = [
            _make_mod("promods-def-v270.scs", "ProMods Def"),
            _make_mod("promods-map-v270.scs", "ProMods Map"),
            _make_mod("promods-model1-v270.scs", "ProMods Model 1"),
            _make_mod("promods-model3-v270.scs", "ProMods Model 3"),
            _make_mod("promods-assets-v270.scs", "ProMods Assets"),
        ]

        statuses = ProModsManager.scan_promods(mods, GameType.ETS2)
        europe = next(s for s in statuses if s.pack_type == ProModsPackType.EUROPE)

        self.assertTrue(europe.is_installed)
        self.assertFalse(europe.is_complete)
        self.assertEqual(europe.total_found, 5)
        self.assertIn("ProMods Europe Models 2", europe.missing_names)
        self.assertIn("ProMods Europe Media", europe.missing_names)

    def test_promods_canada_ats(self):
        mods = [
            _make_mod("promods-ats-assets-v130.scs", "ProMods ATS Assets"),
            _make_mod("promods-ats-def-v130.scs", "ProMods ATS Def"),
            _make_mod("promods-ats-map-v130.scs", "ProMods ATS Map"),
            _make_mod("promods-ats-models-v130.scs", "ProMods ATS Models"),
        ]

        statuses = ProModsManager.scan_promods(mods, GameType.ATS)
        canada = next(s for s in statuses if s.pack_type == ProModsPackType.CANADA)

        self.assertTrue(canada.is_installed)
        self.assertTrue(canada.is_complete)
        self.assertEqual(canada.total_found, 4)
        self.assertEqual(canada.version, "1.30")

    def test_promods_official_load_order(self):
        # Scrambled order
        mods = [
            _make_mod("promods-assets-v270.scs", "ProMods Assets"),
            _make_mod("promods-media-v270.scs", "ProMods Media"),
            _make_mod("promods-model1-v270.scs", "ProMods Model 1"),
            _make_mod("promods-def-v270.scs", "ProMods Def"),
            _make_mod("promods-model3-v270.scs", "ProMods Model 3"),
            _make_mod("promods-map-v270.scs", "ProMods Map"),
            _make_mod("promods-model2-v270.scs", "ProMods Model 2"),
        ]

        ordered = ProModsManager.get_promods_load_order(mods, GameType.ETS2)

        expected_filenames = [
            "promods-def-v270.scs",
            "promods-map-v270.scs",
            "promods-model3-v270.scs",
            "promods-model2-v270.scs",
            "promods-model1-v270.scs",
            "promods-media-v270.scs",
            "promods-assets-v270.scs",
        ]

        actual_filenames = [m.file_name for m in ordered]
        self.assertEqual(actual_filenames, expected_filenames)

    def test_apply_promods_order_with_connectors_and_other_mods(self):
        ui_mod = _make_mod("ui-mod.scs", "UI Mod", [ModCategory.UI])
        truck_mod = _make_mod("scania.scs", "Scania Truck", [ModCategory.TRUCK])
        rc_mod = _make_mod("promods-rusmap-connector.scs", "ProMods RusMap Connector", [ModCategory.MAP])
        rusmap_model = _make_mod("rusmap-model.scs", "RusMap Model", [ModCategory.MAP])

        promods_mods = [
            _make_mod("promods-assets-v270.scs", "ProMods Assets", [ModCategory.MAP]),
            _make_mod("promods-def-v270.scs", "ProMods Def", [ModCategory.MAP]),
            _make_mod("promods-map-v270.scs", "ProMods Map", [ModCategory.MAP]),
        ]

        all_mods = [rusmap_model, promods_mods[0], truck_mod, rc_mod, promods_mods[1], ui_mod, promods_mods[2]]

        sorted_mods = ProModsManager.apply_promods_order(all_mods, GameType.ETS2)
        sorted_names = [m.file_name for m in sorted_mods]

        # Top mods should be UI & Truck
        self.assertIn("ui-mod.scs", sorted_names[:3])
        self.assertIn("scania.scs", sorted_names[:3])

        # Connector should come before ProMods Def
        rc_idx = sorted_names.index("promods-rusmap-connector.scs")
        def_idx = sorted_names.index("promods-def-v270.scs")
        map_idx = sorted_names.index("promods-map-v270.scs")
        assets_idx = sorted_names.index("promods-assets-v270.scs")

        self.assertLess(rc_idx, def_idx)
        self.assertLess(def_idx, map_idx)
        self.assertLess(map_idx, assets_idx)

        # Other map bases (RusMap) should come after ProMods assets
        rusmap_idx = sorted_names.index("rusmap-model.scs")
        self.assertGreater(rusmap_idx, assets_idx)


if __name__ == "__main__":
    unittest.main()
