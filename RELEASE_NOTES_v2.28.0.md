# PS5 PFS Packager v2.28.0 — PS4 ShadowMount+ metadata and optional sound removal

## PS4 game + update
- The PS4 merge dialog is dark-styled and opens centered on the screen.
- Added an unchecked-by-default **snd0.at9 dosyasını sil** checkbox, persisted as `ps4_remove_snd0_at9=1|0` under the `[settings]` section of `ps5-pfs-config.ini`.
- The checkbox removes only `sce_sys/snd0.at9` from the merged TEMP game folder. Source PKGs and user-selected extracted folders are never edited.
- Generated `sce_sys/param.json` from the merged PS4 `param.sfo`, containing CUSA `titleId`, title, localized `en-US.titleName` and other existing SFO metadata. The PS4 SFO is retained unchanged by the compatibility projector.
- Fast in-place TEMP merge and automatic FFPFSC creation remain enabled.
- Successful packaging cleans program-created merge and extraction TEMP folders; errors preserve files for diagnosis.

## Why
A previously generated FFPFSC of Chim Party (`CUSA12381`) compressed and mounted, but ShadowMount+ 1.7-beta5fix1 displayed `missing/invalid param.json`. This version addresses that required ShadowMount+ metadata stage rather than changing the compressor or inventing a PS5 TITLE_ID.

## Limits
Passing host-side SFO and FFPFSC checks does not prove game launch, trophies or update compatibility on a real PS5. Console verification is still required. Do not confuse the app's Windows config INI with `/data/shadowmount/config.ini`.

## MP3 files
The build system includes original `completion.mp3` and `error.mp3` only when provided at `assets/` in the GitHub build. The user's MP3s have not yet been committed as binary GitHub assets; copying them beside the standalone EXE remains the supported fallback until the release includes them.
