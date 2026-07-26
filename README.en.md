# NaviXav

**Documentation:** [Français](README.md) · English · [Deutsch](README.de.md) ·
[Español](README.es.md) · [Italiano](README.it.md) ·
[Português](README.pt.md) · [Nederlands](README.nl.md) ·
[Polski](README.pl.md)

NaviXav is a local IFR flight assistant for Microsoft Flight Simulator. It
retrieves the latest SimBrief OFP, completes terminal information with data
read from the simulator, and presents everything required for flight
preparation and MCDU entry.

NaviXav runs in its own responsive Windows window using Microsoft WebView2.
It does not open an external browser. Its private local service listens only
on `127.0.0.1`; settings, navigation data, charts and caches remain on the
computer.

> NaviXav is intended for flight simulation only. Always verify its output
> against current official publications and applicable ATC instructions.

## Main features

- automatically retrieves the latest SimBrief flight plan;
- supports a SimBrief Pilot ID or username configured in the interface;
- displays the complete route and highlights aircraft progress;
- selects and explains runways, SID, STAR, transitions and approach;
- shows altitude/speed constraints, transition altitude/level, ILS data,
  interception and missed-approach altitudes;
- provides aircraft, dispatch, fuel, weight and MCDU-entry information;
- displays QNH below wind information;
- follows MSFS in real time and records a local replayable flight track;
- displays MSFS ground speed (GS) and indicated airspeed (IAS);
- draws the route over an OpenStreetMap base map;
- gives direct access to official airport PDF charts for the current departure
  and arrival;
- offers an official-chart overlay only when a validated georeference exists;
- obtains navigation and procedure data directly from MSFS, without
  Little Navmap, Navigraph or EUROCONTROL.

## Requirements

- 64-bit Windows 10 or Windows 11;
- Microsoft Flight Simulator for live and navigation data;
- a SimBrief account with an already generated OFP;
- Internet access for SimBrief, map tiles and official AIS/FAA publications.

Python, application libraries and the autonomous NaviXav SimConnect connector
are included. The installer checks Microsoft WebView2 and installs it only when
it is missing.

### SimConnect

NaviXav never installs, registers, reinstalls or replaces system SimConnect.
It carries a modern private `SimConnect.dll` inside its own application
directory. Any SimConnect installation already present on the computer remains
untouched. The private connector communicates with the SimConnect service
provided by MSFS, so the simulator must be running to receive live data.

## Windows installation

1. Download `NaviXav-Setup-<version>.exe` from the latest
   [GitHub Release](https://github.com/xalacaga/NaviXav/releases/latest).
2. Run the installer.
3. Review the prerequisite check page.
4. Select the installation folder and choose **Install**.
5. Start NaviXav from the Start menu or the optional desktop shortcut.

A portable archive is also available:
`NaviXav-<version>-windows-x64-portable.zip`. Extract it and run `NaviXav.exe`.
Use the complete installer on computers where WebView2 may be missing.

## First configuration

Open **Settings** in the top-right corner:

1. select the interface language;
2. enter the SimBrief Pilot ID or username;
3. choose the METAR source;
4. set approach, runway and aircraft preferences;
5. save the settings.

The language applies immediately and is stored locally. French, English,
German, Spanish, Italian, Portuguese, Dutch and Polish are provided.
Aviation identifiers, METAR and MCDU notation remain international.

At startup NaviXav automatically retrieves the latest available SimBrief OFP.
Flight-plan generation remains on the SimBrief website.

## Official charts

The **Official charts** tab proposes current-flight documents for the departure
and arrival. Supported sources include French SIA, Spanish ENAIRE, Dutch LVNL
and US FAA d-TPP, subject to the availability of their public services.

PDFs can be opened inside NaviXav. The overlay button is hidden when automatic
alignment has not been validated, preventing a visually misleading overlay.
All operational values must still be checked on the official chart.

## Run from source

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

The launcher creates an isolated `.venv`, installs missing dependencies and
opens the dedicated NaviXav window.

## Build a distribution

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

The build machine requires Python 3.11 or later, the modern MSFS SimConnect SDK,
PyInstaller and Inno Setup. The script checks prerequisites, runs the automated
tests and creates the installer, portable archive and SHA-256 checksums in
`release\`.

## Troubleshooting

- **No plan:** check the Pilot ID/username, generate an OFP in SimBrief and
  verify Internet access.
- **MSFS indicator is red:** start MSFS, fully load a flight and wait a few
  seconds. Reinstall NaviXav if its private DLL was quarantined.
- **Window does not open:** run the complete installer to repair WebView2 and
  review `%LOCALAPPDATA%\NaviXav\logs\navixav.log`.
- **Port 8765 is occupied:** close the previous NaviXav instance. The **Quit**
  button and window close action normally release the process and port.

The diagnostic log is stored at
`%LOCALAPPDATA%\NaviXav\logs\navixav.log`. It records startup/shutdown, errors,
slow API calls and SimBrief/MSFS/cache timings, but never the Pilot ID,
username or complete route. It rotates at 2 MB and keeps five backups.

## Detailed operation

### Flight-plan completion

NaviXav retrieves the latest generated SimBrief OFP at startup. It reads the
departure, destination, alternate, route, aircraft, fuel, weights, cruise
level and embedded METAR. Flight-plan generation itself remains on SimBrief.
Terminal procedures are completed from MSFS data and may be overridden in the
interface when ATIS or ATC assigns another runway or procedure.

The departure and arrival summary can be collapsed. The route strip shows
runway, SID, transitions, en-route points, STAR and approach. The active route
point changes colour as the aircraft progresses.

### Guidance, approach and MCDU

The flight panel shows distance, bearing, desired altitude, next constraint,
ground speed (GS) and indicated airspeed (IAS). Approach information includes
ILS frequency and course when available, glide angle, intercept altitude,
threshold elevation, minima and missed-approach altitude. These values assist
simulation setup and never replace the current chart or ATC clearance.

The MCDU sheet groups the values normally entered on INIT, F-PLN, RAD NAV,
PERF TAKEOFF and PERF APPR pages: origin/destination, company route, flight
number, cost index, cruise level, runways, SID/STAR, transitions, approach,
ILS, QNH, wind, temperature, minima and take-off reference data when known.

### Map and live tracking

The map draws the complete SimBrief route over OpenStreetMap. SID, en-route,
STAR and approach segments use distinct styles. Airport ground geometry is
filtered by zoom to avoid unreadable taxiway and parking-line clutter. The
aircraft can be followed live, centred manually or shown with the whole route.
The local flight recorder keeps a replayable track and does not upload it.

### Official AIS documents

The current flight’s departure and arrival are selected by default. Airport
and approach PDFs are obtained from supported national AIS sources: SIA
France, ENAIRE Spain, LVNL Netherlands and FAA d-TPP for the United States.
Availability depends on each authority’s public catalogue.

PDFs are displayed in the dedicated interface. An **Official overlay** button
is offered only for a chart with a validated georeferencing sidecar. A normal
PDF is still available for reading but is never overlaid approximately.

### Local data and cache

Settings are stored in
`%LOCALAPPDATA%\NaviXav\user_settings.json`, navigation data in
`%LOCALAPPDATA%\NaviXav\navixav.sqlite`, downloaded documents under the local
cache and logs under `%LOCALAPPDATA%\NaviXav\logs`. The first request for a new
airport or procedure can take several tens of seconds while the MSFS cache is
filled. Later requests reuse the local database.

## Automatic updates and Releases

At startup NaviXav checks the latest public Release of
`xalacaga/NaviXav`. If a newer semantic version exists, an **Update** button
appears. Installation starts only after confirmation. The installer is
downloaded to `%LOCALAPPDATA%\NaviXav\updates`, verified against the SHA-256
digest published by GitHub, then launched while NaviXav closes cleanly. A
network or GitHub outage never prevents normal startup.

The repository is public for read access: anyone can inspect the source and
download Releases without a GitHub account, while write access remains limited
to authorised collaborators.

Versions use `MAJOR.MINOR.PATCH`. Conventional commits drive the automatic
bump: `feat:` for minor, `fix:` for patch, and `BREAKING CHANGE` or `!:` for
major. Other changes default to patch. Release notes are generated into
`RELEASE_NOTES.md` and accumulated in `CHANGELOG.md`.

```powershell
.\scripts\prepare_release.ps1 -Bump auto
.\scripts\publish_release.ps1 -Bump auto
```

The publishing script requires a clean repository and an authenticated GitHub
CLI. It tests and builds NaviXav, commits the version files, creates and pushes
the tag, then publishes the installer, portable archive, SHA-256 files and
release notes.

## Command-line and maintenance commands

```powershell
# Dedicated desktop window
.\NaviXav.bat

# Local server without a window, for diagnostics
.\.venv\Scripts\python.exe -m navixav.desktop --no-open

# Build and validate Windows distribution
.\scripts\build_windows.ps1

# Run tests without a live MSFS instance
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```

## Privacy

NaviXav has no central account and sends no telemetry. It contacts only the
services needed for SimBrief, OpenStreetMap and the requested official
publications. User settings, caches and flight history stay on the computer.
