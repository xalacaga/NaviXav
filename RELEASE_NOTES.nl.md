# NaviXav 1.7.3

Uitgebracht op 2026-09-16.

## Nieuw

- MSFS-vliegplannen: NaviXav leest nu het plan dat in de MSFS-planner is voorbereid, voor piloten die geen SimBrief gebruiken. Een instelling “Bron van het vliegplan” kiest tussen SimBrief en een MSFS-plan (.PLN); de in MSFS geladen vlucht wordt automatisch gelezen en met de knop “.PLN-bestand openen” kies je een ander bestand. Luchthavens, route, luchtwegen, SID, STAR en geplande banen worden gebruikt als een SimBrief-OFP; het weer wordt live opgehaald. De eerste start biedt deze keuze aan en vereist geen SimBrief-account meer.
- Diagnose: het commando “navixav probe-fms” legt vast wat het geladen vliegtuig van zijn FMS prijsgeeft — het vliegplan van de simulator via SimConnect en, op de Fenix A320, het FMGC-plan van de lokale EFB-gateway — in een apart rapport, alleen-lezen.
- Fenix A320: NaviXav leest het actieve vliegplan van het FMGC via de lokale gateway van de Fenix-EFB, alleen-lezen. Op de kaart wordt de FMS-route alleen geel getekend waar ze afwijkt van de NaviXav-route (DIRECT TO, nieuwe STAR), met legenda-item, en het uitwijkplan is op verzoek zichtbaar; de T/C en T/D van het FMGC vervangen de schattingen (bron „FMGC van het vliegtuig”); tijdens de vlucht vervangt de FMGC-fase de uit telemetrie afgeleide fase. De vluchtopvolging krijgt het actieve FMGC-waypoint, de ETA en de FMS-gewichten, plus twee waarschuwingen: snelheidslimiet 250 kt en vertragingspunt. De MCDU-kaart opent met een regel-voor-regel controle van wat het FMGC bevat (FROM/TO, uitwijkhaven, vluchtnummer, niveau, banen, SID, route, STAR, nadering, ZFW, startsnelheden) en sluit af met een spiegel van MCDU 1 en 2. Het logboek bewaart het FMGC-vluchtnummer en de ETA.
- FlyByWire en PMDG: de MCDU-spiegel werkt ook op de A32NX/A380X (schermen gelezen via SimBridge, FMGC-fase via de vliegtuigvariabele) en op de PMDG 737/777 (CDU-schermen uitgezonden door de SDK zodra EnableCDUBroadcast aanstaat). Alleen-lezen, de bron staat in de spiegel; het commando „navixav probe-fms” meldt welk kanaal antwoordt.

## Opgelost

- Kaart: de TOC-markering volgt het vliegtuig niet meer. Ze wordt vastgezet waar de klim werkelijk eindigt, ook als ATC een ander niveau dan gepland heeft toegewezen, en wordt alleen opnieuw berekend als de klim wordt hervat (step climb). Na een herstart tijdens de vlucht plaatst NaviXav de TOC niet meer onder het vliegtuig: het neemt die van het SimBrief-profiel over of toont er geen. Bij een MSFS-plan wordt de vlucht herkend aan de inhoud en niet aan de bestandsdatum, die MSFS bij elke lading herschrijft: het vluchtlogboek en de teruggevonden TOC overleven een herstart.
- Waarschuwingen: de waarschuwing „Gevaarlijke opening gedetecteerd”, overgenomen van het MSFS-veiligheidssignaal, is verwijderd. Ze ging af bij deuren of luiken die de piloot op de grond bewust opent.

## Gewijzigd

- News.

Het installatieprogramma wordt vóór elke automatische update geverifieerd aan de hand van zijn SHA-256-controlesom.
