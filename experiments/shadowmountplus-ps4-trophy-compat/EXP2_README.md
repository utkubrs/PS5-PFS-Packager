# EXP2 — PS4 Trophy Registration Read-only Diagnostics

Source: drakmor/ShadowMountPlus `1.7-beta5fix1` at `98c524890176c7b474fcb03387bec88c4a559861`.

## Outcome of EXP1

User's PS5 (FW 10.01), Chim Party TR (CUSA12381) as FFPFSC:
`[PS4-TROPHY-EXPERIMENT] title=CUSA12381 copied=4 preserved=0 absent=0` and `[REG] Installed NEW!`. Trophy registration nevertheless failed. The *same game installed as PKG* registers trophies successfully. Therefore staging four files alone is insufficient.

## What EXP2 does and DOES NOT do

EXP2 **does not apply EXP1's metadata staging patch**. It adds an additional PS4-only observer to original ShadowMountPlus:
- logs at `after-register` and `game-start` for `CUSA#####` titles only;
- queries `tbl_appinfo` and `tbl_contentinfo` in PS5 `app.db` with a **separate SQLITE_OPEN_READONLY** connection, logging a small allowlist of fields such as `contentLocation`, `category`, `appType`, `status`;
- checks presence/types of a limited number of PS4 metadata paths and sandbox entries using `lstat`, not contents;
- never changes app.db, deletes files, overrides game metadata, patches the trophy service, or registers a trophy.

**Important:** the original ShadowMountPlus runtime **still has its original install/mount side effects** when a user actually mounts a game. Read-only describes **only the new EXP2 diagnostic code**, not all of ShadowMountPlus. The diagnostic database reader may use SQLite's ordinary read-only locking mechanisms.

The `install=0` in older FW 10.01's ShellCore log is expected: upstream activates its *third* install hook only on firmware >= 12.00, not evidence of trophy failure.

## Controlled comparison without deleting game registrations

1. Back up the working ShadowMountPlus ELF. Do not merge this diagnostic experiment into the packager's main branch.
2. Stop the existing ShadowMountPlus process and run the EXP2 ELF using your normal payload loader. Keep your tested kstuff unchanged.
3. Launch one **already-installed, working PS4 PKG** game (with a distinct CUSA title ID). Close it.
4. Launch **Chim Party FFPFSC CUSA12381** that reproduces the error. Close it.
5. Fetch `/data/shadowmount/debug.log` (and `debug.log.1` if rotated). Provide the exact **CUSA IDs of both games**.
6. Filter for `[PS4-TROPHY-EXP2]`. Compare `tbl_contentinfo.contentLocation`, `appType`, `category`, metadata presence, sandbox; do **not** infer that a field alone causes the error.
7. If the baseline installed PKG cannot be launched while the FFPFSC exists, **do not remove additional games or trophy data**. A different installed PS4 PKG baseline suffices initially.

Do not manually modify system databases, fake license material, or force-install ShellCore hooks. No direct LNC/NPDRM fix is claimed. These snapshots narrow the next source change and are not guaranteed to explain the trophy error without further system-level tracing.

## Development

Only apply the stand-alone `patches/0002-ps4-trophy-readonly-registration-diagnostics.patch` to upstream `1.7-beta5fix1`. Copy `src/sm_ps4_trophy_diag.c` and `include/sm_ps4_trophy_diag.h` to the matching upstream source paths, then compile with the original PS5 SDK and Makefile. GitHub Actions workflow `.github/workflows/ps4-trophy-exp2-diagnostics.yml` performs pinned-source patch checks, host SQLite tests and the full PS5 cross-build.

This is a diagnostics-only EXP2; do not use it as proof that trophy registration is fixed.
