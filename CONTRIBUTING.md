# Contributing

Contributions are welcome.

## Before opening a pull request

1. Create or reference an issue.
2. Keep changes focused.
3. Preserve all 15 language dictionaries.
4. Run Python syntax checks.
5. Do not add copyrighted games, firmware, keys or proprietary libraries.
6. Do not commit real user paths, tokens or personal information.
7. Test writable-image changes only with backups.

## Development setup

```bat
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
scripts\run_source.bat
```

## Commit style

Examples:

```text
fix: restore start button after FFPFSC save
feat: add block-size profile selector
docs: expand Turkish installation guide
```

## Translation changes

When adding a new interface string:

- add the English value,
- add the Turkish value,
- preserve fallback behavior,
- check that long translations fit the interface.

## Pull requests

Describe:

- what changed,
- why it changed,
- how it was tested,
- Windows version,
- affected source type,
- and screenshots when the UI changes.
