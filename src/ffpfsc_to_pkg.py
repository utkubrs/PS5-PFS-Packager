"""PS4 FFPFSC to FPKG conversion through MkPFS and OrbisPkgTool.

This is a PS4-only pipeline. No retail decryption, PS5 PKG building,
or guarantee of console compatibility is provided.
"""
from __future__ import annotations

import os
from pathlib import Path
import queue
import shutil
import struct
import subprocess
import tempfile
import threading

from ps4_merge import sfo_fields

PFS_MAGIC = 20130315
PS5_OUTER_PFS_VERSION = 2
PKG_MAGIC = b"\x7fCNT"


class ConversionCancelled(RuntimeError):
    """Raised when the user aborts the conversion."""


def inspect_ffpfsc(source: str | Path) -> Path:
    """Validate the known MkPFS outer PFS header; don't use suffix as validation."""
    image = Path(source).resolve()
    if not image.is_file() or image.suffix.lower() != ".ffpfsc":
        raise ValueError("Select a valid .ffpfsc file (not .ffpfcs or .pkg).")
    with image.open("rb") as handle:
        header = handle.read(80)
    if len(header) < 80:
        raise ValueError("The FFPFSC file is truncated.")
    version, magic = struct.unpack_from("<qq", header)
    block = struct.unpack_from("<I", header, 0x20)[0]
    if version != PS5_OUTER_PFS_VERSION or magic != PFS_MAGIC or not (4096 <= block <= 1 << 20):
        raise ValueError("Unsupported FFPFSC outer PFS header.")
    return image


def find_ps4_game_root(folder: str | Path) -> Path:
    """Accept a single game root, never choose an arbitrary game in a multi-game image."""
    folder = Path(folder).resolve()
    candidates = [folder]
    candidates.extend(p for p in folder.iterdir() if p.is_dir() and not p.is_symlink())
    matches = [p for p in candidates if (p / "eboot.bin").is_file()
               and (p / "sce_sys" / "param.sfo").is_file()]
    if len(matches) != 1:
        if (folder / "sce_sys" / "param.json").exists() and not matches:
            raise ValueError("This is a PS5 image. PS5 FFPFSC to PKG requires a separate PS5 builder.")
        raise ValueError("A single supported PS4 game (eboot.bin and sce_sys/param.sfo) was not found.")
    root = matches[0]
    fields = sfo_fields(str(root / "sce_sys" / "param.sfo"))
    if fields.get("CATEGORY") not in ("gd",):
        raise ValueError("Only standalone PS4 base games (CATEGORY=gd) can be packaged.")
    if not fields.get("TITLE_ID", "").startswith("CUSA"):
        raise ValueError("A valid PS4 CUSA title ID is required.")
    return root


def run_live_command(args: list[str], log=None, cancel: threading.Event | None = None):
    """Run a subprocess without a shell; consume both streams without pipe deadlock."""
    if log:
        log("Running: " + " ".join(Path(a).name if idx == 0 else str(a) for idx, a in enumerate(args)))
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               encoding="utf-8", errors="replace", text=True,
                               creationflags=creationflags)
    lines = queue.Queue()
    def reader():
        try:
            for line in process.stdout:
                lines.put(line.rstrip("\r\n"))
        finally:
            lines.put(None)
    worker = threading.Thread(target=reader, daemon=True)
    worker.start()
    done = False
    try:
        while not done:
            if cancel is not None and cancel.is_set():
                process.terminate()
                raise ConversionCancelled("Conversion cancelled.")
            try:
                line = lines.get(timeout=0.2)
            except queue.Empty:
                if process.poll() is not None and not worker.is_alive():
                    break
                continue
            if line is None:
                done = True
            elif line and log:
                log(line)
        rc = process.wait()
        if rc != 0:
            raise RuntimeError(f"Command failed with exit code {rc}: {Path(args[0]).name}")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def convert_ffpfsc_to_ps4_pkg(
    source: str | Path, destination: str | Path, temp_dir: str | Path,
    mkpfs_prefix: list[str], pkg_builder: str | Path,
    log=None, cancel: threading.Event | None = None,
    command_runner=None,
) -> Path:
    """Unpack -> validate PS4 -> generate GP4 -> build and validate PKG.

    Source image is read-only; the destination never gets a partial PKG.
    Staging remains after a failure for diagnostics and safe retry.
    """
    image = inspect_ffpfsc(source)
    dest = Path(destination).resolve()
    temp = Path(temp_dir).resolve()
    builder = Path(pkg_builder).resolve()
    if not builder.is_file():
        raise ValueError("OrbisPkgTool.exe is missing. Please install/select the PS4 PKG builder.")
    if not mkpfs_prefix:
        raise ValueError("MkPFS is unavailable.")
    if dest.suffix.lower() != ".pkg" or dest == image:
        raise ValueError("Select a different output filename ending in .pkg.")
    if dest.exists():
        raise FileExistsError("The output PKG already exists; it will not be overwritten.")
    if not dest.parent.is_dir() or not temp.is_dir():
        raise ValueError("Output and temporary directories must already exist.")
    if temp == image.parent and temp == dest.parent:
        if log:
            log("Warning: input, output and TEMP share a volume; allow enough free space.")
    minimum_free = image.stat().st_size
    if shutil.disk_usage(temp).free < minimum_free:
        raise OSError("Insufficient TEMP space: free space is smaller than the source image.")
    if shutil.disk_usage(dest.parent).free < minimum_free:
        raise OSError("Insufficient output space: at least the source-image size must be free.")
    invoke = command_runner or (lambda cmd: run_live_command(cmd, log=log, cancel=cancel))
    stage = Path(tempfile.mkdtemp(prefix="ffpfsc_ps4_pkg_", dir=temp))
    extracted = stage / "game"
    gp4 = stage / "project.gp4"
    provisional = stage / "package.pkg"
    success = False
    try:
        if cancel is not None and cancel.is_set():
            raise ConversionCancelled("Conversion cancelled.")
        if log:
            log("Stage 1/3: unpacking the FFPFSC image (read-only).")
        invoke([*mkpfs_prefix, "unpack", "--deep", str(image), str(extracted)])
        if cancel is not None and cancel.is_set():
            raise ConversionCancelled("Conversion cancelled.")
        game = find_ps4_game_root(extracted)
        # ShadowMount+ uses param.json as a companion to PS4 param.sfo;
        # the synthetic JSON must not be treated as PS4 package metadata.
        shadowmount_json = game / "sce_sys" / "param.json"
        if shadowmount_json.is_file():
            shadowmount_json.unlink()
        if log:
            log("Stage 2/3: generating the PS4 GP4 project.")
        invoke([str(builder), "gp4gen", str(game), "--strict-gengp4", "--out", str(gp4)])
        if not gp4.is_file():
            raise RuntimeError("GP4 project generation did not create a file.")
        if cancel is not None and cancel.is_set():
            raise ConversionCancelled("Conversion cancelled.")
        if log:
            log("Stage 3/3: building and validating the PS4 fake PKG.")
        invoke([str(builder), "build", str(gp4), str(game), "--out", str(provisional), "--validate"])
        if not provisional.is_file() or provisional.stat().st_size < 1024:
            raise RuntimeError("The PKG builder did not produce a valid-sized file.")
        with provisional.open("rb") as handle:
            if handle.read(4) != PKG_MAGIC:
                raise RuntimeError("The built file has no PS4 PKG header.")
        if dest.exists():
            raise FileExistsError("The output PKG was created by another process; refusing overwrite.")
        # Cross-volume move is not atomic: copy to a partial file on the output
        # volume, then rename into place only after a successful copy.
        partial = dest.with_name(dest.name + ".partial")
        if partial.exists():
            raise FileExistsError("An output .partial file already exists; refusing overwrite.")
        try:
            shutil.copyfile(provisional, partial)
            if partial.stat().st_size != provisional.stat().st_size:
                raise IOError("Output copy size mismatch.")
            if dest.exists():
                raise FileExistsError("Output appeared during copying.")
            os.replace(partial, dest)
        finally:
            if partial.exists():
                partial.unlink()
        success = True
        if log:
            log("PS4 PKG created: " + str(dest))
        return dest
    except Exception:
        if log:
            log("Conversion failed; TEMP data retained at: " + str(stage))
        raise
    finally:
        if success:
            shutil.rmtree(stage, ignore_errors=True)
