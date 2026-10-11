# v2.18.0

- Removed redundant main-window PS4 TITLE input; title remains editable in game+update merge dialog.
- Infer base title from source filename, and then original extracted param.sfo when not customized.
- Translate the game-preview prompt for all 15 available interface languages.
- Auto-discover pkgextract.exe beside EXE, in tools/ or on PATH, or through PS4_PKG_EXTRACTOR.
- Allow original completion.mp3/error.mp3 next to the executable or assets/ to be played even when not embedded.

## Still required
- The two original sound files have not been added as binary GitHub assets; use the separately supplied ZIP and copy them next to the EXE.
- The PKG extractor is a separately supplied external utility, not bundled by this repository.
- GitHub workflow is manual; source changes do not prove the EXE was successfully built or published.
