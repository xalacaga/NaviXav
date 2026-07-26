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

1. Download `NaviXav-Setup-0.1.0.exe`.
2. Run the installer.
3. Review the prerequisite check page.
4. Select the installation folder and choose **Install**.
5. Start NaviXav from the Start menu or the optional desktop shortcut.

A portable archive is also available:
`NaviXav-0.1.0-windows-x64-portable.zip`. Extract it and run `NaviXav.exe`.
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

## Privacy

NaviXav has no central account and sends no telemetry. It contacts only the
services needed for SimBrief, OpenStreetMap and the requested official
publications. User settings, caches and flight history stay on the computer.
