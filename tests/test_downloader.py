"""
Unit tests for ModDownloader and ArchiveExtractor.
"""
import tempfile
import unittest
import zipfile
from pathlib import Path

from truck_mod_manager.core.downloader import (
    ArchiveExtractor, format_size
)


class TestDownloader(unittest.TestCase):
    def test_format_size(self):
        self.assertEqual(format_size(500), "500 B")
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(format_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_size(1024 * 1024 * 1024 * 2), "2.00 GB")

    def test_deploy_scs_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_file = Path(tmpdir) / "test_mod.scs"
            src_file.write_text("dummy scs content")

            target_dir = Path(tmpdir) / "target_mods"
            deployed = ArchiveExtractor.deploy_or_extract(src_file, target_dir)

            self.assertEqual(len(deployed), 1)
            self.assertEqual(deployed[0].name, "test_mod.scs")
            self.assertTrue(deployed[0].exists())
            self.assertEqual(deployed[0].read_text(), "dummy scs content")

    def test_deploy_zip_with_nested_scs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a zip containing two .scs files
            zip_path = Path(tmpdir) / "promods_pack.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("subfolder/promods-def-v270.scs", "def data")
                zf.writestr("subfolder/promods-map-v270.scs", "map data")
                zf.writestr("readme.txt", "instructions")

            target_dir = Path(tmpdir) / "target_mods"
            deployed = ArchiveExtractor.deploy_or_extract(zip_path, target_dir)

            deployed_names = [d.name for d in deployed]
            self.assertIn("promods-def-v270.scs", deployed_names)
            self.assertIn("promods-map-v270.scs", deployed_names)
            self.assertNotIn("readme.txt", deployed_names)

    def test_deploy_direct_zip_mod(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Zip with manifest.sii directly (standard SCS zip mod)
            zip_path = Path(tmpdir) / "tuning_pack.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("manifest.sii", "SiiNunit {}")
                zf.writestr("def/vehicle/truck.sii", "truck")

            target_dir = Path(tmpdir) / "target_mods"
            deployed = ArchiveExtractor.deploy_or_extract(zip_path, target_dir)

            self.assertEqual(len(deployed), 1)
            self.assertEqual(deployed[0].name, "tuning_pack.zip")
            self.assertTrue(deployed[0].exists())


if __name__ == "__main__":
    unittest.main()
