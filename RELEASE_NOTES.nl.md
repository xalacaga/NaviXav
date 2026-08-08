# NaviXav 1.4.16

Uitgebracht op 2026-08-08.

## Opgelost

- De speedbrakes van de Fenix A319/A320/A321 tonen nu betrouwbaar ARMED, ook wanneer de vliegtuigbenaming in SimBrief algemeen is.
- Het Top of Descent is nu een vast punt op de route, berekend vanaf het kruisniveau: de waarde telt af tot nul en wordt daarna als gepasseerd weergegeven. Voorheen kon die tijdens een daling van 3° blijven staan of zelfs oplopen wanneer de daling te vroeg werd ingezet.
- De afwijking ten opzichte van het daalprofiel blijft zichtbaar tijdens een niveauvlucht onder het kruisniveau. Voorheen verdween die zodra de verticale snelheid weer nul werd, juist wanneer het toestel ver onder het profiel zat.
- Het Top of Descent houdt nu rekening met de gepubliceerde hoogteplafonds van de STAR en de nadering, en leest de hoogte in de standaardatmosfeer zoals een vliegniveau.
- De verticale snelheid die nodig is voor de volgende beperking wordt nu vergeleken met de aangegeven hoogte, de enige die vergelijkbaar is met een gepubliceerde beperking.

## Gewijzigd

- Correction bug TOD.

Het installatieprogramma wordt vóór elke automatische update geverifieerd aan de hand van zijn SHA-256-controlesom.
