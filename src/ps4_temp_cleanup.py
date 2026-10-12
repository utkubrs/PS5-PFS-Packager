"""Remove only temporary work created by this application after a successful pack."""
from __future__ import annotations

import shutil
from pathlib import Path


def owned_merge_paths(temp_dir: str, merged: str, extracted: list[str]) -> list[Path]:
    temp = Path(temp_dir).resolve(strict=True)
    source_root = temp / "ps4_pkg_extract"
    merge = Path(merged).resolve(strict=True)
    if merge.parent != temp or not merge.name.startswith("ps4_merge_"):
        raise ValueError("Refusing to delete a folder outside app-owned PS4 merge TEMP")
    if not merge.is_dir() or merge.is_symlink():
        raise ValueError("PS4 merge folder missing or is a symlink")
    allowed = [merge]
    for original in extracted:
        item = Path(original)
        if not item.exists():
            continue
        item = item.resolve(strict=True)
        if not item.is_relative_to(source_root) or item == source_root:
            raise ValueError("Refusing to delete a non-temporary extracted folder")
        # Nested extraction trees can have many files; remove only top-level,
        # app-created per-PKG extraction subdirectories.
        target = source_root / item.relative_to(source_root).parts[0]
        if target.is_symlink():
            raise ValueError("Refusing to delete a symlinked extraction folder")
        allowed.append(target)
    return list(dict.fromkeys(allowed))


def cleanup_ps4_merge(temp_dir: str, merged: str, extracted: list[str],
                      output: str, log=None) -> None:
    """Never run before the pack+optional verification succeeds."""
    result = Path(output)
    if not result.is_file() or result.stat().st_size < 1024:
        raise ValueError("Output FFPFSC was not successfully written")
    folders = owned_merge_paths(temp_dir, merged, extracted)
    for folder in folders:
        if folder.exists():
            shutil.rmtree(folder)
            if log:
                log("TEMP temizlendi: " + str(folder))
