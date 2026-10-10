# Build from source on Windows

## Requirements

- Windows 10 or Windows 11, 64-bit
- Python 3.11, 64-bit
- Internet access during the first dependency installation
- Approximately 2–4 GiB free space for the Nuitka build environment

## Automated build

Open Command Prompt in the repository folder and run:

```bat
scripts\build_windows.bat
```

The script:

1. locates Python 3.11,
2. creates `.venv`,
3. installs runtime and build requirements,
4. removes old Nuitka folders,
5. builds an administrator-enabled one-file EXE,
6. creates a portable release ZIP.

Outputs:

```text
dist\PS5-PFS-Packager.exe
release\PS5-PFS-Packager-v2.13.0-Windows-x64.zip
```

## Run from source

```bat
scripts\run_source.bat
```

The application requests administrator rights at startup because native writable VHD mounting requires elevation.

## Manual environment

```bat
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
```

## Syntax check

```bat
.venv\Scripts\python.exe -m py_compile src\ps5_pfs_packager.py
.venv\Scripts\python.exe -m py_compile src\native_exfat_mount.py
```

## Reproducibility notes

- MkPFS is pinned to `1.1.0`.
- Python 3.11 is the tested build version.
- The exact Nuitka version may affect EXE size and antivirus heuristics.
- Do not commit proprietary `*.sprx` fakelib files.
