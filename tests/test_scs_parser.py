"""
Unit tests for ScsParser.
"""
import tempfile
import unittest
import zipfile
from pathlib import Path
from truck_mod_manager.core.models import ModCategory
from truck_mod_manager.core.scs_parser import ScsParser


SAMPLE_MANIFEST = """
SiiNunit
{
mod_package : .promods.def {
    package_version: "2.68"
    display_name: "ProMods Definition Package"
    author: "ProMods Team"
    category[]: "map"
    category[]: "def"
    icon: "promods.png"
    description_file: "info.txt"
    mp_mod_optional: true
    compatible_versions[]: "1.50.*"
}
}
"""


class TestScsParser(unittest.TestCase):
    def test_parse_manifest_sii(self):
        meta = ScsParser.parse_manifest_sii(SAMPLE_MANIFEST)
        self.assertEqual(meta["display_name"], "ProMods Definition Package")
        self.assertEqual(meta["package_version"], "2.68")
        self.assertEqual(meta["author"], "ProMods Team")
        self.assertIn(ModCategory.MAP, meta["categories"])
        self.assertIn(ModCategory.DEF, meta["categories"])
        self.assertEqual(meta["icon"], "promods.png")
        self.assertEqual(meta["description_file"], "info.txt")
        self.assertTrue(meta["mp_mod_optional"])
        self.assertIn("1.50.*", meta["compatible_versions"])

    def test_infer_categories_from_files(self):
        truck_files = ["def/vehicle/truck/scania.r/sound.sii", "vehicle/truck/scania_r/truck.pmg"]
        cats = ScsParser.infer_categories_from_files(truck_files)
        self.assertIn(ModCategory.TRUCK, cats)
        self.assertIn(ModCategory.SOUND, cats)

        sound_files = ["sound/truck/v8_engine.bank"]
        cats_sound = ScsParser.infer_categories_from_files(sound_files)
        self.assertIn(ModCategory.SOUND, cats_sound)

    def test_clean_description(self):
        raw = "[b]Titel[/b] [color=#ff0000]Wichtig:[/color] Tolle Mod! [url=http://example.com]Link[/url]"
        clean = ScsParser.clean_description(raw)
        self.assertNotIn("[b]", clean)
        self.assertNotIn("[/b]", clean)
        self.assertNotIn("[color=", clean)
        self.assertEqual(clean, "Titel Wichtig: Tolle Mod! Link")

    def test_zip_mod_parsing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scs_path = Path(tmpdir) / "test_mod.scs"
            with zipfile.ZipFile(scs_path, "w") as z:
                z.writestr("manifest.sii", SAMPLE_MANIFEST)
                z.writestr("info.txt", "Eine wunderbare Mod für ETS2.")
                z.writestr("def/vehicle/truck/test.sii", "dummy content")

            mod = ScsParser.parse_mod_file(scs_path)
            self.assertTrue(mod.has_manifest)
            self.assertEqual(mod.display_name, "ProMods Definition Package")
            self.assertEqual(mod.package_version, "2.68")
            self.assertEqual(mod.author, "ProMods Team")
            self.assertEqual(mod.description, "Eine wunderbare Mod für ETS2.")
            self.assertEqual(len(mod.internal_files), 3)


if __name__ == "__main__":
    unittest.main()
