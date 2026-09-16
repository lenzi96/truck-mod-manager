"""
Telemetry and Plugins manager for ETS2 and ATS.
Manages .so / .dll plugins in bin/linux_x64/plugins/ or bin/win_x64/plugins/.
"""
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from truck_mod_manager.core.models import TruckGame


class TelemetryManager:
    """Manages telemetry and force-feedback plugins."""

    @classmethod
    def get_plugins_dir(cls, game: TruckGame) -> Optional[Path]:
        return game.plugins_dir

    @classmethod
    def list_plugins(cls, game: TruckGame) -> List[Dict[str, any]]:
        pdir = cls.get_plugins_dir(game)
        if not pdir or not pdir.exists():
            return []

        plugins = []
        for file in pdir.iterdir():
            if file.is_file() and not file.name.startswith("."):
                is_enabled = not file.name.endswith(".disabled")
                ext = "".join(file.suffixes).lower()
                clean_name = file.name.replace(".disabled", "")
                plugins.append({
                    "name": clean_name,
                    "file_path": str(file),
                    "is_enabled": is_enabled,
                    "size_bytes": file.stat().st_size,
                    "is_native": file.name.endswith(".so") or file.name.endswith(".so.disabled"),
                    "is_dll": file.name.endswith(".dll") or file.name.endswith(".dll.disabled"),
                })

        plugins.sort(key=lambda p: p["name"].lower())
        return plugins

    @classmethod
    def toggle_plugin(cls, plugin_path: Path) -> bool:
        """Toggles plugin between enabled and .disabled."""
        if not plugin_path.exists():
            return False

        if plugin_path.name.endswith(".disabled"):
            new_path = plugin_path.parent / plugin_path.name[:-9]
            plugin_path.rename(new_path)
            return True
        else:
            new_path = plugin_path.parent / f"{plugin_path.name}.disabled"
            plugin_path.rename(new_path)
            return False

    @classmethod
    def install_plugin(cls, game: TruckGame, source_file: Path) -> Path:
        """Installs a plugin file into the game's plugins directory."""
        pdir = cls.get_plugins_dir(game)
        if not pdir:
            raise ValueError("Game plugins directory is not available.")
        pdir.mkdir(parents=True, exist_ok=True)
        dest = pdir / source_file.name
        shutil.copy2(source_file, dest)
        return dest

    @classmethod
    def remove_plugin(cls, plugin_path: Path):
        if plugin_path.exists():
            plugin_path.unlink()
