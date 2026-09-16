"""
Unit tests for Installer Backend logic.
"""
import unittest
from truck_mod_manager.installer.installer_backend import InstallerDetector


class TestInstallerBackend(unittest.TestCase):
    def test_source_dir_exists(self):
        src_dir = InstallerDetector.get_source_dir()
        self.assertTrue(src_dir.exists())
        self.assertTrue((src_dir / "truck_mod_manager").exists())
        self.assertTrue((src_dir / "main.py").exists())

    def test_check_prerequisites(self):
        pre = InstallerDetector.check_prerequisites()
        self.assertTrue(pre["python_ok"])
        self.assertTrue(pre["pyqt6_ok"])
        self.assertTrue(pre["space_ok"])
        self.assertGreater(pre["free_space_mb"], 0)

    def test_check_existing_installations(self):
        ext = InstallerDetector.check_existing_installations()
        self.assertIn("is_installed", ext)
        self.assertIn("user_installed", ext)
        self.assertIn("system_installed", ext)


if __name__ == "__main__":
    unittest.main()
