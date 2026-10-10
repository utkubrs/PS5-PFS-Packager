# SPDX-License-Identifier: GPL-3.0-or-later
# Windows native VHD adapter for PS5 PFS Packager.

# -*- coding: utf-8 -*-
"""Windows native writable mounting for raw exFAT volume images.

The raw image is temporarily adapted in-place so Windows' built-in VHD provider
can expose it as a normal partition. No separately installed third-party
mounting application is used. Only a few boot sectors are temporarily patched
and a 512-byte fixed VHD footer is appended. A small recovery sidecar allows
restoration after an abnormal application exit.
"""
from __future__ import annotations

import base64
import ctypes
import datetime as _dt
import json
import os
import random
import re
import shutil
import struct
import subprocess
import time
import uuid

EXFAT_SIGNATURE = b"EXFAT   "
VHD_COOKIE = b"conectix"
BACKUP_SUFFIX = ".ps5pfs-native-mount.json"
PATCH_START_EXFAT_SECTOR = 24
PATCH_EXFAT_SECTOR_COUNT = 24

FILE_ATTRIBUTE_SPARSE_FILE = 0x00000200
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_ATTRIBUTE_COMPRESSED = 0x00000800
FILE_ATTRIBUTE_ENCRYPTED = 0x00004000


class NativeExfatError(RuntimeError):
    pass


def _startupinfo():
    if os.name != "nt":
        return None
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = 0
    return info


def _powershell_path() -> str:
    root = os.environ.get("SystemRoot", r"C:\Windows")
    candidate = os.path.join(root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    return candidate if os.path.isfile(candidate) else "powershell.exe"


def _cleanup_powershell_output(output: str) -> str:
    text = (output or "").replace("\r", "")
    # PowerShell may serialize progress records as CLIXML when called headless.
    if "<Objs Version=\"1.1.0.1\"" in text or "#< CLIXML" in text:
        text = re.sub(r"#<\s*CLIXML\s*", "", text, flags=re.I)
        text = re.sub(
            r"<Objs[^>]*>|</Objs>|<Obj[^>]*>|</Obj>|<TN[^>]*>|</TN>|<T>.*?</T>|<MS>|</MS>|<ToString>.*?</ToString>|<Props>|</Props>|<S [^>]*>|</S>|<I32>|</I32>|<SBK>.*?</SBK>|<Nil />|<Nil/>|<PR>|</PR>|<AV>|</AV>|<PI>.*?</PI>|<PC>.*?</PC>|<SR>|</SR>|<Ref[^>]*>|</Ref>",
            " ",
            text,
            flags=re.S,
        )
        text = text.replace("_x000D__x000A_", "\n")
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lower().startswith("preparing modules for first use"):
            continue
        if line in {"Completed", "progress", "OK"}:
            continue
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    return cleaned or "Unknown PowerShell error."


def _run_powershell(script: str, timeout: int = 90) -> str:
    if os.name != "nt":
        raise NativeExfatError("Windows is required.")
    prelude = (
        "$ProgressPreference='SilentlyContinue';"
        "$InformationPreference='Continue';"
        "$WarningPreference='Continue';"
        "$ErrorActionPreference='Stop';"
    )
    encoded = base64.b64encode((prelude + "\n" + script).encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [
            _powershell_path(),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        startupinfo=_startupinfo(),
        creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
    )
    output = _cleanup_powershell_output(result.stdout or "")
    if result.returncode != 0:
        raise NativeExfatError(output or f"PowerShell exit code: {result.returncode}")
    return output


def _ps_b64_text(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def backup_path(image_path: str | os.PathLike[str]) -> str:
    return os.fspath(image_path) + BACKUP_SUFFIX


def has_recovery_sidecar(image_path: str | os.PathLike[str]) -> bool:
    return os.path.isfile(backup_path(image_path))


def _load_backup(image_path: str) -> dict:
    sidecar = backup_path(image_path)
    try:
        with open(sidecar, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        raise NativeExfatError(f"Recovery metadata could not be read: {exc}") from exc
    if data.get("format") != "PS5PFS_NATIVE_EXFAT_V1":
        raise NativeExfatError("Recovery metadata format is invalid.")
    return data


def _atomic_write_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _win_file_attributes(path: str) -> int:
    if os.name != "nt":
        return 0
    GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
    GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
    GetFileAttributesW.restype = ctypes.c_uint32
    attrs = GetFileAttributesW(os.path.abspath(path))
    if attrs == 0xFFFFFFFF:
        raise NativeExfatError(f"Windows could not read the file attributes: {path}")
    return int(attrs)


def _is_probably_ntfs_local_path(path: str) -> bool:
    if os.name != "nt":
        return True
    drive = os.path.splitdrive(os.path.abspath(path))[0]
    if not drive:
        return True
    script = f"""
$drv = '{drive}'
$vol = Get-Volume -DriveLetter $drv.TrimEnd(':') -ErrorAction SilentlyContinue
if ($vol) {{ $vol.FileSystem }}
"""
    try:
        fs = (_run_powershell(script, timeout=20).splitlines() or [""])[-1].strip().upper()
        return fs in {"NTFS", "REFS", "CSVFS"}
    except Exception:
        return True


def _rewrite_plain_file(image_path: str) -> None:
    src = os.path.abspath(image_path)
    tmp = src + ".plaincopy.tmp"
    try:
        with open(src, "rb") as fin, open(tmp, "wb", buffering=0) as fout:
            while True:
                chunk = fin.read(16 * 1024 * 1024)
                if not chunk:
                    break
                fout.write(chunk)
            fout.flush()
            os.fsync(fout.fileno())
        try:
            shutil.copystat(src, tmp)
        except Exception:
            pass
        os.replace(tmp, src)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _ensure_mountable_backing_file(image_path: str) -> None:
    if os.name != "nt":
        return
    if not _is_probably_ntfs_local_path(image_path):
        raise NativeExfatError(
            "The image must be stored on a local NTFS/ReFS drive for the built-in Windows virtual disk system. "
            "Move the file to a normal local folder such as C:\\Temp or D:\\Images and try again."
        )

    attrs = _win_file_attributes(image_path)
    if attrs & FILE_ATTRIBUTE_ENCRYPTED:
        raise NativeExfatError(
            "The image file is EFS-encrypted. Windows cannot attach a writable VHD from an encrypted file. "
            "Remove encryption from the file or move it to a non-encrypted folder and try again."
        )

    needs_rewrite = False
    if attrs & FILE_ATTRIBUTE_COMPRESSED:
        compact = shutil.which("compact") or os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "compact.exe")
        try:
            subprocess.run(
                [compact, "/U", "/I", "/Q", image_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                startupinfo=_startupinfo(),
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
        except Exception:
            pass
        attrs = _win_file_attributes(image_path)
        if attrs & FILE_ATTRIBUTE_COMPRESSED:
            needs_rewrite = True

    if attrs & FILE_ATTRIBUTE_SPARSE_FILE:
        needs_rewrite = True

    if attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        # Reparse points (for example some cloud placeholders) often break VHD attach.
        needs_rewrite = True

    if needs_rewrite:
        _rewrite_plain_file(image_path)
        attrs = _win_file_attributes(image_path)
        if attrs & (FILE_ATTRIBUTE_COMPRESSED | FILE_ATTRIBUTE_SPARSE_FILE | FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_ENCRYPTED):
            raise NativeExfatError(
                "Windows could not convert the image file into a plain local backing file for the virtual disk. "
                "Please copy the image to a normal local NTFS folder (not cloud-only / not compressed) and try again."
            )


def _boot_checksum(region_first_11_sectors: bytes, bytes_per_sector: int) -> int:
    expected = 11 * bytes_per_sector
    if len(region_first_11_sectors) != expected:
        raise NativeExfatError("Invalid exFAT boot region length.")
    checksum = 0
    for index, value in enumerate(region_first_11_sectors):
        if index in (106, 107, 112):
            continue
        checksum = (((checksum << 31) | (checksum >> 1)) & 0xFFFFFFFF) + value
        checksum &= 0xFFFFFFFF
    return checksum


def _build_shifted_boot_region(main_boot_region: bytes, bytes_per_sector: int, shift_sectors: int) -> bytes:
    if len(main_boot_region) != 12 * bytes_per_sector:
        raise NativeExfatError("The exFAT boot region is incomplete.")
    region = bytearray(main_boot_region)
    vbr = memoryview(region)[:bytes_per_sector]
    if bytes(vbr[3:11]) != EXFAT_SIGNATURE:
        raise NativeExfatError("The selected file is not a raw exFAT volume image.")

    volume_length = struct.unpack_from("<Q", vbr, 72)[0]
    fat_offset = struct.unpack_from("<I", vbr, 80)[0]
    heap_offset = struct.unpack_from("<I", vbr, 88)[0]

    if volume_length <= shift_sectors:
        raise NativeExfatError("The exFAT image is too small for native mounting.")
    if fat_offset < shift_sectors + 24 or heap_offset <= shift_sectors:
        raise NativeExfatError(
            "This exFAT layout has insufficient reserved space for the native Windows mount adapter."
        )

    struct.pack_into("<Q", vbr, 64, shift_sectors)
    struct.pack_into("<Q", vbr, 72, volume_length - shift_sectors)
    struct.pack_into("<I", vbr, 80, fat_offset - shift_sectors)
    struct.pack_into("<I", vbr, 88, heap_offset - shift_sectors)

    checksum = _boot_checksum(bytes(region[: 11 * bytes_per_sector]), bytes_per_sector)
    checksum_sector = struct.pack("<I", checksum) * (bytes_per_sector // 4)
    region[11 * bytes_per_sector : 12 * bytes_per_sector] = checksum_sector
    return bytes(region)


def _vhd_geometry(total_sectors: int) -> tuple[int, int, int]:
    # Microsoft VHD specification CHS geometry calculation.
    max_sectors = 65535 * 16 * 255
    total = min(max(total_sectors, 1), max_sectors)
    if total >= 65535 * 16 * 63:
        sectors_per_track = 255
        heads = 16
        cylinders = total // (sectors_per_track * heads)
    else:
        sectors_per_track = 17
        cylinder_times_heads = total // sectors_per_track
        heads = (cylinder_times_heads + 1023) // 1024
        if heads < 4:
            heads = 4
        if cylinder_times_heads >= heads * 1024 or heads > 16:
            sectors_per_track = 31
            heads = 16
            cylinder_times_heads = total // sectors_per_track
        if cylinder_times_heads >= heads * 1024:
            sectors_per_track = 63
            heads = 16
            cylinder_times_heads = total // sectors_per_track
        cylinders = cylinder_times_heads // heads
    return min(cylinders, 65535), heads, sectors_per_track


def _build_fixed_vhd_footer(virtual_size: int) -> bytes:
    if virtual_size <= 0 or virtual_size % 512:
        raise NativeExfatError("The image size must be a positive multiple of 512 bytes.")
    footer = bytearray(512)
    footer[0:8] = VHD_COOKIE
    struct.pack_into(">I", footer, 8, 0x00000002)  # Features
    struct.pack_into(">I", footer, 12, 0x00010000)  # File format version
    struct.pack_into(">Q", footer, 16, 0xFFFFFFFFFFFFFFFF)  # Fixed disk: no dynamic header
    epoch = _dt.datetime(2000, 1, 1, tzinfo=_dt.timezone.utc)
    timestamp = int((_dt.datetime.now(_dt.timezone.utc) - epoch).total_seconds())
    struct.pack_into(">I", footer, 24, timestamp & 0xFFFFFFFF)
    footer[28:32] = b"P5PK"
    struct.pack_into(">I", footer, 32, 0x00020032)  # v2.3.2
    footer[36:40] = b"Wi2k"
    struct.pack_into(">Q", footer, 40, virtual_size)
    struct.pack_into(">Q", footer, 48, virtual_size)
    cylinders, heads, sectors = _vhd_geometry(virtual_size // 512)
    struct.pack_into(">HBB", footer, 56, cylinders, heads, sectors)
    struct.pack_into(">I", footer, 60, 2)  # Fixed hard disk
    footer[68:84] = uuid.uuid4().bytes
    footer[84] = 0
    struct.pack_into(">I", footer, 64, 0)
    checksum = (~sum(footer)) & 0xFFFFFFFF
    struct.pack_into(">I", footer, 64, checksum)
    return bytes(footer)


def _build_mbr(partition_start_lba: int, partition_length_lba: int) -> bytes:
    if not (1 <= partition_start_lba <= 0xFFFFFFFF):
        raise NativeExfatError("The partition start cannot be represented by an MBR.")
    if not (1 <= partition_length_lba <= 0xFFFFFFFF):
        raise NativeExfatError("Images larger than the MBR limit are not supported by this adapter.")
    mbr = bytearray(512)
    struct.pack_into("<I", mbr, 440, random.SystemRandom().randint(1, 0xFFFFFFFF))
    entry = bytearray(16)
    entry[0] = 0x00
    entry[1:4] = b"\xFE\xFF\xFF"
    entry[4] = 0x07  # NTFS/exFAT partition type
    entry[5:8] = b"\xFE\xFF\xFF"
    struct.pack_into("<I", entry, 8, partition_start_lba)
    struct.pack_into("<I", entry, 12, partition_length_lba)
    mbr[446:462] = entry
    mbr[510:512] = b"\x55\xAA"
    return bytes(mbr)


def _inspect_raw_exfat(image_path: str) -> dict:
    size = os.path.getsize(image_path)
    if size < 512 or size % 512:
        raise NativeExfatError("The selected image size is not aligned to 512 bytes.")
    with open(image_path, "rb") as fh:
        first = fh.read(512)
        if len(first) < 512 or first[3:11] != EXFAT_SIGNATURE or first[510:512] != b"\x55\xAA":
            raise NativeExfatError("The selected file is not a raw exFAT volume image.")
        bps_shift = first[108]
        if not 9 <= bps_shift <= 12:
            raise NativeExfatError(f"Unsupported exFAT sector-size shift: {bps_shift}")
        bytes_per_sector = 1 << bps_shift
        fh.seek(0)
        main_boot = fh.read(12 * bytes_per_sector)
    if len(main_boot) != 12 * bytes_per_sector:
        raise NativeExfatError("The exFAT boot region is incomplete.")
    volume_length = struct.unpack_from("<Q", main_boot, 72)[0]
    fat_offset = struct.unpack_from("<I", main_boot, 80)[0]
    if volume_length * bytes_per_sector > size:
        raise NativeExfatError("The exFAT volume length is larger than the image file.")
    if fat_offset < PATCH_START_EXFAT_SECTOR + PATCH_EXFAT_SECTOR_COUNT:
        raise NativeExfatError("The exFAT reserved area is too small for native mounting.")
    return {
        "size": size,
        "bytes_per_sector": bytes_per_sector,
        "volume_length": volume_length,
        "main_boot": main_boot,
    }


def prepare_image(image_path: str) -> dict:
    image_path = os.path.abspath(image_path)
    if has_recovery_sidecar(image_path):
        restore_image(image_path)

    _ensure_mountable_backing_file(image_path)
    info = _inspect_raw_exfat(image_path)
    bps = int(info["bytes_per_sector"])
    original_size = int(info["size"])
    patch_offset = PATCH_START_EXFAT_SECTOR * bps
    patch_length = PATCH_EXFAT_SECTOR_COUNT * bps
    with open(image_path, "rb") as fh:
        original_sector0 = fh.read(bps)
        fh.seek(patch_offset)
        original_patch = fh.read(patch_length)
    if len(original_sector0) != bps or len(original_patch) != patch_length:
        raise NativeExfatError("The image is truncated in the reserved boot area.")

    metadata = {
        "format": "PS5PFS_NATIVE_EXFAT_V1",
        "image_path": image_path,
        "original_size": original_size,
        "bytes_per_sector": bps,
        "volume_length": int(info["volume_length"]),
        "patch_start_sector": PATCH_START_EXFAT_SECTOR,
        "patch_sector_count": PATCH_EXFAT_SECTOR_COUNT,
        "original_sector0": base64.b64encode(original_sector0).decode("ascii"),
        "original_patch": base64.b64encode(original_patch).decode("ascii"),
        "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }
    _atomic_write_json(backup_path(image_path), metadata)

    shifted_boot = _build_shifted_boot_region(info["main_boot"], bps, PATCH_START_EXFAT_SECTOR)
    start_lba = patch_offset // 512
    volume_bytes = int(info["volume_length"]) * bps
    partition_length_lba = (volume_bytes - patch_offset) // 512
    mbr = _build_mbr(start_lba, partition_length_lba)
    footer = _build_fixed_vhd_footer(original_size)

    try:
        with open(image_path, "r+b", buffering=0) as fh:
            fh.seek(0)
            fh.write(mbr)
            fh.seek(patch_offset)
            fh.write(shifted_boot)
            fh.write(shifted_boot)
            fh.seek(original_size)
            fh.write(footer)
            fh.flush()
            os.fsync(fh.fileno())
    except Exception:
        try:
            restore_image(image_path)
        except Exception:
            pass
        raise
    return metadata


def _propagate_runtime_flags(fh, metadata: dict, original_sector0: bytearray) -> None:
    bps = int(metadata["bytes_per_sector"])
    patch_offset = int(metadata["patch_start_sector"]) * bps
    try:
        fh.seek(patch_offset)
        temp_vbr = fh.read(bps)
        if len(temp_vbr) >= 113 and temp_vbr[3:11] == EXFAT_SIGNATURE:
            original_sector0[106:108] = temp_vbr[106:108]
            original_sector0[112] = temp_vbr[112]
            # Original backup VBR at exFAT sector 12 was never overwritten.
            fh.seek(12 * bps)
            backup_vbr = bytearray(fh.read(bps))
            if len(backup_vbr) == bps and backup_vbr[3:11] == EXFAT_SIGNATURE:
                backup_vbr[106:108] = temp_vbr[106:108]
                backup_vbr[112] = temp_vbr[112]
                fh.seek(12 * bps)
                fh.write(backup_vbr)
    except Exception:
        # The backed-up original metadata is still sufficient to recover the image.
        pass


def restore_image(image_path: str) -> None:
    image_path = os.path.abspath(image_path)
    metadata = _load_backup(image_path)
    original_size = int(metadata["original_size"])
    bps = int(metadata["bytes_per_sector"])
    patch_offset = int(metadata["patch_start_sector"]) * bps
    original_sector0 = bytearray(base64.b64decode(metadata["original_sector0"]))
    original_patch = base64.b64decode(metadata["original_patch"])
    if len(original_sector0) != bps:
        raise NativeExfatError("Recovery sector backup is invalid.")
    if len(original_patch) != int(metadata["patch_sector_count"]) * bps:
        raise NativeExfatError("Recovery boot-area backup is invalid.")
    current_size = os.path.getsize(image_path)
    if current_size < original_size:
        raise NativeExfatError("The mounted image became smaller than its original size; automatic recovery stopped.")

    with open(image_path, "r+b", buffering=0) as fh:
        _propagate_runtime_flags(fh, metadata, original_sector0)
        fh.seek(0)
        fh.write(original_sector0)
        fh.seek(patch_offset)
        fh.write(original_patch)
        fh.truncate(original_size)
        fh.flush()
        os.fsync(fh.fileno())

    try:
        os.remove(backup_path(image_path))
    except FileNotFoundError:
        pass


def is_attached(image_path: str) -> bool:
    if os.name != "nt":
        return False
    img64 = _ps_b64_text(os.path.abspath(image_path))
    script = f"""
$img = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{img64}'))
$di = Get-DiskImage -ImagePath $img -StorageType VHD -ErrorAction SilentlyContinue
if ($di -and $di.Attached) {{ '1' }} else {{ '0' }}
"""
    try:
        return _run_powershell(script, timeout=20).splitlines()[-1].strip() == "1"
    except Exception:
        return False


def _dismount_windows(image_path: str, drive_letter: str = "U") -> None:
    img64 = _ps_b64_text(os.path.abspath(image_path))
    letter = drive_letter.upper()[0]
    script = f"""
$img = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{img64}'))
$di = Get-DiskImage -ImagePath $img -StorageType VHD -ErrorAction SilentlyContinue
if ($di -and $di.Attached) {{
    try {{
        $disk = $di | Get-Disk
        $parts = $disk | Get-Partition -ErrorAction SilentlyContinue
        foreach ($part in $parts) {{
            if ($part.DriveLetter) {{
                $access = "$($part.DriveLetter):\\"
                Remove-PartitionAccessPath -InputObject $part -AccessPath $access -ErrorAction SilentlyContinue
            }}
        }}
    }} catch {{}}
    Dismount-DiskImage -ImagePath $img -StorageType VHD -ErrorAction Stop
}}
'OK'
"""
    _run_powershell(script, timeout=60)


def mount_image(image_path: str, drive_letter: str = "U") -> None:
    image_path = os.path.abspath(image_path)
    letter = drive_letter.upper()[0]
    prepare_image(image_path)
    img64 = _ps_b64_text(image_path)
    script = f"""
$img = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{img64}'))
$letter = '{letter}'
if (Get-Volume -DriveLetter $letter -ErrorAction SilentlyContinue) {{
    throw "Drive $letter`: is already in use."
}}
$old = Get-DiskImage -ImagePath $img -StorageType VHD -ErrorAction SilentlyContinue
if ($old -and $old.Attached) {{
    Dismount-DiskImage -ImagePath $img -StorageType VHD -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
}}
Mount-DiskImage -ImagePath $img -StorageType VHD -Access ReadWrite -NoDriveLetter -ErrorAction Stop | Out-Null
Start-Sleep -Milliseconds 700
$disk = Get-DiskImage -ImagePath $img -StorageType VHD -ErrorAction Stop | Get-Disk -ErrorAction Stop
if ($disk.IsOffline) {{ $disk | Set-Disk -IsOffline $false -ErrorAction Stop }}
if ($disk.IsReadOnly) {{ $disk | Set-Disk -IsReadOnly $false -ErrorAction Stop }}
Start-Sleep -Milliseconds 500
$part = $disk | Get-Partition -ErrorAction Stop | Where-Object {{ $_.Size -gt 0 }} | Sort-Object Offset | Select-Object -First 1
if (-not $part) {{ throw 'Windows attached the virtual disk but did not find the exFAT partition.' }}
if ($part.DriveLetter -and $part.DriveLetter -ne $letter) {{
    Remove-PartitionAccessPath -InputObject $part -AccessPath "$($part.DriveLetter):\\" -ErrorAction SilentlyContinue
    $part = $disk | Get-Partition | Sort-Object Offset | Select-Object -First 1
}}
if ($part.DriveLetter -ne $letter) {{
    Set-Partition -InputObject $part -NewDriveLetter $letter -ErrorAction Stop
}}
Start-Sleep -Milliseconds 800
$vol = Get-Volume -DriveLetter $letter -ErrorAction Stop
if ($vol.FileSystem -ne 'exFAT') {{
    throw "Mounted volume is not exFAT (detected: $($vol.FileSystem))."
}}
'OK'
"""
    try:
        _run_powershell(script, timeout=90)
    except Exception as mount_exc:
        try:
            _dismount_windows(image_path, letter)
        except Exception:
            pass
        try:
            restore_image(image_path)
        except Exception as restore_exc:
            raise NativeExfatError(f"{mount_exc}\nRecovery also failed: {restore_exc}") from mount_exc
        raise NativeExfatError(str(mount_exc)) from mount_exc


def unmount_image(image_path: str, drive_letter: str = "U") -> None:
    image_path = os.path.abspath(image_path)
    _dismount_windows(image_path, drive_letter)
    deadline = time.time() + 10
    drive_root = f"{drive_letter.upper()[0]}:\\"
    while time.time() < deadline and os.path.exists(drive_root):
        time.sleep(0.2)
    if is_attached(image_path):
        raise NativeExfatError("Windows still reports the virtual disk as attached.")
    restore_image(image_path)


def recover_image(image_path: str, drive_letter: str = "U") -> None:
    image_path = os.path.abspath(image_path)
    if not has_recovery_sidecar(image_path):
        return
    if os.name == "nt":
        try:
            _dismount_windows(image_path, drive_letter)
        except Exception as exc:
            if is_attached(image_path):
                raise NativeExfatError(f"The previous virtual disk could not be detached: {exc}") from exc
    restore_image(image_path)
