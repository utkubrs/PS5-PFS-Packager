# Troubleshooting

## U: drive does not appear

- Confirm that `U:` is not already assigned.
- Close any old File Explorer window using `U:`.
- Run the application as administrator.
- Keep the image on a local NTFS/ReFS drive.
- Avoid cloud-only, EFS-encrypted, sparse or NTFS-compressed backing files.

## U: cannot be disconnected

Close:

- files opened from `U:`,
- editors,
- command prompts currently located on `U:`,
- antivirus scans,
- and File Explorer windows displaying `U:`.

Then try **Save / Close** again.

## Windows Error 126 / "Error, load DLL." during MkPFS packaging

If PKG extraction and the PS4 merge succeeded but the log then says `Error, load DLL. ([Error 126] ...)`, the Windows Nuitka onefile runtime could not load its child process. This is not evidence of a broken game, SFO or FFPFSC input.

Use v2.26.0 or newer, which disables Nuitka onefile DLL mode and keeps runtime bootstrap temp files on a Windows local directory. Game extraction/merge and MkPFS's large files still use the user-selected TEMP. Keep the already merged `ps4_merge_...` directory and retry only the conversion; do not repeat package extraction unless the merge folder is missing. If Error 126 persists, Windows security software, missing system DLLs and file permissions may need diagnosis.

## Not enough temp space

Opening FFPFSC requires space for the wrapped raw exFAT image. The required size can be significantly larger than the compressed FFPFSC.

Choose a larger NTFS SSD/NVMe temp drive.

## Memory error

The application automatically retries once with low-memory settings. If it still fails:

- select the **Low RAM** profile,
- use CPU 1 or 2,
- close browsers and other memory-heavy applications,
- increase the Windows page file,
- avoid `auto-fit` when temp space is limited.

## FAT32 error

FAT32 cannot store files larger than 4 GiB. Use NTFS or exFAT for the output drive.

NTFS is still recommended for the temp folder.

## Access denied

- Check folder permissions.
- Close applications locking the image.
- Avoid protected Windows folders.
- Do not use read-only media.
- Temporarily test with a short path such as `F:\PS5-Temp`.

## Antivirus warning

Nuitka one-file executables can trigger heuristic alerts because they extract bundled modules to a temporary directory.

Verify the release checksum and download only from the official repository.

## Reporting a bug

Include:

- application version,
- Windows version,
- source type,
- selected profile/CPU/compression/block,
- filesystem types,
- last relevant log lines,
- exact reproduction steps.

Do not upload copyrighted game content.
