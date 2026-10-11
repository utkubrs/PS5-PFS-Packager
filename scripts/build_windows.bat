@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0\.."

where py.exe >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python launcher not found. Install Python 3.11 x64.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
  if errorlevel 1 goto :error
)

set "PY=.venv\Scripts\python.exe"

echo [1/4] Installing dependencies...
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r requirements-build.txt
if errorlevel 1 goto :error

echo [2/4] Syntax check...
"%PY%" -m py_compile src\ps5_pfs_packager.py
"%PY%" -m py_compile src\native_exfat_mount.py
if errorlevel 1 goto :error

echo [3/4] Cleaning output...
if exist dist rmdir /s /q dist
mkdir dist

echo [4/4] Preparing application icon...
"%PY%" scripts\generate_icon.py
if errorlevel 1 goto :error

echo [4/4] Building portable standalone EXE with Nuitka...
set "SOUND_ARGS="
if exist "assets\completion.mp3" if exist "assets\error.mp3" (
  set "SOUND_ARGS=--include-data-files=assets\completion.mp3=completion.mp3 --include-data-files=assets\error.mp3=error.mp3"
  echo [INFO] Original MP3 sound effects included.
) else (
  echo [WARN] Original completion.mp3/error.mp3 missing from assets; using application fallback sounds.
)

"%PY%" -m nuitka ^
  --mode=onefile ^
  --onefile-no-compression ^
  --mingw64 ^
  --assume-yes-for-downloads ^
  --enable-plugin=tk-inter ^
  --windows-console-mode=disable ^
  %SOUND_ARGS% ^
  --windows-uac-admin ^
  --windows-icon-from-ico=assets\appicon.ico ^
  --include-data-files=assets\appicon.ico=appicon.ico ^
  --output-dir=dist ^
  --output-filename=PS5-PFS-Packager.exe ^
  --include-package=mkpfs ^
  --include-package-data=mkpfs ^
  --include-module=mkpfs.cli ^
  --include-module=native_exfat_mount ^
  --include-module=ps4_inputs ^
  --include-module=ps4_merge ^
  --include-module=upgrade_features ^
  --include-package=psutil ^
  --include-package=cryptography ^
  --file-description="PS5 PFS Packager - FFPFSC and exFAT Converter" ^
  --product-name="PS5 PFS Packager" ^
  --company-name="PS5 PFS Packager Contributors" ^
  --copyright="GPL-3.0-or-later" ^
  --file-version=2.20.0.0 ^
  --product-version=2.20.0.0 ^
  src\ps5_pfs_packager.py

if errorlevel 1 goto :error

echo.
echo [DONE] dist\ps5_pfs_packager.dist\PS5-PFS-Packager.exe
pause
exit /b 0

:error
echo.
echo [ERROR] Build failed.
pause
exit /b 1
