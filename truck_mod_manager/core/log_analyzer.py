"""
Game Log & Crash Analyzer for Euro Truck Simulator 2 and American Truck Simulator.
Parses game.log.txt, highlights errors/warnings, and detects common SCS crash causes.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from truck_mod_manager.core.models import LogIssue


COMMON_FIXES: List[Tuple[re.Pattern, str, str]] = [
    (
        re.compile(r"Failed to open file.*in the read_only mode", re.IGNORECASE),
        "fs",
        "Eine Datei wird von einer Mod referenziert, existiert aber nicht. Häufig bei veralteten Mods oder fehlender Map-Verbindung."
    ),
    (
        re.compile(r"dangling pointer|unknown unit type", re.IGNORECASE),
        "unit",
        "Defekte Definitionsdatei! Eine Mod greift auf ein nicht existierendes Bauteil zu. Verursacht häufig CTD beim LKW-Händler."
    ),
    (
        re.compile(r"Sound bank.*not found", re.IGNORECASE),
        "sound",
        "FMOD Sound-Bank fehlt oder ist inkompatibel. Sound-Mod für die aktuelle Spielversion aktualisieren."
    ),
    (
        re.compile(r"obsolete format", re.IGNORECASE),
        "model",
        "Veraltetes 3D-Modellformat (.pmg). Meist nicht fatal, kann aber Frame-Drops verursachen."
    ),
    (
        re.compile(r"pool size|memory.*exhausted|allocation failed", re.IGNORECASE),
        "memory",
        "Speicherlimit erreicht! Füge '-mm_pool_size 4096' oder '-mm_pool_size 8192' zu den Startoptionen hinzu."
    ),
    (
        re.compile(r"texture.*not found|unable to load.*\.tobj", re.IGNORECASE),
        "texture",
        "Fehlende Textur. LKW/Trailer könnte im Spiel rosa/schwarz erscheinen."
    ),
]


class LogAnalyzer:
    """Parses and analyzes SCS game.log.txt."""

    LOG_PATTERN = re.compile(
        r"^(?P<timestamp>\d\d:\d\d:\d\d\.\d\d\d)\s*:\s*(?:<(?P<level>[A-Z]+)>\s*)?(?:\[(?P<subsystem>[a-zA-Z0-9_-]+)\]\s*)?(?P<message>.*)$"
    )

    @classmethod
    def analyze_file(cls, log_path: Path) -> Tuple[List[LogIssue], Dict[str, any]]:
        """
        Parses the log file.
        Returns a list of LogIssue items and a diagnostic summary dictionary.
        """
        if not log_path.exists() or not log_path.is_file():
            return [], {
                "exists": False,
                "total_lines": 0,
                "error_count": 0,
                "warning_count": 0,
                "game_version": "Unbekannt",
                "crashed": False,
                "summary": "Logdatei nicht gefunden."
            }

        issues: List[LogIssue] = []
        error_count = 0
        warning_count = 0
        game_version = "Unbekannt"
        crashed = False
        total_lines = 0

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_no, raw_line in enumerate(f, start=1):
                    total_lines += 1
                    line = raw_line.strip()
                    if not line:
                        continue

                    # Extract Game Version (usually in first 20 lines)
                    if line_no < 30 and ("Euro Truck Simulator 2 init ver." in line or "American Truck Simulator init ver." in line):
                        match_ver = re.search(r"init ver\.([0-9\.\w]+)", line)
                        if match_ver:
                            game_version = match_ver.group(1)

                    # Check for crash indicator
                    if "Crash dump generated" in line or "SIGSEGV" in line or "Game crashed" in line:
                        crashed = True

                    match = cls.LOG_PATTERN.match(line)
                    level = ""
                    subsystem = ""
                    msg = line

                    if match:
                        level = match.group("level") or ""
                        subsystem = match.group("subsystem") or ""
                        msg = match.group("message") or line
                    elif "<ERROR>" in line:
                        level = "ERROR"
                    elif "<WARNING>" in line:
                        level = "WARNING"

                    if level == "ERROR":
                        error_count += 1
                        suggestion = cls._find_suggestion(msg)
                        issues.append(LogIssue(
                            level="ERROR",
                            subsystem=subsystem or "general",
                            message=msg,
                            line_number=line_no,
                            suggestion=suggestion,
                        ))
                    elif level == "WARNING":
                        warning_count += 1
                        suggestion = cls._find_suggestion(msg)
                        issues.append(LogIssue(
                            level="WARNING",
                            subsystem=subsystem or "general",
                            message=msg,
                            line_number=line_no,
                            suggestion=suggestion,
                        ))

        except Exception as e:
            print(f"[LogAnalyzer] Error reading log: {e}")

        summary = {
            "exists": True,
            "total_lines": total_lines,
            "error_count": error_count,
            "warning_count": warning_count,
            "game_version": game_version,
            "crashed": crashed,
            "summary": f"{error_count} Fehler, {warning_count} Warnungen gefunden." + (" (Absturz erkannt!)" if crashed else "")
        }

        return issues, summary

    @classmethod
    def _find_suggestion(cls, message: str) -> str:
        for pattern, _, suggestion in COMMON_FIXES:
            if pattern.search(message):
                return suggestion
        return ""

    @classmethod
    def get_clean_log_snippet(cls, log_path: Path, max_lines: int = 150) -> str:
        """Returns the last max_lines lines from the log for easy forum copy/paste."""
        if not log_path.exists():
            return "Logdatei existiert nicht."
        try:
            lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            return "\n".join(lines[-max_lines:])
        except Exception as e:
            return f"Fehler beim Lesen des Logs: {e}"
