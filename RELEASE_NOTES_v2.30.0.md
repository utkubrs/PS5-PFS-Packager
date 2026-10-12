# v2.30.0 — PS4 FFPFSC mount compatibility

## Confirmed root cause
The user's console showed `0x00000016 (Invalid argument)` mounting `CUSA12381.ffpfsc` in ShadowMount+ 1.7 Beta 3. Comparing the **working** PS4 PKG Tool Turkish project's upstream FFPFSC writer with this packager revealed:

- Working Orbis FFPFSC exporter: PS4 files are wrapped in an exFAT game image; **outer unsigned PS5 PFS profile version 2**, 64 KiB block by default.
- Previous PS5 PFS Packager: PS4 platform dropdown also passed `--version PS4` to MkPFS, writing **outer PFS version 1**. This is wrong for PS5's ShadowMount+ FFPFSC mount.
- Working converter also repairs the SHA-1 footer of an otherwise valid `sce_sys/npbind.dat` in its *temporary copy* and emits `sce_sys/param.json` with game identity.

## Changes
- For both game-folder to FFPFSC and existing exFAT to FFPFSC, always use `--version PS5` for the OUTER container; preserve PS4 game metadata, SFO and platform selection.
- Check completed PFS header for version 2, magic, unsigned/unencrypted mode and supported block size before declaring success or cleaning TEMP.
- Safely recalculate the footer only if the `npbind.dat` structure matches the documented layout; leave missing/unknown files untouched.
- Preserve one-pass exFAT wrapping, CUSA-named inner image, generated ShadowMount+ param.json, user-selectable snd0.at9 removal, centered dialog and TEMP cleanup.
- Add regression unit tests and actual Windows EXE FFPFSC smoke test that asserts PS5 PFS v2 outer header, single CUSA-named inner exFAT and game-root param.json.

## Validation
Windows CI can confirm the file's format, not a particular console/payload compatibility. Test on PS5 using the same USB and ShadowMount+ payload after the new image is rebuilt. Never re-use the previous invalid v1 output. Keep original PKG files.
