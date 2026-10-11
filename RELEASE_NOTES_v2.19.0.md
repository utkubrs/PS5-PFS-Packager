# PS5 PFS Packager v2.19.0

- Fixed packaging of Windows PS4 PKG extractor: download v0.0.1 and verify SHA-256 before bundling tools/pkgextract.exe.
- PS4 update folders may omit eboot.bin; their sce_sys/param.sfo is still required.
- Updated program and Windows EXE versions to 2.19.0.
- Original custom MP3s are available separately and must be placed alongside the EXE; they are not yet embedded in GitHub release builds.
- PS4 retail/encrypted PKGs are not guaranteed to be supported.

Release is published only if Windows CI tests, compilation and packaging all succeed.
