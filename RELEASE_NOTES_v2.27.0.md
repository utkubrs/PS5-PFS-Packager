# PS5 PFS Packager v2.27.0 – PS4 PKG extractor portability fix

## Fixed
- Nuitka onefile previously searched the unpacked runtime (e.g. AppData\\Local\\Temp\\onefile_...) for `pkgextract.exe` instead of the installed application's `tools` folder. The code now resolves the actual application location, then the built-in payload, then optional PATH / explicit overrides.
- A verified, pinned `pkgextract.exe` is bundled inside the new onefile EXE, so users no longer have to separately carry the `tools` folder for PS4 PKG extraction.
- If the extractor truly cannot be found, the merge dialog displays the warning before it closes. The debug output provides checked paths.
- A pre-existing partial extraction folder does not abort a new conversion: the previous data is preserved and a unique new extraction folder is chosen.

## Windows release gates
1. Compile and run PS4 regression unit tests.
2. Run the extracted onefile executable in an isolated directory **without any external tools folder**, checking `--check-pkg-extractor`.
3. Run MkPFS `--internal-mkpfs --help` and create a real synthetic FFPFSC from a folder.
4. Build the final Windows ZIP and run its EXE after extracting it to a directory containing spaces; verify `tools/pkgextract.exe` and diagnostics.
5. Only then publish a GitHub Release.

## Preserve user data
Previously merged source folders such as `F:\\temp\\ps4_merge_76aafcf376` can be selected directly for FFPFSC conversion when still intact. A failed output FFPFSC is not considered valid; retry conversion.
