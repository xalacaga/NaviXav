# Changelog

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
