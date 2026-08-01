# NaviXav

**Documentation:** [Français](README.md) · English ·
[Deutsch](README.de.md) · [Español](README.es.md) ·
[Italiano](README.it.md) · [Português](README.pt.md) ·
[Nederlands](README.nl.md) · [Polski](README.pl.md)

NaviXav is a local IFR flight assistance application for Microsoft Flight
Simulator. It retrieves the latest SimBrief flight plan, completes the terminal
information using simulator data, and presents everything in an interface
designed for flight preparation and MCDU entry.

The application has its own Windows window. Its interface is rendered by
Microsoft WebView2 and communicates only with a local service bound to
`127.0.0.1`. No external browser is opened unless the user clicks **Create a
SimBrief plan** to open the official editor. Settings, the navigation database
and caches all stay on the computer.

The window is fully resizable. The interface rearranges its panels, controls,
tabs and map height according to the space available, down to a minimum size of
720 × 560 pixels.

> NaviXav is intended for flight simulation only. The information displayed
> must be checked against official publications and applicable ATC
> instructions.

## Features

### SimBrief flight plan

- automatic retrieval of the latest OFP at startup;
- support for either the SimBrief Pilot ID or username;
- display of the complete route, from origin to destination;
- highlighting of the next route point based on the aircraft's actual position,
  with already-passed points dimmed;
- weights, fuel, flight time, alternate and dispatch data;
- aircraft information, registration and declared equipment.

### IFR preparation

NaviXav completes and presents:

- the departure runway and the arrival runway;
- the SID and its transition;
- the STAR and its transition;
- the approach and its VIA;
- the ILS frequency and identifier;
- altitude and speed constraints;
- the transition altitude and transition level;
- the approach intercept altitude;
- the missed approach altitude;
- the rationale and confidence level behind every choice.

The **Departure · Route · Arrival** blocks can be collapsed to free up space in
the interface.

### Flight tracking

The **Flight tracking** tab uses the real-time MSFS position to display:

- the automatically detected flight phase;
- the ground speed (GS) and indicated airspeed (IAS) reported by MSFS;
- the next point and its distance;
- the lateral deviation from the active segment;
- the remaining distance;
- the next altitude or speed constraint;
- the vertical rate required to meet that constraint;
- the Top of Descent and an indicative descent rate on a 3° path;
- the deviation from the planned vertical profile.

#### Aircraft configuration

The **Aircraft configuration** block reads the landing gear, flaps,
speedbrakes, parking brake and the seven exterior lights straight from MSFS,
together with the altimeter setting, the autopilot modes, the selected
altitude, the fuel on board and the actual wind. Units are requested from the
simulator and never recomputed locally.

#### Visual alerts

NaviXav monitors that configuration and flags anything left out: gear not down
on approach, flaps or speedbrakes not configured, strobes or landing lights
off, parking brake still set, QNH or standard setting not selected when
crossing the transition altitude, selected altitude above the next constraint,
ILS frequency different from the planned one, anti-ice off in icing conditions,
fuel below the final reserve.

Three safeguards keep false alarms away:

- rules that depend on retractable gear, flaps or speedbrakes are only
  evaluated once the simulator confirms the aircraft has them;
- a condition must hold for a few seconds before an alert is raised, which
  removes the flicker when a threshold is crossed;
- alerts are suspended whenever the simulator runs at an accelerated rate.

Each alert clears and re-arms automatically once the correction is stable; a
click can still acknowledge it immediately. A
`MASTER CAUTION` or `MASTER WARNING` pill summarises the situation, and the
whole system can be switched off from the panel. Blinking, reserved for
critical alerts, is dropped when the system asks for reduced motion.

The local journal keeps no detailed track: after landing, it stores only a
flight summary (duration, distance and maximum altitude). All summaries can be
purged from the interface, and no flight data is sent to any external service.

### MCDU card

The **MCDU card** tab adapts its pages to the aircraft type: Airbus MCDU,
Boeing CDU, or a generic FMS for other aircraft. It does not offer takeoff
performance values that cannot be automated:

- `FROM/TO`, flight number and alternate;
- Cost Index and cruise level;
- ZFW, block, taxi, trip and reserve fuel;
- runway, SID, transition and transition altitude;
- `VIA/TO` route;
- STAR, transition, approach and VIA;
- QNH, temperature, wind, ILS frequency and final course;
- RADIO or BARO minima and RVR.

### Direct connection to MSFS

NaviXav uses SimConnect to:

- detect the presence of the simulator;
- show a green or red indicator in the top bar;
- track the aircraft position in real time;
- read altitude, height above ground, heading, ground speed and vertical speed;
- retrieve airports, runways, procedures, waypoints and radio navigation aids;
- progressively build a local database in `data/navixav.sqlite`.

The simulator must be running with a flight loaded in order to retrieve new
data. Information already cached remains available offline.

### Map

The map includes:

- an OpenStreetMap background;
- the SimBrief route drawn with its waypoints;
- distinct colours for the SID, the enroute portion, the STAR and the approach;
- the runways and the selected runway;
- the aircraft position and heading;
- a trail of the movement;
- an automatic follow mode;
- zoom, panning and fitting to the airport or the route;
- the complete track actually flown from departure to arrival;
- a customisable flight-track colour;
- a choice between OpenStreetMap Standard, OpenTopoMap, CartoDB Positron
  (light) and CartoDB Dark Matter (dark, cockpit), straight from the map bar or
  from Settings.

### Ground taxiing

The **Taxiing** tab provides a dedicated airport diagram, separate from the
flight map and built only from native MSFS facilities:

- the canvas fills the available area and remains usable in compact windows;
- a dark aviation background with a metric grid and north arrow provides scale
  and orientation without the noise of a road map;
- runways, primary taxiways, stands and the aircraft are visually prioritised;
- secondary taxiways and stand access paths are hidden by default; the
  **Secondary** button reveals them on demand;
- on departure, when the aircraft is on the ground within 180 m of a stand,
  NaviXav automatically proposes a route from that stand to the selected runway;
- clicking another stand immediately replaces the proposal; on arrival, the
  destination stand remains a manual choice;
- the route separates travelled and remaining portions and shows only useful
  names, hold-short points, the next manoeuvre and remaining distance;
- after a deviation, the route is recalculated from the aircraft’s real position.

SimConnect parking paths are used only to attach stands to the taxi network.
They can never become shortcuts between taxiways, preventing artificial lines
across runways.

### Official national AIS charts

NaviXav queries national authority publications directly, without going through
EUROCONTROL/EAD:

- France: SIA eAIP (`LF`);
- Spain and the Canary Islands: ENAIRE AIP (`LE`, `GC`, `GE`);
- Netherlands: LVNL eAIP (`EH`);
- United States and covered territories: FAA d-TPP.

For these aerodromes, NaviXav can:

- present every departure and arrival PDF in the **Official charts** tab, sorted
  by type;
- open each document inside the interface or separately;
- select by default the SID, STAR or approach matching the current flight;
- automatically find the approach chart matching the selected runway and
  approach type;
- download on demand only the PDFs actually consulted;
- keep the publication in the local AIRAC cache;
- display the official chart in the MCDU card;
- extract SIA ILS CAT I minima when the format is recognised;
- propose the DA, DH and RVR before validation.

Extracted values are never applied silently: they must be validated in the
interface. The **Official overlay** button is offered only for a document with
validated georeferencing. It follows the chart selection: the departure PDF can
only be overlaid on the departure, and the arrival PDF only on the arrival.
This rule is identical for every source.

A country is only added to the automatic list after direct, stable access to
its official PDFs has been validated. A missing source is therefore never
silently replaced by a third-party aggregator.

## Requirements

- Windows 10 or Windows 11, 64-bit;
- Microsoft WebView2 Runtime, installed automatically by the installer;
- Microsoft Flight Simulator for data and real-time tracking;
- a SimBrief account with a generated OFP;
- an Internet connection for SimBrief, the map background and the national AIS
  or FAA publications.

The installer includes Python, the libraries, pywebview, NaviXav's standalone
SimConnect connector and the signed Microsoft WebView2 bootstrapper. None of
these tools need to be installed separately. MSFS is not required to try the
Demo mode or to consult data already saved.

SimConnect is never installed or reinstalled into Windows by NaviXav. The
application ships a private copy of the modern DLL in its own folder. If the
machine already has SimConnect, its installation, version and settings are
neither replaced nor modified. This private DLL talks to the MSFS SimConnect
service: only the simulator needs to be installed and running to receive live
data.

### Interface languages

The language is chosen in **Settings**, applies immediately and is remembered on
the computer. NaviXav provides French, English, German, Spanish, Italian,
Portuguese, Dutch and Polish interfaces. Aeronautical abbreviations, procedure
identifiers, METAR and MCDU values deliberately remain in their international
notation.

## Quick installation on Windows

1. Download the `NaviXav-Setup-<version>.exe` file from the latest
   [GitHub Release](https://github.com/xalacaga/NaviXav/releases/latest).
2. Run the installer.
3. Check the prerequisites verification page.
4. Keep or change the proposed folder, then click **Install**.
5. Start NaviXav from the Start menu or the optional desktop shortcut.

The installer checks Microsoft WebView2 and installs it automatically if
missing. Installation is done for the current user and normally does not
require administrator rights.

A portable archive is also available: extract
`NaviXav-<version>-windows-x64-portable.zip`, then run `NaviXav.exe`. On a
machine without WebView2, use the full installer first.

### From source

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

On first launch, the script:

1. looks for Python;
2. creates the `.venv` virtual environment;
3. installs NaviXav and its dependencies;
4. starts the private local service;
5. opens the interface in the NaviXav window.

Subsequent launches reuse the environment already installed.

### Building a distribution

From PowerShell, in the project folder:

```powershell
.\scripts\build_windows.ps1
```

The script:

1. checks 64-bit Windows, Python and the SimConnect SDK;
2. installs any missing build tools;
3. downloads the official WebView2 bootstrapper and verifies its Microsoft
   signature;
4. runs the tests excluding live MSFS integration;
5. produces the installer, the portable archive and their SHA-256 checksums in
   `release\`.

The SimConnect SDK mentioned in step 1 concerns only the machine that builds
NaviXav. It is not installed on user machines.

### Distribution files

After a successful build:

| File | Purpose |
|---|---|
| `release\NaviXav-Setup-<version>.exe` | recommended Windows installer |
| `release\NaviXav-<version>-windows-x64-portable.zip` | portable version |
| `release\*.sha256` | checksums of the distributed files |

The `release\` folder is deliberately ignored by Git. The executables are build
artefacts to be published in a GitHub Release, not sources to be versioned.

## Manual installation

From PowerShell, in the project folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m navixav.desktop
```

This command opens the NaviXav window. To diagnose the local service without a
window:

```powershell
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
```

The service then remains reachable only at `http://127.0.0.1:8765`.

## Configuration

Day-to-day configuration is done from the **Settings** button in the interface.

### SimBrief account

Fill in one of the two fields:

- **SimBrief Pilot ID**: the numeric identifier shown in the SimBrief account
  settings;
- **SimBrief username**: the account alias.

The Pilot ID is recommended. After saving, NaviXav immediately retrieves the
latest available OFP. On every subsequent startup, that last plan is loaded
automatically.

### Available settings

The interface also lets you configure:

- the METAR source;
- the approach preference order;
- the maximum tailwind component;
- the maximum crosswind component;
- the minimum runway length;
- the aircraft's RNP capability.

In the installed version, the values are kept in
`%LOCALAPPDATA%\NaviXav\user_settings.json`.

## First use

1. Generate a flight plan in SimBrief.
2. Start Microsoft Flight Simulator and load a flight.
3. Start NaviXav from the Start menu, or with `NaviXav.bat` in development
   mode.
4. Open **Settings** and save the SimBrief Pilot ID.
5. Wait for the latest OFP to load automatically.
6. Check the **MSFS connected** indicator in the top right.
7. Review the runway, SID, STAR and approach choices.
8. Consult the constraints and the official chart.
9. Validate the minima before copying them into the MCDU.

The **Complete the plan** button retrieves the latest OFP again after
generating or modifying a flight in SimBrief.

## Using the map

- **Map background**: shows or hides the selected open-source map.
- **Base-map picker**: switches straight from the map between OpenStreetMap
  Standard, OpenTopoMap, CartoDB Positron (light) and CartoDB Dark Matter
  (dark, cockpit). The choice is saved into the settings.
- **Settings**: offers the same base-map choice and the colour of the complete
  flight track.
- **Official overlay**: appears only for the georeferenced chart of the
  aerodrome currently displayed, and adjusts its opacity.
- **Full route**: frames the entire flight route.
- **Follow**: keeps the aircraft centred.
- **Fit**: frames the selected airport.
- **+ / −**: changes the zoom level.
- **Wheel**: zooms under the pointer.
- **Drag**: pans the map.

The airport buttons make it quick to switch between the departure and the
arrival aerodrome.

## Window and responsive display

### Phone and tablet access on the local network

Enable **Phone and tablet access** in **Settings**, save, then restart NaviXav.
Open the protected address shown on the PC from a phone or tablet connected to
the same Wi-Fi. The mobile interface provides live tracking, the map,
constraints, MCDU data, aircraft data and official charts. Settings, shutdown
and updates remain restricted to the PC. If Windows asks, allow NaviXav on
private networks only.

NaviXav adapts its interface automatically when resized:

- above 1100 px, the Departure, Route and Arrival cards can be shown side by
  side;
- below 1100 px, these cards move to a single column;
- below 980 px, the toolbar and map controls take the full available width;
- below 760 px, the tabs become scrollable, buttons are redistributed and
  tables remain readable horizontally;
- below 520 px, statistics and complex panels switch to a column layout.

The map listens for every window size change and recomputes its canvas
immediately. The minimum size of the native window is 720 × 560 pixels.

## Demo mode

The **Demo** switch loads a sample flight and simulates movement on the ground.
It lets you explore the interface without a SimBrief account or a simulator.

Demo mode is always disabled at startup so that NaviXav gives priority to the
latest SimBrief plan.

## Stopping the application

Use the **Quit** button in the top bar. NaviXav shuts the server down cleanly,
closes the window and the SimConnect connection, then releases port `8765`.
Closing the window directly produces the same result.

In `--no-open` diagnostic mode, `Ctrl+C` in the console also performs a normal
shutdown.

## Startup options

The Windows launcher accepts the following options:

```powershell
.\NaviXav.bat --port 9000
.\NaviXav.bat --no-open
```

- `--port` changes the local port;
- `--no-open` starts only the local service, for diagnostics.

The listening address deliberately stays fixed at `127.0.0.1`.

## Additional commands

NaviXav can also be used from PowerShell:

```powershell
# Show the latest SimBrief plan
.\.venv\Scripts\navixav.exe plan

# Generate a text MCDU card
.\.venv\Scripts\navixav.exe plan --mcdu

# Produce JSON output
.\.venv\Scripts\navixav.exe plan --json

# Import airports from MSFS
.\.venv\Scripts\navixav.exe import LFBO LFPO

# Examine the local database
.\.venv\Scripts\navixav.exe navdata

# Show an airport's information
.\.venv\Scripts\navixav.exe airport LFBO --runway 32R
```

## Local data

NaviXav uses the following locations:

| Location | Contents |
|---|---|
| `%LOCALAPPDATA%\NaviXav\user_settings.json` | configuration of the installed version |
| `%LOCALAPPDATA%\NaviXav\navixav.sqlite` | navigation database built from MSFS |
| `%LOCALAPPDATA%\NaviXav\cache\` | cached national AIS and FAA charts |
| `%LOCALAPPDATA%\NaviXav\webview\` | local storage of the WebView2 window |
| `%LOCALAPPDATA%\NaviXav\logs\navixav.log` | log of the installed version |
| `data\` and `.venv\` | development-mode data and environment |

This local data, the secrets and the caches are not meant to be versioned.

The log records startups and shutdowns, errors, slow API calls, SimBrief
retrieval times, MSFS completion times and cache fills. It records neither the
Pilot ID, nor the username, nor the complete route. Its size is capped at 2 MB
with five older versions kept (`navixav.log.1` to `navixav.log.5`).

On first access to an aerodrome or a procedure, the interface warns that the
MSFS cache is being filled and that the operation may take several tens of
seconds. Subsequent accesses reuse the local data.

## Git versioning

The source repository is intended to be hosted at:
`https://github.com/xalacaga/NaviXav.git`.

The `.gitignore` file excludes in particular:

- `.env`, user settings and local databases;
- `.claude/`, `CLAUDE.md`, `.codex/`, `AGENTS.md` and `CODEX.md`;
- Graphify data and `graphify-out/`;
- Python environments, test caches and build outputs;
- `dist\`, `build\` and `release\`.

Claude/Codex memories can therefore be maintained locally without being
published in the Git repository.

### Automatic updates

At startup, NaviXav queries only the latest public Release of the
`xalacaga/NaviXav` repository. If its version is higher than the installed one,
an **Update** button appears in the top bar. Installation starts only after the
user confirms.

The installer is downloaded to `%LOCALAPPDATA%\NaviXav\updates\`, then its
SHA-256 checksum is compared with the one published by GitHub. If the checksum
is missing or different, the file is deleted and never executed. A GitHub or
Internet outage blocks neither startup nor the flight functions.

The repository is publicly readable. A user can browse the code and download
Releases without a GitHub account, but only authorised collaborators can write
to the repository.

### Version and Release notes

The version follows the semantic format `MAJOR.MINOR.PATCH`. Conventional
commit messages automatically determine the next level:

- `feat:` normally produces a minor version;
- `fix:` produces a patch version;
- `BREAKING CHANGE` or `!:` produces a major version;
- other changes produce a patch version.

Prepare the version and its notes locally:

```powershell
.\scripts\prepare_release.ps1 -Bump auto
```

Publish the installer, the portable archive, their checksums and the notes in a
GitHub Release:

```powershell
.\scripts\publish_release.ps1 -Bump auto
```

The second script requires a clean repository and an authenticated GitHub CLI.
It runs the tests, builds the deliverables, creates the version commit and tag,
pushes `main` and the tag, then creates the GitHub Release. `CHANGELOG.md`
keeps the history and `RELEASE_NOTES.md` contains the current version's notes.

## Troubleshooting

### Port 8765 is already in use

A NaviXav instance is probably still open. Close its window or click **Quit** in
the interface. The executable detects an existing instance; if another
application occupies 8765, it automatically picks a free port between 8766 and
8775.

To identify the process:

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

It is also possible to start the application on another port:

```powershell
.\NaviXav.bat --port 9000
```

### The NaviXav window does not open

- run the full installer again so that it checks WebView2;
- make sure Windows and Microsoft Edge WebView2 Runtime are up to date;
- consult `%LOCALAPPDATA%\NaviXav\logs\navixav.log`;
- check that an antivirus is not blocking `NaviXav.exe` or the
  `msedgewebview2.exe` processes.

The portable archive cannot install WebView2 by itself. On a machine that does
not have this component, use `NaviXav-Setup-<version>.exe`.

### The MSFS indicator stays red

- check that the simulator is running;
- load a flight completely;
- wait a few seconds then click the indicator;
- run the installer again if the private copy of `SimConnect.dll` shipped with
  NaviXav has been deleted or quarantined by an antivirus.

### No SimBrief plan is loaded

- check the Pilot ID or username in **Settings**;
- generate an OFP on SimBrief before retrying the retrieval;
- check the Internet connection.

### An official chart is unavailable

- check that the ICAO prefix is covered by SIA, ENAIRE, LVNL or FAA;
- check the Internet connection;
- confirm that the runway and the approach have been determined;
- use manual entry of the minima if extraction is unavailable.

## Current limitations

- the procedure actually cleared may differ from the plan depending on the
  ATIS, the weather and ATC instructions;
- minima depend on the aircraft category, its equipment and operational
  conditions;
- automatic extraction of minima is limited to recognised SIA formats;
- a PDF without validated georeferencing remains readable, but cannot be used
  as an overlay;
- new MSFS data requires the simulator to be reachable.

Always confirm important information before entering it into the simulator.

## Architecture and privacy

- `navixav/desktop.py` manages the native window and the process lifecycle;
- `navixav/web/app.py` provides the FastAPI API bound only to `127.0.0.1`;
- `navixav/web/static/` contains the responsive HTML/CSS/JavaScript interface;
- `navixav/planner/` completes the IFR plan;
- `navixav/navdata/` builds and queries the database derived from MSFS;
- `navixav/live/` handles SimConnect tracking;
- `navixav/sia.py`, `navixav/faa.py` and `navixav/national_aip.py` handle the
  official publications.

The local service never listens on the external network. The SimBrief Pilot ID,
the preferences, the flight summaries and the cached PDFs stay on the machine. Only
the requests needed for SimBrief, OpenStreetMap, the weather and the official
AIS publications leave the computer.

## Licence

NaviXav is free software distributed under the
[Apache 2.0](LICENSE) licence.

Copyright 2026 Xavier BEGUE (xalacaga)

You may freely use, modify, redistribute and integrate NaviXav, including in a
commercial project. In return, the licence requires that you **credit the
author**:

- retain the copyright notice and a copy of the licence in any redistribution;
- retain the [NOTICE](NOTICE) file and its attribution content;
- **state prominently which files you have modified**, as required by
  section 4(b) of the licence.

The licence also grants a patent licence and excludes any warranty. Navigation
data, official charts and the map background are not covered by this licence:
they remain subject to their respective providers' terms, detailed in the
NOTICE file.

## Tests

The reproducible profile used to build the distribution is:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```

Tests marked `live_msfs` query a simulator that is actually running and are
therefore not part of the installer's automatic check.
