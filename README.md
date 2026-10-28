# PS5 PFS Packager v1.0

Portable Windows 10/11 x64 GUI for converting PS5 game folders and raw exFAT images to FFPFSC, handling PS4 game/update merges, editing PS4 PARAM.SFO title fields, and **experimentally building PS4 fake PKGs from supported PS4 FFPFSC images**.

[**Download PS5-PFS-Packager.exe**](https://github.com/utkubrs/PS5-PFS-Packager/releases/download/v1.0/PS5-PFS-Packager.exe) · [Release v1.0](https://github.com/utkubrs/PS5-PFS-Packager/releases/tag/v1.0)

## Installation

1. Download **PS5-PFS-Packager.exe** from the existing v1.0 release.
2. Run it on Windows 10/11 x64. Administrative rights are needed for writable virtual-drive features.
3. Select the game/image, output location, and a temporary working directory with sufficient free disk space.
4. Keep source backups and test generated packages on your own compatible hardware.

The executable bundles Python runtime components, MkPFS 1.1.0, the PS4 PKG extractor and the open-source GP4 generator (OrbisPkgTool). The Orbis Publisher Tools PKG builder must be supplied separately by the user. No Python or .NET installation is needed for the downloadable EXE. A local `ps5-pfs-config.ini` file may be generated for settings.

## Features

- Convert supported PS5 folders and raw `.exfat` images into `.ffpfsc` containers.
- Merge PS4 base game + optional update before FFPFSC conversion, with a FIFO job queue.
- Preserve the base game artwork; if `pic0.png` or `pic0.dds` is missing inside the staging directory, rename the corresponding `pic1` image without editing source games.
- Apply a custom PS4 game title to all existing `TITLE` and `TITLE_XX` text fields in the staged PARAM.SFO while preserving title/content IDs and version metadata.
- Edit existing PARAM.SFO localized title fields individually or together, with an original-file backup.
- Configure CPU, compression level, block size, TEMP paths, additional verification and optional cleanup.
- Open and modify supported exFAT/FFPFSC images.
- Switch between 15 interface languages, including Turkish and English.

## FFPFSC → PS4 PKG (Orbis Publisher Tools)

**User-verified console test:** A PS4 base game + merged update packed into FFPFSC ran with ShadowMountPlus; the independently built Orbis Publisher Tools 3.87 PKG of the same source installed and launched on a PS5 Pro (FW 10.01). The earlier all-open-source OrbisPkgTool-built PKG was rejected with CE-118872-7. This does not yet establish that the *new automated GP4 pipeline* produces console-installable PKGs; please test it.

1. Select a PS4 `.ffpfsc` image, output `.pkg` file, and a TEMP folder with ample space.
2. Select your **locally installed** `orbis-pub-cmd.exe`. Its sibling `ext/` directory must exist. The app can auto-detect a common `Desktop/Playstation Araçları/Obris` installation.
3. MkPFS extracts the image; the tool checks `eboot.bin`, `sce_sys/param.sfo`, CUSA title ID, and `CATEGORY=gd`.
4. The bundled **open-source OrbisPkgTool** generates a `--strict-gengp4` project. Paths are rebound to the temporary extraction directory.
5. The installed **Orbis Publisher Tools** CLI builds the actual PKG via `img_create --oformat pkg <project.gp4> <output_directory>`. Exactly one output package and its magic header are checked, and it is safely copied to the selected destination.

**Important:** Sony Orbis Publisher Tools executables and proprietary dependencies are **not included** in the release or repository; users must supply their own lawful installation. Neither the user's source image nor an existing destination package is overwritten. Failed staging is retained for diagnostics; successful staging is removed.

This converter supports PS4 base-game content only, not native PS5 packages, and it does not decrypt retail games. Large TEMP capacity is needed. Console compatibility remains to be checked per output.

## Requirements and troubleshooting

- Windows 10/11 x64. Use an NTFS temporary folder, preferably on SSD/NVMe.
- For PS4 packaging, the image must contain a **PS4 CUSA game** and a valid `sce_sys/param.sfo`; PS5 PPSA-only images are rejected.
- If GP4 generation or PKG validation fails, inspect the dialog logs and the retained TEMP staging directory. Do not rename an `.ffpfsc` file to `.pkg` manually.
- The downloadable EXE is unsigned, so Microsoft SmartScreen may display a warning. Compare the SHA-256 value shown in the v1.0 release description.
- Actual PS4/PS5 console compatibility must be tested separately from GitHub Actions integration and synthetic tests.

## Build from source

The GUI and converters are in `src/`; tests are in `tests/`. On Windows with Python 3.11 x64, use `scripts/build_windows.bat`. GitHub Actions compiles a single Windows executable and updates **the existing v1.0 release only**. It never creates a new release automatically.

The CI pipeline builds the pinned MIT-licensed OrbisPkgTool GP4 generator source (commit `5cd42a515dc29a453c7abcb93318493bdb5b5e1f`) for Windows x64, embeds its self-contained executable and MIT license notice, compiles the Python GUI with Nuitka, tests bundled tools, and publishes the one executable.

## Legal and third-party notices

Use this software only for homebrew, research, preservation and backups of content you lawfully own. No games, Sony firmware, retail decryption keys, or proprietary console libraries are distributed. PS4, PS5 and PlayStation are trademarks of Sony Interactive Entertainment. This project is independent and is not endorsed by Sony.

- **MkPFS 1.1.0** (PSBrew/MkPFS): GPL-3.0; FFPFSC/PFS image handling.
- **OrbisPkgTool** (pearlxcore/OrbisPkgTool): MIT; strict GP4 generation only in the conversion pipeline. Its MIT license is embedded in the executable as `tools/OrbisPkgTool.LICENSE.txt`.\n- **Orbis Publisher Tools** (user-installed): external PKG building; not redistributed.
- **Python + Tkinter**: Python Software Foundation License.
- **Nuitka**: Apache-2.0.
- **psutil**: BSD-3-Clause.
- **cryptography**: Apache-2.0/BSD.

The repository itself is GPL-3.0-or-later. Consult upstream projects for full third-party license texts.
