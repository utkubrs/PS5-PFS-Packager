# PS5 PFS Packager v2.28.0

## PS4 game + update dialog
- Modern dark dialog with clear sections for input sources and output settings.
- Center dialog over the main app, clamp to the visible desktop, and retain all existing editable TITLE/CUSA fields.
- Keep existing one-click extraction, move-based merge, automatic FFPFSC packaging and console logs.

## Safe post-success cleanup
- Clean up only uniquely named temporary merge/extraction paths created by the **current** PS4 one-click operation.
- Before cleanup, MkPFS must exit successfully and produce an existing non-empty FFPFSC output.
- On failures/cancellation, leave all staging data intact for recovery.
- Never delete user-chosen game folders or unrelated TEMP data.

## Custom audio
- Supported MP3 sidecar filenames: `completion.mp3` and `error.mp3` next to the Windows EXE or in the adjacent `assets` directory.
- The build embeds those files if both are present in source `assets` at build time. The original user-provided audio can also be included in a portable distribution ZIP as sidecar files.

## Verification
- Python compile checks and regression tests for cleanup safety.
- Windows MkPFS and isolated PKG extractor smoke tests preserved from v2.27.
- Full PS4 game/update compatibility must still be checked using your legally obtained files and console.
