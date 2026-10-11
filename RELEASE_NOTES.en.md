# NaviXav 1.7.4

Released on 2026-10-11.

## Added

- VATSIM, IVAO and OpenSky traffic anticipates turns: an aircraft turning at the last report keeps turning, gradually easing off, on the map and in the simulator, instead of flying straight until the next report.
- Landing analysis: at touchdown, NaviXav shows the vertical speed recorded by MSFS, pitch and bank, distance past the threshold and centreline deviation on the runway actually used, headwind and crosswind, bounces and approach stability, with a score out of 100. The analysis is attached to the flight in the logbook, and a ready-to-share image can be copied or saved.
- The logbook is now kept in the NaviXav data folder rather than in the window: it survives a reinstall or a WebView2 reset, and a tablet connected over the local network shows the same logbook, read-only. Flights already recorded are carried over automatically at first launch.
- Logbook statistics: number of flights, total flight hours and distance, average touchdown and score, best landing, most flown aircraft and most visited airports. The complete logbook can be exported to CSV for a spreadsheet.

## Fixed

- OpenSky traffic now keeps moving smoothly on the map and in the simulator between two reports, instead of freezing and then jumping several nautical miles.
- OpenSky is polled much more often at the start of a flight, about every 30 seconds: the public allowance is spread over a flight rather than a whole day.
- The first load of an airport no longer waits nearly a minute: NaviXav now looks up the ILS and fixes in the airport’s own region instead of going through those of every airport already known, and recovers ILS frequencies it wrongly reported as missing, such as EGCC runway 23R.

## Changed

- Correction bug et ajout logbook.

The installer is verified against its SHA-256 checksum before any automatic update.
