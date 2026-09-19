"""
Unit tests for TruckToolsEngine (savegame inspection and editing).
"""
import datetime
from pathlib import Path
import shutil
import tempfile
import unittest

from truck_mod_manager.core.models import GameProfile, GameType
from truck_mod_manager.core.truck_tools import SaveGameInfo, TruckToolsEngine


SYNTHETIC_GAME_SII = """SiiNunit
{
economy : _nameless.5757.fc60 {
 bank: _nameless.3a7b.d400
 player: _nameless.42d6.3dc0
 companies: 4
 companies[0]: company.volatile.dg_wd_saw.port_angeles
 companies[1]: company.volatile.bit_rd_svc.los_angeles
 companies[2]: company.volatile.tid_mkt.portland
 companies[3]: company.volatile.wal_mkt.denver
 garages: 2
 garages[0]: garage.los_angeles
 garages[1]: garage.seattle
 visited_cities: 1
 visited_cities[0]: los_angeles
 visited_cities_count: 1
 visited_cities_count[0]: 1
 unlocked_dealers: 2
}

bank : _nameless.3a7b.d400 {
 money_account: 500000
}

player : _nameless.42d6.3dc0 {
 hq_city: los_angeles
 assigned_truck: _nameless.6137.6ea0
 my_truck: _nameless.6137.6ea0
 assigned_trailer: _nameless.f6b7.35e0
 my_trailer: _nameless.f6b7.35e0
 experience_points: 125000
}

driver_player : _nameless.player.driver {
 adr: 5
 long_dist: 3
 heavy: 2
 fragile: 1
 urgent: 4
 mechanical: 2
 user_colors: 4
}

garage : garage.los_angeles {
 status: 2
 vehicles: 3
 vehicles[0]: _nameless.6137.6ea0
 vehicles[1]: null
 vehicles[2]: null
 drivers: 3
 drivers[0]: _nameless.player.driver
 drivers[1]: null
 drivers[2]: null
}

garage : garage.seattle {
 status: 0
 vehicles: 0
 drivers: 0
}

vehicle : _nameless.6137.6ea0 {
 fuel_relative: &3f400000
 engine_wear: &3c000000
 transmission_wear: &3c000000
 cabin_wear: &3c000000
 chassis_wear: &3c000000
 wheels_wear: 2
 wheels_wear[0]: &3c000000
 wheels_wear[1]: &3c000000
 engine_wear_unfixable: &3a000000
 user_mileage: 45000
 license_plate: "CAL-999|california"
 accessories: 3
 accessories[0]: _nameless.acc.data
 accessories[1]: _nameless.acc.engine
 accessories[2]: _nameless.acc.trans
}

vehicle_accessory : _nameless.acc.data {
 data_path: "/def/vehicle/truck/kenworth.w900/data.sii"
}

vehicle_engine_accessory : _nameless.acc.engine {
 data_path: "/def/vehicle/truck/kenworth.w900/engine/isx15.sii"
}

vehicle_transmission_accessory : _nameless.acc.trans {
 data_path: "/def/vehicle/truck/kenworth.w900/transmission/18_speed.sii"
}

trailer : _nameless.f6b7.35e0 {
 cargo_mass: 22500
 trailer_body_wear: &3c000000
 wheels_wear: 2
 wheels_wear[0]: &3c000000
 wheels_wear[1]: &3c000000
 license_plate: "TR-888|california"
}

}
"""


class TestTruckToolsEngine(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="tmm_test_save_")
        self.save_dir = Path(self.tmp_dir) / "save" / "autosave"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.game_sii = self.save_dir / "game.sii"
        self.game_sii.write_text(SYNTHETIC_GAME_SII, encoding="utf-8")

        self.save_info = SaveGameInfo(
            folder_name="autosave",
            display_name="Autosave Test",
            save_dir=self.save_dir,
            game_sii_path=self.game_sii,
            info_sii_path=None,
            modified_time=datetime.datetime.now(),
            is_autosave=True,
        )

        self.engine = TruckToolsEngine()
        self.assertTrue(self.engine.load_save(self.save_info))

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_list_savegames(self):
        profile_dir = Path(self.tmp_dir)
        # Profile directory holds save/ directory
        prof = GameProfile(
            id="test_profile",
            name="Test Profile",
            path=profile_dir,
            game_type=GameType.ATS
        )
        saves = TruckToolsEngine.list_savegames(prof)
        self.assertEqual(len(saves), 1)
        self.assertEqual(saves[0].folder_name, "autosave")
        self.assertTrue(saves[0].is_autosave)

    def test_money_get_and_set(self):
        self.assertEqual(self.engine.get_money(), 500000)
        self.assertTrue(self.engine.set_money(12500000))
        self.assertEqual(self.engine.get_money(), 12500000)
        # Verify persistence on save
        self.assertTrue(self.engine.save_changes(create_auto_backup=False))
        content = self.game_sii.read_text(encoding="utf-8")
        self.assertIn("money_account: 12500000", content)

    def test_experience_get_and_set(self):
        self.assertEqual(self.engine.get_experience(), 125000)
        self.assertTrue(self.engine.set_experience(500000))
        self.assertEqual(self.engine.get_experience(), 500000)
        self.assertTrue(self.engine.save_changes(create_auto_backup=False))
        content = self.game_sii.read_text(encoding="utf-8")
        self.assertIn("experience_points: 500000", content)

    def test_skills_get_and_max(self):
        skills = self.engine.get_skills()
        self.assertEqual(skills["adr"], 5)
        self.assertEqual(skills["long_dist"], 3)
        self.assertEqual(skills["urgent"], 4)

        self.assertTrue(self.engine.max_all_skills())
        updated = self.engine.get_skills()
        self.assertEqual(updated["adr"], 63)
        self.assertEqual(updated["long_dist"], 6)
        self.assertEqual(updated["heavy"], 6)
        self.assertEqual(updated["fragile"], 6)
        self.assertEqual(updated["urgent"], 6)
        self.assertEqual(updated["mechanical"], 6)

    def test_unlock_all_garages(self):
        count = self.engine.unlock_all_garages()
        self.assertGreater(count, 0)
        self.assertTrue(self.engine.save_changes(create_auto_backup=False))
        content = self.game_sii.read_text(encoding="utf-8")
        self.assertIn("status: 3", content)

    def test_unlock_all_cities_and_dealers(self):
        cities_count, dealers_count = self.engine.unlock_all_cities_and_dealers()
        self.assertGreaterEqual(cities_count, 4)
        self.assertEqual(dealers_count, 100)
        self.assertTrue(self.engine.save_changes(create_auto_backup=False))
        content = self.game_sii.read_text(encoding="utf-8")
        self.assertIn("visited_cities: 4", content)
        self.assertIn("unlocked_dealers: 100", content)

    def test_repair_all_trucks(self):
        resets = self.engine.repair_all_trucks()
        self.assertGreater(resets, 0)
        self.assertTrue(self.engine.save_changes(create_auto_backup=False))
        content = self.game_sii.read_text(encoding="utf-8")
        self.assertIn("engine_wear: 0", content)
        self.assertIn("wheels_wear[0]: 0", content)
        self.assertIn("engine_wear_unfixable: 0", content)

    def test_refuel_trucks_and_infinite(self):
        self.assertEqual(self.engine.refuel_all_trucks(infinite=False), 1)
        self.assertTrue(self.engine.save_changes(create_auto_backup=False))
        content = self.game_sii.read_text(encoding="utf-8")
        self.assertIn("fuel_relative: 1", content)

        self.assertEqual(self.engine.refuel_all_trucks(infinite=True), 1)
        self.assertTrue(self.engine.save_changes(create_auto_backup=False))
        content = self.game_sii.read_text(encoding="utf-8")
        self.assertIn("fuel_relative: &4f000000", content)

    def test_mileage_and_license_plate(self):
        self.assertGreater(self.engine.set_truck_mileage(123456), 0)
        self.assertGreater(self.engine.set_truck_license_plate("SPEED-1", "germany"), 0)
        self.assertTrue(self.engine.save_changes(create_auto_backup=False))
        content = self.game_sii.read_text(encoding="utf-8")
        self.assertIn("user_mileage: 123456", content)
        self.assertIn('"SPEED-1|germany"', content)

    def test_trailer_repair_and_cargo_mass(self):
        self.assertEqual(self.engine.get_cargo_mass(), 22500.0)
        self.assertGreater(self.engine.set_cargo_mass(0.0), 0)
        self.assertGreater(self.engine.repair_all_trailers(), 0)
        self.assertTrue(self.engine.save_changes(create_auto_backup=False))
        content = self.game_sii.read_text(encoding="utf-8")
        self.assertIn("cargo_mass: 0.0", content)
        self.assertIn("trailer_body_wear: 0", content)

    def test_backup_and_restore(self):
        bak_file = self.engine.create_backup(self.save_info)
        self.assertIsNotNone(bak_file)
        self.assertTrue(bak_file.is_file())

        backups = TruckToolsEngine.list_backups(self.save_dir)
        self.assertIn(bak_file, backups)

        # Modify file
        self.engine.set_money(999)
        self.engine.save_changes(create_auto_backup=False)
        self.assertEqual(self.engine.get_money(), 999)

        # Restore from backup
        self.assertTrue(TruckToolsEngine.restore_backup(bak_file, self.save_dir))
        self.engine.load_save(self.save_info)
        self.assertEqual(self.engine.get_money(), 500000)

    def test_player_truck_summary(self):
        summary = self.engine.get_player_truck_summary()
        self.assertEqual(summary["truck_id"], "_nameless.6137.6ea0")
        self.assertIn("Kenworth", summary["model_name"])
        self.assertIn("ISX15", summary["engine_name"])
        self.assertIn("18 Speed", summary["transmission_name"])
        self.assertIn("CAL-999", summary["license_plate"])


if __name__ == "__main__":
    unittest.main()
