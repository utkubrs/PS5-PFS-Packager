# Optional fakelib files

This directory is intentionally empty.

The application can optionally copy the following user-supplied files:

- `libSceAmpr.sprx`
- `libScePlayGo.sprx`

These files are **not distributed by this repository**. Only add files that you are legally permitted to use and distribute.


## MkPFS 1.1.0 update

This release updates the bundled MkPFS dependency to **1.1.0**.

Notable upstream changes used by this GUI:

- compression-related bug fixes,
- dependency updates,
- safer PS5 compression behavior,
- restored PS4 / PS5 selection in the upstream GUI.

The desktop GUI now exposes a **Platform** selector with `PS5` and `PS4`. `PS5` remains the default target.
