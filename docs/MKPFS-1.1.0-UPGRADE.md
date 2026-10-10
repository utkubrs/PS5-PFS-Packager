# MkPFS 1.1.0 migration (PS5 PFS Packager v2.11)

The supplied application was updated locally from MkPFS 0.0.9 to 1.1.0. The updated full project is delivered as a ZIP attachment in the associated ChatGPT conversation; this documentation commit alone does **not** deploy the full application code.

## Changes
- Update bundled MkPFS version detection to `1.1.0`.
- Pin the build dependency to `mkpfs[gui]==1.1.0`.
- Keep `--version PS5`, `--inode-bits 32` and exFAT-wrapped default folder packing (`pack folder` without `--raw`).
- Benefit from upstream fix preventing PS5-unsafe automatic ISA-L compression.
- Replace machine-specific Python executable path in Windows Nuitka build script with `py -3` / `python` detection.
- Update application and executable version from 2.10 to 2.11.
- Add requirements, gitignore and migration documentation.

## Important
- Python syntax validated; Windows EXE build and console hardware/ShadowMountPlus compatibility require Windows and PS5 testing.
- Upstream release: https://github.com/PSBrew/MkPFS/releases/tag/1.1.0
