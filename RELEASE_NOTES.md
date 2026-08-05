# NaviXav 1.4.8

Released on 2026-08-05.

## Added

- On wide desktop windows, modules now sit in a compact floating rail at the upper left with a modern glass treatment and a clearer active marker. The concise **Flight plan** entry now behaves like every other module, with no collapse control, is selected by default, and clicking any entry scrolls directly to its content. The main area fills all remaining width and an opened official PDF expands across the chart grid. A visible global flight alert now pushes the rail below the enlarged header, preventing it from covering the first module. Compact windows keep the horizontal selector and mobile navigation is unchanged.
- The first plan opens faster when SimBrief provides a detailed navlog : validated en-route coordinates and published procedure links are reused before NaviXav asks MSFS Facilities for any missing positions. The existing route-corridor checks and local-cache fallback remain active.
- Flight tracking now keeps a timeline of the flight. A ribbon shows every phase flown, the longer ones taking up the more room, and the log underneath groups what happened under the phase it happened in : takeoff and landing runway with the actual wind, phase changes, gear, flaps, spoilers, parking brake, lights and autopilot modes. A change is recorded only once it has held, so a moving flap lever no longer floods the log.
- The timeline of a completed flight is kept with its summary in the local logbook and can be replayed from there. It is recorded as data rather than as sentences, so a flight logged in one language reads back in whichever language is selected later.

## Fixed

- Aircraft configuration and Flight events now react to flap, spoiler and parking-brake changes on aircraft that leave one standard MSFS value frozen. NaviXav cross-checks official handle, effective-position, surface-position and cockpit-indicator SimVars, and flaps no longer remain stuck on FULL after the lever moves. Fenix A319, A320 and A321 controls are read directly from their common cockpit variables, including with engines and hydraulics off.
- Named taxiways now remain visible on the ground chart even when MSFS reports them as generic `path` segments. At airports such as LCPH, the main A, B, K and other taxiways no longer disappear with the unnamed secondary links.
- On phones and tablets, the MSFS connection state is now shown as a compact coloured dot, so the `MSFS connected` label no longer overflows narrow screens. The translated label remains available to assistive technologies.
- The Constraints module now follows the selected language : vertical profile, altitude instructions and constraint tables are no longer French only.
- The Official charts module is translated as well, including the document picker, the overlay notices and the AIS catalogue sections.
- The MCDU tab now displays the official chart card, the chart minima form and the ATIS reminders in the selected language.
- Taxi labels coming from the simulator, such as gate names and hold-short instructions, are translated on the ground plan and in the taxi banner.
- Connection tooltips and error banners are no longer displayed in French when another language is selected.
- Flap detents are read correctly on Airbus aircraft that expose five handle positions : the handle on 2 was displayed as 1, and every detent above 1 was shifted down by one. The retracted detent now follows the Airbus marking and reads 0.
- Aircraft without a known flap profile now show the handle position and the measured flap angle instead of a percentage of travel, so any airframe stays readable. The last Boeing detent keeps its angle instead of turning into FULL.
- The displayed flight level now comes from the standard atmosphere, as the altimeter reads it. An aircraft levelled at FL330 was announced at FL342 in warm air, and the cruise phase was lost for the same reason.
- Phones and tablets can now change the display language from the toolbar. The settings stay reserved for the PC, but the language was unreachable once the welcome screen had been answered.

## Changed

- Amelioration interface et ajout timeline.
- Amelioration interface/ajout Timeline.

The installer is verified against its SHA-256 checksum before any automatic update.
