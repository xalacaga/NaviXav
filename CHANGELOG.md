# Changelog

## [1.4.8] - 2026-08-05

## Added

- On wide desktop windows, modules now sit in a compact floating rail at the upper left with a modern glass treatment and a clearer active marker. The concise **Flight plan** entry now behaves like every other module, with no collapse control, is selected by default, and clicking any entry scrolls directly to its content. The main area fills all remaining width and an opened official PDF expands across the chart grid. A visible global flight alert now pushes the rail below the enlarged header, preventing it from covering the first module. Compact windows keep the horizontal selector and mobile navigation is unchanged.
- The first plan opens faster when SimBrief provides a detailed navlog : validated en-route coordinates and published procedure links are reused before NaviXav asks MSFS Facilities for any missing positions. The existing route-corridor checks and local-cache fallback remain active.
- Flight tracking now keeps a timeline of the flight. A ribbon shows every phase flown, the longer ones taking up the more room, and the log underneath groups what happened under the phase it happened in : takeoff and landing runway with the actual wind, phase changes, gear, flaps, spoilers, parking brake, lights and autopilot modes. A change is recorded only once it has held, so a moving flap lever no longer floods the log.
- The timeline of a completed flight is kept with its summary in the local logbook and can be replayed from there. It is recorded as data rather than as sentences, so a flight logged in one language reads back in whichever language is selected later.

## Fixed

- Aircraft configuration and Flight events now react to flap, spoiler and parking-brake changes on aircraft that leave one standard MSFS value frozen. NaviXav cross-checks official handle, effective-position, surface-position and cockpit-indicator SimVars, and flaps no longer remain stuck on FULL after the lever moves. Fenix A319, A320 and A321 controls are read directly from their common cockpit variables, including with engines and hydraulics off.
- Named taxiways now remain visible on the ground chart even when MSFS reports them as generic `path` segments. At airports such as LCPH, the main A, B, K and other taxiways no longer disappear with the unnamed secondary links.
- On phones and tablets, the MSFS connection state is now shown as a compact coloured dot, so the `MSFS connected` label no longer overflows narrow screens. The translated label remains available to assistive technologies.
- The Constraints module now follows the selected language : vertical profile, altitude instructions and constraint tables are no longer French only.
- The Official charts module is translated as well, including the document picker, the overlay notices and the AIS catalogue sections.
- The MCDU tab now displays the official chart card, the chart minima form and the ATIS reminders in the selected language.
- Taxi labels coming from the simulator, such as gate names and hold-short instructions, are translated on the ground plan and in the taxi banner.
- Connection tooltips and error banners are no longer displayed in French when another language is selected.
- Flap detents are read correctly on Airbus aircraft that expose five handle positions : the handle on 2 was displayed as 1, and every detent above 1 was shifted down by one. The retracted detent now follows the Airbus marking and reads 0.
- Aircraft without a known flap profile now show the handle position and the measured flap angle instead of a percentage of travel, so any airframe stays readable. The last Boeing detent keeps its angle instead of turning into FULL.
- The displayed flight level now comes from the standard atmosphere, as the altimeter reads it. An aircraft levelled at FL330 was announced at FL342 in warm air, and the cruise phase was lost for the same reason.
- Phones and tablets can now change the display language from the toolbar. The settings stay reserved for the PC, but the language was unreachable once the welcome screen had been answered.

## Changed

- Amelioration interface et ajout timeline.
- Amelioration interface/ajout Timeline.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.7] - 2026-08-05

### Added

- Flight tracking now records a bounded, debounced event timeline with a
  proportional phase ribbon and grouped events for runways, observed wind,
  flight phases, gear, flaps, spoilers, parking brake, lights and autopilot
  modes.
- Completed-flight summaries retain that timeline in the local logbook. Events
  are stored as language-neutral data and replay in the currently selected
  interface language.

### Fixed

- Aircraft configuration and Flight events now follow flaps, spoilers and the
  parking brake even when a third-party aircraft freezes one standard SimVar.
  NaviXav cross-checks the official handle, effective-position,
  surface-position and cockpit-indicator values, and a previous 100% flap
  extension can no longer pin the display to `FULL` after the lever moves.
  A dedicated Fenix A319/A320/A321 adapter reads the flap, speedbrake and
  parking-brake cockpit variables directly, including with engines and
  hydraulic systems off.
- Named taxiways now remain visible on the ground chart when MSFS classifies
  them as generic `path` segments, as at LCPH. Only unnamed secondary links and
  stand access paths stay hidden behind the **Secondary** control.
- On remote mobile screens narrower than 760 px, the MSFS connection status is
  now shown as an accessible coloured dot instead of the overflowing
  `MSFS connected` label.
- Airbus aircraft exposing five physical flap-handle positions now display the
  correct `0`, `1`, `2`, `3`, `FULL` detents instead of shifting every position
  above `1` down by one.
- Aircraft without a known flap profile now display the handle position and
  measured flap angle instead of an ambiguous travel percentage; non-Airbus
  final detents retain their angle instead of becoming `FULL`.
- Flight level and cruise-phase detection now use pressure altitude in the
  standard atmosphere instead of true altitude, preventing warm-air errors
  such as displaying FL342 for an aircraft level at FL330.
- Constraints, official charts, chart minima, MCDU chart guidance, simulator
  taxi labels, connection tooltips and error banners now follow the selected
  interface language.
- The Windows installer and the application are no longer flagged as a threat by antivirus heuristics : the executable is shipped uncompressed and now carries full publisher information.
- The installer and the application now consistently show Xalacaga as the publisher.

### Changed

- Wide desktop windows now use a compact glass-effect module rail at the upper left
  with a clearer active state. Its concise **Flight plan** entry behaves like
  every other exclusive module and replaces the old collapsible Departure,
  Route and Arrival section. It is selected by default, and every choice scrolls directly to its content.
  The main area now fills all space beside the rail, and an opened official PDF
  expands across the complete chart grid. When a global flight alert adds a
  second header row, the rail automatically moves below it instead of
  overlapping the first module. Compact desktop windows retain the
  horizontal selector and mobile navigation keeps its accessible side drawer.
- First plan preparation now reuses validated coordinates from the detailed
  SimBrief navlog and published procedure links before querying MSFS Facilities.
  Missing positions still use the MSFS cache and SimConnect fallback, with the
  existing route-corridor safeguards.
- Phones and tablets can select their display language directly from the mobile
  toolbar while PC-only settings remain unavailable remotely.
- English is now the source language for the documentation; localized README
  files are synchronized from it after user-facing changes.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.6] - 2026-08-02

### Added

- A **Weather** tab replaces the **JSON** tab and brings together departure, cruise, arrival and alternate briefings.
- Each airport shows decoded essentials: wind, visibility, ceiling, temperature and dew point, QNH, significant phenomena and flight category (VFR, MVFR, IFR or LIFR), including the observation age.
- The TAF summary focuses on meaningful changes, while raw METAR and TAF reports remain available with one click.
- The cruise briefing includes OFP average wind, wind component, ISA deviation, outside air temperature and tropopause.
- The briefing flags stale observations, mist or fog risk, gusts, low temperatures and low IFR conditions.
- In live METAR mode, observations refresh on load and every five minutes without recalculating the route or changing procedures.
- A graphical summary shows conditions, wind direction, visibility and ceiling for each airport.
- The **Dispatch** tab compares the OFP forecast with live simulator values: loaded and remaining fuel, actual burn, take-off and landing weights, time and distance. Values refresh every two seconds.
- Projected arrival fuel warns when it falls below final reserve plus alternate fuel, and projected landing weight warns above maximum landing weight.
- Hourly fuel burn uses a five-minute rolling average and remains accurate when simulation rate is increased.
- Tracking survives closing the application during a flight: block fuel and take-off time recorded at departure are restored when NaviXav reopens.
- The **Dispatch** and **Aircraft** tabs now follow the selected language. Only standard aviation identifiers such as ZFW, MTOW, MLW, SELCAL and cost index remain unchanged.

### Fixed

- Removed the misleading “SimBrief planned runway X, but wind would favour Y” warning. In light, calm or variable wind, it incorrectly attributed a ranking driven by airport preference and ILS availability to the wind. The OFP runway remains selected, with moderate confidence when it differs from the planner ranking.

### Changed

- Added weather features and improved the mobile layout.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.5] - 2026-08-01

### Fixed

- Approach lines no longer jump to a same-named waypoint hundreds of miles away; the Orly final approach could previously lead to Corsica.
- Runway-related waypoint names such as `CF02`, `FI21L` and `DER07` are recognised at any airport and can no longer borrow a same-named position from a neighbouring airport.
- En-route waypoints with multiple database matches are selected near the route and rejected when they would create an excessive detour.
- On flight-plan import and whenever the route changes, the full path is validated. Out-of-area points are removed and reported in planner warnings regardless of the source of the bad position.
- Routes crossing the antimeridian are drawn continuously instead of crossing the map in the wrong direction.
- Flights returning to their departure airport keep their turning point; the planned distance is used instead of a direct route.
- Procedure fixes incorrectly stored as reporting points are removed from the navigation database at startup.

### Changed

- Fixed route rendering issues.
- Added a link to the official NaviXav website.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.4] - 2026-08-01

### Added

- A new **Taxi** tab provides a dedicated aerodrome chart on a dark aviation background with a metric grid and north indicator, separate from the road basemap and flight route.
- The taxi chart fills the available area and remains readable in compact windows. Secondary taxiways are hidden by default and can be shown on demand.
- At departure, NaviXav automatically identifies the stand near the aircraft and proposes a route to the selected runway. Selecting another stand immediately replaces the proposal.
- Only taxiways used by the route are labelled, keeping the path easy to read.
- The current taxi instruction is displayed prominently with the remaining path and distance.
- The Taxi tab, flight tracking, local history, flight phases, map states and SimBrief creation command now follow the selected language. Standard aviation identifiers and phraseology remain unchanged.
- Departure, Route and Arrival cards also translate their labels, wind components, planner explanations and warnings without altering SimBrief procedures, fixes or values.

### Fixed

- Ground taxiways, stands and labels no longer obscure map tiles, the flight route or the aircraft. Ground detail now belongs to the dedicated Taxi tab.
- Changing the selected stand cancels previous requests, preventing a delayed network or routing response from restoring the old route.
- SimConnect parking paths are no longer treated as taxiway segments and cannot create artificial diagonals across an airport, such as between T41 and N1 at LFBO.
- Rerouting after a deviation stays on the usable main network and no longer selects an isolated node or service road.

### Changed

- Added taxi guidance and improved translations.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.3] - 2026-07-31

### Added

- Airport data now retains taxiway names, segment types and runway holding points as the basis for stand-to-runway guidance.
- Previously stored airports are refreshed automatically the next time the simulator is available and remain accessible offline.
- NaviXav calculates taxi routes between a stand and a runway, follows taxiways, avoids closed segments and service roads, uses a runway only as a last resort and identifies the runway holding point.
- The map displays taxiways and stands with taxiway names.
- Selecting a stand draws the taxi route to the planned runway: green behind the aircraft, blue ahead, with holding bars and remaining distance.
- At departure, the holding point matches the runway threshold in use; on arrival, the exit nearest the selected stand is chosen automatically.
- During taxi, NaviXav displays the next instruction, such as “Turn left onto Q” or “Hold short of runway 05”, together with the remaining distance.
- Deviating from the route triggers a new calculation from the aircraft’s current position instead of sending it back to the starting point.

### Changed

- Added taxiway data and taxi tracking.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.2] - 2026-07-30

### Fixed

- The basemap no longer shows tile-grid seams: opacity now applies to the complete layer and tiles no longer overlap.

### Changed

- Improved map rendering.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.1] - 2026-07-30

### Changed

- Improved map rendering.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.0] - 2026-07-30

### Added

- Flight tracking displays a departure-to-arrival progress line with the aircraft’s real-time position, percentage completed and remaining distance.
- Current altitude follows the aircraft along that line, shown as a flight level above transition altitude and in feet below it, with vertical trend.
- Planned flight time, elapsed time and estimated remaining time appear below the path.
- Demo mode now replays a complete flight, from departure taxi to arrival parking through climb, cruise, descent and approach.
- The map banner shows indicated airspeed, altitude, vertical speed, outside air temperature and flight phase.

### Fixed

- `RELEASE_HIGHLIGHTS.md` is now included in version commits.

### Changed

- Updated the feature set.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.3.0] - 2026-07-30

### Added

- Application updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.2.0] - 2026-07-29

### Added

- Application updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.1.0] - 2026-07-29

### Added

- Application updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.0.0] - 2026-07-29

### Fixed

- Restored the in-memory flight trace and Airbus detents.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.13.0] - 2026-07-29

### Added

- Application updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.12.0] - 2026-07-29

### Added

- Application updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.11.0] - 2026-07-29

### Added

- Application updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.10.0] - 2026-07-29

### Added

- Application updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.9.0] - 2026-07-29

### Added

- Application updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.8.0] - 2026-07-29

### Added

- Application updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.7.0] - 2026-07-29

### Added

- Configuration and test updates.

### Changed

- Release maintenance.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.6.0] - 2026-07-29

### Added

- Configuration and test updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.5.0] - 2026-07-26

### Added

- Map customisation and distribution reliability improvements.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.4.2] - 2026-07-26

### Fixed

- Relaunched the application after an update.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.4.1] - 2026-07-26

### Fixed

- Forced an interface refresh after updates.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.4.0] - 2026-07-26

### Added

- Map customisation and distribution reliability improvements.

### Fixed

- Removed build side effects.

### Changed

- Expanded the Polish documentation.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.3.2] - 2026-07-26

### Fixed

- Corrected PowerShell accent handling.
- Added a Windows release launcher.
- Improved GitHub release detection reliability.

### Changed

- Expanded the Dutch documentation.
- Expanded European translations.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.3.1] - 2026-07-26

### Fixed

- Improved GitHub publishing reliability.
- Located GitHub CLI after installation through Winget.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.3.0] - 2026-07-26

### Added

- Real-time progress along the complete SID–route–STAR–approach geometry.
- Display and progressive activation of procedure fixes.
- Monotonic progress protection against jumps at route crossings.
- A permanent manual update-check button.
- Explicit aircraft icon assignment for the window and Windows identity.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.2.1] - 2026-07-26

### Fixed

- Vertical-profile monitoring is enabled only during descent or approach.
- “Waiting for TOD” is shown before descent begins.
- Profile tolerance is stabilised at 500 ft to prevent oscillating warnings.

The installer is verified against its SHA-256 checksum before any automatic update.

## [0.2.0] - 2026-07-26

### Added

- Automatic updates from GitHub Releases with confirmation and SHA-256 validation.
- Semantic versioning and automated release-note generation.
- A responsive Windows window and an interface in eight languages.
- Latest SimBrief OFP, mapped route, official charts, MCDU card, QNH, minima and approach data.
- MSFS tracking with progress, ground speed, indicated airspeed and local recording.
- Privacy-conscious rotating logs.

### Fixed

- The complete process and port `8765` are released when the application closes.
- Fixed the JavaScript error `stage is not defined`.
- Added status information while initially filling the MSFS cache.
- Filtered overly dense ground detail.
- Added WebView2 checks and a non-intrusive, application-private SimConnect connector.

### Maintenance

- Installer, portable archive and SHA-256 checksums.
- Detailed documentation in French, English, German, Spanish, Italian, Portuguese, Dutch and Polish.
- Git exclusions for local Claude, Codex and Graphify data, caches and build artifacts.
