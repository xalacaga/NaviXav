# NaviXav 1.6.0

Released on 2026-08-30.

## Added

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

## Fixed

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

## Changed

- Integration trafic.

The installer is verified against its SHA-256 checksum before any automatic update.
