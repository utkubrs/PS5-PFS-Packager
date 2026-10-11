# PS5 PFS Packager v2.21.0

- Hide pkgextract Windows command prompt and report approximate extraction progress in application log.
- Automatically select PS4/PS5 based on source game folder metadata and CUSA/PPSA file identifiers (manual choice remains for unknown sources).
- Log original MP3 discovery and playback errors to diagnose sound-test failures.
- Retain MkPFS 1.1.0 and existing game+update merge.

Limitations: the custom original completion.mp3 and error.mp3 are not committed as binary GitHub assets. Place the supplied MP3s beside the executable. Windows build and release are not verified until GitHub Actions succeeds.
