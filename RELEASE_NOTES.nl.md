# NaviXav 1.5.0

Uitgebracht op 2026-08-28.

## Nieuw

- Een klik op een vliegtuigfoto opent nu een grote voorvertoning in NaviXav; deze sluit met de knop, een klik erbuiten of de Escape-toets.
- De Aircraft-kaart en inventaris tonen nu naast de naam van elke ondersteunde vliegtuigfamilie een echte vrij gelicentieerde foto; extra vliegtuigen in Community gebruiken automatisch hun lokale miniatuur wanneer die beschikbaar is.
- Wanneer een ChartFox-kaart niet kan worden ingesloten, biedt NaviXav nu de officiële nationale catalogus in dezelfde kaart aan als de luchthaven wordt gedekt.
- De vluchtvolging schat nu de Top of Climb aan de hand van het kruisniveau, de verticale snelheid en de grondsnelheid; de berekende punten TOC en TOD verschijnen als afzonderlijke routepunten op de kaart.
- ChartFox kan nu via Instellingen aan een VATSIM-account worden gekoppeld; de kaarten op aanvraag zijn beschikbaar als optionele bron voor vertrek en aankomst.
- Het menu Charts vermeldt nu dat een ChartFox-/VATSIM-account vereist is voor toegang tot de AIRAC-kaarten van ChartFox en biedt een rechtstreekse link naar Instellingen.

## Opgelost

- Vliegtuigfoto’s blijven niet langer verborgen achter het ICAO-typevlak in de Aircraft-kaart en inventaris.
- Bij het openen van een luchthaven-pdf in Charts wordt de andere luchthaven niet meer onder het document geduwd: Vertrek en Aankomst blijven naast elkaar op brede schermen en de ongeopende kaart blijft bovenaan in compacte vensters.
- De ChartFox-vermelding ‘alleen simulatie’ in Instellingen volgt nu de taal van de interface.
- ChartFox-kaarten waarvan de bron insluiting verbiedt tonen geen leeg vlak meer: NaviXav legt de beperking uit en biedt aan ze rechtstreeks op ChartFox te openen.
- De berekende TOC- en TOD-punten gebruiken nu eigen magenta en rode kleuren, anders dan alle routepunten.
- De kaartachtergronden CartoDB Positron en Dark Matter zijn verwijderd: hun gratis dienst voorziet elke tegel nu van het watermerk "API key required". De keuze gaat tussen OpenStreetMap Standard en OpenTopoMap, en een ongeldig geworden instelling valt automatisch terug op OpenStreetMap.
- De weerbriefing verschijnt niet langer gedeeltelijk in het Frans wanneer de interface op een andere taal staat: de aandachtspunten en de METAR-verschijnselen volgen nu de gekozen taal.
- Onweer zonder waargenomen neerslag wordt nu gemeld: de groepen TS, VCTS en VCSH werden bij het decoderen van de METAR overgeslagen. Ook wordt de „PO” in „TEMPO” niet langer als stofhozen gelezen.
- SID’s verschijnen eindelijk op de kaart: hun tracé, hun punten en hun gepubliceerde beperkingen ontbraken zodra één procedure twee baankoppen bediende, wat op vrijwel elke grote luchthaven het geval is. Het vertrek werd daardoor een rechte lijn naar het eerste routepunt. STAR’s krijgen bovendien hun laatste deel terug, eigen aan de landingsbaan. De navigatiedatabase wordt bij de volgende start automatisch opnieuw uit de simulator ingelezen.

## Gewijzigd

- Reformuler l'annonce ChartFox de la 1.5.0.
- Ajout fonctionnalite et correction bugs.

Het installatieprogramma wordt vóór elke automatische update geverifieerd aan de hand van zijn SHA-256-controlesom.
