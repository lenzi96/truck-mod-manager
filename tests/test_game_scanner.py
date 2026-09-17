import tempfile
import struct
from pathlib import Path
import unittest

from truck_mod_manager.core.game_scanner import GameScanner
from truck_mod_manager.core.models import GameType


class TestGameScannerVersionDetection(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_extract_pe_version_fixedfileinfo(self):
        # Create a mock PE file with VS_FIXEDFILEINFO
        pe_file = self.root / "eurotrucks2.exe"
        magic = b"\xbd\x04\xef\xfe"
        # VS_FIXEDFILEINFO:
        # dwSignature (4B), dwStrucVersion (4B), dwFileVersionMS (4B), dwFileVersionLS (4B), dwProductVersionMS (4B), dwProductVersionLS (4B)
        # For version 1.51.2.0:
        # FileVersionMS: (1 << 16) | 51 = 0x00010033
        # FileVersionLS: (2 << 16) | 0  = 0x00020000
        f_ms = (1 << 16) | 51
        f_ls = (2 << 16) | 0
        p_ms = f_ms
        p_ls = f_ls
        # VS_FIXEDFILEINFO has 13 DWORDs (52 bytes):
        payload = b"RANDOM_PADDING_BEFORE" + struct.pack(
            "<IIIIIIIIIIIII",
            0xFEEF04BD, 0x00010000, f_ms, f_ls, p_ms, p_ls,
            0, 0, 0x00040004, 1, 0, 0, 0
        ) + b"RANDOM_PADDING_AFTER"
        pe_file.write_bytes(payload)

        ver = GameScanner._extract_pe_version(pe_file)
        self.assertEqual(ver, "1.51.2")

    def test_extract_pe_version_ignores_corrupt_early_sig(self):
        pe_file = self.root / "eurotrucks2_false_pos.exe"
        f_ms = (1 << 16) | 51
        f_ls = (2 << 16) | 0
        corrupted = b"PADDING" + struct.pack(
            "<IIIIIIIIIIIII",
            0xFEEF04BD, 0x79812A75, (256 << 16) | 4, (3873 << 16) | 29952, 0, 0,
            0, 0, 0, 0, 0, 0, 0
        )
        valid = b"MORE_PADDING" + struct.pack(
            "<IIIIIIIIIIIII",
            0xFEEF04BD, 0x00010000, f_ms, f_ls, f_ms, f_ls,
            0, 0, 0x00040004, 1, 0, 0, 0
        )
        pe_file.write_bytes(corrupted + valid)
        ver = GameScanner._extract_pe_version(pe_file)
        self.assertEqual(ver, "1.51.2")

    def test_extract_pe_version_fallback_regex(self):
        pe_file = self.root / "dummy.exe"
        pe_file.write_bytes(b"some headers ... init ver.1.51.1.5s ... more binary data")
        ver = GameScanner._extract_pe_version(pe_file)
        self.assertEqual(ver, "1.51.1.5s")

    def test_extract_elf_version(self):
        elf_file = self.root / "eurotrucks2"
        elf_file.write_bytes(b"\x7fELF" + b"A" * 100 + b"Euro Truck Simulator 2 init ver.1.50.2s" + b"B" * 50)
        ver = GameScanner._extract_elf_version(elf_file)
        self.assertEqual(ver, "1.50.2s")

    def test_detect_version_from_logs_deep_line(self):
        # Multi-core CPUs produce 40+ lines of CPU/GPU logs before init ver.
        # Ensure parser does not stop at line 35
        log_dir = self.root / "Documents" / "Euro Truck Simulator 2"
        log_dir.mkdir(parents=True)
        log_file = log_dir / "game.log.txt"

        lines = [f"00:00:0{i:02d}.000 : [cpu] CPU core {i} initialized\n" for i in range(50)]
        lines.append("00:00:00.512 : [sys] Euro Truck Simulator 2 init ver.1.51.1.5s (rev. 12345)\n")
        lines.append("00:00:00.515 : [net] socket init\n")
        log_file.write_text("".join(lines), encoding="utf-8")

        ver = GameScanner.detect_version_from_logs([log_dir])
        self.assertEqual(ver, "1.51.1.5s")

    def test_detect_version_from_logs_backup_fallback(self):
        log_dir = self.root / "Euro Truck Simulator 2"
        log_dir.mkdir(parents=True)
        bak_file = log_dir / "game.log.bak.txt"
        bak_file.write_text("00:00:00.100 : init ver.1.49.2.15\n", encoding="utf-8")

        ver = GameScanner.detect_version_from_logs([log_dir])
        self.assertEqual(ver, "1.49.2.15")

    def test_detect_version_from_binaries(self):
        bin_dir = self.root / "bin" / "win_x64"
        bin_dir.mkdir(parents=True)
        exe_file = bin_dir / "eurotrucks2.exe"
        exe_file.write_bytes(b"padding ... init ver.1.51.0 ... end")

        ver = GameScanner.detect_version_from_binaries(self.root, GameType.ETS2)
        self.assertEqual(ver, "1.51.0")

    def test_find_game_returns_valid_truckgame(self):
        game = GameScanner.find_game(GameType.ETS2)
        self.assertIsNotNone(game)
        self.assertEqual(game.game_type, GameType.ETS2)
        self.assertEqual(game.name, "Euro Truck Simulator 2")

        game_ats = GameScanner.find_game(GameType.ATS)
        self.assertIsNotNone(game_ats)
        self.assertEqual(game_ats.game_type, GameType.ATS)
        self.assertEqual(game_ats.name, "American Truck Simulator")

    def test_deployer_load_all_mods_none_safe(self):
        from truck_mod_manager.core.deployer import ModDeployer
        mods = ModDeployer.load_all_mods(None)
        self.assertEqual(mods, [])


if __name__ == "__main__":
    unittest.main()

