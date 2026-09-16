"""
Unit tests for Mod Deletion functionality.
"""
import tempfile
import unittest
from pathlib import Path
from truck_mod_manager.core.deployer import ModDeployer
from truck_mod_manager.core.models import GameType, ScsMod, TruckGame


class TestDeleteMod(unittest.TestCase):
    def test_delete_mod_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging_dir = tmp / "staging"
            staging_dir.mkdir()
            game_mod_dir = tmp / "game_mods"
            game_mod_dir.mkdir()
            cache_icons_dir = tmp / "cache" / "icons"
            cache_icons_dir.mkdir(parents=True)

            # Create mod file in staging
            mod_file = staging_dir / "test_addon.scs"
            mod_file.write_text("dummy scs content")

            # Create symlink in game mod directory
            symlink_dest = game_mod_dir / "test_addon.scs"
            symlink_dest.symlink_to(mod_file)

            # Create cached icon
            icon_file = cache_icons_dir / "dummy_icon.png"
            icon_file.write_bytes(b"\x89PNG\r\n\x1a\n")

            game = TruckGame(
                game_type=GameType.ETS2,
                name="ETS2 Test",
                steam_appid="227300",
                mod_dir=str(game_mod_dir)
            )

            mod = ScsMod(
                file_path=str(mod_file),
                file_name="test_addon.scs",
                display_name="Test Addon",
                icon_path=str(icon_file),
                is_enabled=True
            )

            self.assertTrue(mod_file.exists())
            self.assertTrue(symlink_dest.exists())
            self.assertTrue(icon_file.exists())

            # Perform delete
            deleted = ModDeployer.delete_mod(game, mod)
            self.assertTrue(deleted)

            # Verify all traces were removed
            self.assertFalse(mod_file.exists(), "Staging mod file should be deleted")
            self.assertFalse(symlink_dest.exists(), "Game mod symlink should be removed")
            self.assertFalse(icon_file.exists(), "Cached icon should be cleaned up")


if __name__ == "__main__":
    unittest.main()
