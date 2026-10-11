# PS5 PFS Packager v2.14.0

## New
- Game folder metadata: title, title ID and local PNG icon preview
- Preflight checks for selected TEMP and output locations and disk free space
- Guard against writing output inside a source game folder
- Additional PS5 safety check against compressed raw PFS output
- Advisory block size in source preview; MkPFS auto remains selected unless changed manually
- Embed a generated multi-resolution Windows program icon during executable build

## Retained
- MkPFS 1.1.0, PS4/PS5 selector, profiles, batch conversion, exFAT/FFPFSC editing, verification and logs

## Test status
- Changes committed; GitHub Actions compiles and packages the executable on Windows. Real-console runtime compatibility and download availability require separate confirmation.
