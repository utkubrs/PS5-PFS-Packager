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
    """Prefer real SFO/PKG identity to an arbitrary filename."""
    p = Path(path)
    sfo = p / "sce_sys" / "param.sfo"
    if sfo.is_file():
        try:
            from ps4_merge import sfo_fields
            title_id = sfo_fields(str(sfo)).get("TITLE_ID", "")
            if re.fullmatch(r"CUSA\d{5}", title_id, re.I):
                return title_id.upper()
        except (OSError, ValueError):
            pass
    if p.is_file() and p.suffix.lower() in (".pkg", ".fpkg"):
        try:
            # PS4 PKG headers normally expose the CONTENT_ID in clear text.
            # Read only the header; never load multi-GB packages into memory.
            with p.open("rb") as stream:
                header = stream.read(65536)
            match = re.search(rb"(?:[A-Z]{2}\d{4}-)?(CUSA\d{5})(?:_\d{2})?", header, re.I)
            if match:
                return match.group(1).decode("ascii").upper()
        except OSError:
            pass
    for value in (p.name, p.parent.name):
        match = re.search(r"CUSA\d{5}", value, re.I)
        if match:
            return match.group(0).upper()
    return ""


def inspect_ps4_source(path: str) -> dict:
    """Best-effort title/ID preview without unpacking the selected PKG.

    Folder titles come from PARAM.SFO. For PKGs the visible filename is used
    until extraction makes their internal PARAM.SFO available.
    """
    p = Path(path)
    title_id = detect_ps4_title_id(path)
    title = ""
    sfo = p / "sce_sys" / "param.sfo"
    if sfo.is_file():
        try:
            from ps4_merge import sfo_fields
            title = sfo_fields(str(sfo)).get("TITLE", "").strip()
        except (OSError, ValueError):
            pass
    if not title:
        stem = p.stem if p.is_file() else p.name
        stem = re.sub(r"CUSA\d{5}", "", stem, flags=re.I)
        stem = re.sub(r"(?i)(?:[-_. ]+(?:TR|TURKCE|UPDATE|PATCH|V\d+|\d+))+$", "", stem)
        title = re.sub(r"[_]+", " ", stem).strip(" -_.")
    return {"title": title, "title_id": title_id}

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
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    startup = None
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
    process=subprocess.Popen([str(tool),str(source),"-o",str(folder)],stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors="replace",
        creationflags=flags, startupinfo=startup,
        env={**os.environ,"TEMP":str(Path(temp_dir).resolve()),"TMP":str(Path(temp_dir).resolve())})
    # Track an approximate size-based progress indicator; no separate CMD window.
    import threading
    import time
    stop=threading.Event()
    expected=max(1,source.stat().st_size)
    def watch():
        previous=-1
        while not stop.wait(3):
            try:
                current=sum(Path(root,filename).stat().st_size for root,_,files in os.walk(folder) for filename in files)
                approx=min(99,int(current*100/expected))
                if approx>previous and log:
                    log(f"PKG extraction: ~{approx}% (size estimate, not exact)")
                    previous=approx
            except OSError:
                pass
    watcher=threading.Thread(target=watch,daemon=True)
    watcher.start()
    try:
        output,_=process.communicate(timeout=21600)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise RuntimeError("PKG extraction timed out")
    finally:
        stop.set()
        watcher.join(timeout=1)
    if process.returncode:
        raise RuntimeError(f"pkgextract failed with exit code {process.returncode}: {(output or '')[-2000:]}")
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
