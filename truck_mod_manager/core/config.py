"""
Configuration manager for Truck Mod Manager.
Saves settings to ~/.config/truck-mod-manager/config.json
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


CONFIG_DIR = Path(os.path.expanduser("~/.config/truck-mod-manager"))
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_DIR = Path(os.path.expanduser("~/.cache/truck-mod-manager"))
ICONS_CACHE_DIR = CACHE_DIR / "icons"
PRESETS_DIR = Path(os.path.expanduser("~/.local/share/truck-mod-manager/presets"))
STAGING_DIR = Path(os.path.expanduser("~/.local/share/truck-mod-manager/mods"))


DEFAULT_CONFIG: Dict[str, Any] = {
    "active_game": "ets2",
    "zero_pollution_staging": True,
    "auto_sort_on_enable": False,
    "theme": "dark",
    "extra_steam_paths": [],
    "ets2": {
        "custom_install_dir": "",
        "custom_user_dir": "",
        "custom_mod_dir": "",
        "is_proton": False,
        "launch_args": "-nointro -mm_pool_size 4096",
        "custom_launch_command": "",
    },
    "ats": {
        "custom_install_dir": "",
        "custom_user_dir": "",
        "custom_mod_dir": "",
        "is_proton": False,
        "launch_args": "-nointro -mm_pool_size 4096",
        "custom_launch_command": "",
    },
    "window": {
        "width": 1250,
        "height": 820,
    }
}


class ConfigManager:
    def __init__(self):
        self.config_path = CONFIG_FILE
        self._config: Dict[str, Any] = {}
        self._ensure_directories()
        self.load()

    def _ensure_directories(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        ICONS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)
        (STAGING_DIR / "ets2").mkdir(parents=True, exist_ok=True)
        (STAGING_DIR / "ats").mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            self._config = dict(DEFAULT_CONFIG)
            self.save()
            return self._config

        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            # Deep merge defaults
            self._config = dict(DEFAULT_CONFIG)
            for k, v in data.items():
                if isinstance(v, dict) and k in self._config and isinstance(self._config[k], dict):
                    self._config[k].update(v)
                else:
                    self._config[k] = v
        except Exception as e:
            print(f"[ConfigManager] Error reading config, fallback to default: {e}")
            self._config = dict(DEFAULT_CONFIG)

        return self._config

    def save(self):
        try:
            self.config_path.write_text(
                json.dumps(self._config, indent=4, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        self._config[key] = value
        self.save()

    def get_game_config(self, game_type: str) -> Dict[str, Any]:
        return self._config.get(game_type, {})

    def set_game_config(self, game_type: str, key: str, value: Any):
        if game_type not in self._config:
            self._config[game_type] = {}
        self._config[game_type][key] = value
        self.save()


# Singleton
config = ConfigManager()
