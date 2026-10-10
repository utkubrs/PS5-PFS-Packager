# PS5 PFS Packager v2.13.0

## Highlights

- Updated MkPFS from `0.0.9` to `1.1.0`
- Added target platform selector: `PS5` / `PS4`
- `PS5` remains the default target
- Selected platform is passed to MkPFS `--version`
- Keeps Windows native VHD editing workflow
- Keeps automatic memory-error retry and pre-flight storage checks

## MkPFS 1.1.0 compatibility

MkPFS 1.1.0 includes compression-related bug fixes, dependency updates, restored PS4/PS5 selection in the upstream GUI and safer PS5 compression behavior.

## Build

Run:

```bat
scripts\build_windows.bat
```

The compiled EXE will bundle MkPFS 1.1.0.

## Important

- Windows 10/11 x64 only
- Administrator rights required
- Back up exFAT and FFPFSC images before editing
- No games, keys, firmware or proprietary fakelib files are included
