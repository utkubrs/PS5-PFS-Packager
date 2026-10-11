# PS5 PFS Packager / FFPFSC - exFAT Converter

<p align="center">
  <img src="assets/social-preview.png" alt="PS5 PFS Packager - FFPFSC and exFAT Converter" width="100%">
</p>

<p align="center">
  <strong>Windows GUI for PS5 game-folder → FFPFSC and exFAT → FFPFSC conversion, writable image editing, batch workflows and 15-language support.</strong>
</p>

<p align="center">
  <a href="README_TR.md">Türkçe</a> •
  <a href="#download">Download</a> •
  <a href="#features">Features</a> •
  <a href="#usage">Usage</a> •
  <a href="docs/BUILDING.md">Build from source</a> •
  <a href="docs/TROUBLESHOOTING.md">Troubleshooting</a>
</p>

![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4)
![Python](https://img.shields.io/badge/Python-3.11-3776AB)
![MkPFS](https://img.shields.io/badge/MkPFS-1.1.0-6f42c1)
![Languages](https://img.shields.io/badge/UI%20Languages-15-2f6fed)
![License](https://img.shields.io/badge/License-GPL--3.0-green)

PS5 PFS Packager is a desktop GUI built around **MkPFS**. It simplifies PS5 PFS image workflows for users who prefer a graphical interface instead of terminal commands.

Search keywords: **PS5 FFPFSC converter**, **FFPFS tool**, **exFAT to FFPFSC**, **PS5 PFS packager**, **MkPFS GUI**, **PS5 image editor**, **PS5 homebrew tools**.

> [!IMPORTANT]
> Use this project only with homebrew and content you legally own. No games, keys, firmware or proprietary Sony files are included.

## Download

Download the latest Windows package from the repository's **Releases** page.

The release asset is named:

```text
PS5-PFS-Packager-v2.15.0-Windows-x64.zip
```

After downloading:

1. Extract the ZIP to a normal writable folder.
2. Run `PS5-PFS-Packager.exe`.
3. Accept the Windows administrator prompt.
4. Select a source, output folder and temp folder.
5. Start the conversion.

The executable is currently unsigned, so Windows SmartScreen may display a warning. Verify the SHA-256 checksum published with each release.

## Features

### Conversion

- PS5 game folder → exFAT-wrapped `.ffpfsc`
- `.exfat` image → compressed `.ffpfsc`
- Single-game and multi-game batch modes
- Recursive discovery of valid PS5 game folders and exFAT images
- Optional extra verification
- Optional source-folder deletion after success
- Optional shutdown after completion

### Writable image editing

- Open a raw `.exfat` image directly as writable `U:`
- No full temp copy for direct exFAT mounting
- Open `.ffpfsc`, extract its wrapped exFAT to the selected temp folder and mount it as `U:`
- Add, replace or delete files using Windows File Explorer
- Save changes back over the original `.ffpfsc` through a safe temporary rebuild
- Windows native VHD system; no OSFMount or ImDisk dependency

### Performance and reliability

- Compression profiles: Fast, Balanced, Maximum and Low RAM
- CPU-core selection
- Compression levels `0–9`
- Block sizes: `auto`, `auto-fit`, `16384`, `32768`, `65536`
- Automatic retry with safer settings after memory errors
- Pre-flight free-space and filesystem checks
- FAT32 large-file protection
- SSD/HDD temp-drive warnings
- Compression-gain reporting
- Progress, speed, ETA, CPU and memory monitoring
- HTML operation logs

### Optional fakelib workflow

The program can copy user-supplied:

- `libSceAmpr.sprx`
- `libScePlayGo.sprx`

No proprietary libraries are included in this repository.

## 15 interface languages

- Türkçe
- English
- Français
- Español
- Italiano
- Ελληνικά
- 한국어
- 日本語
- Deutsch
- Português
- Русский
- 中文
- العربية
- Nederlands
- Polski

## Requirements

- Windows 10 or Windows 11, 64-bit
- Windows 7 / 8 / 8.1 are not supported
- Administrator rights for writable virtual-drive operations
- Enough output space for the final FFPFSC
- Enough temp space when opening or rebuilding FFPFSC images
- NTFS is recommended for the temp folder
- SSD or NVMe is recommended for large workflows

## Usage

### Convert a PS5 game folder

1. Select **Single Game Convert**.
2. Choose the game folder.
3. Choose the output and temp folders.
4. Select a profile or manual CPU/compression/block settings.
5. Click **Convert Single Game**.

A valid game folder normally contains:

```text
eboot.bin
sce_sys/param.json
```

### Convert an exFAT image

1. Select the `.exfat` file as the source.
2. Choose the output folder.
3. Confirm the output filename.
4. Start the conversion.

### Batch conversion

1. Select **Multi Game Convert**.
2. Choose a parent folder.
3. The application scans up to three levels deep.
4. Valid game folders and `.exfat` files are added to the queue.
5. Start the batch.

### Open and edit exFAT

1. Click **Open Exfat/Ffpfsc**.
2. Choose **Open Exfat file**.
3. The image is mounted directly as writable `U:`.
4. Edit files through File Explorer.
5. Use **Save EXFAT and safely disconnect U:**.

Changes are written to the original exFAT image. Make a backup before editing.

### Open and edit FFPFSC

1. Click **Open Exfat/Ffpfsc**.
2. Choose **Open Ffpfsc file**.
3. The wrapped exFAT is extracted under the selected temp folder.
4. The temporary exFAT is mounted as writable `U:`.
5. Edit files.
6. Choose **Save and overwrite original FFPFSC**.

The new FFPFSC is built completely before the original is atomically replaced.

## Build from source

See [docs/BUILDING.md](docs/BUILDING.md).

Quick build:

```bat
scripts\build_windows.bat
```

## Documentation

- [Turkish README](README_TR.md)
- [Installation](docs/INSTALLATION.md)
- [Detailed user guide](docs/USER_GUIDE.md)
- [Build instructions](docs/BUILDING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [GitHub publishing guide — Turkish](docs/GITHUB_PUBLISHING_TR.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Credits

- [MkPFS](https://github.com/PSBrew/MkPFS) by PSBrew
- Python, Tkinter, Nuitka, psutil and cryptography contributors
- Translators, testers and issue reporters

## License

GPL-3.0-or-later. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

This project is not affiliated with Sony Interactive Entertainment.

## MkPFS 1.1.0 update

This release updates the bundled MkPFS dependency to **1.1.0**.

Notable upstream changes used by this GUI:

- compression-related bug fixes,
- dependency updates,
- safer PS5 compression behavior,
- restored PS4 / PS5 selection in the upstream GUI.

The desktop GUI now exposes a **Platform** selector with `PS5` and `PS4`. `PS5` remains the default target.


## v2.15.0 enhancements

- Game title, Title ID and locally available `sce_sys/icon0.png` preview when selecting a game directory.
- Preflight disk space and TEMP/output directory checks before packing; output-in-source protection.
- Explicit block-size advice in preview while preserving upstream auto selection.
- Safety guard blocking PS5 compressed raw PFS packing.
- Windows EXE icon generated and embedded at build time.
- Existing batch conversion and image editing capabilities remain available.

See [v2.15.0 release notes](RELEASE_NOTES_v2.15.0.md). Windows binaries are published via GitHub Actions after a successful build. Source changes are not evidence of a successful executable build.


## PS4 inputs (v2.15.0)

Choose **PS4** in the Platform control before converting a PS4 title.

- Unpacked PS4 game folders containing `eboot.bin` and `sce_sys/param.sfo` are accepted, including in batch discovery.
- `.exfat` and MkPFS-compatible `.ffpkg` images are passed directly to MkPFS `pack file`.
- `.pkg` files use optional external [pkgextract](https://github.com/paulomanrique/ps4-pkg-extractor) CLI. Install `pkgextract.exe` in PATH, or set `PS4_PKG_EXTRACTOR` to the absolute executable path. Extraction is staged under the **selected TEMP directory** and retained for inspection. Provide enough disk space for both extraction and the output. Do not reuse an existing extraction folder without cleaning it manually.
- Existing PlayStation encrypted retail PKGs are **not guaranteed** to be extractable. Extraction does not remove license or encryption requirements; only convert your legally owned and compatible content.
- PS4 folder packing omits PS5-specific `--require-game-files` validation. Actual console compatibility must be verified separately.

Read [release notes](RELEASE_NOTES_v2.15.0.md) for limitations and test status.
