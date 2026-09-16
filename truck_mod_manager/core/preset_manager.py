"""
Preset manager for Truck Mod Manager.
Saves, loads, exports and imports mod configurations and load orders per game.
"""
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional

from truck_mod_manager.core.config import PRESETS_DIR
from truck_mod_manager.core.models import GameType, ModPreset, ScsMod


class PresetManager:
    """Manages loadout presets for ETS2 and ATS."""

    @staticmethod
    def get_game_preset_dir(game_type: GameType) -> Path:
        p = PRESETS_DIR / game_type.value
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def list_presets(cls, game_type: GameType) -> List[ModPreset]:
        """Returns all saved presets for a given game."""
        preset_dir = cls.get_game_preset_dir(game_type)
        presets: List[ModPreset] = []

        for json_file in preset_dir.glob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                presets.append(ModPreset(
                    name=data.get("name", json_file.stem),
                    game_type=GameType(data.get("game_type", game_type.value)),
                    description=data.get("description", ""),
                    mod_order=data.get("mod_order", []),
                    created_at=data.get("created_at", ""),
                ))
            except Exception as e:
                print(f"[PresetManager] Error loading {json_file}: {e}")

        presets.sort(key=lambda p: p.name.lower())
        return presets

    @classmethod
    def save_preset(cls, preset: ModPreset) -> Path:
        """Saves a preset to disk."""
        preset_dir = cls.get_game_preset_dir(preset.game_type)
        safe_name = "".join(c for c in preset.name if c.isalnum() or c in (" ", "-", "_")).strip()
        if not safe_name:
            safe_name = "preset"

        file_path = preset_dir / f"{safe_name}.json"
        if not preset.created_at:
            preset.created_at = datetime.now().isoformat()

        payload = {
            "name": preset.name,
            "game_type": preset.game_type.value,
            "description": preset.description,
            "mod_order": preset.mod_order,
            "created_at": preset.created_at,
        }

        file_path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")
        return file_path

    @classmethod
    def delete_preset(cls, name: str, game_type: GameType) -> bool:
        """Deletes a preset file."""
        preset_dir = cls.get_game_preset_dir(game_type)
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
        file_path = preset_dir / f"{safe_name}.json"
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    @classmethod
    def export_preset(cls, preset: ModPreset, target_path: Path):
        """Exports a preset to any destination path."""
        payload = {
            "name": preset.name,
            "game_type": preset.game_type.value,
            "description": preset.description,
            "mod_order": preset.mod_order,
            "created_at": preset.created_at,
        }
        target_path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def import_preset(cls, source_path: Path) -> ModPreset:
        """Imports a preset from a JSON file."""
        data = json.loads(source_path.read_text(encoding="utf-8"))
        preset = ModPreset(
            name=data["name"],
            game_type=GameType(data["game_type"]),
            description=data.get("description", ""),
            mod_order=data.get("mod_order", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )
        cls.save_preset(preset)
        return preset

    @classmethod
    def apply_preset(cls, preset: ModPreset, all_mods: List[ScsMod]) -> List[ScsMod]:
        """
        Activates only the mods present in the preset and sorts them
        according to the preset's mod_order. Mods not in the preset are disabled.
        """
        mod_dict = {m.file_name: m for m in all_mods}
        active_mods: List[ScsMod] = []
        inactive_mods: List[ScsMod] = []

        # Find and order active mods in preset order
        for file_name in preset.mod_order:
            if file_name in mod_dict:
                mod = mod_dict[file_name]
                mod.is_enabled = True
                active_mods.append(mod)

        # Set priorities for active mods
        for idx, mod in enumerate(active_mods, start=1):
            mod.priority = idx

        # Disable all others
        active_filenames = set(preset.mod_order)
        for mod in all_mods:
            if mod.file_name not in active_filenames:
                mod.is_enabled = False
                mod.priority = 0
                inactive_mods.append(mod)

        return active_mods + inactive_mods
