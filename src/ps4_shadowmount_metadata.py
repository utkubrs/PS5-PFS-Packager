"""PS4 PARAM.SFO to ShadowMount+ compatibility metadata.

This writes a JSON projection beside the original SFO in a *staged* game tree.
Never modify the user's original PKG or unpacked game.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from ps4_merge import _parse_sfo

# System PS4 TITLE_00..29 locale order, matching a ShadowMountPlus-compatible
# PS4-to-FFPFSC converter. Fall back to en-US for missing fields.
TITLE_LOCALES = (
    "ja-JP", "en-US", "fr-FR", "es-ES", "de-DE", "it-IT",
    "nl-NL", "pt-PT", "ru-RU", "ko-KR", "zh-Hant", "zh-Hans",
    "fi-FI", "sv-SE", "da-DK", "no-NO", "pl-PL", "pt-BR",
    "en-GB", "tr-TR", "es-419", "ar-AE", "fr-CA", "cs-CZ",
    "hu-HU", "el-GR", "ro-RO", "th-TH", "vi-VN", "id-ID",
)


def read_ps4_sfo_fields(path: Path) -> dict:
    data = path.read_bytes()
    fields: dict = {}
    for name, fmt, length, maximum, offset, _ in _parse_sfo(data):
        raw = data[offset:offset + length]
        if fmt == 0x0204:
            fields[name] = raw.split(b"\0", 1)[0].decode("utf-8", "replace")
        elif fmt == 0x0404 and 1 <= len(raw) <= 4:
            fields[name] = int.from_bytes(raw, "little")
    return fields


def prepare_ps4_shadowmount_metadata(merged_folder: str, remove_snd0: bool = False) -> dict:
    """Validate game metadata and prepare staged PS4 image root for ShadowMount+."""
    root = Path(merged_folder).resolve()
    if not (root / "eboot.bin").is_file():
        raise ValueError("PS4 game root is missing eboot.bin")
    sce_sys = root / "sce_sys"
    sfo = sce_sys / "param.sfo"
    if not sfo.is_file():
        raise ValueError("PS4 game root is missing sce_sys/param.sfo")
    fields = read_ps4_sfo_fields(sfo)
    title_id = str(fields.get("TITLE_ID") or "").strip().upper()
    if not re.fullmatch(r"CUSA\d{5}", title_id):
        raise ValueError("PS4 param.sfo is missing a valid CUSA TITLE_ID")
    title = str(fields.get("TITLE") or fields.get("TITLE_01") or "").strip()
    if not title:
        raise ValueError("PS4 param.sfo has no usable TITLE")

    json_path = sce_sys / "param.json"
    payload = {}
    if json_path.exists():
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8-sig"))
            if isinstance(existing, dict):
                payload.update(existing)
        except (OSError, ValueError, UnicodeError):
            pass
    localized = payload.get("localizedParameters")
    if not isinstance(localized, dict):
        localized = {}
    for index, locale in enumerate(TITLE_LOCALES):
        value = fields.get(f"TITLE_{index:02d}")
        if isinstance(value, str) and value.strip():
            item = localized.get(locale)
            if not isinstance(item, dict):
                item = {}
            item["titleName"] = value.strip()
            localized[locale] = item
    en = localized.get("en-US")
    if not isinstance(en, dict):
        en = {}
    en["titleName"] = str(fields.get("TITLE_01") or title).strip() or title
    localized["en-US"] = en
    if not isinstance(localized.get("defaultLanguage"), str):
        localized["defaultLanguage"] = "en-US"
    payload["titleId"] = title_id
    payload["titleName"] = title
    payload["localizedParameters"] = localized
    cid = str(fields.get("CONTENT_ID") or "").strip()
    if cid:
        payload["contentId"] = cid
    for i in range(1, 5):
        value = fields.get(f"USER_DEFINED_PARAM_{i}")
        if isinstance(value, int) and value != 0:
            payload[f"userDefinedParam{i}"] = value

    # Write UTF-8 without BOM and atomically replace only the staged JSON.
    tmp = sce_sys / "param.json.tmp"
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, json_path)
    finally:
        if tmp.exists():
            tmp.unlink()

    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    if parsed.get("titleId") != title_id or not parsed.get("localizedParameters", {}).get("en-US", {}).get("titleName"):
        raise ValueError("ShadowMount+ param.json compatibility verification failed")

    removed = False
    if remove_snd0:
        sound = sce_sys / "snd0.at9"
        if sound.is_file():
            sound.unlink()
            removed = True
    return {"title_id": title_id, "title": title, "param_json": str(json_path), "snd0_removed": removed}


def prepare_existing_temp_merge(source: str, selected_temp: str, remove_snd0: bool = False) -> dict | None:
    """Repair an old user-selected merge staging directory only if app-owned.

    Never write into original game directories, even when they happen to have
    a similar name; the merge tree must be an immediate child of selected TEMP.
    """
    root = Path(source)
    temp = Path(selected_temp).resolve()
    if root.is_symlink() or not root.is_dir():
        return None
    root = root.resolve()
    if root.parent != temp or not re.fullmatch(r"ps4_merge_[0-9a-f]{10,32}", root.name):
        return None
    return prepare_ps4_shadowmount_metadata(str(root), remove_snd0=remove_snd0)
