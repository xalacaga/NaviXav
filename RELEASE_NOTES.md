# NaviXav 1.8.0

Released on 2026-11-08.

## Added

- Voice callouts: NaviXav speaks MASTER CAUTION and MASTER WARNING alerts, the top of descent at 50, 10 and 0 NM, and taxi instructions such as hold-short points; switch them on in Settings or from Flight tracking.
- Fuel monitoring: Flight tracking compares the fuel on board with the SimBrief OFP at your position along the route, estimates the fuel at destination (EFOB) and raises a caution when it falls below the final reserve plus alternate fuel.
- Diagnostic log: every loss and recovery of the connection to MSFS is now recorded with its reason, the duration of the read that failed and the length of the outage, to make connection reports easier to investigate.
- Map and taxi diagram: your aircraft is now drawn as the same airliner silhouette in both views, turned to its heading, with engines, windscreen and a soft shadow, instead of an arrow.
- NaviXav voice: callouts are spoken by high-quality neural voices shipped with the application, in all eight languages, fully offline and with nothing to install; aviation terms stay in English and three voices are available in English.
- SIGMET on the map: the SIGMETs in force near the route are drawn as coloured areas with their levels, those the route crosses are highlighted, the weather tab lists them with their full text, and an alert warns when the aircraft is about to enter one at its level.
- Stabilized approach: below the gate (1000 ft IMC, 500 ft VMC) NaviXav checks gear, flaps, speed, sink rate and the ILS needles, calls out "Stabilized" when all is in order and raises an unstable approach alarm otherwise; a flight tracking tile shows the faulty criteria.
- MSFS panel 1.2.3: the in-sim panel shows the active alarms, colour-coded by severity, and the stabilized approach status on final; update it from the NaviXav settings.

## Fixed

- An aircraft that does not publish its fuel quantity no longer shows 0 kg or raises a false fuel-below-reserve MASTER WARNING.
- Saving the settings is immediate again: the aircraft thumbnails of the installed-aircraft list no longer reread thousands of Community files each and no longer hold up the rest of the application.
- The weather warnings “in LIFR conditions” and “weather unavailable” are no longer shown in French when another interface language is selected.

## Changed

- Mettre en cache la lecture des aircraft.cfg de Community.

The installer is verified against its SHA-256 checksum before any automatic update.
