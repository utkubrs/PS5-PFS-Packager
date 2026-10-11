# PS5 PFS Packager v2.15.0

## Changes
- Added PS4 game-folder recognition using `eboot.bin` and `sce_sys/param.sfo`.
- Scan PS4 folders in batch discovery; recognize CUSA title IDs in filenames.
- Accept `.ffpkg` directly using MkPFS 1.1.0 `pack file`.
- Optionally extract PS4 `.pkg` to the selected TEMP disk with the independently installed `pkgextract` executable, then package the extracted PS4 game directory.
- Updated source picker and Windows build.
- PS4 folders no longer receive PS5-specific `--require-game-files` flag.

## Prerequisites & limitations
- For PKG input install `pkgextract.exe` from https://github.com/paulomanrique/ps4-pkg-extractor into PATH or configure `PS4_PKG_EXTRACTOR`. The extractor is not redistributed with this software.
- Extracted directories remain in TEMP until manually cleaned; this also helps diagnose failures.
- Retail encrypted packages, DRM and console compatibility are not bypassed by the application.
- Real Windows and PS4 console validation is still needed.

## Distribution
GitHub Actions workflow `.github/workflows/windows-release.yml` builds `PS5-PFS-Packager-v2.15.0-Windows-x64.zip` and uploads the zip and SHA256SUMS after a successful job. Do not consider the binary published until the run passes.
