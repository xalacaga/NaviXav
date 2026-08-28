# NaviXav 1.5.3

Released on 2026-08-28.

## Fixed

- Airports missing from the cache are imported from the simulator again: runway lighting was read with the wrong field width, which lost the whole airport and left its ground chart unavailable.
- An unavailable ground chart now says why — airport missing from the database — instead of reporting a network error, and unknown lighting intensity is no longer shown as off.

## Changed

- Bug correction.

The installer is verified against its SHA-256 checksum before any automatic update.
