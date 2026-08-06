# NaviXav 1.4.10

Uitgebracht op 2026-08-06.

## Nieuw

- De instellingen openen nu de volledige versiegeschiedenis: alle belangrijke wijzigingen sinds het bijhouden begon, versie per versie, met de datum en een markering op de geïnstalleerde. De geschiedenis wordt met de toepassing meegeleverd en is offline leesbaar. De wijzigingsteksten blijven in het Engels; het kader en de rubrieken volgen de gekozen taal.
- De vluchtvolging onderscheidt nu een gepauzeerde simulatie van een verloren simulatie: de MSFS-indicator en de volgpil tonen “MSFS gepauzeerd” in plaats van een verbroken verbinding te suggereren. Een simulator die deze status niet doorgeeft, wordt gewoon verder gevolgd.
- Een onopvallend potlood verschijnt bij het zweven over de baan, de SID, de STAR, hun transities en de nadering: het opent de lijst van de andere gepubliceerde procedures en laat de keuze achteraf wijzigen, ook wanneer de motor zeker is. De lijst is niet langer beperkt tot drie regels, hij toont alles wat vanaf de gekozen baan vliegbaar is, en “Terug naar de automatische keuze” geeft de beslissing terug aan de motor. Bij een opgelegde keuze blijft het potlood oplichten.

## Opgelost

- Een ontbrekende procedure neemt niet langer de plaats van een echte in. Wanneer er geen STAR voor de baan is gepubliceerd, vervangt de reden het streepje op één strakkere regel, en de transitieregel die de afwezigheid alleen herhaalde verdwijnt. Dezelfde verdichting voor een SID of een nadering zonder transitie.
- Een SID of STAR die niet voor de gekozen baan is gepubliceerd, wordt niet langer aaneengeschakeld: hij vertrekt van een andere drempel of leidt naar de IAF aan de andere kant van het veld. NaviXav meldt nu een radargeleid vertrek of een directe aankomst, en de afgewezen procedure blijft beschikbaar in de keuzelijst. In Brive-Souillac op baan 29 toont het plan BSC en daarna ILS RWY 29 in plaats van een onvliegbare STAR.
- Zonder STAR sluiten de nadering en de bijbehorende transitie nu aan op het laatste routepunt in plaats van zonder verband te blijven. Een transitie die precies op dat punt is gepubliceerd, wordt herkend en niet langer als onzekere keuze getoond.
- Naderingspunten die SimBrief ongemarkeerd in het navigatielog laat staan, zoals CF29 of RW11, tellen niet langer als routepunten: ze worden niet meer op de route getekend en niet meer gebruikt om de aankomst te koppelen.
- Wanneer een STAR de landingsbaan wel bedient maar eindigt op een punt dat geen enkele nadering opent, meldt NaviXav dat uitdrukkelijk in plaats van de breuk pas tijdens de vlucht te laten ontdekken.
- De versiegeschiedenis staat niet langer permanent over de interface: hij opent alleen bij een klik op zijn pictogram in de instellingen en sluit volledig.
- Het instellingenvenster heeft geen horizontale schuifbalk meer: een onzichtbaar veld liep over de volle breedte van het kader buiten, ongeacht de venstergrootte.

## Gewijzigd

- Correction bug et améliorations diverses.

Het installatieprogramma wordt vóór elke automatische update geverifieerd aan de hand van zijn SHA-256-controlesom.
