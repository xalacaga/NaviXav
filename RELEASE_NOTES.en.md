# NaviXav 1.4.12

Released on 2026-08-08.

## Fixed

- Automatic updates now wait for the old NaviXav process to close completely, reinstall into the directory actually in use and keep an installation log, preventing the previous version from restarting and offering the same update again.
- Release preparation now handles an empty Added or Fixed category without shifting the following PowerShell arguments or interrupting publication.

## Changed

- Correction bug.
- Bug de versioning.

The installer is verified against its SHA-256 checksum before any automatic update.
