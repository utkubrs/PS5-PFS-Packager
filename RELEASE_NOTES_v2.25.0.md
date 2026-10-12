# PS5 PFS Packager v2.25.0

## PS4 base game + update: one-click FFPFSC

- Select the base game and patch as either PKG or extracted folders.
- Auto-detect game title (PARAM.SFO for folders, readable filename for PKGs).
- Auto-detect CUSA from readable PS4 PKG metadata, or from the extracted base PARAM.SFO after extraction. The output filename is editable.
- Use **Birleştir ve FFPFSC Oluştur** to extract, merge and immediately start the existing FFPFSC packer; no second click or confirmation prompt is required.
- When the sources were extracted by the application into the selected TEMP directory, rename the base staging folder and move update files to avoid a redundant full-game copy.
- User-selected folders remain untouched. Base artwork and identity fields are preserved.
- Keep selected TEMP/output directories and the extraction/merge progress logs through the conversion phase.
- Updated workflow messages in all 15 supported languages.

## Verification

Python sources and tests compile on GitHub Actions, including CUSA detection, ID mismatch rejection, fast merge, base artwork preservation and the existing folder merge path. Real-world PKG extraction and an end-to-end PS5 compatibility check still require testing with your legally obtained backups and console.
