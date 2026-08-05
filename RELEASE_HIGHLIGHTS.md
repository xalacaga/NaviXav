# Highlights for the next release

Update this file for **every code change**, not only immediately before a
release. Add one bullet per change, in English and from the user's perspective.
This file is used instead of commit subjects in the release notes and is then
reset by `scripts\prepare_release.ps1`.

<!-- Example, remove before use:
- Flight tracking displays the estimated time remaining before arrival.
-->

## Fixes

- The Windows installer and the application are no longer flagged as a threat
  by antivirus heuristics: the executable is shipped uncompressed and now
  carries full publisher information.
- The installer and the application now consistently show Xalacaga as the
  publisher.

<!-- Example, remove before use:
- The basemap no longer shows seams between map tiles.
-->
