# PS5 PFS Packager v2.26.0 — Windows Error 126 fix

## Problem
On some systems v2.25 extracted/merged the PS4 PKGs successfully but the internal MkPFS subprocess terminated immediately with:

```
Error, load DLL. ([Error 126] (null))
```

This is emitted by the Nuitka onefile bootstrap before MkPFS starts; it is not a PARAM.SFO, game merge, or PFS error.

## Changes
- Build Nuitka onefile using `--onefile-no-dll` to avoid the Windows onefile DLL loader path.
- Keep the native EXE bootstrap in a Windows-local TEMP directory. Large extraction, merge and MkPFS packaging files still use the user's selected TEMP folder through `--temp-folder`.
- Verify a real synthetic `--internal-mkpfs pack folder` run in Windows CI, including output-file creation, in addition to the existing `--help` smoke test.
- No need to extract or merge PKGs again if the successful `ps4_merge_...` directory is still intact.

## Testing
Windows CI verifies the process, but the specific user's Windows + exFAT setup still needs a local test. The change does not repair partially written .ffpfsc files; convert again to a fresh output.
