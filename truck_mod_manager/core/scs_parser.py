"""
SCS / ZIP Mod Archive and manifest.sii parser.
Extracts metadata, categories, description, and icons without full archive decompression.
"""
import hashlib
import os
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from truck_mod_manager.core.config import ICONS_CACHE_DIR
from truck_mod_manager.core.models import ModCategory, ScsMod


# Category string mapping from SCS manifest to internal ModCategory enum
CATEGORY_MAP: Dict[str, ModCategory] = {
    "map": ModCategory.MAP,
    "maps": ModCategory.MAP,
    "model": ModCategory.MODELS,
    "models": ModCategory.MODELS,
    "prefab": ModCategory.PREFABS,
    "prefabs": ModCategory.PREFABS,
    "def": ModCategory.DEF,
    "truck": ModCategory.TRUCK,
    "trucks": ModCategory.TRUCK,
    "trailer": ModCategory.TRAILER,
    "trailers": ModCategory.TRAILER,
    "tuning": ModCategory.TUNING,
    "interior": ModCategory.INTERIOR,
    "sound": ModCategory.SOUND,
    "sounds": ModCategory.SOUND,
    "physics": ModCategory.PHYSICS,
    "ai_traffic": ModCategory.AI_TRAFFIC,
    "traffic": ModCategory.AI_TRAFFIC,
    "paint_job": ModCategory.PAINT_JOB,
    "skin": ModCategory.PAINT_JOB,
    "skins": ModCategory.PAINT_JOB,
    "cargo": ModCategory.CARGO,
    "graphics": ModCategory.GRAPHICS,
    "graphic": ModCategory.GRAPHICS,
    "weather": ModCategory.WEATHER,
    "ui": ModCategory.UI,
    "other": ModCategory.OTHER,
}


class ScsParser:
    """Parses SCS / ZIP mod packages and directory mods."""

    @staticmethod
    def parse_manifest_sii(text: str) -> Dict[str, any]:
        """
        Tokenizes and parses SCS manifest.sii format.
        Handles key: value, array key[]: value, comments (# or //).
        """
        result: Dict[str, any] = {
            "display_name": "",
            "package_version": "1.0",
            "author": "Unknown",
            "categories": [],
            "icon": "",
            "description_file": "",
            "mp_mod_optional": False,
            "compatible_versions": [],
        }

        # Remove single-line comments
        lines = []
        for line in text.splitlines():
            line_no_comment = re.split(r"//|#", line)[0].strip()
            if line_no_comment:
                lines.append(line_no_comment)

        clean_text = "\n".join(lines)

        # Regex for key: value or key[]: value
        # Matches: display_name: "ProMods 1.50" or category[]: "map"
        attr_matches = re.findall(
            r'([a-zA-Z0-9_]+(?:\[\])?)\s*:\s*(?:"([^"]*)"|([^\s\r\n{}]+))',
            clean_text
        )

        for key, val_quoted, val_raw in attr_matches:
            val = val_quoted if val_quoted != "" else val_raw
            if not val:
                continue

            val = val.strip()

            if key == "display_name":
                result["display_name"] = val
            elif key == "package_version":
                result["package_version"] = val
            elif key == "author":
                result["author"] = val
            elif key == "category[]":
                cat_lower = val.lower().replace(" ", "_")
                cat_enum = CATEGORY_MAP.get(cat_lower, ModCategory.OTHER)
                if cat_enum not in result["categories"]:
                    result["categories"].append(cat_enum)
            elif key == "icon":
                result["icon"] = val
            elif key == "description_file":
                result["description_file"] = val
            elif key == "mp_mod_optional":
                result["mp_mod_optional"] = val.lower() in ("true", "1")
            elif key == "compatible_versions[]":
                result["compatible_versions"].append(val)

        return result

    @classmethod
    def clean_description(cls, raw_desc: str) -> str:
        """Strips or converts SCS BBCode formatting tags ([b], [color], [normal], etc.)."""
        # Remove BBCode tags like [b], [/b], [color=#ffffff], [normal], [url=...], [/url]
        clean = re.sub(r'\[/?[a-zA-Z0-9_#]+(?:=[^\]]*)?\]', '', raw_desc)
        return clean.strip()

    @classmethod
    def infer_categories_from_files(cls, file_list: List[str]) -> List[ModCategory]:
        """Infers mod category based on contained paths when manifest.sii is missing."""
        cats: Set[ModCategory] = set()
        lower_files = [f.lower().replace("\\", "/") for f in file_list]

        for f in lower_files:
            if "def/vehicle/truck/" in f:
                cats.add(ModCategory.TRUCK)
            if "def/vehicle/trailer/" in f:
                cats.add(ModCategory.TRAILER)
            if "def/vehicle/addon_hookups/" in f or "def/vehicle/truck/common/" in f:
                cats.add(ModCategory.TUNING)
            if "sound/" in f or "/sound" in f or f.endswith(".bank") or "sound.sii" in f:
                cats.add(ModCategory.SOUND)
            if "map/" in f or f.endswith(".mbd"):
                cats.add(ModCategory.MAP)
            if "physics" in f:
                cats.add(ModCategory.PHYSICS)
            if "paint_job" in f or "skin" in f:
                cats.add(ModCategory.PAINT_JOB)
            if "def/cargo/" in f or "cargo/" in f:
                cats.add(ModCategory.CARGO)
            if "weather" in f or "climate" in f:
                cats.add(ModCategory.WEATHER)
            if "model/" in f or "prefab/" in f:
                cats.add(ModCategory.MODELS)
            if "ui/" in f or "font/" in f:
                cats.add(ModCategory.UI)
            if "traffic" in f:
                cats.add(ModCategory.AI_TRAFFIC)

        if not cats:
            cats.add(ModCategory.OTHER)

        return sorted(list(cats), key=lambda c: c.value)

    @classmethod
    def parse_mod_file(cls, file_path: Path) -> ScsMod:
        """
        Inspects an .scs, .zip, or directory mod.
        Extracts metadata and cached icon.
        """
        file_name = file_path.name
        file_size = file_path.stat().st_size if file_path.exists() else 0

        # Fallback defaults
        display_name = file_path.stem.replace("_", " ").replace("-", " ").title()
        mod = ScsMod(
            file_path=str(file_path.resolve()),
            file_name=file_name,
            display_name=display_name,
            file_size=file_size,
        )

        # Check if directory mod
        if file_path.is_dir():
            cls._parse_directory_mod(file_path, mod)
            return mod

        # ZIP / SCS Archive
        if zipfile.is_zipfile(file_path):
            cls._parse_zip_mod(file_path, mod)
            return mod

        # Raw file (could be encrypted base or uncompressed single file)
        mod.display_name = file_path.stem
        mod.categories = [ModCategory.OTHER]
        return mod

    @classmethod
    def _parse_zip_mod(cls, file_path: Path, mod: ScsMod):
        try:
            with zipfile.ZipFile(file_path, "r") as z:
                names = z.namelist()
                mod.internal_files = names

                # Check for manifest.sii (case-insensitive)
                manifest_name = next((n for n in names if n.lower() == "manifest.sii"), None)

                if manifest_name:
                    try:
                        manifest_content = z.read(manifest_name).decode("utf-8", errors="ignore")
                        meta = cls.parse_manifest_sii(manifest_content)
                        mod.has_manifest = True
                        if meta["display_name"]:
                            mod.display_name = meta["display_name"]
                        mod.package_version = meta["package_version"]
                        mod.author = meta["author"]
                        if meta["categories"]:
                            mod.categories = meta["categories"]
                        else:
                            mod.categories = cls.infer_categories_from_files(names)
                        mod.mp_mod_optional = meta["mp_mod_optional"]
                        mod.compatible_versions = meta["compatible_versions"]

                        # Check description file
                        desc_file_name = meta.get("description_file") or "description.txt"
                        desc_entry = next((n for n in names if n.lower() == desc_file_name.lower()), None)
                        if desc_entry:
                            raw_desc = z.read(desc_entry).decode("utf-8", errors="ignore")
                            mod.description = cls.clean_description(raw_desc)

                        # Extract icon
                        icon_file_name = meta.get("icon") or "mod_icon.png"
                        icon_entry = next((n for n in names if n.lower() == icon_file_name.lower()), None)
                        if icon_entry:
                            icon_data = z.read(icon_entry)
                            icon_hash = hashlib.md5(f"{file_path.name}_{icon_entry}".encode()).hexdigest()
                            cached_icon_path = ICONS_CACHE_DIR / f"{icon_hash}.png"
                            cached_icon_path.write_bytes(icon_data)
                            mod.icon_path = str(cached_icon_path)
                    except Exception as e:
                        print(f"[ScsParser] Failed reading manifest in {file_path.name}: {e}")

                if not mod.has_manifest:
                    mod.categories = cls.infer_categories_from_files(names)

                    # Look for default mod_icon.png
                    icon_entry = next((n for n in names if n.lower() in ("mod_icon.png", "icon.png")), None)
                    if icon_entry:
                        try:
                            icon_data = z.read(icon_entry)
                            icon_hash = hashlib.md5(f"{file_path.name}_{icon_entry}".encode()).hexdigest()
                            cached_icon_path = ICONS_CACHE_DIR / f"{icon_hash}.png"
                            cached_icon_path.write_bytes(icon_data)
                            mod.icon_path = str(cached_icon_path)
                        except Exception:
                            pass

        except Exception as e:
            print(f"[ScsParser] Failed opening zip {file_path.name}: {e}")
            mod.categories = [ModCategory.OTHER]

    @classmethod
    def _parse_directory_mod(cls, dir_path: Path, mod: ScsMod):
        files = []
        for root, _, filenames in os.walk(dir_path):
            rel_root = os.path.relpath(root, dir_path)
            for f in filenames:
                rel_f = f if rel_root == "." else os.path.join(rel_root, f)
                files.append(rel_f)

        mod.internal_files = files
        manifest_file = dir_path / "manifest.sii"

        if manifest_file.exists():
            try:
                content = manifest_file.read_text(encoding="utf-8", errors="ignore")
                meta = cls.parse_manifest_sii(content)
                mod.has_manifest = True
                if meta["display_name"]:
                    mod.display_name = meta["display_name"]
                mod.package_version = meta["package_version"]
                mod.author = meta["author"]
                if meta["categories"]:
                    mod.categories = meta["categories"]
                else:
                    mod.categories = cls.infer_categories_from_files(files)
                mod.mp_mod_optional = meta["mp_mod_optional"]
                mod.compatible_versions = meta["compatible_versions"]

                desc_name = meta.get("description_file") or "description.txt"
                desc_path = dir_path / desc_name
                if desc_path.exists():
                    mod.description = cls.clean_description(desc_path.read_text(encoding="utf-8", errors="ignore"))

                icon_name = meta.get("icon") or "mod_icon.png"
                icon_path = dir_path / icon_name
                if icon_path.exists():
                    mod.icon_path = str(icon_path.resolve())
            except Exception as e:
                print(f"[ScsParser] Failed reading manifest from {dir_path}: {e}")

        if not mod.has_manifest:
            mod.categories = cls.infer_categories_from_files(files)
            if (dir_path / "mod_icon.png").exists():
                mod.icon_path = str((dir_path / "mod_icon.png").resolve())
