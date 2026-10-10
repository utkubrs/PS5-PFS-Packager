@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv
)

set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install -r requirements.txt
"%PY%" src\ps5_pfs_packager.py
