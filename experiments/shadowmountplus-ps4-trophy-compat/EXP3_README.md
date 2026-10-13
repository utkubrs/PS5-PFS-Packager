# EXP3 — PS4 user-appmeta trophy compatibility experiment

**Scope:** PS5 firmware 10.01, ShadowMountPlus `1.7-beta5fix1` (`98c524890176c7b474fcb03387bec88c4a559861`). Includes EXP2A and EXP2B logging already demonstrated to load on the target console.

## Why this experiment

Observed for AER installed as native PS4 PKG (CUSA08005) versus Adam's Venture Origins as FFPFSC (CUSA03772):
- Both `platform=1` and `appType=1`.
- Native PKG: `contentLocation=0`, `metaDataPath=/user/appmeta/CUSA08005`, trophies work.
- FFPFSC: `contentLocation=2`, `metaDataPath=/user/app/CUSA03772/sce_sys`, `Trophy registration failed`.
- EXP1 copied four PS4 files into `/system_data/priv/appmeta/`, but did **not** fix trophy registration.
- Upstream ShadowMountPlus filters files copied to `/user/appmeta` to param JSON/SFO and artwork/audio; it does not mirror root `npbind.dat`, `nptitle.dat`, or `trophy/trophy00.trp`.

**Hypothesis only:** add-only mirroring of the missing PS4 metadata files into `/user/appmeta/CUSAxxxxx` may help PS4 trophy initialization. It does **not** change the FFPFSC app's `metaDataPath`, `contentLocation`, sandbox, native LNC/NPDRM context, or trophy service registration path. It might have no effect. This is not a confirmed fix.

## Safety

- By default EXP3 is **OFF**. It adds only logs; EXP2B fields remain read-only.
- To enable for **Adam's Venture only**, create a **regular empty file** exactly:
  `/data/shadowmount/exp3_CUSA03772.enable`
- The marker is checked at each ShadowMountPlus install/remount. No marker = no new metadata writes.
- Only target CUSA IDs with matching marker files are enabled; `PPSA` titles are not changed.
- When enabled, copy **only missing** files from mounted image `sce_sys` to `/user/appmeta/CUSA03772`: `param.sfo`, `npbind.dat`, `nptitle.dat`, `trophy/trophy00.trp`.
- All copies use `O_NOFOLLOW` and `O_CREAT|O_EXCL`; pre-existing files are preserved. The copy refuses paths that are not ordinary files/directories or copies exceeding 64 MiB. The source FFPFSC image is not modified. No `app.db` write.
- Log `[PS4-TROPHY-EXP3]` per title and each file: result `1`=newly copied; `2`=preserved; `0`=source missing; `-1`=error.

## Console test steps

1. **Power off the PS5 completely, then boot** before this test (previous trace had unreleased `/dev/lvd2` and busy nullfs mounts). Keep backup of your stable `© UtkuBrs - Fix 1` payload and the working kstuff 1.13 Test4.
2. Via FTP, back up `/user/appmeta/CUSA03772` (if it exists) before enabling. Avoid deleting existing PS4 PKG installs or trophies.
3. Create `/data/shadowmount/exp3_CUSA03772.enable` as a **regular empty file**.
4. Run this **experimental EXP3 ELF** using the same payload loader where EXP2A/EXP2B worked. Do not automatically inject another ShadowMountPlus instance simultaneously.
5. Start Adam's Venture (FFPFSC), then observe whether "Trophy registration failed" still appears. You need not reinstall the game. If you do not see `[PS4-TROPHY-EXP3] title=CUSA03772 enabled=1`, the mirror did **not** run; restart ShadowMountPlus or remount the game, rather than concluding failure.
6. Capture `/data/shadowmount/debug.log` including `[PS4-TROPHY-EXP3]`, `[PS4-TROPHY-EXP2B]` and relevant launch lines. Report both the **console outcome** and log.

## Disable / restore

Deleting only the `exp3_CUSA03772.enable` marker stops *future* mirroring; it **does not undo files already added**. Never delete the whole `/user/appmeta/CUSA03772` folder or `app.db` casually. Use the per-file EXP3 log with `result=1`, plus the backup from before testing, to distinguish files added by EXP3 from pre-existing user data. If needed, restore from backup with the game not running and the mounts properly unmounted.

**No production merge / release.** All changes are isolated on `experimental/ps4-trophy-exp3-user-appmeta-mirror`. If trophy registration still fails, the next step is native PS4 LNC/NPDRM initialization tracing; do not attempt arbitrary numeric edits to `contentLocation` or force unsupported ShellCore hooks.
