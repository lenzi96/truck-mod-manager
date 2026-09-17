"""
Deployer for Truck Mod Manager.
Handles Zero-Pollution staging via Symlinks, direct mod directory management, and Vanilla Reset.
"""
import json
import os
from pathlib import Path
import shutil
from typing import Dict, List, Set, Tuple

from truck_mod_manager.core.config import STAGING_DIR, config
from truck_mod_manager.core.models import GameType, ScsMod, TruckGame
from truck_mod_manager.core.scs_parser import ScsParser


class ModDeployer:
    """Deploys active mods to the game mod directory and manages state."""

    MANIFEST_NAME = ".tmm_manifest.json"

    @classmethod
    def get_staging_dir(cls, game_type: GameType) -> Path:
        p = STAGING_DIR / game_type.value
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def load_all_mods(cls, game: TruckGame) -> List[ScsMod]:
        """
        Discovers all mods available for this game:
        Checks both the centralized staging directory and the game's actual mod/ directory.
        """
        if not game:
            return []
        mods: Dict[str, ScsMod] = {}
        staging_dir = cls.get_staging_dir(game.game_type)
        use_staging = config.get("zero_pollution_staging", True)

        # 1. Read mods from staging directory
        if staging_dir.exists():
            for entry in staging_dir.iterdir():
                if entry.name.startswith("."):
                    continue
                if entry.suffix.lower() in (".scs", ".zip") or entry.is_dir():
                    mod = ScsParser.parse_mod_file(entry)
                    mods[entry.name] = mod

        # 2. Read mods from game mod directory
        if game.mod_dir:
            mod_dir = Path(game.mod_dir)
            if mod_dir.exists():
                manifest_deployed = cls._read_manifest(mod_dir)

                for entry in mod_dir.iterdir():
                    if entry.name.startswith("."):
                        continue

                    # If it's a symlink pointing to staging, mark that staging mod as enabled
                    if entry.is_symlink():
                        target_name = entry.name
                        if target_name in mods:
                            mods[target_name].is_enabled = True
                        continue

                    # Check for direct disabled mods (.disabled)
                    is_disabled = entry.name.endswith(".disabled")
                    clean_name = entry.name[:-9] if is_disabled else entry.name

                    if entry.suffix.lower() in (".scs", ".zip") or is_disabled or entry.is_dir():
                        if clean_name not in mods:
                            mod = ScsParser.parse_mod_file(entry)
                            mod.is_enabled = not is_disabled
                            mods[clean_name] = mod
                        else:
                            # Staging copy already exists
                            if not is_disabled:
                                mods[clean_name].is_enabled = True

        # 3. Read mods from Steam Workshop
        try:
            from truck_mod_manager.core.workshop_scanner import WorkshopScanner
            workshop_mods = WorkshopScanner.scan_workshop(game.game_type)
            for w_mod in workshop_mods:
                if w_mod.file_name not in mods:
                    mods[w_mod.file_name] = w_mod
        except Exception as e:
            print(f"[Deployer] Error loading workshop mods: {e}")

        result = list(mods.values())
        result.sort(key=lambda m: m.display_name.lower())
        return result

    @classmethod
    def deploy(cls, game: TruckGame, active_mods: List[ScsMod]) -> Tuple[bool, str]:
        """
        Deploys active mods to the game mod directory.
        If zero_pollution_staging is enabled, creates symlinks from staging to mod/.
        Removes any previously deployed symlinks no longer active.
        """
        if not game.mod_dir:
            return False, "Mod-Verzeichnis des Spiels ist nicht konfiguriert."

        mod_dir = Path(game.mod_dir)
        mod_dir.mkdir(parents=True, exist_ok=True)

        use_staging = config.get("zero_pollution_staging", True)
        deployed_manifest = cls._read_manifest(mod_dir)
        currently_deployed: Set[str] = set(deployed_manifest.get("deployed_files", []))
        newly_deployed: List[str] = []

        try:
            if use_staging:
                # 1. Remove obsolete symlinks previously deployed by TMM
                for old_file in list(currently_deployed):
                    target = mod_dir / old_file
                    if target.is_symlink():
                        target.unlink()

                # 2. Deploy active mods
                for mod in active_mods:
                    if not mod.is_enabled:
                        continue
                    if mod.is_missing:
                        continue
                    if mod.is_workshop:
                        # Steam Workshop mods are loaded natively by SCS from Steam workshop directories.
                        # Never symlink or copy them into mod/
                        continue

                    src_path = Path(mod.file_path)
                    dest_path = mod_dir / mod.file_name

                    # If target is already a regular file and different from src, don't overwrite blindly
                    if dest_path.exists() and not dest_path.is_symlink():
                        if dest_path.resolve() == src_path.resolve():
                            # Already there
                            newly_deployed.append(mod.file_name)
                            continue

                    # Remove existing symlink if present
                    if dest_path.is_symlink() or dest_path.exists():
                        try:
                            if dest_path.is_dir():
                                shutil.rmtree(dest_path)
                            else:
                                dest_path.unlink()
                        except Exception:
                            pass

                    # Create relative or absolute symlink
                    try:
                        dest_path.symlink_to(src_path.resolve())
                        newly_deployed.append(mod.file_name)
                    except Exception as e:
                        print(f"[Deployer] Symlink failed for {mod.file_name}: {e}")
                        # Fallback: copy if filesystem doesn't support symlinks (e.g. FAT32/exFAT)
                        if src_path.is_file():
                            shutil.copy2(src_path, dest_path)
                            newly_deployed.append(mod.file_name)
            else:
                # Direct mode: rename .disabled files
                for mod in active_mods:
                    if mod.is_missing or mod.is_workshop or not mod.file_path:
                        continue
                    current_path = Path(mod.file_path)
                    if mod.is_enabled:
                        if current_path.name.endswith(".disabled"):
                            enabled_name = current_path.name[:-9]
                            new_path = current_path.parent / enabled_name
                            current_path.rename(new_path)
                            mod.file_path = str(new_path)
                            mod.file_name = enabled_name
                        newly_deployed.append(mod.file_name)
                    else:
                        if not current_path.name.endswith(".disabled"):
                            disabled_name = f"{current_path.name}.disabled"
                            new_path = current_path.parent / disabled_name
                            current_path.rename(new_path)
                            mod.file_path = str(new_path)
                            mod.file_name = disabled_name

            # Save manifest
            cls._write_manifest(mod_dir, {"deployed_files": newly_deployed})
            return True, f"{len(newly_deployed)} Mods erfolgreich bereitgestellt."

        except Exception as e:
            return False, f"Fehler bei der Bereitstellung: {e}"

    @classmethod
    def vanilla_reset(cls, game: TruckGame) -> Tuple[bool, str]:
        """
        Removes all symlinks created by TMM in the game's mod directory.
        Restores clean vanilla state without touching game core files.
        """
        if not game.mod_dir:
            return False, "Kein Mod-Verzeichnis gefunden."

        mod_dir = Path(game.mod_dir)
        if not mod_dir.exists():
            return True, "Mod-Verzeichnis ist bereits leer."

        count = 0
        manifest = cls._read_manifest(mod_dir)
        tracked_files = set(manifest.get("deployed_files", []))

        for entry in list(mod_dir.iterdir()):
            if entry.is_symlink() or entry.name in tracked_files:
                try:
                    if entry.is_symlink() or entry.is_file():
                        entry.unlink()
                        count += 1
                except Exception as e:
                    print(f"[Deployer] Error removing {entry}: {e}")

        # Clear manifest
        manifest_file = mod_dir / cls.MANIFEST_NAME
        if manifest_file.exists():
            manifest_file.unlink()

        return True, f"Vanilla Reset abgeschlossen: {count} Verknüpfungen restlos entfernt."

    @classmethod
    def import_mod_archive(cls, game: TruckGame, file_path: Path) -> ScsMod:
        """Copies or moves an external mod file into staging."""
        target_dir = cls.get_staging_dir(game.game_type)
        dest = target_dir / file_path.name

        if file_path.is_dir():
            shutil.copytree(file_path, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(file_path, dest)

        return ScsParser.parse_mod_file(dest)

    @classmethod
    def delete_mod(cls, game: TruckGame, mod: ScsMod) -> bool:
        """Deletes a mod file from staging and/or mod directory, cleans up icons and symlinks."""
        if mod.is_workshop:
            # Workshop mods cannot be deleted locally; user must unsubscribe in Steam.
            return False

        # 1. Remove primary file
        path = Path(mod.file_path)
        if path.exists():
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except Exception as e:
                print(f"[Deployer] Error removing mod file {path}: {e}")

        # 2. Remove from game mod directory if symlink or direct file exists
        if game.mod_dir:
            mod_dir = Path(game.mod_dir)
            targets = [
                mod_dir / mod.file_name,
                mod_dir / f"{mod.file_name}.disabled"
            ]
            for target in targets:
                if target.is_symlink() or target.exists():
                    try:
                        if target.is_dir():
                            shutil.rmtree(target)
                        else:
                            target.unlink()
                    except Exception as e:
                        print(f"[Deployer] Error removing game copy {target}: {e}")

            # Update manifest
            manifest = cls._read_manifest(mod_dir)
            deployed = manifest.get("deployed_files", [])
            if mod.file_name in deployed:
                deployed.remove(mod.file_name)
                cls._write_manifest(mod_dir, {"deployed_files": deployed})

        # 3. Clean up cached icon
        if mod.icon_path:
            icon_p = Path(mod.icon_path)
            if icon_p.exists() and "cache" in str(icon_p).lower():
                try:
                    icon_p.unlink()
                except Exception:
                    pass

        return True

    @classmethod
    def _read_manifest(cls, mod_dir: Path) -> dict:
        m = mod_dir / cls.MANIFEST_NAME
        if m.exists():
            try:
                return json.loads(m.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    @classmethod
    def _write_manifest(cls, mod_dir: Path, data: dict):
        m = mod_dir / cls.MANIFEST_NAME
        try:
            m.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Deployer] Failed writing manifest: {e}")
