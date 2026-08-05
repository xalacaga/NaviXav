# Highlights for the next release

Update this file for **every code change**, not only immediately before a
release. Add one bullet per change, in English and from the user's perspective.
This file is used instead of commit subjects in the release notes and is then
reset by `scripts\prepare_release.ps1`.

<!-- Example, remove before use:
- Flight tracking displays the estimated time remaining before arrival.
-->

## Fixes

- Application shutdown now uses FastAPI's supported lifespan lifecycle without
  deprecation warnings.
- The bundled LCPH-EHAM demonstration no longer warns about its expected
  offline navigation-cache fallback.

<!-- Example, remove before use:
- The basemap no longer shows seams between map tiles.
-->
