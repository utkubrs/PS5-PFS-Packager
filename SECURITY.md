# Security policy

## Supported version

The latest published release is supported.

## Reporting a vulnerability

Use GitHub's private security-advisory feature when available. Do not publish exploit details or sensitive disk-image data in a public issue.

Include:

- application version,
- Windows version,
- affected workflow,
- reproduction steps,
- impact,
- and a minimal non-copyrighted test case.

## Operational safety

The application:

- runs with administrator rights,
- mounts writable virtual disks,
- can overwrite the original FFPFSC,
- and can directly modify raw exFAT images.

Always keep backups. Test new releases with disposable images before using important archives.
