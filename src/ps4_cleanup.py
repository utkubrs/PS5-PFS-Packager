"""Delete only TEMP data created by a successful PS4 one-click operation.

This deliberately does not discover directories by glob and never touches a user
source directory. Failures leave staged data available for inspection/retry.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path


def cleanup_ps4_temp(merge_folder: str, extracted_folders: list[str],
                     temp_folder: str, log=None) -> list[str]:
    tmp = Path(temp_folder).resolve()
    extraction_root = (tmp / "ps4_pkg_extract").resolve()
    merged = Path(merge_folder).resolve()
    # Only application-generated names directly under the selected TEMP.
    if merged.parent != tmp or not re.fullmatch(r"ps4_merge_[0-9a-f]{10}", merged.name):
        raise ValueError("Refusing cleanup outside an owned PS4 merge folder")
    if tmp.is_symlink() or extraction_root.is_symlink() or merged.is_symlink():
        raise ValueError("Refusing cleanup via symlink")

    cleanup_targets = [merged]
    for folder in extracted_folders:
        candidate = Path(folder).resolve()
        # pkgextract can expose inner folders, so clean only its top-level root.
        try:
            subpath = candidate.relative_to(extraction_root)
        except ValueError as exc:
            raise ValueError("Refusing cleanup of unowned extraction path") from exc
        if not subpath.parts or subpath.parts[0] in (".", ".."):
            raise ValueError("Refusing cleanup of extraction parent")
        target = extraction_root / subpath.parts[0]
        if target.is_symlink() or candidate.is_symlink():
            raise ValueError("Refusing cleanup via symlink")
        if target not in cleanup_targets:
            cleanup_targets.append(target)

    cleaned = []
    for target in cleanup_targets:
        try:
            if target.is_dir():
                shutil.rmtree(target)
                cleaned.append(str(target))
                if log:
                    log("Başarılı işlem sonrası TEMP temizlendi: " + str(target), "success")
        except OSError as exc:
            if log:
                log("TEMP temizlenemedi; elle silinebilir: " + str(target) + " - " + str(exc), "warn")
    try:
        if extraction_root.is_dir() and not any(extraction_root.iterdir()):
            extraction_root.rmdir()
    except OSError:
        pass
    return cleaned
