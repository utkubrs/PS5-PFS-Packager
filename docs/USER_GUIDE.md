# Detailed user guide

## Main fields

- **Source path:** game folder, exFAT file or parent folder for batch mode
- **Output folder:** destination for generated FFPFSC images
- **File name:** single-mode output filename
- **Temp folder:** temporary extraction and staging location
- **Profile:** coordinated CPU, compression and block settings
- **Block:** PFSC block-size selection
- **CPU:** worker/core limit
- **Compression:** zlib level from 0 to 9

## Profiles

### Fast

Prioritizes throughput and uses a lower compression level.

### Balanced

Recommended general-purpose profile.

### Maximum

Prioritizes compression. `auto-fit` can require substantially more temporary disk space.

### Low RAM

Uses fewer CPU workers and conservative settings.

## Checkboxes

- **Extra verification:** compares the final output with the source
- **Add fakelib files:** copies user-provided optional libraries
- **Delete game folder:** removes the source only after a successful conversion
- **Shut down PC when finished:** shuts Windows down after the queue completes

Memory-error retry is always enabled. If MkPFS reports an allocation failure, the application retries once with safer CPU and compression settings.

## Direct exFAT editing

The native adapter temporarily presents the raw exFAT image to Windows as a fixed VHD. The application creates a small recovery sidecar before changing the temporary VHD metadata. On normal disconnect, the raw layout is restored while filesystem changes remain.

Always keep a backup.

## FFPFSC editing

FFPFSC cannot be edited in place as a normal Windows filesystem. The application:

1. extracts the wrapped exFAT to the selected temp folder,
2. mounts the temporary exFAT as `U:`,
3. lets you edit files,
4. safely disconnects the volume,
5. rebuilds a temporary FFPFSC,
6. optionally verifies it,
7. atomically replaces the original FFPFSC.

## Logs

The terminal panel shows the exact MkPFS command, progress, throughput, gain and errors. HTML logs are saved by the application for later troubleshooting.

Remove private paths before posting logs publicly.
