# PS5 PFS Packager v2.16.0

## Added
- PS4 game + update folder merge dialog using user-selected TEMP location; source folders untouched.
- Preserve base-game icons and artwork rather than replacing them with patch assets.
- Safe in-app `param.sfo` editor for UTF-8 `TITLE`; verifies `TITLE_ID` and `CONTENT_ID` remain unchanged.
- CUSA/title validation and output folder selection for conversion to FFPFSC after merge.
- Optional bundling of original `completion.mp3` and `error.mp3` in Windows EXE builds when they exist under `assets/`.
- Tests for update overlay, original artwork retention, and SFO title modification.

## Important limitations
- Merge operates on already-extracted folders and targets FFPFSC; it does **not** produce a standalone PS4 PKG.
- Copy-overlay alone cannot guarantee every game update boots; test with your own legally owned content.
- The original MP3 binaries were recovered from the user ZIP separately, but not uploaded as GitHub binary assets in this commit. EXE builds without those files use existing fallback notifications.
- Windows build and real-console compatibility remain unverified.
