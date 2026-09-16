# NaviXav 1.7.3

Released on 2026-09-16.

## Added

- MSFS flight plans: NaviXav now reads the plan prepared in the MSFS planner, for pilots who do not use SimBrief. A “Flight plan source” setting chooses between SimBrief and an MSFS plan (.PLN); the flight loaded in MSFS is read automatically and an “Open a .PLN file” button lets you pick another one. Airports, route, airways, SID, STAR and planned runways are used like a SimBrief OFP; weather is taken live. The first launch offers this choice and no longer requires a SimBrief account.
- Diagnostics: the “navixav probe-fms” command records what the loaded aircraft exposes of its FMS — the simulator flight plan through SimConnect and, on the Fenix A320, the FMGC plan published by the EFB's local gateway — into a separate read-only report.
- Fenix A320: NaviXav reads the FMGC's active flight plan through the local gateway of the Fenix EFB, read-only. On the map, the FMS route is drawn in yellow only where it departs from the NaviXav route (DIRECT TO, new STAR), with its legend entry, and the alternate plan can be shown on demand; the FMGC's T/C and T/D replace the estimates (source “Aircraft FMGC”); in flight the FMGC phase replaces the one deduced from telemetry. Flight tracking gains the FMGC active waypoint, ETA and FMS weights, plus two alerts: the 250 kt speed limit and the deceleration point. The MCDU card opens with a line-by-line check of what the FMGC contains (FROM/TO, alternate, flight number, level, runways, SID, route, STAR, approach, ZFW, take-off speeds) and closes with a mirror of MCDU 1 and 2. The logbook keeps the FMGC flight number and ETA.
- FlyByWire and PMDG: the MCDU mirror also works on the A32NX/A380X (screens read through SimBridge, FMGC phase through the aircraft variable) and on the PMDG 737/777 (CDU screens broadcast by the SDK once EnableCDUBroadcast is set). Read-only, the source is shown in the mirror; the “navixav probe-fms” command reports which channel answers.

## Fixed

- Map: the TOC marker no longer follows the aircraft. It is fixed where the climb actually ends, even when ATC has assigned a level other than the planned one, and is only recomputed if the climb resumes (step climb). Restarted in flight, NaviXav no longer places the TOC under the aircraft: it uses the SimBrief profile's TOC, or does not show one. With an MSFS plan, the flight is recognised by its content rather than by the file date, which MSFS rewrites at every load: the flight log and the recovered TOC survive a restart.
- Alerts: the “Unsafe opening detected” alert, taken from the MSFS safety signal, is removed. It fired on doors or hatches the pilot opens on purpose on the ground.

## Changed

- News.

The installer is verified against its SHA-256 checksum before any automatic update.
