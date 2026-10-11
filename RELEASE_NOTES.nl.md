# NaviXav 1.7.4

Uitgebracht op 2026-10-11.

## Nieuw

- VATSIM-, IVAO- en OpenSky-verkeer anticipeert op bochten: een toestel dat bij de laatste meting in een bocht zat, blijft op de kaart en in de simulator geleidelijk uitlopend draaien, in plaats van rechtdoor te vliegen tot de volgende meting.
- Landingsanalyse: bij de touchdown toont NaviXav de door MSFS vastgelegde verticale snelheid, neusstand en helling, de afstand voorbij de drempel en de afwijking van de middellijn van de werkelijk gebruikte baan, tegen- en zijwind, stuiters en de stabiliteit van de eindnadering, met een score op 100. De analyse wordt aan de vlucht in het logboek gekoppeld en een afbeelding om te delen kan worden gekopieerd of opgeslagen.
- Het logboek wordt nu in de gegevensmap van NaviXav bewaard in plaats van in het venster: het overleeft een herinstallatie of een reset van WebView2, en een via het lokale netwerk verbonden tablet toont hetzelfde logboek, alleen-lezen. Al vastgelegde vluchten worden bij de eerste start automatisch overgenomen.
- Logboekstatistieken: aantal vluchten, totale vlieguren en afstand, gemiddelde touchdown en score, beste landing, meest gevlogen toestellen en meest bezochte vliegvelden. Het volledige logboek kan naar CSV worden geëxporteerd voor een spreadsheet.

## Opgelost

- OpenSky-verkeer beweegt nu vloeiend door op de kaart en in de simulator tussen twee metingen, in plaats van stil te staan en dan enkele zeemijlen te verspringen.
- OpenSky wordt aan het begin van een vlucht veel vaker opgevraagd, ongeveer elke 30 seconden: het openbare tegoed wordt over een vlucht verdeeld in plaats van over een hele dag.
- Het eerste laden van een vliegveld duurt niet langer bijna een minuut: NaviXav zoekt het ILS en de bakens nu in de regio van het vliegveld in plaats van die van alle al bekende vliegvelden af te lopen, en vindt ILS-frequenties terug die ten onrechte als onvindbaar werden gemeld, zoals die van baan 23R van EGCC.

## Gewijzigd

- Correction bug et ajout logbook.

Het installatieprogramma wordt vóór elke automatische update geverifieerd aan de hand van zijn SHA-256-controlesom.
