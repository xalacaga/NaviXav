# NaviXav 1.5.3

Uitgebracht op 2026-08-28.

## Opgelost

- Luchthavens die in de cache ontbreken worden weer uit de simulator geïmporteerd: de baanverlichting werd met een verkeerde veldbreedte gelezen, waardoor de hele luchthaven verloren ging en de plattegrond niet beschikbaar bleef.
- Een niet-beschikbare plattegrond geeft nu de reden — luchthaven ontbreekt in de database — in plaats van een netwerkfout te melden, en een onbekende verlichtingssterkte wordt niet langer als uit getoond.

## Gewijzigd

- Bug correction.

Het installatieprogramma wordt vóór elke automatische update geverifieerd aan de hand van zijn SHA-256-controlesom.
