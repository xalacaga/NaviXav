# Changelog

## [1.7.0] - 2026-09-06

### Added

- AIG AI Traffic models join FSLTL for traffic injection: Settings offers one set or the other, never both at once; the package installed by AI Manager is detected automatically, with a manual path as a fallback, and NaviXav never writes to it.
- The active-flight banner now shows the remaining flight time, recalculated from ground speed in flight and based on the SimBrief ETE before takeoff.
- After closing FSLTL Traffic Injector or AIG Traffic Controller, switching Traffic off and on restarts NaviXav injection; closing the other program does not trigger automatic resumption.
- A NaviXav panel can be added to the MSFS toolbar: it shows the detected model set, the traffic state and the injection state, switches traffic on or off, changes source and brings the window back — without leaving the simulator; the package is copied into Community only by pressing “Install the MSFS panel” in Settings, and Remove takes it away.
- The MSFS panel install and remove button now shows an animated spinner and the operation in progress until it actually completes; it remains locked while waiting to prevent double clicks.
- A fourth traffic source needs no network at all: static traffic parks aircraft on the stands MSFS itself reports, with the liveries of the selected model set and a plausible aircraft for each stand category; the radius and the number of parked aircraft are set in Settings.
- The MSFS panel offers four sources including static traffic and shows versions and general service status; its green dot indicates an active manager, not a confirmed creation count.
- Settings now offers to update an already installed MSFS panel: the package copied into Community keeps the content of the version that wrote it, and the status line now shows the installed version next to the one shipped here.
- Static traffic uses the common limits, initially 40 NM and 10 aircraft, prioritising nearby stands already available in the MSFS cache; performance depends on scenery and models.
- The MSFS panel now shows My flight: next waypoint and distance, time remaining, next constraint and TOD, synchronized with the NaviXav window and its language. Flight values are hidden after ten seconds without an update. Traffic shows confirmed, selected and skipped aircraft, loading, errors and stale states; the green dot requires confirmed creations. The return button opens the window for details. Reinstall panel 1.2.0 from Settings, then restart MSFS to load the new files.
- The Map and Taxi toolbars group view, display and traffic controls. Buttons provide a 40-pixel-high target, zoom controls stay together and controls adapt to compact windows. Taxi clearance and route actions remain together.
- While settings are being saved, the Save button shows an animated indicator and “Saving…”. It stays disabled until the operation finishes to prevent duplicate submissions, then becomes available again, including after errors. The animation respects reduced-motion preferences.
- The map and the taxi chart follow the aircraft from the moment they open: framing a chart on arrival no longer cancels Follow, which only the Fit and Route buttons give up — those exist precisely to show the whole picture. The taxi chart stays framed on the airfield until the aircraft is there: in cruise, the arrival taxi chart no longer wanders off after an aircraft three hundred miles away.

### Fixed

- The active-flight banner also shows remaining time: remaining distance and ground speed when usable, otherwise the SimBrief ETE before takeoff. After saving Settings, flight-plan refresh continues in the background without holding the dialog open. MSFS-panel traffic commands preserve other settings, including SimBrief identifiers.
- The engine anti-ice alert no longer flickers incorrectly on the Fenix A319, A320 and A321: NaviXav now reads both Fenix cockpit engine anti-ice controls directly instead of its unstable standard SimVar.
- Traffic filters parking-position noise and joins reports with independent animation targeting 30 updates per second; the actual rate depends on MSFS and the computer.
- Static traffic shows on the map again: the source did not answer the call that feeds it, so parked aircraft entered the simulator without ever appearing on screen; their details now open on click as well.
- The NaviXav window and the MSFS panel no longer announce two different traffic sources: the window re-reads the real setting every three seconds and follows what the service injects, instead of keeping the one it showed before the change made in the simulator.
- Traffic shows progress, confirmed MSFS creations and errors on the map and taxi chart; static traffic shares its cache and quickly retries unavailable stands; dedicated animation smooths movement.
- Traffic animation uses a dedicated SimConnect connection: position reads, presence checks and aircraft creation no longer suspend movement of existing aircraft; diagnostics record the achieved update rate and longest interval between updates.
- Documentation in all eight languages now matches controls, traffic limits, MSFS-panel updates, remaining time and Fenix readings; older presentation copy is clarified.
- Changing a setting unrelated to traffic no longer restarts injection or existing aircraft. Source, model and active static-traffic settings still take effect. Modules share a timestamped MSFS sample for at most 250 ms; injection takes the player position and altitude from the same state. An expired sample or failed connection does not supply an old position as if it were current.
- On the ground, a stop report cancels prediction and smoothing converges on the reported parking position without retaining momentum. Without a new motion report, prediction slows down and its window is limited to five seconds; transitions remain gradual. Small position variations of an already parked aircraft are filtered. These rules use source positions, without building detection.
- Periodic position, traffic, VATSIM controller and simulator status reads prevent overlapping requests for the same read and discard responses made obsolete by a context change. On the Taxi view, a temporary error retains the last positions for at most ten seconds after the last successful report, with a warning. A confirmed empty report or disabling traffic clears positions immediately.
- Tracking uses individual OpenSky position timestamps when valid: receiving an old report does not make it fresh, and out-of-order positions are ignored. Without a usable individual timestamp, NaviXav retains its conservative local estimate. Hidden Map and Taxi views suspend their traffic reads and drawing; showing them resumes reading and resizing. Flight tracking and MSFS injection remain active.
- On Fenix A319/A320/A321 aircraft, NaviXav reads the captain EFIS STD mode for the display and QNH/STD alerts. A conflicting generic MSFS SimVar no longer overrides that mode. If the Fenix read is unavailable or invalid, the setting remains unknown and these alerts are not triggered from generic pressure. This read does not monitor the first officer side.
- Every SimBrief import and recalculation checks SID–route–STAR–approach connections against the actual flown endpoints in MSFS data, even when transition names differ from connecting fixes. Missing connections require confirmation; no arbitrary transition is selected. Runway branches that exactly duplicate the STAR start no longer create a return to its entry; distinct constraints are preserved. The resulting route retains OFP DCT segments and airways. User-selected transitions absent from the database are marked unverified.
- MSFS panel 1.2.1 automatically reconnects to NaviXav after an interruption or port change. An unavailable connection is no longer reported as a stopped application. Requests have a real timeout, and display errors no longer stop reconnection. After updating the panel from Settings, restart MSFS to load its new files.
- In wide windows, Map and Taxi controls stay below the flight strip while scrolling, using its measured height. Module changes update these measurements before scrolling. In compact windows, the strip and controls scroll normally to preserve map space.
- On Fenix A319/A320/A321 aircraft, STD detection reads the actual captain barometer state (B_FCU_EFIS1_BARO_STD), rather than the S_FCU_EFIS1_BARO_STD input. An input returning to zero no longer causes a false alarm while STD is displayed. Unavailable or invalid readings remain unknown.
- Animation keeps its cadence after a late frame without adding a full extra wait. Nearby aircraft retain priority at 30 Hz; beyond 10 NM updates use 15 Hz, then 5 Hz beyond 40 NM. Settled parked aircraft are no longer recalculated every frame. Ground acceleration is smoothed, heading follows the shortest turn and stops remain immediate. Parking prediction limits remain in place.
- The displayed TOD is a SimBrief or NaviXav estimate, not a reading from the MCDU. The FMS profile can place it elsewhere even with the same route and flight level. If constraints move the SimBrief point earlier, its displayed source becomes “Calculated estimate”.
- Flight tracking and the in-game panel show “Descent in progress” instead of TOD during descent, then “Approach”. Level segments retain this indication when altitude loss confirms descent. This status comes from telemetry, not the FMS DES mode.
- Saving a setting no longer re-reads the model package for nothing: the in-memory index was only valid for a minute, so a save spaced from the previous one spent three seconds re-reading thousands of liveries. It now stays valid as long as package detection returns the same thing, and an install or an update rebuilds it.
- ILS monitoring now compares the frequency of the receiver actually assigned by the aircraft: captain NAV3 on Fenix A319/A320/A321 and FlyByWire A32NX, or the NAV1–NAV4 index selected by MSFS on other aircraft. Unavailable data remains unknown and no longer triggers a false warning.
- Release preparation no longer mistakes the local 127.0.0.1 address in publishing copy for an old NaviXav version.
- Traffic settings again provide a radius and maximum aircraft count for every source. Defaults are 40 NM and 10 aircraft; nearest aircraft are retained first and every change cleanly restarts selection and injection.
- OpenSky real-world traffic no longer exhausts its public quota with one-minute refreshes: anonymous snapshots are spaced four minutes apart, an HTTP 429 response suspends requests for OpenSky’s requested delay, and identical errors no longer fill the log several times per second. The window and MSFS panel then explicitly show “OpenSky daily quota exhausted” and explain the automatic retry.

### Changed

- Ajouts et corrections.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.6.0] - 2026-08-30

### Added

- Clearer controls: Flight tracking now provides a visible switch to disable or re-enable every NaviXav alarm, including MASTER WARNING and MASTER CAUTION messages, without stopping flight tracking; after an update, Version history opens automatically on the first restart and then remains available on demand.
- Instant traffic-source switching from the Map and Taxi toolbars: the VATSIM, IVAO and OpenSky selectors stay synchronized, restart traffic collection cleanly and save the choice locally.
- OpenSky real traffic: NaviXav can display public ADS-B state vectors within 100 NM of the aircraft, with source attribution and API-friendly caching; this real-world view remains strictly separate from MSFS injection.
- Settings reorganized into collapsible categories suited to compact windows, with a manual FSLTL path, access to the official FlyByWire Installer when models are missing, and IVAO as a second free public network traffic source alongside VATSIM.
- MSFS 2024-only compatibility: NaviXav now uses the native MSFS 2024 SimConnect AI EX1 API and rejects an old MSFS 2020 DLL at startup or build time instead of continuing with an unsuitable connection or functions.
- VATSIM traffic injection into MSFS: NaviXav automatically detects FSLTL Base Models in Community, indexes its aircraft.cfg files and VMR rules without modifying them, selects the safest exact or generic model, then creates, updates and removes only its own SimConnect objects within a bounded bubble around the player. The option is off by default and the interface shows the detected FSLTL version.
- Surrounding traffic: a “VATSIM traffic” button on the map bar, “Simulator traffic” on the taxi bar, shows the other aircraft. On the map each network aircraft is a silhouette turned to its heading with its callsign below, and a click opens its card: type, frequency, pilot, departure and arrival airports named from the MSFS database, ground speed and altitude. The taxi chart shows the simulator’s traffic, the only one accurate to the metre. Off by default, and no network call is made while it is.
- Vertical profile: the TOD now prefers the performance point from the latest SimBrief OFP after validating its coordinates against the active route; STAR and approach ceilings still apply, and the 3° geometric calculation automatically takes over when that point is missing or no longer matches the route.
- VATSIM positions online: once enabled in the settings, NaviXav marks with a dot the airport frequencies whose position is staffed, and shows on hover the controller’s callsign and frequency — the network’s is not always the one the simulator publishes. The setting is off by default, and no network call is made while it is.
- Airport frequencies: the departure frequency now completes the row, and a role holding several frequencies says so with a “+n” instead of suggesting there is only one; the detail of every station, aprons included, is readable on hover.
- Flight tracking: a second pill announces the frequency expected at the current stage and marks itself when the radio is already on it. It stays silent when the airport publishes several frequencies for the same role, since nothing says which one serves the runway in use.
- Flight tracking: a radio pill shows the frequency dialled on COM1 and names the matching airport station, per-runway ground included — enough to check at a glance that the frequency you were given is the one you typed.
- Diagnostics: the “navixav airport” command now lists the airport frequencies alongside the number the simulator uses for each role, and flags a role it cannot translate instead of hiding it.
- Airport frequencies: the Departure and Arrival cards of the flight plan now show the radio chain published by MSFS, in the order it is used — ATIS, DEL, GND, TWR on departure, ATIS, APP, TWR, GND on arrival. Where an airport publishes several frequencies for the same role, the others appear on hover.
- TOD preparation: at 50 NM, the alert engine asks the pilot to prepare for descent and highlights the TOD tile; at 10 NM, a separate imminent-TOD caution is raised and remains active until the descent is engaged.
- Aircraft configuration: the guided interface now uses a clearer cockpit-style synoptic with balanced tiles, one icon per system, a status accent, and proper light indicators; the classic interface retains the previous design.
- New flight-guided interface: a persistent strip highlights the phase, runway or procedure, next action, and recommended module; departure, arrival, and approach charts are prepared in a pinboard, and Ground mode gets more room. The Interface layout setting instantly restores the classic interface without a restart.
- Taxi plan: leaving a nose-in stand now starts with a pushback, drawn in purple with a tight dash on the plan and announced in the banner with its distance and the heading once the aircraft is lined up; a ramp, a taxi taken up again or an arrival show none.
- Flight plan preparation: the banner announcing the MSFS cache fill now shows an aircraft crossing the frame, trail behind it, for as long as the read lasts. The wait could reach several tens of seconds with nothing moving on screen.
- MCDU card: NaviXav now retrieves ZFWCG from SimBrief and shows the zero-fuel centre of gravity together with the passenger count on the weights page; ZFWCG is also shown in Dispatch.
- Choosing a traffic source is now enough to inject it into MSFS: injection is on by default and the settings checkbox is only there to opt out.
- A “map only” marker appears on the map toolbar when traffic is displayed without being injected, and its tooltip gives the reason: injection turned off, FSLTL missing or real-world source.
- Real ADS-B traffic finally enters MSFS: each aircraft's type is resolved from two complementary public registries, which is what makes choosing an FSLTL model possible at last. An aircraft unknown on the first sweep shows up on the next, once its address has been resolved.
- Choosing a traffic source is now enough to inject it into the simulator. The “Inject network traffic into MSFS” checkbox is gone from the settings: the layer button is the only switch, and what it shows is what flies.

### Fixed

- Parked OpenSky aircraft remain injectable when their transponder omits barometric altitude, speed or heading: NaviXav first uses geometric altitude, then fills only missing ground-state data.
- OpenSky real traffic in MSFS: aircraft without an ADS-B type immediately use a safe generic FSLTL model instead of remaining invisible, then adopt their exact model as soon as the ICAO24 registry responds; injection now updates their position every second.
- Smoother IVAO and OpenSky traffic in MSFS: NaviXav extrapolates positions every second between network readings and briefly retains an aircraft omitted by the source, preventing disappear-and-reappear flicker; the fixed 15-second countdown, inaccurate for these sources, has been removed from the interface.
- Network traffic at gates and on taxiways: when VATSIM does not publish the ground state, NaviXav now infers it from a speed at or below 50 kt; parked and taxiing aircraft are injected instead of being skipped.
- Aircraft inventory: Refresh now detects flyable add-ons with an incorrect isAirTraffic flag, such as the Rafale M, and each aircraft displays its own local thumbnail instead of reusing the loaded aircraft's image.
- Arrival taxi plan: the aircraft’s actual position and runway heading now exclude exits already passed; after landing on 24R, NaviXav no longer suggests backtracking toward an exit behind the aircraft.
- Map: the en-route section of the flight plan keeps its violet colour but now uses a solid line that is easier to read at low zoom levels.
- Aircraft page: long ICAO equipment strings now wrap inside their tile instead of overflowing into the neighbouring profile.
- SimConnect identity: text variables such as TITLE and ATC MODEL are now declared with the null unit expected by the MSFS SDK, instead of the literal NULL string that silently produced an empty value.
- Aircraft page: the primary identity now follows the aircraft actually loaded in MSFS live, automatically falling back to ATC MODEL when an add-on leaves TITLE empty; the aircraft planned in SimBrief remains clearly separated for the OFP weights and performance figures.
- Exterior lights: NaviXav now cross-checks the seven individual SimVars against MSFS's official LIGHT STATES mask; complex aircraft that publish only the aggregate state once again show their indicators and trigger alerts correctly, with an automatic fallback to the previous reading when the mask is unavailable.
- Flight tracking: the new Aircraft configuration synoptic is now strictly isolated to its own block and no longer enlarges or disrupts the real-time tracking tiles.
- Demo mode has been removed: NaviXav now exclusively uses the latest SimBrief plan and real flight data supplied by MSFS through SimConnect.
- Guided interface: the horizontal route strip now remains only in the Flight plan menu and no longer overlaps the top strip in other modules; the classic interface keeps its historical display.
- Module navigation: the guided top strip now measures the toolbar's actual height and remains fully visible instead of being clipped after changing menus.
- Procedures module: a phase made only of reminders, such as landing, is no longer shown as completed before the flight; its meter stays empty and its items carry the information mark instead of a green confirmation.
- Procedures module: a phase the flight has not reached yet no longer shows confirmations; at the gate, the parking brake set and the lights off no longer tick the after landing and shutdown items.
- Taxi plan: the departure entry is now selected from every aircraft-accessible runway junction according to its proximity to the requested threshold. At CYYZ, a departure from gate 139 to runway 23 now uses AK, A, H and Q instead of crossing runway 15L to reach the H3 intersection. Every confirmed runway crossing is split at an explicit hold-short point, and the route is rejected if that instruction disappears.
- Network traffic injected into MSFS: aircraft dropped by the simulator mid-flight are now detected and recreated on the next cycle, instead of disappearing for good while NaviXav believed it was still tracking them.
- The log now records every change in an injection cycle — aircraft tracked, recreated, removed, skipped — making a silently empty injection visible.
- The injection option label no longer mentions VATSIM alone: it names network traffic, whichever source is selected.
- The real-world source is now called “Real-world traffic · OpenSky” in all three pickers, instead of the provider name alone, and that label finally follows the interface language.
- An aircraft sitting on the exact spot of yours is no longer shown or injected: it is almost always your own aircraft, rendered by the network you are connected to. The neighbouring stand stays visible, and an overflight is not mistaken for an overlap.
- An aircraft publishing no callsign is given a stable generic one, instead of its hexadecimal address or an empty field that the simulator would show as a missing registration.
- Traffic injection now owns its own lifecycle: its state can be queried instead of being locked inside the web service, so a stopped injection can no longer pass for a healthy one.

### Changed

- Integration trafic.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.5.3] - 2026-08-28

### Fixed

- Airports missing from the cache are imported from the simulator again: runway lighting was read with the wrong field width, which lost the whole airport and left its ground chart unavailable.
- An unavailable ground chart now says why — airport missing from the database — instead of reporting a network error, and unknown lighting intensity is no longer shown as off.

### Changed

- Bug correction.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.5.2] - 2026-08-28

### Added

- MSFS tracking now explicitly distinguishes STD from QNH, shows runway edge and centreline lighting, and can warn about an open door, hatch or canopy that presents a risk.

### Fixed

- ChartFox charts delivered as images now fit the width of the Charts panel and follow the zoom buttons; they opened oversized and the controls had no effect.

### Changed

- Mise a jout varsim.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.5.1] - 2026-08-28

### Fixed

- PDFs in Charts now fit the available width instead of opening oversized, with controls to zoom out, zoom in or restore the fitted view.

### Changed

- Bug mineur.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.5.0] - 2026-08-28

### Added

- Clicking an aircraft photo now opens a large preview inside NaviXav; it closes with its button, an outside click or the Escape key.
- The Aircraft card and inventory now show a real freely licensed photo beside the name for every supported aircraft family; additional aircraft installed in Community automatically use their local thumbnail when available.
- When a ChartFox chart cannot be embedded, NaviXav now offers the official national catalogue in the same card whenever the airport is covered.
- Flight tracking now estimates the Top of Climb from the cruise level, vertical speed and ground speed; the calculated TOC and TOD points appear on the map as distinct fixes.
- ChartFox can now be linked from Settings with a VATSIM account; its on-demand charts are offered as an optional source for the departure and arrival airports.
- The Charts menu now states that a ChartFox/VATSIM account is required to access ChartFox AIRAC charts and provides a direct link to Settings.

### Fixed

- Aircraft photos are no longer hidden behind the ICAO type tile in the Aircraft card and inventory.
- Opening an airport PDF in Charts no longer pushes the other airport below the document: Departure and Arrival stay side by side on wide screens, and the unopened card stays first in compact windows.
- The ChartFox “simulation only” notice in Settings now follows the interface language.
- ChartFox charts whose source forbids embedding no longer show a blank area: NaviXav explains the restriction and offers to open them directly on ChartFox.
- The calculated TOC and TOD fixes now use their own magenta and red colours, distinct from every route waypoint.
- The CartoDB Positron and Dark Matter base maps have been removed: their free service now watermarks every tile with "API key required". The choice is between OpenStreetMap Standard and OpenTopoMap, and a setting that has become invalid falls back to OpenStreetMap automatically.
- The weather briefing no longer appears partly in French when the interface is set to another language: the operational notes and the METAR phenomena now follow the selected language.
- Thunderstorms with no observed precipitation are now reported: the TS, VCTS and VCSH groups were ignored by the METAR decoding. The "PO" in "TEMPO" is no longer read as dust whirls either.
- SIDs finally appear on the map: their path, fixes and published constraints were missing whenever one procedure served two runway ends, which is the case at almost every major airport. The departure was reduced to a straight line to the first en route fix. STARs also regain their final portion, specific to the landing runway. The navigation database is refreshed from the simulator automatically at the next start.

### Changed

- Reformuler l'annonce ChartFox de la 1.5.0.
- Ajout fonctionnalite et correction bugs.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.17] - 2026-08-09

### Added

- The map now shows the published altitude and speed constraints under each SID, STAR and approach fix, in the colour of their procedure; a Constraints button in the map bar hides them.
- Taxi routes can now be dictated: type the taxiways given by the controller — "N D B" — in the airport chart bar and NaviXav draws and guides exactly that route, which helps on VATSIM and IVAO. A taxiway that does not extend the previous one is refused by name, never silently replaced by the computed route; a clearance stopping short of the runway is extended as a dashed portion.

### Fixed

- Ground taxi messages — unknown taxiway, stand not found, runway not served — now follow the interface language. They were shown in French whatever language was selected.

### Changed

- Ajout fonctionnalites.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.16] - 2026-08-08

### Fixed

- Fenix A319/A320/A321 speedbrakes now show ARMED reliably even when the SimBrief aircraft name is generic.
- Top of Descent is now a fixed point on the route, computed from the cruise level: it counts down to zero and then reads as passed. It could previously freeze during a 3° descent, or even grow when the descent was started too early.
- The deviation from the descent profile keeps being reported during a level-off below the cruise level. It used to disappear as soon as the vertical speed returned to zero, exactly when the aircraft was far below profile.
- Top of Descent now honours the published altitude ceilings of the STAR and the approach, and reads altitude in the standard atmosphere like a flight level.
- The vertical speed required for the next constraint is now compared with the indicated altitude, the only one comparable with a published constraint.

### Changed

- Correction bug TOD.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.15] - 2026-08-08

### Fixed

- Commercial licensing and contribution enquiries now use the dedicated NaviXav contact address.
- The automatic update now really installs itself: the helper that waits for NaviXav to close was started without any console and died immediately, so the update was announced as scheduled and the application reopened on the previous version. The helper also keeps its own log next to the installer, so a future failure can be diagnosed.
- Downloaded installers no longer pile up: each update sweeps the previous ones, and the installer does the same once it finishes. Half a gigabyte had accumulated on a machine followed since the first versions. The logs are kept, so a failure can still be examined.

### Changed

- Nettoyage des installateurs telecharges.
- Correctif mise a jour automatique.
- Update NaviXav contact email.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.14] - 2026-08-08

### Fixed

- A procedure item already confirmed now stays confirmed for the rest of the flight: a phase no longer loses its ticks when the simulator state moves on, such as the beacon switched off, the flaps retracted or the parking brake released, and an item the simulator no longer reports reads Confirmed earlier instead of Confirmed · SimConnect.

### Changed

- Correctif procedure.
- Mise a jour License et ajout GS pour taxi.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.13] - 2026-08-08

### Added

- The taxi chart now shows live ground speed and warns you as you approach the taxi speed limit, then raises a flashing alarm and an audible beep once you exceed it; the limit tightens automatically for turns, hold short bars and the arrival stand, and never applies on a runway.
- Settings now hold the maximum taxi speed, the lower limit used in turns and a switch for the audible alarm, which can also be muted straight from the taxi toolbar.
- The current NaviXav source now permits noncommercial use under PolyForm Noncommercial 1.0.0, with separate commercial licensing for paid reuse.

### Fixed

- Release preparation now distinguishes the NaviXav version from the PolyForm licence version and preserves the historical Apache release boundary.

### Changed

- Mise a jour License et ajout GS pour taxi.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.12] - 2026-08-08

### Fixed

- Automatic updates now wait for the old NaviXav process to close completely, reinstall into the directory actually in use and keep an installation log, preventing the previous version from restarting and offering the same update again.
- Release preparation now handles an empty Added or Fixed category without shifting the following PowerShell arguments or interrupting publication.

### Changed

- Correction bug.
- Bug de versioning.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.11] - 2026-08-08

### Added

- An aircraft-specific Procedure Assistant now presents normal procedures by flight phase, tracks progress and confirms compatible items automatically through SimConnect.
- Settings can inventory installed aircraft against the local procedure database, select an MSFS Community folder and create a reviewable draft for an uncovered aircraft.
- The whole application now offers automatic, light and dark appearance modes, with a direct toolbar toggle and a persistent local preference.

### Fixed

- The top toolbar, flight route and Procedure Assistant use a finer and more coherent visual hierarchy; procedure status badges stay discreet and the assistant label is now easier to read.
- Long flight routes can now be scrolled horizontally with the wheel, pointer drag, touch or keyboard, while subtle edge fades indicate hidden waypoints.
- Settings now place the support option at the top and keep the lengthy aircraft procedure inventory collapsed by default.
- Procedure source notes now follow the selected interface language instead of remaining in a single language.

### Changed

- Ajout module procedure et amelioration visuel interface.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.10] - 2026-08-06

### Added

- The settings now open the complete version history: every important change since tracking began, version by version, with the date and a marker on the one installed. The history ships with the application and reads offline. The change texts stay in English; the frame and the section labels follow the selected language.
- Flight tracking now tells a paused simulation from a lost one: the MSFS indicator and the tracking pill read “MSFS paused” instead of suggesting a dropped connection. A simulator that does not expose this state keeps being tracked normally.
- A discreet pencil appears when hovering the runway, the SID, the STAR, their transitions and the approach: it opens the list of the other published procedures and lets you change the choice afterwards, even when the engine is confident. The list is no longer limited to three entries, it shows everything flyable from the selected runway, and “Back to the automatic choice” hands control back to the engine. The pencil stays lit on a choice you imposed.

### Fixed

- An absent procedure no longer takes the room of a real one. When no STAR is published for the runway, the reason replaces the dash on a single tightened line, and the transition line that merely repeated the absence is gone. Same tightening for a SID or an approach without a transition.
- A SID or STAR that is not published for the selected runway is no longer chained: it starts from another threshold or leads to the IAF on the opposite side of the airport. NaviXav now announces a radar-vectored departure or a direct arrival, and the discarded procedure remains offered in the list of choices. At Brive-Souillac landing on runway 29, the plan reads BSC then ILS RWY 29 instead of an unflyable STAR.
- Without a STAR, the approach and its transition now connect to the last en-route waypoint instead of being left unconnected. A transition published on that very waypoint is recognised and is no longer presented as an uncertain choice.
- Approach fixes that SimBrief leaves in the navigation log without marking them, such as CF29 or RW11, no longer count as en-route waypoints: they are no longer drawn on the route and no longer used to link the arrival.
- When a STAR does serve the landing runway but ends on a waypoint that starts no approach, NaviXav says so explicitly instead of leaving the break to be discovered in flight.
- The version history no longer sits permanently on top of the interface: it opens only when its icon in the settings is clicked, and it closes completely.
- The settings window no longer has a horizontal scrollbar: an invisible field used to overflow the whole width of the box, whatever the window size.

### Changed

- Correction bug et améliorations diverses.

The installer is verified against its SHA-256 checksum before any automatic update.

## [1.4.9] - 2026-08-05

## Fixed

- Application shutdown now uses FastAPI's supported lifespan lifecycle without deprecation warnings.
- The bundled LCPH-EHAM demonstration no longer warns about its expected offline navigation-cache fallback.

## Changed

- Correction bug.

The installer is verified against its SHA-256 checksum before any automatic update.

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
