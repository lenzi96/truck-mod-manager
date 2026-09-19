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

    def test_promods_pack_card_ui_rendering(self):
        """Verifies ProModsPackCard instantiates without AttributeError when mods are found."""
        import sys
        from PyQt6.QtWidgets import QApplication
        from truck_mod_manager.ui.views.promods_view import ProModsPackCard

        app = QApplication.instance() or QApplication(sys.argv)

        mods = [
            _make_mod("promods-assets-v270.scs", "ProMods Assets"),
            _make_mod("promods-def-v270.scs", "ProMods Def"),
            _make_mod("promods-map-v270.scs", "ProMods Map"),
        ]
        statuses = ProModsManager.scan_promods(mods, GameType.ETS2)
        europe = next(s for s in statuses if s.pack_type == ProModsPackType.EUROPE)

        # Card should render cleanly without 'str' object has no attribute 'name' error
        card = ProModsPackCard(europe)
        self.assertIsNotNone(card)

    def test_promods_v283_and_modern_addons(self):
        mods = [
            _make_mod("promods-eu-assets-v283.scs", "ProMods Europe Assets"),
            _make_mod("promods-eu-def-v283.scs", "ProMods Europe Def"),
            _make_mod("promods-eu-map-v283.scs", "ProMods Europe Map"),
            _make_mod("promods-eu-media-v283.scs", "ProMods Europe Media"),
            _make_mod("promods-eu-model1-v283.scs", "ProMods Europe Model 1"),
            _make_mod("promods-eu-model2-v283.scs", "ProMods Europe Model 2"),
            _make_mod("promods-eu-model3-v283.scs", "ProMods Europe Model 3"),
            _make_mod("promods-eu-dlcsupport-v283.zip", "ProMods Europe DLC Support"),
            _make_mod("promods-me-defmap-v283.scs", "ProMods Middle East DefMap"),
            _make_mod("promods-me-assets-v283.scs", "ProMods Middle East Assets"),
            _make_mod("promods-tgs-defmap-v162.scs", "ProMods Steppe DefMap"),
            _make_mod("promods-tgs-assets-v162.scs", "ProMods Steppe Assets"),
            _make_mod("promods-ma-defmap-v103.scs", "ProMods Maghreb DefMap"),
            _make_mod("promods-ma-models-v103.scs", "ProMods Maghreb Models"),
            _make_mod("promods-ma-assets-v103.scs", "ProMods Maghreb Assets"),
            _make_mod("promods-cap-v160.scs", "ProMods Classic Asset Pack"),
        ]

        statuses = ProModsManager.scan_promods(mods, GameType.ETS2)
        status_map = {s.pack_type: s for s in statuses}

        self.assertTrue(status_map[ProModsPackType.EUROPE].is_complete)
        self.assertEqual(status_map[ProModsPackType.EUROPE].version, "2.83")

        self.assertTrue(status_map[ProModsPackType.MIDDLE_EAST].is_complete)
        self.assertEqual(status_map[ProModsPackType.MIDDLE_EAST].version, "2.83")

        self.assertTrue(status_map[ProModsPackType.GREAT_STEPPE].is_complete)
        self.assertEqual(status_map[ProModsPackType.GREAT_STEPPE].version, "1.62")

        self.assertTrue(status_map[ProModsPackType.MAGHREB].is_complete)
        self.assertEqual(status_map[ProModsPackType.MAGHREB].version, "1.03")

        self.assertTrue(status_map[ProModsPackType.CAP].is_complete)
        self.assertEqual(status_map[ProModsPackType.CAP].version, "1.60")

    def test_version_comparison_and_updates(self):
        # Comparison logic
        self.assertEqual(ProModsManager.compare_versions("2.70", "2.83"), -1)
        self.assertEqual(ProModsManager.compare_versions("2.83", "2.83"), 0)
        self.assertEqual(ProModsManager.compare_versions("2.83", "2.70"), 1)
        self.assertEqual(ProModsManager.compare_versions("1.62", "1.60"), 1)
        self.assertEqual(ProModsManager.compare_versions("1.03", "1.60"), -1)

        # Pack with older version
        old_mods = [
            _make_mod("promods-assets-v270.scs", "ProMods Assets"),
            _make_mod("promods-def-v270.scs", "ProMods Def"),
            _make_mod("promods-map-v270.scs", "ProMods Map"),
            _make_mod("promods-media-v270.scs", "ProMods Media"),
            _make_mod("promods-model1-v270.scs", "ProMods Model 1"),
            _make_mod("promods-model2-v270.scs", "ProMods Model 2"),
            _make_mod("promods-model3-v270.scs", "ProMods Model 3"),
        ]
        statuses = ProModsManager.scan_promods(old_mods, GameType.ETS2)
        europe = next(s for s in statuses if s.pack_type == ProModsPackType.EUROPE)

        self.assertEqual(europe.version, "2.70")
        self.assertEqual(europe.latest_version, "2.83")
        self.assertTrue(europe.is_update_available)
        self.assertFalse(europe.is_up_to_date)
        self.assertEqual(europe.download_url, "https://promods.net/setup.php")

        # Pack with latest version
        new_mods = [
            _make_mod("promods-eu-assets-v283.scs", "ProMods Assets"),
            _make_mod("promods-eu-def-v283.scs", "ProMods Def"),
            _make_mod("promods-eu-map-v283.scs", "ProMods Map"),
            _make_mod("promods-eu-media-v283.scs", "ProMods Media"),
            _make_mod("promods-eu-model1-v283.scs", "ProMods Model 1"),
            _make_mod("promods-eu-model2-v283.scs", "ProMods Model 2"),
            _make_mod("promods-eu-model3-v283.scs", "ProMods Model 3"),
        ]
        statuses_new = ProModsManager.scan_promods(new_mods, GameType.ETS2)
        europe_new = next(s for s in statuses_new if s.pack_type == ProModsPackType.EUROPE)

        self.assertEqual(europe_new.version, "2.83")
        self.assertEqual(europe_new.latest_version, "2.83")
        self.assertFalse(europe_new.is_update_available)
        self.assertTrue(europe_new.is_up_to_date)

    def test_promods_download_dialog_instantiation(self):
        import sys
        from PyQt6.QtWidgets import QApplication
        from truck_mod_manager.core.models import TruckGame
        from truck_mod_manager.ui.dialogs.promods_download_dialog import ProModsDownloadDialog

        app = QApplication.instance() or QApplication(sys.argv)
        game = TruckGame(
            game_type=GameType.ETS2,
            name="Euro Truck Simulator 2",
            steam_appid="227300",
            mod_dir="/tmp/fake_mod_dir"
        )
        pack_status = ProModsPackStatus(
            pack_type=ProModsPackType.EUROPE,
            title="ProMods Europe",
            game_type=GameType.ETS2,
            latest_version="2.83",
            download_url="https://promods.net/setup.php"
        )
        dialog = ProModsDownloadDialog(pack_status, game)
        self.assertIsNotNone(dialog)
        self.assertIn("ProMods Europe", dialog.windowTitle())


if __name__ == "__main__":
    unittest.main()

