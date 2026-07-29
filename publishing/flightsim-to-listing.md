# Flightsim.to Publication Pack — NaviXav 0.12.0

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

0.12.0

**Release status**

Freeware

**Suggested tags**

- IFR
- SimBrief
- SimConnect
- Flight Planning
- Flight Tracking
- MCDU
- CDU
- Moving Map
- Navigation
- MSFS 2024
- Utility

**Short summary**

Local Windows IFR assistant combining the latest SimBrief OFP with live MSFS
data, terminal procedures, flight tracking, MCDU/CDU guidance and official
charts.

## Full English Description

### About NaviXav

NaviXav is a free, open-source IFR flight assistance application for Microsoft
Flight Simulator 2024. It combines your latest SimBrief Operational Flight
Plan with navigation and real-time aircraft data obtained directly from MSFS
through SimConnect.

The application runs in its own responsive Windows window. It is designed to
keep the information needed for flight preparation and flight monitoring in
one place, without requiring a separate browser during normal use.

> NaviXav is intended for flight simulation only. Always verify operational
> information against current official publications and applicable ATC
> instructions.

### Main Features

- Retrieves the latest SimBrief OFP using a Pilot ID or username.
- Displays the complete route, dispatch information, weights, fuel, alternate
  and flight time.
- Suggests departure and arrival runways, SID, STAR, transitions, approach and
  VIA using MSFS navigation data.
- Displays altitude and speed constraints, transition altitude/level, ILS
  frequency, intercept altitude and missed-approach altitude.
- Tracks the aircraft in real time using SimConnect.
- Shows flight phase, IAS, ground speed, next waypoint, lateral deviation,
  remaining distance, Top of Descent and vertical-profile guidance.
- Monitors gear, flaps, speedbrakes, parking brake, exterior lights, altimeter
  setting, autopilot modes, selected altitude, fuel and wind.
- Automatically clears and re-arms configuration alerts after a correction
  becomes stable.
- Provides an aircraft-adaptive Airbus MCDU, Boeing CDU or generic FMS card.
- Includes a moving map with route segments, procedures, aircraft position,
  flown track and several selectable map styles.
- Provides official national AIS charts where supported.
- Stores only a local summary of completed flights; summaries can be purged at
  any time.
- Includes a Demo mode for exploring the interface without MSFS or SimBrief.
- Provides English, French, German, Spanish, Italian, Portuguese, Dutch and
  Polish interfaces.

### Official Chart Coverage

NaviXav connects directly to the following official sources:

- France: SIA eAIP
- Spain and the Canary Islands: ENAIRE AIP
- Netherlands: LVNL eAIP
- United States and covered territories: FAA d-TPP

Charts are downloaded only when requested and cached locally. Automatic minima
extraction is currently limited to recognised French SIA ILS CAT I chart
formats. Extracted values always require user validation.

### Requirements

- Windows 10 or Windows 11, 64-bit
- Microsoft Flight Simulator 2024
- A SimBrief account and a previously generated OFP for SimBrief functions
- Internet access for SimBrief, map tiles, update checks and official charts
- Microsoft Edge WebView2 Runtime

The recommended installer checks WebView2 and can install the official runtime
if it is missing. Python and a separate SimConnect installation are not
required.

### Installation

#### Recommended Installer

1. Extract the downloaded Flightsim.to ZIP archive.
2. Run `NaviXav-Setup-0.12.0.exe`.
3. Follow the installation wizard.
4. Start NaviXav from the Windows Start menu or the optional desktop shortcut.
5. Open **Settings** and enter your SimBrief Pilot ID or username.
6. Start MSFS, load a flight and wait for the MSFS connection indicator to
   turn green.

NaviXav is an external Windows application. Do not install it in the MSFS
Community folder.

#### Portable Version

1. Extract the portable ZIP into a folder where you have write access.
2. Run `NaviXav.exe`.

If WebView2 is not already installed, use the recommended installer first.

### First Use

1. Generate a flight plan on SimBrief.
2. Start MSFS and load a flight.
3. Start NaviXav.
4. Save your SimBrief Pilot ID or username in **Settings**.
5. Review the suggested runway and terminal procedures.
6. Validate all important information before entering it into the aircraft.

The **Create a SimBrief plan** button opens the official SimBrief flight-plan
editor. SimBrief does not provide NaviXav with a supported method for importing
and modifying an already prepared plan automatically.

### Privacy

NaviXav has no advertising telemetry and does not identify or profile users.
Settings, the MSFS navigation cache and completed-flight summaries remain on
the computer.

The application connects externally only when required for features selected
by the user, including SimBrief, map tiles, official charts, weather and update
checks. Diagnostic logs do not contain the SimBrief Pilot ID, username or full
route.

### Known Limitations

- Microsoft Flight Simulator 2020 compatibility is not currently claimed.
- A flight must be fully loaded in MSFS before live SimConnect data becomes
  available.
- A SimBrief OFP must already have been generated before NaviXav can retrieve
  it.
- Procedure suggestions may differ from current ATIS information or ATC
  clearances.
- Official chart availability is limited to the supported national sources
  listed above.
- Automatic minima extraction is not available for every chart format.
- Internet-dependent features remain unavailable while offline; previously
  cached local data can still be used.

### Support and Source Code

NaviXav is developed by Xavier BEGUE (`xalacaga`).

Project and issue tracker:
`https://github.com/xalacaga/NaviXav`

Please include the NaviXav version, Windows version, simulator version and a
clear description when reporting an issue. Do not post your SimBrief Pilot ID
or other personal information.

### License and Credits

NaviXav is distributed under the Apache License 2.0.

Copyright 2026 Xavier BEGUE (xalacaga).

Microsoft Flight Simulator, MSFS, SimConnect, Microsoft Edge and WebView2 are
trademarks of the Microsoft group of companies. Map data and tiles are
provided by OpenStreetMap contributors. Runtime aeronautical information and
charts remain subject to the terms of their respective providers.

NaviXav is an independent project and is not affiliated with or endorsed by
Microsoft, Navigraph/SimBrief, national AIS authorities or the FAA.

## Version 0.12.0 Changelog

- Simplified the local journal to completed-flight summaries only.
- Added the ability to purge all locally stored flight summaries.
- Removed takeoff-performance entries that cannot be automated safely.
- Adapted the flight-management card to Airbus MCDU, Boeing CDU and generic
  FMS layouts according to aircraft type.
- Alerts now clear and re-arm automatically after a stable correction.
- Added direct access to the official SimBrief flight-plan creation page.
- Improved flight tracking, navigation presentation and application
  reliability.
- Automatic application updates remain protected by SHA-256 verification and
  explicit user confirmation.

## Suggested Screenshot Set

Flightsim.to requires at least two relevant screenshots. Use original
screenshots captured from your own installation, preferably at 1920 × 1080.
Show NaviXav running alongside or over your own MSFS session so the images
clearly demonstrate the application in action.

1. **Main IFR Overview**  
   Caption: `Complete IFR overview with SimBrief route, runway and procedure suggestions.`

2. **Live Flight Tracking**  
   Caption: `Real-time MSFS flight tracking with next waypoint, constraints and vertical guidance.`

3. **Moving Map**  
   Caption: `Moving map showing the SimBrief route, terminal procedures and the aircraft track.`

4. **Aircraft-Adaptive MCDU/CDU Card**  
   Caption: `Aircraft-adaptive flight-management card for Airbus, Boeing and other aircraft types.`

5. **Aircraft Configuration and Alerts**  
   Caption: `Live aircraft configuration monitoring with automatically clearing alerts.`

6. **Official Charts**  
   Caption: `Official national AIS chart viewer integrated into the flight preparation workflow.`

Recommended thumbnail text:

`NaviXav — IFR Planning & Live Flight Assistant`

Keep promotional text limited and do not cover important interface elements.
Use only images and logos for which you hold the necessary rights.

## Files to Upload

### Primary File

`NaviXav-0.12.0-FlightsimTo-Installer.zip`

Label:

`Recommended Windows Installer`

Description:

`Recommended installation for Windows 10/11 64-bit. Includes the NaviXav setup program and installation notes. Do not install in the MSFS Community folder.`

### Optional Secondary File

`NaviXav-0.12.0-windows-x64-portable.zip`

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
- [ ] Set version to **0.12.0**.
- [ ] Upload the installer ZIP as the primary file.
- [ ] Optionally upload the portable ZIP as a secondary independent file.
- [ ] Paste the full English description.
- [ ] Paste the version 0.12.0 changelog.
- [ ] Add at least two original, relevant screenshots of 512 × 512 px or
      larger.
- [ ] Add a clear thumbnail without clickbait wording.
- [ ] Scan every uploaded archive with VirusTotal and confirm zero detections.
- [ ] Confirm that each ZIP extracts and launches correctly on a clean Windows
      user account.
- [ ] Confirm that `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES` and the bundled
      third-party licence texts are present.
- [ ] Do not add an external download link to the Flightsim.to description.
- [ ] Do not create a new listing for future versions; update this listing
      through its Versioning tab.
- [ ] Review Flightsim.to's current upload rules immediately before
      submission.

## Suggested First Comment

Thank you for trying NaviXav. Please report issues with the application
version, your Windows version and your MSFS version. For privacy, never post
your SimBrief Pilot ID or username in a public comment.

