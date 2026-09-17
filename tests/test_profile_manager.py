"""
Unit tests for ProfileManager, profile.sii decryption, and profile-specific mod configurations.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from truck_mod_manager.core.models import GameProfile, GameType, ScsMod, TruckGame
from truck_mod_manager.core.profile_manager import (
    ProfileManager,
    decode_profile_name,
    encode_profile_name,
    read_sii_active_mods,
    match_sii_active_mods_to_scs_mods,
)


class TestProfileManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.user_dir = self.temp_dir / "user_dir"
        self.user_dir.mkdir(parents=True)

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_decode_profile_name(self):
        # Known ETS2 / ATS hex folder names
        self.assertEqual(decode_profile_name("50726F6D6F6473"), "Promods")
        self.assertEqual(decode_profile_name("4D6172696F2046726161747A"), "Mario Fraatz")
        self.assertEqual(decode_profile_name("4D6172696F"), "Mario")
        self.assertEqual(decode_profile_name("4D6172696F33323132"), "Mario3212")

        # Fallbacks for non-hex or odd length
        self.assertEqual(decode_profile_name("NotHex"), "NotHex")
        self.assertEqual(decode_profile_name("123"), "123")
        self.assertEqual(decode_profile_name(""), "")

    def test_encode_profile_name(self):
        self.assertEqual(encode_profile_name("Promods"), "50726F6D6F6473")
        # Roundtrip
        original = "Trucker 2026 - Test"
        self.assertEqual(decode_profile_name(encode_profile_name(original)), original)

    def test_list_profiles_discovery(self):
        local_profiles = self.user_dir / "profiles"
        steam_profiles = self.user_dir / "steam_profiles"
        local_profiles.mkdir()
        steam_profiles.mkdir()

        (local_profiles / "50726F6D6F6473").mkdir()
        (local_profiles / "4D6172696F").mkdir()
        (self.user_dir / "profiles(1.50.2s).bak").mkdir()
        (local_profiles / "profiles(1.49).bak").mkdir()

        (steam_profiles / "4D6172696F33323132").mkdir()

        game = TruckGame(
            game_type=GameType.ATS,
            name="American Truck Simulator",
            steam_appid="270880",
            user_dir=str(self.user_dir),
        )

        profiles = ProfileManager.list_profiles(game)
        self.assertEqual(len(profiles), 3)

        names = [p.name for p in profiles]
        self.assertIn("Promods", names)
        self.assertIn("Mario", names)
        self.assertIn("Mario3212", names)

        cloud_p = next(p for p in profiles if p.name == "Mario3212")
        self.assertTrue(cloud_p.is_steam_cloud)

        local_p = next(p for p in profiles if p.name == "Promods")
        self.assertFalse(local_p.is_steam_cloud)

    def test_fallback_profile_when_empty(self):
        empty_dir = self.temp_dir / "empty_user_dir"
        empty_dir.mkdir()
        game = TruckGame(
            game_type=GameType.ETS2,
            name="Euro Truck Simulator 2",
            steam_appid="227300",
            user_dir=str(empty_dir),
        )

        profiles = ProfileManager.list_profiles(game)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].id, "default")
        self.assertEqual(profiles[0].name, "Standard-Profil")

    def test_read_sii_active_mods_plain(self):
        sii_file = self.temp_dir / "profile.sii"
        sii_content = """SiiNunit
{
user_profile : _nameless {
 active_mods: 3
 active_mods[0]: "promods-models|ProMods Models"
 active_mods[1]: "promods-map|ProMods Map"
 active_mods[2]: "promods-def|ProMods Def"
}
}"""
        sii_file.write_text(sii_content, encoding="utf-8")

        # In SCS Mod Manager, active_mods[2] (def) is loaded last, so it has HIGHEST priority (#1)
        mods_order = read_sii_active_mods(sii_file)
        self.assertEqual(len(mods_order), 3)
        self.assertEqual(mods_order[0], ("promods-def", "ProMods Def"))
        self.assertEqual(mods_order[1], ("promods-map", "ProMods Map"))
        self.assertEqual(mods_order[2], ("promods-models", "ProMods Models"))

    def test_match_sii_active_mods_to_scs_mods(self):
        m_def = ScsMod(file_path="/tmp/promods-def.scs", file_name="promods-def.scs", display_name="ProMods Def")
        m_map = ScsMod(file_path="/tmp/promods-map.scs", file_name="promods-map.scs", display_name="ProMods Map")
        m_models = ScsMod(file_path="/tmp/promods-models.scs", file_name="promods-models.scs", display_name="ProMods Models")
        m_unused = ScsMod(file_path="/tmp/other.scs", file_name="other.scs", display_name="Other Mod")

        all_mods = [m_unused, m_models, m_map, m_def]
        sii_tuples = [
            ("promods-def", "ProMods Def"),
            ("promods-map", "ProMods Map"),
            ("promods-models", "ProMods Models"),
        ]

        result = match_sii_active_mods_to_scs_mods(sii_tuples, all_mods)
        active = [m for m in result if m.is_enabled]
        inactive = [m for m in result if not m.is_enabled]

        self.assertEqual(len(active), 3)
        self.assertEqual(active[0].file_name, "promods-def.scs")
        self.assertEqual(active[0].priority, 1)

        self.assertEqual(active[1].file_name, "promods-map.scs")
        self.assertEqual(active[1].priority, 2)

        self.assertEqual(active[2].file_name, "promods-models.scs")
        self.assertEqual(active[2].priority, 3)

        self.assertEqual(len(inactive), 1)
        self.assertEqual(inactive[0].file_name, "other.scs")
        self.assertFalse(inactive[0].is_enabled)
        self.assertEqual(inactive[0].priority, 0)

    def test_save_and_apply_profile_state(self):
        mod1 = ScsMod(file_path="/tmp/mod1.scs", file_name="mod1.scs", display_name="Mod One", is_enabled=True, priority=1)
        mod2 = ScsMod(file_path="/tmp/mod2.scs", file_name="mod2.scs", display_name="Mod Two", is_enabled=True, priority=2)
        mod3 = ScsMod(file_path="/tmp/mod3.scs", file_name="mod3.scs", display_name="Mod Three", is_enabled=False, priority=0)

        all_mods = [mod1, mod2, mod3]
        profile_id = "test_profile_123"
        profile = GameProfile(id=profile_id, name="Test Profile", path=None, game_type=GameType.ATS)

        # Save state: mod1 and mod2 active (mod1 prio 1, mod2 prio 2)
        saved_path = ProfileManager.save_profile_state(GameType.ATS, profile_id, all_mods, profile_name="Test Profile")
        self.assertTrue(saved_path.exists())

        # Modify mod state in memory
        mod1.is_enabled = False
        mod1.priority = 0
        mod3.is_enabled = True
        mod3.priority = 1

        # Re-apply profile state using profile object
        reordered = ProfileManager.apply_profile_state(GameType.ATS, profile, [mod1, mod2, mod3])

        # mod1 and mod2 should be active again, mod3 inactive
        active = [m for m in reordered if m.is_enabled]
        inactive = [m for m in reordered if not m.is_enabled]

        self.assertEqual(len(active), 2)
        self.assertEqual(active[0].file_name, "mod1.scs")
        self.assertEqual(active[0].priority, 1)
        self.assertEqual(active[1].file_name, "mod2.scs")
        self.assertEqual(active[1].priority, 2)

        self.assertEqual(len(inactive), 1)
        self.assertEqual(inactive[0].file_name, "mod3.scs")
        self.assertFalse(inactive[0].is_enabled)
        self.assertEqual(inactive[0].priority, 0)

        if saved_path.exists():
            saved_path.unlink()

    def test_match_sii_workshop_mods(self):
        # Workshop ID: 3249577826 -> hex: 00000000C1B09F62
        ws_mod1 = ScsMod(
            file_path="/tmp/workshop/3249577826/150_icons.zip",
            file_name="mod_workshop_package.00000000C1B09F62",
            display_name="150 Icons",
            is_workshop=True,
            workshop_id="3249577826",
        )
        # Workshop ID: 812000379 -> hex: 000000003066247B
        ws_mod2 = ScsMod(
            file_path="/tmp/workshop/812000379/universal.zip",
            file_name="mod_workshop_package.000000003066247B",
            display_name="Universal",
            is_workshop=True,
            workshop_id="812000379",
        )
        local_mod = ScsMod(
            file_path="/tmp/mods/Apple Siri.scs",
            file_name="Apple Siri",
            display_name="Apple Siri",
            is_workshop=False,
        )

        all_mods = [local_mod, ws_mod1, ws_mod2]
        sii_tuples = [
            ("mod_workshop_package.00000000C1B09F62", "Return Old Icons"),
            ("Apple Siri", "Apple Siri"),
            ("mod_workshop_package.000000003066247B", "1000 XP Park v1.51"),
        ]

        result = match_sii_active_mods_to_scs_mods(sii_tuples, all_mods)
        active = [m for m in result if m.is_enabled]
        self.assertEqual(len(active), 3)

        self.assertEqual(active[0].file_name, "mod_workshop_package.00000000C1B09F62")
        self.assertEqual(active[0].priority, 1)

        self.assertEqual(active[1].file_name, "Apple Siri")
        self.assertEqual(active[1].priority, 2)

        self.assertEqual(active[2].file_name, "mod_workshop_package.000000003066247B")
        self.assertEqual(active[2].priority, 3)
        # Verify generic name 'Universal' was replaced with official profile name
        self.assertEqual(active[2].display_name, "1000 XP Park v1.51")

    def test_deployer_skips_workshop_mods(self):
        from truck_mod_manager.core.deployer import ModDeployer

        staging_dir = self.temp_dir / "staging"
        mod_dir = self.temp_dir / "mod"
        staging_dir.mkdir()
        mod_dir.mkdir()

        # Create dummy local mod in staging
        local_file = staging_dir / "test_local.scs"
        local_file.write_text("dummy scs")

        local_mod = ScsMod(
            file_path=str(local_file),
            file_name="test_local.scs",
            display_name="Test Local",
            is_enabled=True,
            is_workshop=False,
        )
        ws_mod = ScsMod(
            file_path="/fake/workshop/3249577826/content.zip",
            file_name="mod_workshop_package.00000000C1B09F62",
            display_name="Test Workshop",
            is_enabled=True,
            is_workshop=True,
            workshop_id="3249577826",
        )

        game = TruckGame(
            game_type=GameType.ATS,
            name="American Truck Simulator",
            steam_appid="270880",
            mod_dir=str(mod_dir),
        )

        # Deploy both active mods
        success, msg = ModDeployer.deploy(game, [local_mod, ws_mod])
        self.assertTrue(success)

        # Local mod should be symlinked in mod_dir
        self.assertTrue((mod_dir / "test_local.scs").exists())

        # Workshop mod should NOT be symlinked in mod_dir
        self.assertFalse((mod_dir / "mod_workshop_package.00000000C1B09F62").exists())
        self.assertFalse((mod_dir / "3249577826").exists())

        # Workshop delete should be protected
        self.assertFalse(ModDeployer.delete_mod(game, ws_mod))

    def test_read_save_active_mods(self):
        profile_dir = self.temp_dir / "profile_with_save"
        save_slot = profile_dir / "save" / "autosave"
        save_slot.mkdir(parents=True)
        info_sii = save_slot / "info.sii"

        info_content = """SiiNunit
{
save_container : _nameless.save {
 dependencies: 3
 dependencies[0]: "mod|promods-assets|ProMods Assets"
 dependencies[1]: "mod|promods-def|ProMods Definition"
 dependencies[2]: "mod|promods-map|ProMods Map"
}
}"""
        info_sii.write_text(info_content, encoding="utf-8")

        result = ProfileManager.read_save_active_mods(profile_dir)
        self.assertEqual(len(result), 3)
        # Mounting order was 0: assets, 1: def, 2: map.
        # Highest priority (Priority 1) is the last mounted (map -> def -> assets)
        self.assertEqual(result[0], ("promods-map", "ProMods Map"))
        self.assertEqual(result[1], ("promods-def", "ProMods Definition"))
        self.assertEqual(result[2], ("promods-assets", "ProMods Assets"))

    def test_read_log_active_mods(self):
        log_file = self.temp_dir / "game.log.txt"
        log_content = """00:00:01.000 : [mod_package_manager] Mod "ProMods Assets Package" has been mounted. (package_name: promods-assets-v270, version: 2.70, source: User mods)
00:00:02.000 : [mod_package_manager] Mod "ProMods Definition Package" has been mounted. (package_name: promods-def-v270, version: 2.70, source: User mods)
00:00:03.000 : [mod_package_manager] Mod "ProMods Background Map" has been mounted. (package_name: promods_bg, version: 1.0, source: User mods)
"""
        log_file.write_text(log_content, encoding="utf-8")

        result = ProfileManager.read_log_active_mods(log_file)
        self.assertEqual(len(result), 3)
        # Last mounted is highest priority (#1)
        self.assertEqual(result[0], ("promods_bg", "ProMods Background Map"))
        self.assertEqual(result[1], ("promods-def-v270", "ProMods Definition Package"))
        self.assertEqual(result[2], ("promods-assets-v270", "ProMods Assets Package"))

    def test_match_sii_missing_mod_placeholder(self):
        installed_mod = ScsMod(
            file_path="/tmp/promods-def.scs",
            file_name="promods-def.scs",
            display_name="ProMods Definition Package"
        )
        all_mods = [installed_mod]

        sii_tuples = [
            ("promods-def", "ProMods Definition Package"),
            ("missing-pack.scs", "Missing Map Addon"),
        ]

        result = ProfileManager.match_sii_active_mods_to_scs_mods(sii_tuples, all_mods)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].file_name, "promods-def.scs")
        self.assertFalse(result[0].is_missing)
        self.assertEqual(result[0].priority, 1)

        self.assertEqual(result[1].file_name, "missing-pack.scs")
        self.assertEqual(result[1].display_name, "Missing Map Addon")
        self.assertTrue(result[1].is_missing)
        self.assertTrue(result[1].is_enabled)
        self.assertEqual(result[1].priority, 2)

    def test_auto_sort_hierarchy(self):
        from truck_mod_manager.core.load_order import LoadOrderManager

        bg = ScsMod(file_path="", file_name="promods_background.scs", display_name="ProMods High Quality Background Map")
        ui = ScsMod(file_path="", file_name="minimal_advisor.scs", display_name="Minimal Route Advisor UI")
        sound = ScsMod(file_path="", file_name="sound_fixes.scs", display_name="Sound Fixes Pack")
        weather = ScsMod(file_path="", file_name="weather.scs", display_name="Realistic Brutal Weather")
        physics = ScsMod(file_path="", file_name="physics.scs", display_name="Truck Physics Mod")
        traffic = ScsMod(file_path="", file_name="ai_traffic.scs", display_name="AI Traffic Pack by Jazzycat")
        truck = ScsMod(file_path="", file_name="scania_rjld.scs", display_name="Scania R & Streamline Modification")
        rc = ScsMod(file_path="", file_name="promods_poland_rc.scs", display_name="ProMods Poland Rebuilding Road Connection")
        pm_def = ScsMod(file_path="", file_name="promods-def-v270.scs", display_name="ProMods Definition Package")
        pm_map = ScsMod(file_path="", file_name="promods-map-v270.scs", display_name="ProMods Map Package")
        pm_model3 = ScsMod(file_path="", file_name="promods-model3-v270.scs", display_name="ProMods Models Package 3")
        pm_model1 = ScsMod(file_path="", file_name="promods-model1-v270.scs", display_name="ProMods Models Package 1")
        pm_assets = ScsMod(file_path="", file_name="promods-assets-v270.scs", display_name="ProMods Assets Package")

        for m in (bg, ui, sound, weather, physics, traffic, truck, rc, pm_def, pm_map, pm_model3, pm_model1, pm_assets):
            m.is_enabled = True

        all_unordered = [pm_assets, truck, sound, pm_def, bg, traffic, pm_model1, weather, pm_map, rc, physics, ui, pm_model3]
        sorted_mods = LoadOrderManager.auto_sort(all_unordered)
        active_sorted = [m for m in sorted_mods if m.is_enabled]

        # Verify strict priority sequence:
        # 1. Background Map
        self.assertEqual(active_sorted[0].display_name, bg.display_name)
        # 2. UI
        self.assertEqual(active_sorted[1].display_name, ui.display_name)
        # 3. Sound
        self.assertEqual(active_sorted[2].display_name, sound.display_name)
        # 4. Weather
        self.assertEqual(active_sorted[3].display_name, weather.display_name)
        # 5. Physics
        self.assertEqual(active_sorted[4].display_name, physics.display_name)
        # 6. AI Traffic
        self.assertEqual(active_sorted[5].display_name, traffic.display_name)
        # 7. Trucks
        self.assertEqual(active_sorted[6].display_name, truck.display_name)
        # 8. Road Connection (above maps)
        self.assertEqual(active_sorted[7].display_name, rc.display_name)
        # 9. Map packages: Def > Map > Model 3 > Model 1 > Assets
        self.assertEqual(active_sorted[8].display_name, pm_def.display_name)
        self.assertEqual(active_sorted[9].display_name, pm_map.display_name)
        self.assertEqual(active_sorted[10].display_name, pm_model3.display_name)
        self.assertEqual(active_sorted[11].display_name, pm_model1.display_name)
        self.assertEqual(active_sorted[12].display_name, pm_assets.display_name)

    def test_get_most_recent_profile(self):
        p1 = GameProfile(id="p1", name="Mario", path=None, last_modified=100.0)
        p2 = GameProfile(id="p2", name="Promods", path=None, last_modified=500.0)
        p3 = GameProfile(id="p3", name="Vanilla", path=None, last_modified=200.0)

        recent = ProfileManager.get_most_recent_profile([p1, p2, p3])
        self.assertIsNotNone(recent)
        self.assertEqual(recent.id, "p2")
        self.assertEqual(recent.name, "Promods")


if __name__ == "__main__":
    unittest.main()
