"""PS4 input handling for PFS Packager v2.15.0.

Extraction uses the open-source pkgextract CLI only when installed locally.
Encrypted retail packages may not be extractable; this module does not bypass encryption.
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
from pathlib import Path

def is_ps4_game_folder(path: str) -> bool:
    p=Path(path)
    return p.is_dir() and (p/"eboot.bin").is_file() and (p/"sce_sys"/"param.sfo").is_file()

def detect_ps4_title_id(path: str) -> str:
    p=Path(path)
    for value in (p.name, p.parent.name):
        m=re.search(r"CUSA\d{5}",value,re.I)
        if m:return m.group(0).upper()
    sfo=p/"sce_sys"/"param.sfo"
    if sfo.is_file():
        try:
            data=sfo.read_bytes()
            for pat in (rb"CUSA\d{5}",):
                m=re.search(pat,data,re.I)
                if m:return m.group().decode("ascii").upper()
        except OSError:pass
    return ""

def extract_pkg(source: str, temp_dir: str, log=None) -> str:
    """Extract using pkgextract -o; caller validates extracted game and converts it."""
    source=Path(source).resolve()
    if source.suffix.lower() not in (".pkg",".fpkg") or not source.is_file():
        raise ValueError("Select an existing .pkg or .fpkg file")
    # Support portable placement beside the EXE or in a tools directory.
    import sys
    app_dir=Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) or "__compiled__" in globals() else Path(__file__).resolve().parents[1]
    candidates=[
        os.environ.get("PS4_PKG_EXTRACTOR"),
        str(app_dir/"pkgextract.exe"),
        str(app_dir/"tools"/"pkgextract.exe"),
        str(app_dir/"pkgextract"/"pkgextract.exe"),
        str(app_dir/"PS5-PFS-Packager"/"pkgextract.exe"),
        shutil.which("pkgextract.exe"),
        shutil.which("pkgextract"),
    ]
    tool=next((x for x in candidates if x and Path(x).is_file()),None)
    if not tool or not Path(tool).is_file():
        raise RuntimeError("PKG extractor missing. Place pkgextract.exe beside PS5-PFS-Packager.exe, in its tools folder, or set PS4_PKG_EXTRACTOR.")
    base=Path(temp_dir).resolve()/"ps4_pkg_extract"
    base.mkdir(parents=True,exist_ok=True)
    folder=base/(re.sub(r"[^A-Za-z0-9_.-]","_",source.stem)[:80])
    if folder.exists():
        raise FileExistsError(f"Extraction target exists: {folder}. Remove it or choose a different TEMP directory.")
    if log:log(f"Extracting {source.name} to {folder}")
    completed=subprocess.run([str(tool),str(source),"-o",str(folder)],stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors="replace",timeout=21600,
        env={**os.environ,"TEMP":str(Path(temp_dir).resolve()),"TMP":str(Path(temp_dir).resolve())})
    if completed.returncode:
        raise RuntimeError(f"pkgextract failed with exit code {completed.returncode}: {completed.stdout[-2000:]}")
    def looks_like_ps4_content(path):
        p=Path(path)
        return p.is_dir() and (p/"sce_sys"/"param.sfo").is_file() and (p/"eboot.bin").is_file()
    def looks_like_ps4_update(path):
        p=Path(path)
        return p.is_dir() and (p/"sce_sys"/"param.sfo").is_file()
    if looks_like_ps4_update(str(folder)):
        return str(folder)
    for root,dirs,files in os.walk(folder):
        relative=Path(root).relative_to(folder)
        if len(relative.parts)>3:
            dirs.clear()
            continue
        if looks_like_ps4_content(root) or looks_like_ps4_update(root):
            return str(Path(root))
    raise RuntimeError(f"No valid extracted PS4 game folder in {folder}. Files were retained for inspection.")
