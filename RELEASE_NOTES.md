# NaviXav 1.5.0

Released on 2026-08-28.

## Added

- Clicking an aircraft photo now opens a large preview inside NaviXav; it closes with its button, an outside click or the Escape key.
- The Aircraft card and inventory now show a real freely licensed photo beside the name for every supported aircraft family; additional aircraft installed in Community automatically use their local thumbnail when available.
- When a ChartFox chart cannot be embedded, NaviXav now offers the official national catalogue in the same card whenever the airport is covered.
- Flight tracking now estimates the Top of Climb from the cruise level, vertical speed and ground speed; the calculated TOC and TOD points appear on the map as distinct fixes.
- ChartFox can now be linked from Settings with a VATSIM account; its on-demand charts are offered as an optional source for the departure and arrival airports.
- The Charts menu now states that a ChartFox/VATSIM account is required to access ChartFox AIRAC charts and provides a direct link to Settings.

## Fixed

- Aircraft photos are no longer hidden behind the ICAO type tile in the Aircraft card and inventory.
- Opening an airport PDF in Charts no longer pushes the other airport below the document: Departure and Arrival stay side by side on wide screens, and the unopened card stays first in compact windows.
- The ChartFox “simulation only” notice in Settings now follows the interface language.
- ChartFox charts whose source forbids embedding no longer show a blank area: NaviXav explains the restriction and offers to open them directly on ChartFox.
- The calculated TOC and TOD fixes now use their own magenta and red colours, distinct from every route waypoint.
- The CartoDB Positron and Dark Matter base maps have been removed: their free service now watermarks every tile with "API key required". The choice is between OpenStreetMap Standard and OpenTopoMap, and a setting that has become invalid falls back to OpenStreetMap automatically.
- The weather briefing no longer appears partly in French when the interface is set to another language: the operational notes and the METAR phenomena now follow the selected language.
- Thunderstorms with no observed precipitation are now reported: the TS, VCTS and VCSH groups were ignored by the METAR decoding. The "PO" in "TEMPO" is no longer read as dust whirls either.
- SIDs finally appear on the map: their path, fixes and published constraints were missing whenever one procedure served two runway ends, which is the case at almost every major airport. The departure was reduced to a straight line to the first en route fix. STARs also regain their final portion, specific to the landing runway. The navigation database is refreshed from the simulator automatically at the next start.

## Changed

- Reformuler l'annonce ChartFox de la 1.5.0.
- Ajout fonctionnalite et correction bugs.

The installer is verified against its SHA-256 checksum before any automatic update.
