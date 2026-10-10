# Architecture

## Application layer

`src/ps5_pfs_packager.py` contains:

- Tkinter user interface
- 15-language translation tables
- conversion queue
- process management
- progress parsing
- disk checks
- profile and retry logic
- MkPFS command construction
- logging and configuration

## Native exFAT mount layer

`src/native_exfat_mount.py` uses Windows' built-in VHD APIs through PowerShell and temporary VHD metadata adaptation.

It does not require OSFMount or ImDisk.

## Conversion flows

### Game folder → FFPFSC

```text
Game folder
   ↓ MkPFS pack folder
exFAT-wrapped compressed FFPFSC
```

### exFAT → FFPFSC

```text
Raw exFAT image
   ↓ MkPFS pack file
Compressed FFPFSC
```

### FFPFSC edit

```text
FFPFSC
   ↓ MkPFS unpack
Temporary raw exFAT
   ↓ Windows native VHD mount
Writable U:
   ↓ safe disconnect
Modified raw exFAT
   ↓ MkPFS pack file
Temporary rebuilt FFPFSC
   ↓ optional verification + atomic replace
Original FFPFSC updated
```

## Security boundaries

- The application runs elevated.
- Direct exFAT editing changes the original image.
- FFPFSC editing uses a temporary working image.
- Proprietary fakelib files are not included.
- User-controlled paths are passed as subprocess argument arrays rather than shell command strings.
