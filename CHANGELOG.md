# Changelog

## 2.32.0

- Use update `sce_sys/param.sfo` and its `APP_VER` during PS4 base+update merging.
- Preserve base-game `CATEGORY` for a mountable standalone PS4 image and retain base artwork.
- Keep custom TITLE edits scoped to the staged SFO and report APP_VER in logs.
- Preserve the existing base-only workflow, FIFO queue, and safe TEMP cleanup.
- Add tests for updated APP_VER, title, CATEGORY and fast staged moves.


## 2.31.0

- Added live PS4 FIFO job queue with pause/resume and removal of waiting entries.
- PS4 update is optional: a base-game-only source can be packaged through the same pipeline.
- Per-job output, TEMP, options and title are captured when enqueued.
- Added output collision checks and regression tests for no-update games.

## 2.13.0

- Added ordered tuning row: Profile, Block, CPU, Compression
- Added separator and left-aligned options row
- Made memory-error retry always active
- Added compression profiles and selectable block size
- Added pre-flight storage and filesystem checks
- Added recursive valid-game discovery
- Added writable exFAT and FFPFSC editing through Windows native VHD
- Added safe original-FFPFSC replacement
- Added automatic mount-session cleanup
- Added 15-language interface
- Added single and multi-game workflows
- Added progress, ETA, performance statistics and HTML logs
- Updated for MkPFS 1.1.0 exFAT-wrapped one-pass workflow
