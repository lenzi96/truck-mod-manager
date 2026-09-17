"""
Profile Manager for Truck Mod Manager.
Discovers ETS2 & ATS player profiles (local & Steam Cloud), decodes hex directory names,
decrypts profile.sii save files, and manages profile-specific active mod lists and load orders.
"""
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Dict, List, Optional, Tuple
import zlib

from truck_mod_manager.core.config import PROFILES_DIR, config
from truck_mod_manager.core.models import GameProfile, GameType, ScsMod, TruckGame


# SCS Software SII AES Key for ScsC encrypted files
SCS_SII_AES_KEY = bytes([
    0x2A, 0x5F, 0xCB, 0x17, 0x91, 0xD2, 0x2F, 0xB6, 0x02, 0x45, 0xB3, 0xD8,
    0x36, 0x9E, 0xD0, 0xB2, 0xC2, 0x73, 0x71, 0x56, 0x3F, 0xBF, 0x1F, 0x3C,
    0x9E, 0xDF, 0x6B, 0x11, 0x82, 0x5A, 0x5D, 0x0A,
])
SCS_SII_KEY_HEX = "2a5fcb1791d22fb60245b3d8369ed0b2c27371563fbf1f3c9edf6b11825a5d0a"


def decode_profile_name(hex_name: str) -> str:
    """
    Decodes an ETS2/ATS hex folder name into a human-readable profile name.
    e.g. '50726F6D6F6473' -> 'Promods', '4D6172696F' -> 'Mario'.
    Falls back to original string if not valid hex or contains invalid characters.
    """
    if not hex_name:
        return ""
    try:
        if len(hex_name) % 2 == 0:
            decoded = bytes.fromhex(hex_name).decode("utf-8", errors="replace").strip()
            if decoded and all(c.isprintable() or c.isspace() for c in decoded):
                return decoded
    except Exception:
        pass
    return hex_name


def encode_profile_name(name: str) -> str:
    """Encodes a string into uppercase hexadecimal UTF-8 bytes (SCS convention)."""
    return name.encode("utf-8").hex().upper()


def decrypt_sii(file_path: Path) -> Optional[str]:
    """
    Reads and decrypts an SCS .sii file (e.g. profile.sii or game.sii).
    Supports plain text (SiiNunit header) and encrypted (ScsC AES-256-CBC + zlib header).
    """
    if not file_path or not file_path.is_file():
        return None

    try:
        data = file_path.read_bytes()
        if not data:
            return None

        # 1. Plain text format
        if data.startswith(b"SiiN"):
            return data.decode("utf-8", errors="ignore")

        # 2. Encrypted ScsC format
        if data.startswith(b"ScsC"):
            if len(data) < 56:
                return None
            iv_hex = data[36:52].hex()
            ciphertext = data[56:]

            # Primary: OpenSSL CLI (fast, built into Linux systems)
            try:
                proc = subprocess.run(
                    ["openssl", "enc", "-d", "-aes-256-cbc", "-K", SCS_SII_KEY_HEX, "-iv", iv_hex],
                    input=ciphertext,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                )
                if proc.returncode == 0 and proc.stdout:
                    decompressed = zlib.decompress(proc.stdout)
                    return decompressed.decode("utf-8", errors="ignore")
            except Exception as e:
                print(f"[ProfileManager] OpenSSL decryption notice: {e}")

            # Fallback: cryptography library if available
            try:
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                from cryptography.hazmat.backends import default_backend
                iv = data[36:52]
                cipher = Cipher(algorithms.AES(SCS_SII_AES_KEY), modes.CBC(iv), backend=default_backend())
                decryptor = cipher.decryptor()
                decrypted = decryptor.update(ciphertext) + decryptor.finalize()
                pad_len = decrypted[-1]
                if 1 <= pad_len <= 16:
                    decrypted = decrypted[:-pad_len]
                decompressed = zlib.decompress(decrypted)
                return decompressed.decode("utf-8", errors="ignore")
            except Exception as e:
                print(f"[ProfileManager] Cryptography fallback decryption notice: {e}")

    except Exception as e:
        print(f"[ProfileManager] Failed reading/decrypting {file_path}: {e}")

    return None


def read_sii_active_mods(file_path: Path) -> List[Tuple[str, str]]:
    """
    Parses active_mods array from a profile.sii file.
    Returns list of (package_name, display_name) ordered by priority (1 = highest priority).
    Note: SCS internally stores active_mods from lowest priority (index 0) to highest priority (index N-1).
    Therefore, the parsed list is reversed so that index 0 is Priority 1 (top of load order).
    """
    text = decrypt_sii(file_path)
    if not text:
        return []

    active_raw: List[str] = []
    for line in text.splitlines():
        line_clean = line.strip()
        m = re.match(r'^active_mods\[\d+\]:\s*"([^"]+)"', line_clean)
        if m:
            active_raw.append(m.group(1))

    # Reverse list: in SCS Mod Manager UI, index N-1 is top (Priority 1) and index 0 is bottom
    ordered_entries = list(reversed(active_raw))
    result: List[Tuple[str, str]] = []
    for entry in ordered_entries:
        if "|" in entry:
            pkg, name = entry.split("|", 1)
            result.append((pkg.strip(), name.strip()))
        else:
            result.append((entry.strip(), ""))

    return result


def read_save_active_mods(profile_dir: Path) -> List[Tuple[str, str]]:
    """
    Fallback reader: scans profile_dir / 'save' for the newest save's info.sii
    and extracts dependencies[N]: "mod|<pkg>|<display_name>".
    Returns list in priority order (reversed mount order).
    """
    if not profile_dir or not profile_dir.is_dir():
        return []

    save_dir = profile_dir / "save"
    if not save_dir.is_dir():
        return []

    # Find the newest info.sii
    candidate_files = list(save_dir.glob("*/info.sii"))
    if not candidate_files:
        return []

    candidate_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    best_file = candidate_files[0]

    text = decrypt_sii(best_file)
    if not text:
        return []

    raw_entries: List[str] = []
    for line in text.splitlines():
        line_clean = line.strip()
        m = re.match(r'^dependencies\[\d+\]:\s*"mod\|([^"]+)"', line_clean)
        if m:
            raw_entries.append(m.group(1))

    ordered = list(reversed(raw_entries))
    result: List[Tuple[str, str]] = []
    for entry in ordered:
        if "|" in entry:
            pkg, name = entry.split("|", 1)
            result.append((pkg.strip(), name.strip()))
        else:
            result.append((entry.strip(), ""))
    return result


def read_log_active_mods(log_path: Path) -> List[Tuple[str, str]]:
    """
    Parses live mounted mod load order from game.log.txt.
    Log entries:
      [mod_package_manager] Mod "<name>" has been mounted. (package_name: <pkg>, ...)
    Returns list ordered by priority (1 = highest priority).
    """
    if not log_path or not Path(log_path).is_file():
        return []

    try:
        content = Path(log_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    # Find all [mod_package_manager] Mod "..." has been mounted entries
    mounted: List[Tuple[str, str]] = []
    for line in content.splitlines():
        if "[mod_package_manager] Mod " in line and "has been mounted" in line:
            m = re.search(r'Mod\s+"([^"]+)"\s+has been mounted\.\s+\(package_name:\s*([^,)]+)', line)
            if m:
                display_name = m.group(1).strip()
                pkg_name = m.group(2).strip()
                mounted.append((pkg_name, display_name))

    if not mounted:
        return []

    # In game.log.txt, mods are mounted from lowest priority to highest priority.
    # The last mounted mod is Priority 1 (top of load order list).
    return list(reversed(mounted))


def match_sii_active_mods_to_scs_mods(
    active_tuples: List[Tuple[str, str]],
    all_mods: List[ScsMod]
) -> List[ScsMod]:
    """
    Matches active mod definitions from profile.sii against available ScsMod items.
    Assigns priorities (1 = highest) and sets is_enabled.
    If an active mod is not found locally, creates a placeholder mod (is_missing=True)
    so load order positions remain accurate.
    Returns re-ordered mod list: active mods first in priority order, then inactive mods.
    """
    seen_files = set()
    ordered_active: List[ScsMod] = []

    current_prio = 1
    for pkg, name in active_tuples:
        matched = None
        clean_pkg = pkg.lower()
        if clean_pkg.endswith(".scs") or clean_pkg.endswith(".zip"):
            clean_pkg = clean_pkg.rsplit(".", 1)[0]

        # 1. Exact or clean stem match on filename
        for m in all_mods:
            if m.file_name in seen_files:
                continue
            m_fn_clean = m.file_name.lower()
            if m_fn_clean.endswith(".scs") or m_fn_clean.endswith(".zip"):
                m_fn_clean = m_fn_clean.rsplit(".", 1)[0]

            if (
                m.file_name == pkg
                or m.file_name.lower() == pkg.lower()
                or m_fn_clean == clean_pkg
                or Path(m.file_name).stem.lower() == clean_pkg
            ):
                matched = m
                break

        # 2. Workshop ID match if package starts with mod_workshop_package.
        if not matched and pkg.startswith("mod_workshop_package."):
            hex_id = pkg.split(".")[-1]
            try:
                dec_id = str(int(hex_id, 16))
                for m in all_mods:
                    if m.file_name in seen_files:
                        continue
                    if m.workshop_id == dec_id or dec_id in m.file_name or (m.file_path and dec_id in m.file_path):
                        matched = m
                        break
            except Exception:
                pass

        # 3. Exact or case-insensitive display_name match (with package disambiguation)
        if not matched and name:
            candidates = [m for m in all_mods if m.file_name not in seen_files and (
                m.display_name == name or m.display_name.lower() == name.lower()
            )]
            if len(candidates) == 1:
                matched = candidates[0]
            elif len(candidates) > 1:
                # Disambiguate multi-part packs by matching file name against clean_pkg
                matched = max(candidates, key=lambda c: (
                    clean_pkg in c.file_name.lower() or c.file_name.lower() in clean_pkg
                ))

        if matched:
            if matched.is_workshop and name:
                matched.display_name = name
            matched.is_enabled = True
            matched.priority = current_prio
            matched.is_missing = False
            current_prio += 1
            seen_files.add(matched.file_name)
            ordered_active.append(matched)
        else:
            # Create a placeholder mod for missing item
            is_ws = pkg.startswith("mod_workshop_package.")
            ws_id = None
            if is_ws:
                hex_part = pkg.split(".")[-1]
                try:
                    ws_id = str(int(hex_part, 16))
                except Exception:
                    pass

            placeholder = ScsMod(
                file_path="",
                file_name=pkg,
                display_name=name or pkg,
                is_enabled=True,
                priority=current_prio,
                is_workshop=is_ws,
                workshop_id=ws_id,
                is_missing=True,
            )
            current_prio += 1
            seen_files.add(placeholder.file_name)
            ordered_active.append(placeholder)

    # Deactivate all other mods
    inactive: List[ScsMod] = []
    for m in all_mods:
        if m.file_name not in seen_files:
            m.is_enabled = False
            m.priority = 0
            m.is_missing = False
            inactive.append(m)

    inactive.sort(key=lambda m: m.display_name.lower())
    return ordered_active + inactive


class ProfileManager:
    """Manages discovery and per-profile mod configurations for ETS2 and ATS."""

    DEFAULT_PROFILE_ID = "default"

    decrypt_sii = staticmethod(decrypt_sii)
    read_sii_active_mods = staticmethod(read_sii_active_mods)
    read_save_active_mods = staticmethod(read_save_active_mods)
    read_log_active_mods = staticmethod(read_log_active_mods)
    match_sii_active_mods_to_scs_mods = staticmethod(match_sii_active_mods_to_scs_mods)

    @classmethod
    def list_profiles(cls, game: Optional[TruckGame]) -> List[GameProfile]:
        """
        Discovers all game profiles for the given TruckGame.
        Checks both 'profiles' and 'steam_profiles' subdirectories.
        Ignores '.bak' backup directories, '.history', etc.
        Returns a list of GameProfile objects sorted by name.
        """
        if not game or not game.user_dir:
            return [cls._get_fallback_profile(game.game_type if game else GameType.ETS2)]

        user_dir = Path(game.user_dir)
        candidate_dirs = [user_dir]

        # In Proton environments, also check Proton documents directory if different
        if game.proton_prefix:
            pfx_docs = Path(game.proton_prefix) / "drive_c" / "users" / "steamuser" / "Documents"
            game_folder_name = "Euro Truck Simulator 2" if game.game_type == GameType.ETS2 else "American Truck Simulator"
            proton_game_dir = pfx_docs / game_folder_name
            if proton_game_dir.exists() and proton_game_dir.resolve() not in [d.resolve() for d in candidate_dirs if d.exists()]:
                candidate_dirs.append(proton_game_dir)

        discovered: Dict[str, GameProfile] = {}

        for root_dir in candidate_dirs:
            if not root_dir.exists():
                continue

            for sub_name, is_cloud in [("profiles", False), ("steam_profiles", True)]:
                p_dir = root_dir / sub_name
                if not p_dir.is_dir():
                    continue

                for entry in p_dir.iterdir():
                    # Must be directory and not a backup (.bak), preview or hidden
                    if not entry.is_dir() or entry.name.startswith(".") or entry.name.endswith(".bak"):
                        continue
                    if entry.name.lower() in ("preview_profiles", "profile backups"):
                        continue

                    profile_id = entry.name
                    if profile_id in discovered:
                        continue

                    readable_name = decode_profile_name(profile_id)
                    try:
                        mtime = 0.0
                        sii_path = entry / "profile.sii"
                        if sii_path.is_file():
                            mtime = sii_path.stat().st_mtime
                        save_dir = entry / "save"
                        if save_dir.is_dir():
                            mtime = max(mtime, save_dir.stat().st_mtime)
                            for s in save_dir.iterdir():
                                if s.is_dir():
                                    info_file = s / "info.sii"
                                    if info_file.is_file():
                                        mtime = max(mtime, info_file.stat().st_mtime)
                                    else:
                                        mtime = max(mtime, s.stat().st_mtime)
                        if mtime == 0.0:
                            mtime = entry.stat().st_mtime
                    except Exception:
                        mtime = 0.0

                    discovered[profile_id] = GameProfile(
                        id=profile_id,
                        name=readable_name,
                        path=entry,
                        is_steam_cloud=is_cloud,
                        game_type=game.game_type,
                        last_modified=mtime,
                    )

        if not discovered:
            return [cls._get_fallback_profile(game.game_type)]

        profiles = list(discovered.values())
        profiles.sort(key=lambda p: p.name.lower())
        return profiles

    @classmethod
    def get_most_recent_profile(cls, profiles: List[GameProfile]) -> Optional[GameProfile]:
        """Returns the profile that was most recently played/modified."""
        if not profiles:
            return None
        valid_profiles = [p for p in profiles if p.last_modified > 0]
        if valid_profiles:
            return max(valid_profiles, key=lambda p: p.last_modified)
        return profiles[0]

    @classmethod
    def _get_fallback_profile(cls, game_type: GameType) -> GameProfile:
        return GameProfile(
            id=cls.DEFAULT_PROFILE_ID,
            name="Standard-Profil",
            path=None,
            is_steam_cloud=False,
            game_type=game_type,
            last_modified=0.0,
        )

    @classmethod
    def get_profile_config_path(cls, game_type: GameType, profile_id: str) -> Path:
        p_dir = PROFILES_DIR / game_type.value
        p_dir.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(c for c in profile_id if c.isalnum() or c in ("-", "_")).strip() or "default"
        return p_dir / f"{safe_id}.json"

    @classmethod
    def get_active_profile_id(cls, game_type: GameType) -> str:
        """Returns the ID of the last active profile for the given game."""
        return config.get(f"active_profile_{game_type.value}", "")

    @classmethod
    def set_active_profile_id(cls, game_type: GameType, profile_id: str):
        """Saves the active profile ID in configuration."""
        config.set(f"active_profile_{game_type.value}", profile_id)

    @classmethod
    def load_profile_state(cls, game_type: GameType, profile_id: str) -> Optional[dict]:
        """Loads the saved profile mod state JSON if present."""
        path = cls.get_profile_config_path(game_type, profile_id)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[ProfileManager] Error reading profile config {path}: {e}")
        return None

    @classmethod
    def save_profile_state(
        cls,
        game_type: GameType,
        profile_id: str,
        mods: List[ScsMod],
        profile_name: str = "",
        user_modified: bool = False,
        sii_mtime: float = 0.0,
    ) -> Path:
        """
        Saves the current active mods and load order for this profile.
        """
        path = cls.get_profile_config_path(game_type, profile_id)
        active = [m for m in mods if m.is_enabled]
        active.sort(key=lambda m: m.priority if m.priority > 0 else 99999)
        active_filenames = [m.file_name for m in active]

        disabled_filenames = [m.file_name for m in mods if not m.is_enabled]

        # Preserve previous sii_mtime if not explicitly passed
        if sii_mtime == 0.0 and path.exists():
            try:
                old_data = json.loads(path.read_text(encoding="utf-8"))
                sii_mtime = old_data.get("sii_mtime", 0.0)
            except Exception:
                pass

        data = {
            "profile_id": profile_id,
            "profile_name": profile_name or decode_profile_name(profile_id),
            "game_type": game_type.value,
            "updated_at": datetime.now().isoformat(),
            "user_modified": user_modified,
            "sii_mtime": sii_mtime,
            "active_mods": active_filenames,
            "mod_order": active_filenames,
            "disabled_mods": disabled_filenames,
        }
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def apply_profile_state(
        cls,
        game_type: GameType,
        profile: GameProfile,
        all_mods: List[ScsMod],
        force_reload_sii: bool = False
    ) -> List[ScsMod]:
        """
        Applies profile-specific active mods and load order.
        If profile.path contains profile.sii:
            Checks if profile.sii is newer than saved JSON or if force_reload_sii is True.
            If so, reads the actual in-game active mods & load order from profile.sii!
        Otherwise, loads from cached profile JSON or initializes it.
        """
        profile_id = profile.id
        sii_file = (profile.path / "profile.sii") if profile.path else None
        sii_mtime = sii_file.stat().st_mtime if (sii_file and sii_file.is_file()) else 0.0

        json_data = cls.load_profile_state(game_type, profile_id)

        # Determine if we should read/reload directly from profile.sii:
        read_from_sii = False
        if sii_file and sii_file.is_file():
            if force_reload_sii or not json_data:
                read_from_sii = True
            elif not json_data.get("user_modified", False):
                # User has not made custom modifications in TMM -> sync with game
                read_from_sii = True
            elif json_data.get("sii_mtime", 0.0) != sii_mtime:
                # The game updated profile.sii since we last cached it!
                read_from_sii = True

        if read_from_sii and sii_file:
            active_tuples = read_sii_active_mods(sii_file)
            if not active_tuples and profile.path:
                active_tuples = read_save_active_mods(profile.path)
            reordered = match_sii_active_mods_to_scs_mods(active_tuples, all_mods)
            # Cache to JSON as clean imported state
            cls.save_profile_state(
                game_type, profile_id, reordered,
                profile_name=profile.name,
                user_modified=False,
                sii_mtime=sii_mtime
            )
            return reordered

        # Read from saved JSON if present
        if json_data:
            active_order: List[str] = json_data.get("mod_order") or json_data.get("active_mods", [])
            active_set = set(active_order)
            mod_map: Dict[str, ScsMod] = {m.file_name: m for m in all_mods}

            ordered_active: List[ScsMod] = []
            for fn in active_order:
                if fn in mod_map:
                    m = mod_map[fn]
                    m.is_enabled = True
                    ordered_active.append(m)

            for idx, m in enumerate(ordered_active, start=1):
                m.priority = idx

            inactive: List[ScsMod] = []
            for m in all_mods:
                if m.file_name not in active_set:
                    m.is_enabled = False
                    m.priority = 0
                    inactive.append(m)

            inactive.sort(key=lambda m: m.display_name.lower())
            return ordered_active + inactive

        # Fallback: check if savegame has active mods
        if profile.path:
            save_tuples = read_save_active_mods(profile.path)
            if save_tuples:
                reordered = match_sii_active_mods_to_scs_mods(save_tuples, all_mods)
                cls.save_profile_state(
                    game_type, profile_id, reordered,
                    profile_name=profile.name,
                    user_modified=False,
                    sii_mtime=sii_mtime
                )
                return reordered

        # Fallback if neither profile.sii nor JSON exists
        cls.save_profile_state(
            game_type, profile_id, all_mods,
            profile_name=profile.name,
            user_modified=False,
            sii_mtime=0.0
        )
        return all_mods
