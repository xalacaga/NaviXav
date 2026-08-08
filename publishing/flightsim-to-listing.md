# Flightsim.to Publication Pack — NaviXav 1.4.14

This document contains the English copy and checklist for publishing NaviXav
on Flightsim.to. It is not intended to be included in the application.

## Listing Details

**Title**

NaviXav – IFR Flight Planning and Live Flight Assistant

**Category**

Utilities / Miscellaneous

**Simulator compatibility**

Microsoft Flight Simulator 2024

MSFS 2020 should not be selected until it has been tested and validated.

**Version**

1.4.14

**Release status**

Freeware

**Suggested tags**

- IFR
- SimBrief
- SimConnect
- Flight Planning
- Flight Tracking
- Weather
- METAR
- Ground Taxi
- MCDU
- CDU
- Moving Map
- Navigation
- MSFS 2024
- Utility

**Short summary**

Local Windows IFR assistant combining the latest SimBrief OFP with live MSFS
data: terminal procedures, weather briefing, dispatch monitoring, ground taxi
guidance, flight tracking, MCDU/CDU guidance and official charts.

## Full English Description

### About NaviXav

NaviXav is a downloadable, standalone Windows desktop application for Microsoft
Flight Simulator 2024. It is installed and executed locally on the user's
computer.

NaviXav is not a hosted website, a browser-delivered add-on or a cloud
application. All primary features are provided by the installed Windows
executable and displayed inside its dedicated desktop window. Microsoft Edge
WebView2 is used only as the embedded rendering component for that window.

NaviXav combines your latest generated SimBrief Operational Flight Plan with
navigation data and live aircraft information obtained directly from Microsoft
Flight Simulator through SimConnect.

> NaviXav is intended for flight simulation only. Always verify important
> information against current official publications and applicable ATC
> instructions.

### What's New in 1.4.14

**Modern desktop navigation.** On wide desktop windows, modules now sit in a
compact floating rail at the upper left with a clear active marker and a subtle glass
treatment. A concise **Flight plan** entry replaces the long collapsible
Departure, Route and Arrival section, behaves like every other module and is
selected by default.
Every choice scrolls directly to its content, the main area fills all remaining
width, and an opened official PDF expands across the chart grid. Compact
desktop windows retain the horizontal selector. A visible global flight alert
automatically moves the rail below the enlarged header instead of covering its
first entry, while mobile navigation keeps
its accessible side drawer.

**Weather briefing.** A **Weather** tab brings together departure, cruise,
arrival and alternate briefings. Each airport shows decoded essentials — wind,
visibility, ceiling, temperature and dew point, QNH, significant phenomena and
flight category (VFR, MVFR, IFR or LIFR) — together with the age of the
observation. The TAF summary keeps only the meaningful changes, and the raw
METAR and TAF remain one click away. The cruise briefing carries the OFP
average wind, wind component, ISA deviation, outside air temperature and
tropopause. The briefing flags stale observations, mist or fog risk, gusts, low
temperatures and low IFR conditions. In live METAR mode, observations refresh
on load and every five minutes without recalculating the route or changing the
selected procedures.

**Dispatch monitoring.** A **Dispatch** tab compares the OFP forecast with live
simulator values: loaded and remaining fuel, actual burn, take-off and landing
weights, time and distance, refreshed every two seconds. Projected arrival fuel
warns when it drops below final reserve plus alternate fuel, and projected
landing weight warns above maximum landing weight. Hourly burn uses a
five-minute rolling average and stays accurate at increased simulation rate.
Tracking now survives closing the application mid-flight: block fuel and
take-off time are restored when NaviXav reopens.

**Flight timeline and replay.** Flight tracking now presents a proportional
ribbon for every phase flown and groups stable events beneath the phase in
which they occurred: take-off and landing runway with the observed wind, gear,
flaps, spoilers, parking brake, lights and autopilot modes. The timeline is kept
with the completed-flight summary in the local logbook and replays in whichever
interface language is selected later.

**Faster first plan preparation.** When SimBrief supplies validated coordinates
in its detailed navlog, NaviXav draws the en-route section immediately and asks
MSFS Facilities only for missing positions. Published procedure links also
avoid unnecessary positional lookups, while route-corridor validation and the
local MSFS cache remain available as safeguards.

**Cleaner mobile connection status.** On phones and tablets narrower than
760 px, the MSFS connection state uses a compact coloured dot instead of the
`MSFS connected` label, keeping the toolbar inside the screen. The translated
label remains accessible to assistive technologies, and the mobile toolbar now
offers its own display-language selector.

**More accurate aircraft indications.** Airbus five-position flap handles now
show the correct detents, unknown aircraft show both handle position and
measured flap angle, and flight levels use pressure altitude in the standard
atmosphere instead of true altitude. Constraints, official charts, MCDU chart
guidance, taxi labels, connection messages and error banners now all follow the
selected interface language.

Aircraft configuration and Flight events also keep following flaps, spoilers
and the parking brake when a third-party aircraft freezes one standard MSFS
value. NaviXav cross-checks the official handle, effective-position,
surface-position and cockpit-indicator SimVars instead of leaving flaps stuck
on FULL or silently missing control changes. A dedicated Fenix A319/A320/A321
adapter reads the flap, speedbrake and parking-brake cockpit controls directly,
including with engines and hydraulic systems off.

**Clearer airport ground charts.** Named taxiways remain visible even when MSFS
classifies them as generic `path` segments. At airports such as LCPH, main
taxiways including A, B and K are no longer hidden with anonymous secondary
links and stand access paths.

**More reliable route drawing.** Approach lines no longer jump to a same-named
waypoint hundreds of miles away — the Orly final approach could previously lead
to Corsica. Runway-related names such as `CF02`, `FI21L` and `DER07` are now
recognised at any airport, en-route waypoints with several database matches are
resolved near the route, and routes crossing the antimeridian are drawn
continuously.

**Fewer false runway warnings.** The misleading "SimBrief planned runway X, but
wind would favour Y" message is gone. In light, calm or variable wind it
attributed to the wind a ranking that actually came from airport preference and
ILS availability.

**Cleaner install.** The application and its installer now carry full publisher
information and are shipped uncompressed, which removes the antivirus
heuristic warnings some users reported on earlier builds.

### Main Features

- Retrieves your latest generated SimBrief OFP from a Pilot ID or username,
  with the complete route, dispatch data, weights, fuel, alternate and
  estimated flight time.
- Suggests departure and arrival runways from weather and aircraft
  configuration, then SIDs, STARs, transitions, approaches and VIA selections
  from MSFS navigation data.
- Displays altitude and speed constraints, transition altitude or level, ILS
  frequency, intercept altitude and missed-approach altitude.
- Provides a full weather briefing for departure, cruise, arrival and
  alternate, with decoded METAR, summarised TAF and operational warnings.
- Compares the OFP dispatch figures with live fuel, weight, time and distance
  values read from the simulator.
- Computes ground taxi routes between a parking stand and the runway, drawn on
  a dedicated aerodrome chart with holding points and turn-by-turn callouts.
- Tracks the aircraft in real time through SimConnect: flight phase, speeds,
  altitude, next waypoint, lateral deviation, route progress, Top of Descent
  and vertical-profile guidance.
- Monitors aircraft configuration — gear, flaps, speedbrakes, parking brake,
  lights, altimeter setting, autopilot modes, selected altitude, fuel and wind
  — and clears configuration alerts automatically once the correction becomes
  stable.
- Provides an aircraft-adaptive reference card: Airbus MCDU, Boeing CDU or a
  generic FMS presentation.
- Includes a moving map with the planned route, terminal procedures, aircraft
  position, flown track, ground taxi route and several selectable styles.
- Gives access to supported official national AIS charts.
- Stores only a local summary of completed flights, which can be purged at any
  time.
- Includes a demonstration mode and automatic update checking with SHA-256
  verification and explicit user confirmation.
- Available in English, French, German, Spanish, Italian, Portuguese, Dutch and
  Polish.

### How NaviXav Is Developed

NaviXav is a one-person project, and it is written with heavy use of AI coding
assistants — what is often called "vibe coding". This is stated openly, because
you are installing an executable on your own machine and you are entitled to
know how it was produced.

What that means in practice:

- I specify every feature, review the result, fly it in the simulator and
  decide what ships. The assistant writes a large share of the code; it does
  not decide what gets released.
- The project carries an automated test suite of more than four hundred tests
  that must pass before any build is produced. A failing test blocks the
  release.
- The complete source is published under the PolyForm Noncommercial License
  1.0.0. Anyone can inspect exactly what runs on their machine. Noncommercial
  use is permitted; commercial use requires a separate written licence.
- NaviXav is advisory software for a flight simulator. It never controls your
  aircraft, and it never replaces official publications or ATC instructions.

The honest caveat: AI-assisted code can contain mistakes that look entirely
plausible on the page. That is precisely why the test suite, source transparency
and the "always verify" warning above matter. If something looks wrong, please
report it — bug reports are the most valuable contribution to this project.

### Antivirus and False Positives

NaviXav is a Python application packaged into a standalone Windows executable.
Unsigned executables built this way are sometimes flagged by generic
machine-learning heuristics — typically as `Wacatac` or a similar generic
label — without any actual malicious code being present.

The 1.4.14 build ships uncompressed and carries full publisher metadata, which
removes the usual cause of these warnings. Every uploaded archive is checked
before publication, and the SHA-256 checksum of each file is published so you
can verify the download.

If your antivirus reports NaviXav, please report it here with the version
number rather than assuming the worst — and please do report it, because
vendor false-positive submissions are what get these fixed for everyone.

### SimBrief Integration

NaviXav retrieves the latest OFP that has already been generated on SimBrief.
The **Create a SimBrief plan** button opens the official SimBrief flight-plan
editor; after generating the OFP, return to NaviXav and select **Import flight
plan**.

A generated SimBrief OFP is required before NaviXav can retrieve it. NaviXav
does not modify or upload flight plans to SimBrief.

### Live Flight Tracking

NaviXav reads live aircraft information directly from MSFS through SimConnect
and displays the current flight phase, position and flown track, speeds,
altitude and vertical speed, remaining distance and route progress, next
waypoint, lateral deviation, Top of Descent estimation, vertical-profile
guidance, fuel information, aircraft configuration and active alerts.

Configuration alerts disappear automatically once the required correction
becomes stable, and can activate again if the same unsafe condition returns
later.

### Ground Taxi Guidance

Using the taxiway network published by Microsoft Flight Simulator, NaviXav
builds a taxi route between a parking stand and the runway. It follows the
taxiways, avoids closed segments and service roads, only uses a runway as a
last resort, and tells you which holding point to stop at.

Selecting a stand draws the route on the map — green behind the aircraft, blue
ahead — with holding bars and remaining distance. While taxiing, the next
manoeuvre is announced ("Turn left on Q", "Hold short of runway 05") together
with the distance to go. At arrival, the runway exit closest to your stand is
chosen automatically.

The dedicated **Ground** tab shows the same information on a full-size
aerodrome chart with a metric grid and north indication, secondary taxiways
hidden by default.

### Weather Briefing

The **Weather** tab covers departure, cruise, arrival and alternate. Each
airport shows wind, visibility, ceiling, temperature and dew point, QNH,
significant phenomena and flight category, with the observation age. A
graphical summary presents conditions, wind direction, visibility and ceiling
at a glance.

The cruise briefing is built from the OFP's own average wind, wind component,
ISA deviation and tropopause, so it triggers no additional network request.
Weather source and refresh behaviour are selected in Settings.

### Aircraft Configuration

NaviXav adapts its configuration display to the aircraft currently loaded in
MSFS. Monitored items can include landing gear, flap position and
aircraft-specific detents, speedbrakes, parking brake, exterior lights,
altimeter setting, selected altitude, autopilot modes, engine anti-ice, fuel
quantity, wind information and overspeed or stall warnings.

Available data depends on the values exposed by the aircraft through
SimConnect.

### Aircraft-Adaptive Flight Management Card

The flight-management reference card adapts its terminology to the detected
aircraft family: MCDU for Airbus, CDU for Boeing, and a generic FMS
presentation for other compatible aircraft. It provides a structured reference
for entering route, departure, arrival and approach information manually into
the aircraft.

NaviXav does not attempt to automate unsupported aircraft performance
calculations.

### Moving Map

The integrated moving map can display the SimBrief route, SID, en-route, STAR
and approach segments, the current aircraft position and flown track, departure
and arrival airports, selected runway information, the ground taxi route,
several selectable styles, and route-fitting or aircraft-follow modes. All map
data is displayed inside the installed NaviXav desktop application.

### Official Chart Coverage

NaviXav connects directly to the following official national sources:

- France: SIA eAIP
- Spain and the Canary Islands: ENAIRE AIP
- Netherlands: LVNL eAIP
- United States and covered territories: FAA d-TPP

Charts are downloaded only when requested and cached locally. Automatic minima
extraction is currently limited to recognised French SIA ILS CAT I chart
formats, and extracted values must always be reviewed and validated by the
user.

### Requirements

- Windows 10 or Windows 11, 64-bit
- Microsoft Flight Simulator 2024
- A SimBrief account and a previously generated SimBrief OFP
- Internet access for SimBrief data, map tiles, weather, official charts and
  update checks
- Microsoft Edge WebView2 Runtime

Python and a separate system-wide SimConnect installation are not required.
NaviXav includes its own application-private SimConnect client components and
communicates with the SimConnect service provided by Microsoft Flight
Simulator.

### Installation

1. Extract the downloaded Flightsim.to ZIP archive.
2. Run `NaviXav-Setup-1.4.14.exe`.
3. Follow the installation wizard.
4. Start NaviXav from the Windows Start menu or the optional desktop shortcut.
5. Open **Settings** and enter your SimBrief Pilot ID or username.
6. Start Microsoft Flight Simulator 2024.
7. Load a flight and wait for the MSFS connection indicator to turn green.

NaviXav is an external Windows desktop application. Do not install it in the
MSFS Community folder. The recommended installer checks whether Microsoft Edge
WebView2 Runtime is available and can install the official Microsoft component
when required.

A portable archive is also provided: extract it into a folder where you have
write access and run `NaviXav.exe`. WebView2 must already be installed.

### First Use

1. Create and generate a flight plan on SimBrief.
2. Start Microsoft Flight Simulator and load your flight.
3. Start NaviXav and open **Settings**.
4. Enter your SimBrief Pilot ID or username.
5. Import your latest generated SimBrief plan.
6. Review the suggested runways and terminal procedures.
7. Validate all important information before entering it into the aircraft.

A demonstration mode is also available for discovering the interface without an
active MSFS or SimBrief connection. It replays an entire flight from your plan
— taxi, take-off, climb, cruise, descent, approach, landing and arrival stand.

### Local Flight Summaries

NaviXav keeps only a concise local summary of completed flights. It does not
store a detailed replay or a permanent position history. Summaries can be
deleted at any time using the purge function and never leave the user's
computer.

### Privacy

NaviXav has no advertising telemetry and does not identify or profile its
users. User settings, the MSFS navigation cache, map preferences,
completed-flight summaries and rotating diagnostic logs all remain stored
locally. Diagnostic logs never contain the SimBrief Pilot ID, SimBrief username
or complete flight route.

The installed desktop application accesses the internet only to retrieve
selected aviation data — SimBrief flight plans, map tiles, official charts,
weather information and update availability. These are outbound requests made
by the installed Windows application; NaviXav is not delivered or operated as
an online web application.

### Freeware

NaviXav is completely free. No feature, update or content is locked behind a
payment. Any financial support offered by users is entirely voluntary and
provides no exclusive functionality or priority access.

### Known Limitations

- Microsoft Flight Simulator 2020 compatibility is not currently claimed.
- A flight must be fully loaded in MSFS before live SimConnect data becomes
  available.
- A SimBrief OFP must already have been generated before NaviXav can retrieve
  it.
- Procedure suggestions may differ from current ATIS information or ATC
  clearances.
- Ground taxi guidance depends on the taxiway data published by the simulator
  for each airport, and is advisory only — it is not an ATC clearance.
- Official chart availability is limited to the supported national sources
  listed above, and automatic minima extraction is not available for every
  chart format.
- Some third-party aircraft may expose incomplete or aircraft-specific
  SimConnect values.
- Internet-dependent features remain unavailable while offline, although
  previously cached local navigation information may remain available.
- The application is unsigned, so Windows SmartScreen may warn on first run.

### Support

NaviXav is developed by Xavier BEGUE (xalacaga).

Project and issue tracker: `https://github.com/xalacaga/NaviXav`

When reporting an issue, please include the NaviXav version, your Windows
version, your Microsoft Flight Simulator version, the aircraft type and a clear
description of the problem.

Never publish your SimBrief Pilot ID, username or other personal information in
a public comment.

### License and Credits

The current NaviXav source is available under the PolyForm Noncommercial
License 1.0.0. Commercial use requires a separate written licence. Git releases
tagged v1.4.12 and earlier remain available under Apache 2.0. Copyright 2026
Xavier BEGUE.

Microsoft Flight Simulator, MSFS, SimConnect, Microsoft Edge and WebView2 are
trademarks of the Microsoft group of companies. Map data and tiles are provided
by OpenStreetMap contributors. Runtime aeronautical information and official
charts remain subject to the terms and conditions of their respective
providers.

NaviXav is an independent project and is not affiliated with or endorsed by
Microsoft, Navigraph, SimBrief, national AIS authorities or the FAA.

## Version 1.4.14 Changelog

- Added a **Weather** tab with departure, cruise, arrival and alternate
  briefings, decoded METAR, summarised TAF and operational warnings.
- Added a **Dispatch** tab comparing OFP forecast figures with live fuel,
  weight, time and distance from the simulator.
- Dispatch tracking now survives closing the application during a flight.
- Added a flight-event timeline with phase ribbon, stable configuration events
  and language-aware replay from the local logbook.
- Named taxiways classified by MSFS as generic paths now remain visible on the
  ground chart; only unnamed secondary links stay hidden by default.
- Faster first plan preparation by reusing validated SimBrief navlog
  coordinates and published procedure links before querying MSFS Facilities.
- Fixed approach and en-route lines jumping to same-named waypoints hundreds of
  miles away.
- Fixed route drawing across the antimeridian and for flights returning to
  their departure airport.
- Removed the misleading runway-versus-wind warning in light or variable wind.
- On narrow mobile screens, replaced the overflowing `MSFS connected` text with
  a compact accessible status dot.
- Phones and tablets can now select the display language from the mobile
  toolbar.
- Fixed Airbus flap detents, generic-aircraft flap indications and flight-level
  calculation from pressure altitude.
- Constraints, official charts, MCDU chart guidance, taxi labels, connection
  messages and error banners now follow the selected language.
- The **Dispatch** and **Aircraft** tabs now follow the selected language.
- The application and installer carry full publisher information and are
  shipped uncompressed, removing antivirus heuristic warnings.
- Documentation now defaults to English.

## Suggested Screenshot Set

Flightsim.to requires at least two relevant screenshots. Use original
screenshots captured from your own installation, preferably at 1920 × 1080.
Show NaviXav running alongside or over your own MSFS session so the images
clearly demonstrate the application in action.

1. **Main IFR Overview**
   Caption: `Complete IFR overview with SimBrief route, runway and procedure suggestions.`

2. **Weather Briefing**
   Caption: `Departure, cruise, arrival and alternate weather with decoded METAR and TAF summary.`

3. **Dispatch Monitoring**
   Caption: `Live fuel, weights, time and distance compared with the SimBrief dispatch figures.`

4. **Live Flight Tracking**
   Caption: `Real-time MSFS flight tracking with next waypoint, constraints and vertical guidance.`

5. **Ground Taxi Guidance**
   Caption: `Taxi route from stand to runway with holding points and turn-by-turn callouts.`

6. **Moving Map**
   Caption: `Moving map showing the SimBrief route, terminal procedures and the aircraft track.`

7. **Aircraft-Adaptive MCDU/CDU Card**
   Caption: `Aircraft-adaptive flight-management card for Airbus, Boeing and other aircraft types.`

8. **Official Charts**
   Caption: `Official national AIS chart viewer integrated into the flight preparation workflow.`

Recommended thumbnail text:

`NaviXav — IFR Planning & Live Flight Assistant`

Keep promotional text limited and do not cover important interface elements.
Use only images and logos for which you hold the necessary rights.

## Files to Upload

### Primary File

`NaviXav-1.4.14-FlightsimTo-Installer.zip`

Label:

`Recommended Windows Installer`

Description:

`Recommended installation for Windows 10/11 64-bit. Includes the NaviXav setup program and installation notes. Do not install in the MSFS Community folder.`

### Optional Secondary File

`NaviXav-1.4.14-windows-x64-portable.zip`

Label:

`Portable Version`

Description:

`Portable Windows version. Extract the complete archive and run NaviXav.exe. Microsoft Edge WebView2 Runtime must already be installed.`

Both files are complete and can be used independently. Do not upload checksum
files as separate download options.

## Upload Checklist

- [ ] Use the title exactly as written above and preserve title case.
- [ ] Select **Utilities / Miscellaneous**.
- [ ] Select **Microsoft Flight Simulator 2024** only.
- [ ] Set version to **1.4.14**.
- [ ] Upload the installer ZIP as the primary file.
- [ ] Optionally upload the portable ZIP as a secondary independent file.
- [ ] Paste the full English description, including the development
      transparency and antivirus sections.
- [ ] Paste the version 1.4.14 changelog.
- [ ] Add at least two original, relevant screenshots of 512 × 512 px or
      larger.
- [ ] Add a clear thumbnail without clickbait wording.
- [ ] Scan every uploaded archive with VirusTotal and record the result. A
      lone generic machine-learning verdict on an unsigned build is expected;
      submit it to the vendor rather than blocking the release.
- [ ] Confirm that each ZIP extracts and launches correctly on a clean Windows
      user account.
- [ ] Confirm that `LICENSE`, `COMMERCIAL_LICENSE.md`, `NOTICE`,
      `THIRD_PARTY_NOTICES` and the bundled third-party licence texts are
      present.
- [ ] Do not add an external download link to the Flightsim.to description.
- [ ] Do not create a new listing for future versions; update this listing
      through its Versioning tab.
- [ ] Review Flightsim.to's current upload rules immediately before
      submission.

## Suggested First Comment

Thank you for trying NaviXav. Please report issues with the application
version, your Windows version and your MSFS version. For privacy, never post
your SimBrief Pilot ID or username in a public comment.
