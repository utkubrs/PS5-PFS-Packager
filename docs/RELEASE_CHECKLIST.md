# Release checklist

## Code

- [ ] Update `APP_VERSION`
- [ ] Update `VERSION`
- [ ] Update `pyproject.toml`
- [ ] Update build-script version metadata
- [ ] Run `py_compile`
- [ ] Test game-folder conversion
- [ ] Test exFAT conversion
- [ ] Test direct exFAT mount/edit/unmount
- [ ] Test FFPFSC extract/edit/repack
- [ ] Test batch mode
- [ ] Test Turkish and English UI

## Safety

- [ ] Confirm no proprietary `*.sprx` files are present
- [ ] Confirm no game files, keys or firmware are present
- [ ] Confirm no personal paths, usernames or tokens are present
- [ ] Test with backup images
- [ ] Scan the final ZIP
- [ ] Generate SHA-256 checksums

## GitHub

- [ ] Commit and push source
- [ ] Create tag such as `v2.13.0`
- [ ] Create GitHub Release
- [ ] Upload Windows ZIP
- [ ] Upload `SHA256SUMS.txt`
- [ ] Paste `RELEASE_NOTES_v2.13.0.md`
- [ ] Upload `assets/social-preview.png` in repository settings
- [ ] Confirm README links
- [ ] Confirm topics and description
