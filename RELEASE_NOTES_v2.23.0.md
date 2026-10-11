# v2.23.0

- Close the PS4 game+update dialog immediately after starting the merge.
- Track exact copy bytes, GiB totals, number of files and percent in the main progress bar and status label.
- Periodically write progress to the operation log.
- Automatically select the merged directory on completion and prevent concurrent conversion during merging.
- Add automated test covering final copied-byte/file counts.

The display measures completed copy work, not estimated game installation progress. The Windows executable and console runtime have not been verified until the CI build finishes.
