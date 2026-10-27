# PS5 PFS Packager v1.0

Portable Windows 10/11 x64 GUI for converting PS5 game folders and raw exFAT images to FFPFSC, handling PS4 game/update merges, editing PS4 PARAM.SFO title fields, and **experimentally building PS4 fake PKGs from supported PS4 FFPFSC images**.

[**Download PS5-PFS-Packager.exe**](https://github.com/utkubrs/PS5-PFS-Packager/releases/download/v1.0/PS5-PFS-Packager.exe) · [Release v1.0](https://github.com/utkubrs/PS5-PFS-Packager/releases/tag/v1.0)

## Installation

1. Download **PS5-PFS-Packager.exe** from the existing v1.0 release.
2. Run it on Windows 10/11 x64. Administrative rights are needed for writable virtual-drive features.
3. Select the game/image, output location, and a temporary working directory with sufficient free disk space.
4. Keep source backups and test generated packages on your own compatible hardware.

The executable bundles Python runtime components, MkPFS 1.1.0, the PS4 PKG extractor and the open-source PS4 PKG builder. No Python or .NET installation is needed for the downloadable EXE. A local `ps5-pfs-config.ini` file may be generated for settings.

## Features

- Convert supported PS5 folders and raw `.exfat` images into `.ffpfsc` containers.
- Merge PS4 base game + optional update before FFPFSC conversion, with a FIFO job queue.
- Preserve the base game artwork; if `pic0.png` or `pic0.dds` is missing inside the staging directory, rename the corresponding `pic1` image without editing source games.
- Apply a custom PS4 game title to all existing `TITLE` and `TITLE_XX` text fields in the staged PARAM.SFO while preserving title/content IDs and version metadata.
- Edit existing PARAM.SFO localized title fields individually or together, with an original-file backup.
- Configure CPU, compression level, block size, TEMP paths, additional verification and optional cleanup.
- Open and modify supported exFAT/FFPFSC images.
- Switch between 15 interface languages, including Turkish and English.

## FFPFSC → PS4 PKG (experimental)

The new **FFPFSC → PS4 PKG** button converts a **supported PS4 game** image using this pipeline:

1. Select a PS4 `.ffpfsc` image (typically a CUSA title), output `.pkg` filename and TEMP folder.
2. MkPFS deep-unpacks the image into a temporary game directory.
3. The tool checks for `eboot.bin`, `sce_sys/param.sfo`, a CUSA title ID and standalone base-game `CATEGORY=gd`.
4. The bundled OrbisPkgTool creates a strict GP4 project and builds and validates a PS4 fake PKG.
5. After checking the PKG header and output size, the app copies the result to the chosen filename. The original FFPFSC image is not modified.

**Limitations and safety:**

- This is **not a PS5 FFPFSC → PS5 PKG converter**. PS5 game images contain different metadata and require a different builder. The converter stops with a clear message rather than producing an invalid PS4 PKG.
- Encrypted retail sources are not decrypted. The input must already contain an unpackable game tree that you have the right to use.
- The open-source PS4 PKG builder's output is **experimental** and has not been verified on a physical PlayStation console by this project. Successful packaging does not guarantee installation, launching or save compatibility.
- Package output will **never overwrite** an existing `.pkg`. Temporary working files are removed after success and retained after failure to aid troubleshooting.
- Sufficient temporary and output free space is required; large games may need considerably more space than the compressed input file.
- Some FFPFSC containers are incompatible with PS4 GP4 packaging even when they unpack correctly.

## Requirements and troubleshooting

- Windows 10/11 x64. Use an NTFS temporary folder, preferably on SSD/NVMe.
- For PS4 packaging, the image must contain a **PS4 CUSA game** and a valid `sce_sys/param.sfo`; PS5 PPSA-only images are rejected.
- If GP4 generation or PKG validation fails, inspect the dialog logs and the retained TEMP staging directory. Do not rename an `.ffpfsc` file to `.pkg` manually.
- The downloadable EXE is unsigned, so Microsoft SmartScreen may display a warning. Compare the SHA-256 value shown in the v1.0 release description.
- Actual PS4/PS5 console compatibility must be tested separately from GitHub Actions integration and synthetic tests.

## Build from source

The GUI and converters are in `src/`; tests are in `tests/`. On Windows with Python 3.11 x64, use `scripts/build_windows.bat`. GitHub Actions compiles a single Windows executable and updates **the existing v1.0 release only**. It never creates a new release automatically.

The CI pipeline builds the pinned MIT-licensed OrbisPkgTool source (commit `5cd42a515dc29a453c7abcb93318493bdb5b5e1f`) for Windows x64, embeds its self-contained executable and MIT license notice, compiles the Python GUI with Nuitka, tests bundled tools, and publishes the one executable.

## Legal and third-party notices

Use this software only for homebrew, research, preservation and backups of content you lawfully own. No games, Sony firmware, retail decryption keys, or proprietary console libraries are distributed. PS4, PS5 and PlayStation are trademarks of Sony Interactive Entertainment. This project is independent and is not endorsed by Sony.

- **MkPFS 1.1.0** (PSBrew/MkPFS): GPL-3.0; FFPFSC/PFS image handling.
- **OrbisPkgTool** (pearlxcore/OrbisPkgTool): MIT; experimental PS4 GP4 and fake-PKG building; MIT license is embedded in the executable as `tools/OrbisPkgTool.LICENSE.txt`.
- **Python + Tkinter**: Python Software Foundation License.
- **Nuitka**: Apache-2.0.
- **psutil**: BSD-3-Clause.
- **cryptography**: Apache-2.0/BSD.

The repository itself is GPL-3.0-or-later. Consult upstream projects for full third-party license texts.
