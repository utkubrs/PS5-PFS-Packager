# PS4 trophy metadata staging experiment (ShadowMountPlus 1.7-beta5fix1)

**EXPERIMENTAL; not verified on PS5; no trophy registration guarantee.**

This is a PS4-only source patch against upstream tag `1.7-beta5fix1`, commit `98c524890176c7b474fcb03387bec88c4a559861`. It DOES NOT implement Sony's PS4 package-backed LNC/NPDRM application mount or magically make trophy registration work.

It only attempts to stage PS4 files `sce_sys/param.sfo`, `npbind.dat`, `nptitle.dat`, `trophy/trophy00.trp` into the existing system appmeta directory when the title is `CUSA#####` and param.sfo is present. PS5/PPSA titles use their unchanged code path. Previous destination metadata is never overwritten and source image contents are never modified. Symlinks are rejected for source/destination files, and existing files are preserved.

## Applying to an isolated upstream checkout

```bash
git clone https://github.com/drakmor/ShadowMountPlus.git
cd ShadowMountPlus
git checkout 1.7-beta5fix1
git apply --check /path/to/patches/0001-ps4-trophy-metadata-staging.patch
git apply /path/to/patches/0001-ps4-trophy-metadata-staging.patch
cp /path/to/include/sm_ps4_trophy_compat.h include/
cp /path/to/src/sm_ps4_trophy_compat.c src/
```

No PS5 payload is produced by the host tests. A real firmware-specific build requires upstream's PS5 payload SDK, plus console testing and a reversible installation plan. The original `drakmor/ShadowMountPlus` repository and the `main` branch of `utkubrs/PS5-PFS-Packager` remain unchanged.

## Host tests

```bash
cc -Wall -Wextra -Werror -std=gnu11 -Iinclude src/sm_ps4_trophy_compat.c tests/test_sm_ps4_trophy_compat.c -o /tmp/test_smps4
/tmp/test_smps4
```

## Follow-up research

A trophy error like `0x80551618` may continue despite correct metadata copying, because ShadowMountPlus still uses `sceAppInstUtilAppInstallTitleDir`/nullfs registration rather than complete PS4 PKG-backed application mount. Compare `/data/shadowmount/debug.log` against a working installed-PKG case. Do not remove trophies or modify PS5 system databases to work around the error.

Research: https://github.com/drakmor/ShadowMountPlus/issues/97 and https://github.com/SadykovIV/PS4pkg_to_ffpfsc/issues/3
