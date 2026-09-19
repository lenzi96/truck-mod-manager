"""
Truck Tools Core Engine for Euro Truck Simulator 2 and American Truck Simulator.
Port of CoffeSiberian/truck-tools to pure Python / PyQt6 on Linux.
Reads, decrypts, parses, modifies, and saves SCS savegame files (game.sii).
"""
from dataclasses import dataclass, field
import datetime
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional, Set, Tuple

from truck_mod_manager.core.models import GameProfile, GameType
from truck_mod_manager.core.profile_manager import decrypt_sii, decode_profile_name


@dataclass
class SaveGameInfo:
    """Represents a discovered ETS2/ATS savegame."""
    folder_name: str
    display_name: str
    save_dir: Path
    game_sii_path: Path
    info_sii_path: Optional[Path]
    modified_time: datetime.datetime
    save_time: Optional[datetime.datetime] = None
    is_autosave: bool = False
    is_quicksave: bool = False


@dataclass
class TruckInfo:
    """Represents a truck found in the save file."""
    truck_id: str
    brand_and_model: str
    is_assigned_to_player: bool = False
    license_plate: str = ""
    fuel_relative: float = 1.0
    mileage_km: float = 0.0
    engine_wear: float = 0.0
    transmission_wear: float = 0.0
    cabin_wear: float = 0.0
    chassis_wear: float = 0.0
    wheels_wear: float = 0.0
    engine_name: str = ""
    transmission_name: str = ""


@dataclass
class TrailerInfo:
    """Represents a trailer found in the save file."""
    trailer_id: str
    name: str = "Auflieger"
    cargo_mass_kg: float = 0.0
    license_plate: str = ""
    body_wear: float = 0.0
    wheels_wear: float = 0.0
    is_assigned_to_player: bool = False


class TruckToolsEngine:
    """
    Engine to inspect and edit ETS2 / ATS game.sii savegames.
    """

    def __init__(self):
        self.current_save: Optional[SaveGameInfo] = None
        self.lines: List[str] = []
        self._raw_text: str = ""
        self._is_loaded: bool = False

        # Load embedded trucks database
        self.trucks_data_ets2: Dict[str, Any] = self._load_embedded_data("trucks_data_ets2.json")
        self.trucks_data_ats: Dict[str, Any] = self._load_embedded_data("trucks_data_ats.json")

    def _load_embedded_data(self, filename: str) -> Dict[str, Any]:
        data_path = Path(__file__).parent.parent / "resources" / "data" / filename
        if data_path.is_file():
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[TruckTools] Error loading {filename}: {e}")
        return {}

    # -------------------------------------------------------------------------
    # Savegame Discovery & Loading
    # -------------------------------------------------------------------------

    @classmethod
    def list_savegames(cls, profile: GameProfile) -> List[SaveGameInfo]:
        """Discovers all savegames within a profile folder, sorted newest first."""
        results: List[SaveGameInfo] = []
        if not profile or not profile.path or not profile.path.is_dir():
            return results

        save_base = profile.path / "save"
        if not save_base.is_dir():
            return results

        try:
            entries = list(save_base.iterdir())
        except Exception:
            return results

        for entry in entries:
            if not entry.is_dir():
                continue
            game_sii = entry / "game.sii"
            if not game_sii.is_file():
                continue

            info_sii = entry / "info.sii"
            if not info_sii.is_file():
                info_sii = None

            folder_name = entry.name
            is_autosave = "autosave" in folder_name.lower()
            is_quicksave = folder_name.lower() in ("quicksave", "quick_save")

            display_name = folder_name
            save_dt = None

            # Try parsing info.sii for friendly name and real save time
            if info_sii and info_sii.is_file():
                try:
                    info_text = decrypt_sii(info_sii)
                    if info_text:
                        name_m = re.search(r'name:\s*["\']([^"\']+)["\']', info_text)
                        if name_m:
                            display_name = f"{name_m.group(1)} ({folder_name})"
                        time_m = re.search(r'file_time:\s*(\d+)', info_text)
                        if time_m:
                            try:
                                save_dt = datetime.datetime.fromtimestamp(int(time_m.group(1)))
                            except Exception:
                                pass
                except Exception:
                    pass

            # Fallback display names for special folders
            if folder_name == "autosave":
                display_name = "Autosave (Haupt)"
            elif folder_name.startswith("autosave_drive"):
                display_name = f"Autosave Fahrt ({folder_name})"
            elif folder_name.startswith("autosave_job"):
                display_name = f"Autosave Auftrag ({folder_name})"
            elif folder_name == "quicksave":
                display_name = "Schnellspeicherstand (QuickSave)"

            mtime = datetime.datetime.fromtimestamp(game_sii.stat().st_mtime)
            effective_time = save_dt or mtime

            results.append(SaveGameInfo(
                folder_name=folder_name,
                display_name=display_name,
                save_dir=entry,
                game_sii_path=game_sii,
                info_sii_path=info_sii,
                modified_time=mtime,
                save_time=effective_time,
                is_autosave=is_autosave,
                is_quicksave=is_quicksave,
            ))

        # Sort: newest first
        results.sort(key=lambda s: s.save_time or s.modified_time, reverse=True)
        return results

    def load_save(self, save_info: SaveGameInfo) -> bool:
        """Loads and decrypts game.sii into memory."""
        if not save_info or not save_info.game_sii_path.is_file():
            self._is_loaded = False
            return False

        decrypted = decrypt_sii(save_info.game_sii_path)
        if not decrypted:
            self._is_loaded = False
            return False

        self.current_save = save_info
        self._raw_text = decrypted
        self.lines = decrypted.splitlines()
        self._is_loaded = True
        return True

    def is_loaded(self) -> bool:
        return self._is_loaded and bool(self.lines)

    # -------------------------------------------------------------------------
    # Backup & Restore
    # -------------------------------------------------------------------------

    def create_backup(self, save_info: Optional[SaveGameInfo] = None) -> Optional[Path]:
        """Creates a timestamped backup of game.sii in the same save directory."""
        target_save = save_info or self.current_save
        if not target_save or not target_save.game_sii_path.is_file():
            return None

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = target_save.save_dir / f"game.sii.bak_{timestamp}"
        try:
            shutil.copy2(target_save.game_sii_path, backup_path)
            return backup_path
        except Exception as e:
            print(f"[TruckTools] Backup failed: {e}")
            return None

    @classmethod
    def list_backups(cls, save_dir: Path) -> List[Path]:
        """Lists all existing backup files for a savegame, sorted newest first."""
        if not save_dir or not save_dir.is_dir():
            return []
        backups = [p for p in save_dir.iterdir() if p.name.startswith("game.sii.bak")]
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return backups

    @classmethod
    def restore_backup(cls, backup_file: Path, save_dir: Path) -> bool:
        """Restores a backup to game.sii."""
        if not backup_file.is_file() or not save_dir.is_dir():
            return False
        dest = save_dir / "game.sii"
        try:
            shutil.copy2(backup_file, dest)
            return True
        except Exception as e:
            print(f"[TruckTools] Restore failed: {e}")
            return False

    def save_changes(self, create_auto_backup: bool = True) -> bool:
        """Writes modified lines back to game.sii in UTF-8 format."""
        if not self.is_loaded() or not self.current_save:
            return False

        if create_auto_backup:
            self.create_backup(self.current_save)

        output_content = "\n".join(self.lines) + "\n"
        try:
            self.current_save.game_sii_path.write_text(output_content, encoding="utf-8")
            self._raw_text = output_content
            return True
        except Exception as e:
            print(f"[TruckTools] Error writing save: {e}")
            return False

    # -------------------------------------------------------------------------
    # Helper: Finding Blocks in SII
    # -------------------------------------------------------------------------

    def _find_block(self, block_type: str, block_name: Optional[str] = None) -> Optional[Tuple[int, int]]:
        """
        Finds the line range (start_idx, end_idx inclusive) of a block:
        e.g. `economy : _nameless.123 {` or `player : ... {`.
        """
        start_idx = -1
        depth = 0
        target_prefix = f"{block_type} :" if block_name is None else f"{block_type} : {block_name}"

        for i, line in enumerate(self.lines):
            stripped = line.strip()
            if start_idx == -1:
                if stripped.startswith(target_prefix) and "{" in stripped:
                    start_idx = i
                    depth = 1
                elif stripped.startswith(target_prefix):
                    start_idx = i
            else:
                if "{" in stripped:
                    depth += stripped.count("{")
                if "}" in stripped:
                    depth -= stripped.count("}")
                    if depth <= 0:
                        return (start_idx, i)

        return None

    def _get_player_id(self) -> Optional[str]:
        """Gets the nameless ID of the player from economy block."""
        for line in self.lines:
            if "player:" in line:
                parts = line.split(":", 1)
                return parts[1].strip()
        return None

    def _get_bank_id(self) -> Optional[str]:
        """Gets the nameless ID of the bank from economy block."""
        for line in self.lines:
            if "bank:" in line:
                parts = line.split(":", 1)
                return parts[1].strip()
        return None

    # -------------------------------------------------------------------------
    # Profile & Economy (Money, XP, Skills, Garages, Exploration)
    # -------------------------------------------------------------------------

    def get_money(self) -> Optional[int]:
        """Gets current player money from bank account."""
        bank_id = self._get_bank_id()
        in_bank = False
        for line in self.lines:
            if bank_id and f"bank : {bank_id}" in line:
                in_bank = True
            elif not bank_id and line.strip().startswith("bank :"):
                in_bank = True

            if in_bank:
                if "money_account:" in line:
                    m = re.search(r'money_account:\s*(-?\d+)', line)
                    if m:
                        return int(m.group(1))
                if line.strip() == "}":
                    in_bank = False

        # Fallback search anywhere
        for line in self.lines:
            if "money_account:" in line:
                m = re.search(r'money_account:\s*(-?\d+)', line)
                if m:
                    return int(m.group(1))
        return None

    def set_money(self, amount: int) -> bool:
        """Sets the player money account balance."""
        bank_id = self._get_bank_id()
        in_bank = False
        modified = False

        for i, line in enumerate(self.lines):
            if bank_id and f"bank : {bank_id}" in line:
                in_bank = True
            elif not bank_id and line.strip().startswith("bank :"):
                in_bank = True

            if in_bank:
                if "money_account:" in line:
                    self.lines[i] = f" money_account: {int(amount)}"
                    modified = True
                    break
                if line.strip() == "}":
                    in_bank = False

        if not modified:
            for i, line in enumerate(self.lines):
                if "money_account:" in line:
                    self.lines[i] = f" money_account: {int(amount)}"
                    modified = True
                    break

        return modified

    def get_experience(self) -> Optional[int]:
        """Gets current player experience points."""
        for line in self.lines:
            if line.strip().startswith("experience_points:"):
                m = re.search(r'experience_points:\s*(\d+)', line)
                if m:
                    return int(m.group(1))
        return None

    def set_experience(self, xp: int) -> bool:
        """Sets player experience points."""
        modified = False
        for i, line in enumerate(self.lines):
            if line.strip().startswith("experience_points:"):
                self.lines[i] = f" experience_points: {int(xp)}"
                modified = True
                break
        return modified

    def get_skills(self) -> Dict[str, int]:
        """
        Gets player driver skills:
        adr (0-63), long_dist (0-6), heavy (0-6), fragile (0-6), urgent (0-6), mechanical (0-6).
        """
        skills = {
            "adr": 0,
            "long_dist": 0,
            "heavy": 0,
            "fragile": 0,
            "urgent": 0,
            "mechanical": 0
        }
        # In game.sii, the first occurrences before user_colors or other drivers belong to the player
        for line in self.lines:
            s = line.strip()
            if s.startswith("user_colors"):
                break
            for k in skills.keys():
                if s.startswith(f"{k}:"):
                    m = re.search(rf'{k}:\s*(\d+)', s)
                    if m:
                        skills[k] = int(m.group(1))
        return skills

    def set_skills(self, skills: Dict[str, int]) -> bool:
        """Sets player driver skills."""
        modified = False
        for i, line in enumerate(self.lines):
            s = line.strip()
            if s.startswith("user_colors"):
                break
            for k, v in skills.items():
                if s.startswith(f"{k}:"):
                    self.lines[i] = f" {k}: {int(v)}"
                    modified = True
        return modified

    def max_all_skills(self) -> bool:
        """Maximizes all skills: ADR all classes (63), and 6/6 for all other skills."""
        return self.set_skills({
            "adr": 63,
            "long_dist": 6,
            "heavy": 6,
            "fragile": 6,
            "urgent": 6,
            "mechanical": 6
        })

    def unlock_all_garages(self) -> int:
        """
        Unlocks all garages in the save file and upgrades them to status 3 (large garage).
        Returns number of upgraded garages.
        """
        count = 0
        in_garage = False
        for i, line in enumerate(self.lines):
            if line.strip().startswith("garage :"):
                in_garage = True
            elif in_garage:
                if "status:" in line:
                    # status 3 = large garage with 5 slots
                    self.lines[i] = " status: 3"
                    count += 1
                elif line.strip() == "}":
                    in_garage = False
        return count

    def unlock_all_cities_and_dealers(self) -> Tuple[int, int]:
        """
        Discovers all cities and dealerships found in the savegame.
        Returns (cities_count, dealers_count).
        """
        # 1. Collect all cities referenced across companies
        cities: Set[str] = set()
        for line in self.lines:
            if "companies[" in line and ":" in line:
                val = line.split(":", 1)[1].strip()
                # format: company.volatile.<name>.<city>
                parts = val.split(".")
                if len(parts) >= 4:
                    cities.add(parts[3])

        cities_added = 0
        dealers_added = 0

        # Replace visited_cities / visited_cities_count
        new_lines: List[str] = []
        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            if "visited_cities:" in line:
                # Add all cities
                sorted_cities = sorted(list(cities))
                new_lines.append(f" visited_cities: {len(sorted_cities)}")
                for idx, c in enumerate(sorted_cities):
                    new_lines.append(f" visited_cities[{idx}]: {c}")
                cities_added = len(sorted_cities)
                i += 1
                # Skip existing visited_cities[*] lines
                while i < len(self.lines) and re.match(r'\s*visited_cities\[\d+\]:', self.lines[i]):
                    i += 1
                continue
            elif "visited_cities_count:" in line:
                new_lines.append(f" visited_cities_count: {cities_added}")
                for idx in range(cities_added):
                    new_lines.append(f" visited_cities_count[{idx}]: 1")
                i += 1
                while i < len(self.lines) and re.match(r'\s*visited_cities_count\[\d+\]:', self.lines[i]):
                    i += 1
                continue
            elif "unlocked_dealers:" in line:
                # Set dealers discovered
                new_lines.append(" unlocked_dealers: 100")
                dealers_added = 100
                i += 1
                continue

            new_lines.append(line)
            i += 1

        self.lines = new_lines
        return (cities_added, dealers_added)

    # -------------------------------------------------------------------------
    # Trucks & Vehicles
    # -------------------------------------------------------------------------

    def get_assigned_truck_id(self) -> Optional[str]:
        """Finds the ID of the truck assigned to the player."""
        for line in self.lines:
            if line.strip().startswith("assigned_truck:"):
                parts = line.split(":", 1)
                val = parts[1].strip()
                if val and val != "null":
                    return val
            elif line.strip().startswith("my_truck:"):
                parts = line.split(":", 1)
                val = parts[1].strip()
                if val and val != "null":
                    return val
        return None

    def get_assigned_trailer_id(self) -> Optional[str]:
        """Finds the ID of the trailer assigned to the player."""
        for line in self.lines:
            if line.strip().startswith("assigned_trailer:"):
                parts = line.split(":", 1)
                val = parts[1].strip()
                if val and val != "null":
                    return val
            elif line.strip().startswith("my_trailer:"):
                parts = line.split(":", 1)
                val = parts[1].strip()
                if val and val != "null":
                    return val
        return None

    def get_player_truck_summary(self) -> Dict[str, Any]:
        """Returns details of the active player truck (model, engine, transmission, wear, fuel, mileage, plate)."""
        truck_id = self.get_assigned_truck_id()
        summary = {
            "truck_id": truck_id or "Kein aktiver LKW",
            "model_name": "Unbekannt",
            "engine_name": "Standard",
            "transmission_name": "Standard",
            "license_plate": "",
            "fuel_percent": 100.0,
            "mileage_km": 0,
            "has_infinite_fuel": False,
        }

        for l in self.lines:
            if "data_path:" in l and "/def/vehicle/truck/" in l and "data.sii" in l:
                m = re.search(r'/def/vehicle/truck/([^/]+)/data\.sii', l)
                if m:
                    summary["model_name"] = m.group(1).replace(".", " ").replace("_", " ").title()
                    break
            elif "data_path:" in l and "/def/vehicle/truck/" in l:
                m = re.search(r'/def/vehicle/truck/([^/]+)/', l)
                if m and summary["model_name"] == "Unbekannt":
                    summary["model_name"] = m.group(1).replace(".", " ").replace("_", " ").title()

        for l in self.lines:
            if "data_path:" in l and "/engine/" in l:
                m = re.search(r'/engine/([^/]+)\.sii', l)
                if m:
                    summary["engine_name"] = m.group(1).replace("_", " ").upper()
                    break

        for l in self.lines:
            if "data_path:" in l and "/transmission/" in l:
                m = re.search(r'/transmission/([^/]+)\.sii', l)
                if m:
                    summary["transmission_name"] = m.group(1).replace("_", " ").title()
                    break

        for l in self.lines:
            if "license_plate:" in l:
                m = re.search(r'license_plate:\s*"([^"]+)"', l)
                if m:
                    clean_p = re.sub(r'<[^>]+>', '', m.group(1))
                    summary["license_plate"] = clean_p
                    break

        for l in self.lines:
            if "odometer:" in l:
                m = re.search(r'odometer:\s*(\d+)', l)
                if m:
                    summary["mileage_km"] = int(m.group(1))
                    break
            elif "user_mileage:" in l:
                m = re.search(r'user_mileage:\s*(\d+)', l)
                if m:
                    summary["mileage_km"] = int(m.group(1))
                    break

        for l in self.lines:
            if "fuel_relative:" in l:
                val = l.split(":", 1)[1].strip()
                if "&" in val:
                    summary["has_infinite_fuel"] = True
                    summary["fuel_percent"] = 100.0
                else:
                    try:
                        summary["fuel_percent"] = min(100.0, max(0.0, float(val) * 100.0))
                    except Exception:
                        summary["fuel_percent"] = 100.0
                break

        return summary

    def get_player_trailer_summary(self) -> Dict[str, Any]:
        """Returns details of the active trailer and cargo mass."""
        trailer_id = self.get_assigned_trailer_id()
        return {
            "trailer_id": trailer_id or "Kein aktiver Auflieger",
            "cargo_mass_kg": self.get_cargo_mass() or 0.0,
        }

    def repair_all_trucks(self) -> int:
        """
        Resets wear to 0 for all trucks, wheels, engines, transmissions, cabins, and chassis,
        including unfixable/permanent wear introduced in ETS2/ATS 1.49+.
        Returns number of wear values reset.
        """
        count = 0
        wear_keys = [
            "wear:", "wheel_wear:", "wheels_wear:", "engine_wear:",
            "transmission_wear:", "cabin_wear:", "chassis_wear:",
            "wear_unfixable:", "wheel_wear_unfixable:", "wheels_wear_unfixable:",
            "engine_wear_unfixable:", "transmission_wear_unfixable:",
            "cabin_wear_unfixable:", "chassis_wear_unfixable:"
        ]
        for i, line in enumerate(self.lines):
            s = line.strip()
            # Also handle array indices like wheels_wear[0]: or wheels_wear_unfixable[0]:
            if re.match(r'^(?:wheels?_wear(?:_unfixable)?\[\d+\]|wheel_wear(?:_unfixable)?\[\d+\]):', s):
                prefix = line.split(":")[0]
                self.lines[i] = f"{prefix}: 0"
                count += 1
                continue

            for key in wear_keys:
                if s.startswith(key) or f" {key}" in line:
                    prefix = line.split(key)[0]
                    self.lines[i] = f"{prefix}{key} 0"
                    count += 1
                    break
        return count

    def refuel_all_trucks(self, infinite: bool = False) -> int:
        """
        Sets fuel_relative to 1 (full tank) or '&4f000000' for infinite fuel.
        Returns number of trucks refueled.
        """
        count = 0
        fuel_val = "&4f000000" if infinite else "1"
        for i, line in enumerate(self.lines):
            if "fuel_relative:" in line:
                self.lines[i] = f" fuel_relative: {fuel_val}"
                count += 1
        return count

    def set_truck_mileage(self, km: float) -> int:
        """Sets odometer / user mileage on trucks."""
        count = 0
        for i, line in enumerate(self.lines):
            if "user_mileage:" in line:
                self.lines[i] = f" user_mileage: {int(km)}"
                count += 1
            elif "odom:" in line:
                self.lines[i] = f" odom: {int(km)}"
                count += 1
        return count

    def set_truck_license_plate(self, plate_text: str, country: str = "") -> int:
        """Sets custom license plate text and country code on trucks."""
        formatted = f'"{plate_text}|{country}"' if country else f'"{plate_text}"'
        count = 0
        for i, line in enumerate(self.lines):
            if "license_plate:" in line:
                self.lines[i] = f" license_plate: {formatted}"
                count += 1
        return count

    # -------------------------------------------------------------------------
    # Trailers & Cargo
    # -------------------------------------------------------------------------

    def repair_all_trailers(self) -> int:
        """Resets wear on all trailers to 0."""
        count = 0
        trailer_wear_keys = {"trailer_body_wear:", "body_wear:", "wheels_wear:", "chassis_wear:"}
        for i, line in enumerate(self.lines):
            for k in trailer_wear_keys:
                if k in line:
                    prefix = line.split(k)[0]
                    self.lines[i] = f"{prefix}{k} 0"
                    count += 1
                    break
        return count

    def get_cargo_mass(self) -> Optional[float]:
        """Gets current trailer cargo weight in kg."""
        for line in self.lines:
            if "cargo_mass:" in line:
                m = re.search(r'cargo_mass:\s*([0-9.]+)', line)
                if m:
                    return float(m.group(1))
        return None

    def set_cargo_mass(self, mass_kg: float) -> int:
        """
        Sets trailer cargo weight (in kg).
        e.g. 0 for Convoy / zero rolling resistance, or custom weight.
        """
        count = 0
        for i, line in enumerate(self.lines):
            if "cargo_mass:" in line:
                self.lines[i] = f" cargo_mass: {float(mass_kg):.1f}"
                count += 1
        return count

    def set_trailer_license_plate(self, plate_text: str, country: str = "") -> int:
        """Sets custom license plate on trailers."""
        formatted = f'"{plate_text}|{country}"' if country else f'"{plate_text}"'
        count = 0
        in_trailer = False
        for i, line in enumerate(self.lines):
            if line.strip().startswith("trailer :"):
                in_trailer = True
            elif in_trailer:
                if "license_plate:" in line:
                    self.lines[i] = f" license_plate: {formatted}"
                    count += 1
                elif line.strip() == "}":
                    in_trailer = False
        return count

    # -------------------------------------------------------------------------
    # Engine & Transmission Swaps
    # -------------------------------------------------------------------------

    def swap_player_truck_engine(self, engine_data_path: str) -> bool:
        """
        Swaps the engine accessory of the player truck with a chosen engine SII path.
        e.g. '/def/vehicle/truck/scania.s_2016/engine/dc16_103_730.sii'
        """
        if not engine_data_path:
            return False

        # In SCS save, vehicle accessory with data_path containing '/engine/'
        modified = False
        in_acc = False
        for i, line in enumerate(self.lines):
            if "vehicle_engine_accessory :" in line:
                in_acc = True
            elif in_acc:
                if "data_path:" in line and "/engine/" in line:
                    self.lines[i] = f' data_path: "{engine_data_path}"'
                    modified = True
                    break
                elif line.strip() == "}":
                    in_acc = False

        if not modified:
            # Fallback search for any data_path with /engine/
            for i, line in enumerate(self.lines):
                if "data_path:" in line and "/engine/" in line:
                    self.lines[i] = f' data_path: "{engine_data_path}"'
                    modified = True
                    break

        return modified

    def swap_player_truck_transmission(self, trans_data_path: str) -> bool:
        """
        Swaps the transmission accessory of the player truck.
        e.g. '/def/vehicle/truck/scania.s_2016/transmission/grso925r.sii'
        """
        if not trans_data_path:
            return False

        modified = False
        in_acc = False
        for i, line in enumerate(self.lines):
            if "vehicle_transmission_accessory :" in line:
                in_acc = True
            elif in_acc:
                if "data_path:" in line and "/transmission/" in line:
                    self.lines[i] = f' data_path: "{trans_data_path}"'
                    modified = True
                    break
                elif line.strip() == "}":
                    in_acc = False

        if not modified:
            for i, line in enumerate(self.lines):
                if "data_path:" in line and "/transmission/" in line:
                    self.lines[i] = f' data_path: "{trans_data_path}"'
                    modified = True
                    break

        return modified
