# NaviXav 1.4.6

Released on 2026-08-02.

## Added

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

## Fixed

- Removed the misleading “SimBrief planned runway X, but wind would favour Y” warning. In light, calm or variable wind, it incorrectly attributed a ranking driven by airport preference and ILS availability to the wind. The OFP runway remains selected, with moderate confidence when it differs from the planner ranking.

## Changed

- Added weather features and improved the mobile layout.

The installer is verified against its SHA-256 checksum before any automatic update.
