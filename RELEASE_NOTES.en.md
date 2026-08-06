# NaviXav 1.4.10

Released on 2026-08-06.

## Added

- The settings now open the complete version history: every important change since tracking began, version by version, with the date and a marker on the one installed. The history ships with the application and reads offline. The change texts stay in English; the frame and the section labels follow the selected language.
- Flight tracking now tells a paused simulation from a lost one: the MSFS indicator and the tracking pill read “MSFS paused” instead of suggesting a dropped connection. A simulator that does not expose this state keeps being tracked normally.
- A discreet pencil appears when hovering the runway, the SID, the STAR, their transitions and the approach: it opens the list of the other published procedures and lets you change the choice afterwards, even when the engine is confident. The list is no longer limited to three entries, it shows everything flyable from the selected runway, and “Back to the automatic choice” hands control back to the engine. The pencil stays lit on a choice you imposed.

## Fixed

- An absent procedure no longer takes the room of a real one. When no STAR is published for the runway, the reason replaces the dash on a single tightened line, and the transition line that merely repeated the absence is gone. Same tightening for a SID or an approach without a transition.
- A SID or STAR that is not published for the selected runway is no longer chained: it starts from another threshold or leads to the IAF on the opposite side of the airport. NaviXav now announces a radar-vectored departure or a direct arrival, and the discarded procedure remains offered in the list of choices. At Brive-Souillac landing on runway 29, the plan reads BSC then ILS RWY 29 instead of an unflyable STAR.
- Without a STAR, the approach and its transition now connect to the last en-route waypoint instead of being left unconnected. A transition published on that very waypoint is recognised and is no longer presented as an uncertain choice.
- Approach fixes that SimBrief leaves in the navigation log without marking them, such as CF29 or RW11, no longer count as en-route waypoints: they are no longer drawn on the route and no longer used to link the arrival.
- When a STAR does serve the landing runway but ends on a waypoint that starts no approach, NaviXav says so explicitly instead of leaving the break to be discovered in flight.
- The version history no longer sits permanently on top of the interface: it opens only when its icon in the settings is clicked, and it closes completely.
- The settings window no longer has a horizontal scrollbar: an invisible field used to overflow the whole width of the box, whatever the window size.

## Changed

- Correction bug et améliorations diverses.

The installer is verified against its SHA-256 checksum before any automatic update.
