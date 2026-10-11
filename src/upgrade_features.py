"""Extra preflight checks and PS5 game metadata discovery (v2.14)."""
from __future__ import annotations
import json
import os
import re
import shutil
from pathlib import Path

def inspect_game(source: str) -> dict:
    root = Path(source)
    result = {"title": root.name, "title_id": "", "icon": "", "size": 0}
    if not root.is_dir():
        return result
    params = root / "sce_sys" / "param.json"
    if params.is_file():
        try:
            data = json.loads(params.read_text(encoding="utf-8-sig"))
            result["title_id"] = str(data.get("titleId") or data.get("title_id") or "")
            localized = data.get("localizedParameters", {})
            default = localized.get("defaultLanguage", "en-US") if isinstance(localized, dict) else "en-US"
            items = localized.get(default, {}) if isinstance(localized, dict) else {}
            title = (items.get("titleName") if isinstance(items, dict) else None) or data.get("titleName")
            if title:
                result["title"] = str(title)
        except (OSError, ValueError, TypeError):
            pass
    if not result["title_id"]:
        match = re.search(r"(PPSA\d{5}|CUSA\d{5})", root.name, re.I)
        if match:
            result["title_id"] = match.group(1).upper()
    for name in ("icon0.png", "icon.png", "pic0.png"):
        path = root / "sce_sys" / name
        if path.is_file():
            result["icon"] = str(path)
            break
    return result

def validate_preflight(temp_folder: str, output_folder: str, source: str = "") -> list[str]:
    issues = []
    for label, location in (("TEMP", temp_folder), ("Output", output_folder)):
        if not location:
            issues.append(f"{label} folder is missing")
            continue
        try:
            Path(location).mkdir(parents=True, exist_ok=True)
            if not Path(location).is_dir():
                issues.append(f"{label} is not a folder: {location}")
            else:
                _, _, free = shutil.disk_usage(location)
                if free < 1024**3:
                    issues.append(f"{label} has under 1 GiB free: {location}")
        except OSError as exc:
            issues.append(f"{label} is not writable: {exc}")
    if source and os.path.isdir(source):
        try:
            if os.path.commonpath((os.path.realpath(source), os.path.realpath(output_folder))) == os.path.realpath(source):
                issues.append("Output folder is inside the source game folder")
        except ValueError:
            pass
    return issues

def recommended_block_size(ram_gib: float, source_size_gib: float) -> str:
    # Advisory only; preserve MkPFS auto as the default.
    if ram_gib < 8: return "16384"
    if ram_gib < 16 or source_size_gib > 150: return "32768"
    return "65536"
