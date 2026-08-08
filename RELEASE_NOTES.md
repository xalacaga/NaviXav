# NaviXav 1.4.16

Released on 2026-08-08.

## Fixed

- Fenix A319/A320/A321 speedbrakes now show ARMED reliably even when the SimBrief aircraft name is generic.
- Top of Descent is now a fixed point on the route, computed from the cruise level: it counts down to zero and then reads as passed. It could previously freeze during a 3° descent, or even grow when the descent was started too early.
- The deviation from the descent profile keeps being reported during a level-off below the cruise level. It used to disappear as soon as the vertical speed returned to zero, exactly when the aircraft was far below profile.
- Top of Descent now honours the published altitude ceilings of the STAR and the approach, and reads altitude in the standard atmosphere like a flight level.
- The vertical speed required for the next constraint is now compared with the indicated altitude, the only one comparable with a published constraint.

## Changed

- Correction bug TOD.

The installer is verified against its SHA-256 checksum before any automatic update.
