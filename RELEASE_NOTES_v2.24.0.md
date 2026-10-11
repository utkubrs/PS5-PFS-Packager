# PS5 PFS Packager v2.24.0

- Added output directory, FFPFSC filename and TEMP directory controls directly to the PS4 game+update merge dialog.
- Values are initialized from and synchronized with the main form; the chosen filename is preserved when the merged directory becomes the source.
- Localized PS4 merge controls/statuses, main PS4 toolbar buttons, and PARAM.SFO TITLE editor in all 15 supported UI languages.
- Preserve v2.23 copy progress reporting in the main window.

MkPFS remains 1.1.0. Packaging remains a separate Convert action after the merge completes. Windows CI tests and executable publication still need to pass before download is confirmed.
