"""
Unit tests for LoadOrderManager.
"""
import unittest
from truck_mod_manager.core.load_order import LoadOrderManager
from truck_mod_manager.core.models import ModCategory, ScsMod


class TestLoadOrder(unittest.TestCase):
    def test_auto_sort_categories(self):
        ui_mod = ScsMod(file_path="ui.scs", file_name="ui.scs", display_name="Minimal Route Advisor", categories=[ModCategory.UI], is_enabled=True)
        sound_mod = ScsMod(file_path="sound.scs", file_name="sound.scs", display_name="V8 Sound Mod", categories=[ModCategory.SOUND], is_enabled=True)
        truck_mod = ScsMod(file_path="truck.scs", file_name="truck.scs", display_name="Scania RJL", categories=[ModCategory.TRUCK], is_enabled=True)
        map_def = ScsMod(file_path="promods-def.scs", file_name="promods-def.scs", display_name="ProMods Definition", categories=[ModCategory.DEF, ModCategory.MAP], is_enabled=True)
        map_assets = ScsMod(file_path="promods-assets.scs", file_name="promods-assets.scs", display_name="ProMods Assets", categories=[ModCategory.MODELS, ModCategory.MAP], is_enabled=True)

        mods = [map_assets, truck_mod, ui_mod, map_def, sound_mod]
        sorted_mods = LoadOrderManager.auto_sort(mods)

        # UI should be #1 (highest priority)
        self.assertEqual(sorted_mods[0].display_name, "Minimal Route Advisor")
        self.assertEqual(sorted_mods[0].priority, 1)

        # Sound should be above Truck
        sound_idx = next(i for i, m in enumerate(sorted_mods) if m.display_name == "V8 Sound Mod")
        truck_idx = next(i for i, m in enumerate(sorted_mods) if m.display_name == "Scania RJL")
        self.assertLess(sound_idx, truck_idx)

        # Truck should be above Map Def
        map_def_idx = next(i for i, m in enumerate(sorted_mods) if m.display_name == "ProMods Definition")
        self.assertLess(truck_idx, map_def_idx)

        # Map Def should be above Map Assets
        map_assets_idx = next(i for i, m in enumerate(sorted_mods) if m.display_name == "ProMods Assets")
        self.assertLess(map_def_idx, map_assets_idx)

    def test_load_order_moves(self):
        mod1 = ScsMod(file_path="1.scs", file_name="1.scs", display_name="Mod 1", is_enabled=True, priority=1)
        mod2 = ScsMod(file_path="2.scs", file_name="2.scs", display_name="Mod 2", is_enabled=True, priority=2)
        mod3 = ScsMod(file_path="3.scs", file_name="3.scs", display_name="Mod 3", is_enabled=True, priority=3)

        mods = [mod1, mod2, mod3]

        # Move mod2 up
        LoadOrderManager.move_up(mods, 1)
        self.assertEqual(mods[0].display_name, "Mod 2")
        self.assertEqual(mods[0].priority, 1)
        self.assertEqual(mods[1].display_name, "Mod 1")
        self.assertEqual(mods[1].priority, 2)

        # Move to bottom
        LoadOrderManager.move_to_bottom(mods, 0)
        self.assertEqual(mods[-1].display_name, "Mod 2")
        self.assertEqual(mods[-1].priority, 3)


if __name__ == "__main__":
    unittest.main()
