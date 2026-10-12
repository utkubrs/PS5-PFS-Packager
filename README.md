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
PS5-PFS-Packager-v2.25.0-Windows-x64.zip
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


## v2.19.0 enhancements

- Game title, Title ID and locally available `sce_sys/icon0.png` preview when selecting a game directory.
- Preflight disk space and TEMP/output directory checks before packing; output-in-source protection.
- Explicit block-size advice in preview while preserving upstream auto selection.
- Safety guard blocking PS5 compressed raw PFS packing.
- Windows EXE icon generated and embedded at build time.
- Existing batch conversion and image editing capabilities remain available.

See [v2.19.0 release notes](RELEASE_NOTES_v2.19.0.md). Windows binaries are published via GitHub Actions after a successful build. Source changes are not evidence of a successful executable build.


## PS4 inputs (v2.19.0)

Choose **PS4** in the Platform control before converting a PS4 title.

- Unpacked PS4 game folders containing `eboot.bin` and `sce_sys/param.sfo` are accepted, including in batch discovery.
- `.exfat` and MkPFS-compatible `.ffpkg` images are passed directly to MkPFS `pack file`.
- `.pkg` files use optional external [pkgextract](https://github.com/paulomanrique/ps4-pkg-extractor) CLI. Install `pkgextract.exe` in PATH, or set `PS4_PKG_EXTRACTOR` to the absolute executable path. Extraction is staged under the **selected TEMP directory** and retained for inspection. Provide enough disk space for both extraction and the output. Do not reuse an existing extraction folder without cleaning it manually.
- Existing PlayStation encrypted retail PKGs are **not guaranteed** to be extractable. Extraction does not remove license or encryption requirements; only convert your legally owned and compatible content.
- PS4 folder packing omits PS5-specific `--require-game-files` validation. Actual console compatibility must be verified separately.

Read [release notes](RELEASE_NOTES_v2.19.0.md) for limitations and test status.


## PS4 Merge + PARAM.SFO (v2.19.0)

- **PS4 Oyun + Update Birleştir** accepts already-extracted base and update game folders and stages the merged game into your selected TEMP location. Originals remain untouched.
- The merge overlays update game files over base files, while preserving base `sce_sys/param.sfo`, `icon0.png`, `pic0.png`, `pic1.png` and related images. The update and base `TITLE_ID` must match when both are present.
- Enter an optional game title; the `TITLE` value is changed with UTF-8 length validation. `TITLE_ID` and `CONTENT_ID` are never edited. A separate **PARAM.SFO Düzenle** window exposes safe TITLE editing.
- After merging, use the existing Convert action to build FFPFSC. This is **folder merge → FFPFSC**, not a newly created PS4 PKG.
- Success/error MP3 calls already exist in the code, but the actual original MP3 binary assets must also be supplied during the build. If they are not embedded, the application falls back to existing notification behavior.
- Consult [v2.16 notes](RELEASE_NOTES_v2.19.0.md).


## v2.19.0: PS4 PKG inputs and custom title

- The PS4 Oyun + Update Birleştir dialog accepts extracted PS4 folders or .pkg files for both base game and update. .pkg extraction requires an optional, separately installed pkgextract CLI.
- Extraction and merged files are staged in the selected TEMP folder. Originals remain unchanged. Allow space for extraction and merged content.
- The PS4 oyun adı (TITLE) main-window field edits sce_sys/param.sfo in a temporary copy during conversion; the FFPFSC output file name is separate.
- Base icon0.png, pic0.png, pic1.png and param.sfo remain authoritative during merge. TITLE_ID and CONTENT_ID remain protected.
- Encrypted retail PKGs might not be extractable; merge does not guarantee runtime compatibility.

See RELEASE_NOTES_v2.19.0.md.


## v2.19.0 refinements

- Removed the redundant main-screen PS4 TITLE entry. The merge dialog still permits editing the game title.
- Base game title is suggested from the file name and refined from its actual PARAM.SFO TITLE after extraction unless customized.
- Game preview heading and empty-source prompt are available for all 15 UI languages.
- PS4 package extractor is located via PS4_PKG_EXTRACTOR, PATH, or a portable pkgextract.exe placed beside the EXE or under tools/.
- Original sound effects are searched beside the installed EXE or in the nearby assets/ folder. The repository presently does not contain the original binary MP3 assets. To hear the original cues, place completion.mp3 and error.mp3 alongside PS5-PFS-Packager.exe (or under assets/).
- A working package extractor remains mandatory for PKG inputs, and encrypted/DRM-protected retail packages may be unsupported. Windows EXE and real console behavior still require tests.


## v2.19.0: PS4 PKG extractor shipped in Windows ZIP

The Windows release workflow downloads pinned upstream `pkgextract.exe` v0.0.1 and verifies the exact SHA-256 archive checksum before shipping it under `tools/pkgextract.exe`. It is distributed with the Windows release ZIP, not embedded inside the Nuitka EXE. Extract the full ZIP before launching the application; copying only the main EXE will result in the missing-extractor error. PS4 update input need not contain eboot.bin; it must contain sce_sys/param.sfo.

**Audio**: Original custom completion.mp3 and error.mp3 are not committed as binary assets in this repository. To use them, copy the previously supplied original files beside PS5-PFS-Packager.exe. The code will detect and play them. This release does NOT claim that the custom MP3s are bundled.

Platform PKG extraction may still fail for encrypted/proprietary PKGs. Windows execution and game compatibility require real tests.


## v2.20.0 – Windows DLL error 126 fix

- Nuitka now builds a **standalone directory**, not a single-file executable. This avoids launching a second instance of the onefile bootstrap when MkPFS runs as a child process.
- GitHub Actions runs `PS5-PFS-Packager.exe --internal-mkpfs --help` as a subprocess and **blocks publication** if it fails.
- The Windows ZIP contains the entire standalone application folder, its DLLs, and the optional PS4 PKG extractor in `tools/`. **Keep all these files together**; do not move only the EXE.
- Build and smoke test success are not a substitute for real PS4/PS5 console verification.


## v2.21.0 – hidden extraction and automatic platform selection

- Windows PKG extraction now sets CREATE_NO_WINDOW and hides the external pkgextract console, with approximate size-based progress messages inside the main program log.
- Automatically selects PS4 for sources with sce_sys/param.sfo or CUSA identifiers, and PS5 for folders with sce_sys/param.json or PPSA identifiers. Unidentified sources keep the manually selected platform; a generic .pkg defaults to PS4.
- The PS4 merge window selects PS4 automatically. The same source-change detection applies in normal single-file conversion.
- Original MP3 playback logs whether completion.mp3/error.mp3 were found and the Windows playback error if present. **The audio binary assets are not committed to this repository**. Put both files beside the EXE or into the assets directory to get the original cues. Log diagnostics do not make unavailable sound assets appear automatically.
- MkPFS remains 1.1.0; real Windows execution and console compatibility still require verification.


## v2.22.0 PS4 merge title fix

Fixed a Python `UnboundLocalError` caused by reassigning the merge dialog TITLE within the background worker's scope. The merge now uses a local `effective_title`; explicitly entered names are preserved and the base game's PARAM.SFO remains the fallback. Previously extracted game/update folders can be selected directly with the **Klasör** buttons after checking that extraction completed. Do not use incomplete extraction folders.


## v2.23.0 – integrated PS4 merge progress

- Clicking **Birleştir ve Kaynak Olarak Seç** closes its small modal immediately and tracks the merge on the main window.
- Main progress bar/status shows actual bytes copied, total copy workload in GiB, and completed/total file count. Copy progress is based on byte counts, not a guessed compression percentage. Update files excluded by the base-artwork protection are not counted as work.
- The main log periodically records merge milestones. Upon completion the merged folder becomes the active source; the user starts FFPFSC packaging separately.
- A concurrent conversion cannot be started while merge is running. Existing source folders are untouched.
- Large directory trees require an initial size inventory before copying starts, which may take time. Windows build success and console game compatibility still require confirmation.


## v2.25.0 – PS4 single-click merge and FFPFSC\n\n- Choose a PS4 base game and patch (PKG or extracted folders), adjust the title/output if desired, then use the single green button.\n- Package extraction, merge and FFPFSC packing continue automatically. No second Convert click or confirmation dialog is needed.\n- Detect CUSA from PKG headers or extracted PARAM.SFO; manually edited FFPFSC output names remain unchanged.\n- Move app-created TEMP extractions to avoid a redundant full-sized game copy. Directly selected game/update folders remain untouched.\n- Uses the selected TEMP/output directories and retains the extraction/merge log into the packing phase.\n\n## v2.24.0 – unified PS4 merge settings and localization

- The PS4 game+update dialog now includes **Output folder**, **FFPFSC file name**, and **TEMP folder**, prefilled from the main window.
- Confirmed values synchronize back to the main form. The selected FFPFSC file name is preserved even after the merged game folder becomes the source.
- Localized the merge dialog, its status/error messages, main PS4 action buttons, and the PARAM.SFO title editor across all 15 UI languages.
- Merge still closes the modal and reports byte/file progress in the main window; MkPFS packaging begins when the user clicks Convert.
- GitHub Actions validates i18n coverage and builds the Windows x64 portable package. Download is available only after the workflow and release upload succeed.
