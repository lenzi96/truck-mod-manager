"""
Unit tests for LogAnalyzer.
"""
import tempfile
import unittest
from pathlib import Path
from truck_mod_manager.core.log_analyzer import LogAnalyzer


SAMPLE_LOG = """
00:00:00.000 : Euro Truck Simulator 2 init ver.1.50.2.3s (rev. 12345)
00:00:01.100 : [net] Server listening on port 27015
00:00:05.200 : <WARNING> [model] Model geometry '/vehicle/truck/upgrade/wheel/rim.pmg' has obsolete format - update it with Conversion Tools!
00:00:10.500 : <ERROR> [fs] Failed to open file '/def/vehicle/truck/volvo/sound.sii' in the read_only mode.
00:00:15.800 : <ERROR> [sound] Sound bank '/sound/truck/scania.bank' not found!
00:00:20.900 : <ERROR> [unit] File 'engine.sii': dangling pointer to 'torque_curve'
00:01:00.000 : <ERROR> Crash dump generated: /home/julian/.local/share/Euro Truck Simulator 2/game.crash.txt
"""


class TestLogAnalyzer(unittest.TestCase):
    def test_log_analyzer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "game.log.txt"
            log_file.write_text(SAMPLE_LOG, encoding="utf-8")

            issues, summary = LogAnalyzer.analyze_file(log_file)
            self.assertEqual(summary["game_version"], "1.50.2.3s")
            self.assertEqual(summary["error_count"], 4)
            self.assertEqual(summary["warning_count"], 1)
            self.assertTrue(summary["crashed"])

            # Check suggestions
            fs_issue = next(i for i in issues if i.subsystem == "fs")
            self.assertIn("Datei wird von einer Mod referenziert", fs_issue.suggestion)

            sound_issue = next(i for i in issues if i.subsystem == "sound")
            self.assertIn("Sound-Bank fehlt", sound_issue.suggestion)

            unit_issue = next(i for i in issues if i.subsystem == "unit")
            self.assertIn("Defekte Definitionsdatei", unit_issue.suggestion)


if __name__ == "__main__":
    unittest.main()
