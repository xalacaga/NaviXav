# NaviXav 1.6.0

Uitgebracht op 2026-08-30.

## Nieuw

- Duidelijkere bediening: Vlucht volgen heeft nu een zichtbare schakelaar om alle NaviXav-alarmen, waaronder MASTER WARNING- en MASTER CAUTION-meldingen, uit of weer in te schakelen zonder het volgen te stoppen; na een update opent de versiegeschiedenis automatisch bij de eerste herstart en blijft daarna op verzoek beschikbaar.
- Direct wisselen van verkeersbron vanuit de kaart- en taxibalk: de VATSIM-, IVAO- en OpenSky-keuzelijsten blijven gesynchroniseerd, herstarten de verkeersmeting netjes en slaan de keuze lokaal op.
- OpenSky echt verkeer: NaviXav kan openbare ADS-B-statusvectoren binnen 100 NM rond het vliegtuig tonen, met bronvermelding en API-vriendelijke caching; deze echte wereldweergave blijft strikt gescheiden van MSFS-injectie.
- De instellingen zijn ingedeeld in inklapbare categorieën voor compacte vensters, met een handmatig FSLTL-pad, toegang tot de officiële FlyByWire Installer wanneer modellen ontbreken en IVAO als tweede gratis openbare netwerkverkeersbron naast VATSIM.
- Uitsluitende compatibiliteit met MSFS 2024: NaviXav gebruikt nu de native SimConnect AI EX1-API van MSFS 2024 en weigert bij starten of bouwen een oude MSFS 2020-DLL, in plaats van door te gaan met een ongeschikte verbinding of functies.
- VATSIM-verkeersinjectie in MSFS: NaviXav detecteert FSLTL Base Models automatisch in Community, indexeert de aircraft.cfg-bestanden en VMR-regels zonder ze te wijzigen, kiest het veiligste exacte of algemene model en maakt, actualiseert en verwijdert uitsluitend eigen SimConnect-objecten binnen een begrensde zone rond de speler. De optie staat standaard uit en de interface toont de gedetecteerde FSLTL-versie.
- Omliggend verkeer: een knop “VATSIM-verkeer” op de kaartbalk en “Simulatorverkeer” op de taxibalk toont de andere toestellen. Op de kaart is elk netwerktoestel een silhouet op koers met de roepnaam eronder, en een klik opent de kaart ervan: type, frequentie, piloot, vertrek- en aankomstvelden benoemd vanuit de MSFS-database, grondsnelheid en hoogte. De taxikaart toont het verkeer van de simulator, als enige nauwkeurig op de meter. Standaard uit; zolang dat zo is wordt er niets opgevraagd.
- Verticaal profiel: de TOD gebruikt nu bij voorkeur het prestatiepunt uit het nieuwste SimBrief-OFP nadat de coördinaten tegen de actieve route zijn gecontroleerd; STAR- en naderingsplafonds blijven gelden en de geometrische 3°-berekening neemt automatisch over als het punt ontbreekt of niet meer bij de route past.
- VATSIM-posities online: eenmaal ingeschakeld in de instellingen markeert NaviXav met een stip de veldfrequenties waarvan de post bezet is, en toont bij het zweven de roepnaam en frequentie van de verkeersleider — die van het netwerk is niet altijd de door de simulator gepubliceerde. De instelling staat standaard uit en zolang dat zo is wordt er niets opgevraagd.
- Veldfrequenties: de vertrekfrequentie vult nu de rij aan, en een rol met meerdere frequenties meldt dat met een “+n” in plaats van te suggereren dat er maar één is; het detail van elke post, platforms inbegrepen, is bij het zweven te lezen.
- Vluchtopvolging: een tweede indicator meldt de in de huidige fase verwachte frequentie en markeert zich wanneer de radio er al op staat. Hij zwijgt wanneer het veld meerdere frequenties voor dezelfde rol publiceert, omdat niets zegt welke de gebruikte baan bedient.
- Vluchtopvolging: een radio-indicator toont de op COM1 ingestelde frequentie en benoemt de bijbehorende post van het veld, inclusief grondverkeersleiding per baan — zo controleer je in één oogopslag of je de opgegeven frequentie hebt ingetoetst.
- Diagnose: de opdracht “navixav airport” toont de veldfrequenties naast het nummer waarmee de simulator elke rol aanduidt, en meldt een rol die niet vertaald kan worden in plaats van die te verzwijgen.
- Veldfrequenties: de kaarten Vertrek en Aankomst van het vluchtplan tonen nu de door MSFS gepubliceerde radioketen, in de volgorde waarin die wordt gebruikt — ATIS, DEL, GND, TWR bij vertrek, ATIS, APP, TWR, GND bij aankomst. Publiceert een veld meerdere frequenties voor dezelfde rol, dan verschijnen de overige bij het zweven met de muis.
- TOD-voorbereiding: op 50 NM vraagt het waarschuwingssysteem om de daling voor te bereiden en markeert het de TOD-tegel; op 10 NM wordt een afzonderlijke TOD-waarschuwing actief die blijft staan totdat de daling is ingezet.
- Vliegtuigconfiguratie: de begeleide interface gebruikt nu een duidelijker cockpitsynoptiek met evenwichtige tegels, een pictogram per systeem, statusaccenten en echte lichtindicatoren; de klassieke interface behoudt het vorige ontwerp.
- Nieuwe vluchtgestuurde interface: een vaste strook toont fase, baan of procedure, volgende actie en aanbevolen module; vertrek-, aankomst- en naderingskaarten worden in een kaartenbalk voorbereid en Taxi krijgt meer ruimte. Met Interface-indeling keer je zonder herstart meteen terug naar de klassieke interface.
- Taxiplan: vertrek van een opstelplaats met de neus naar de terminal begint met een pushback, paars en met korte streepjes op het plan getekend en in de balk aangekondigd met afstand en de koers zodra het toestel is uitgelijnd; een ramp, een hervatte taxi of een aankomst tonen er geen.
- Voorbereiding van het plan: de balk die het vullen van de MSFS-cache aankondigt toont nu een vliegtuig dat het kader oversteekt, met een spoor erachter, zolang het lezen duurt. Het wachten kon tientallen seconden duren zonder dat er iets bewoog.
- MCDU-kaart: NaviXav haalt nu de ZFWCG uit SimBrief en toont het zwaartepunt zonder brandstof samen met het aantal passagiers op de gewichtspagina; de ZFWCG verschijnt ook in Dispatch.
- Een verkeersbron kiezen volstaat nu om die in MSFS te injecteren: injectie staat standaard aan en het vinkje in de instellingen dient alleen om het uit te zetten.
- Een markering ‘alleen kaart’ verschijnt in de kaartbalk wanneer verkeer wordt getoond zonder te worden geïnjecteerd, en de tooltip geeft de reden: injectie uit, FSLTL ontbreekt of echte bron.
- Echt ADS-B-verkeer komt eindelijk in MSFS: het type van elk vliegtuig wordt opgezocht in twee elkaar aanvullende openbare registers, waardoor er eindelijk een FSLTL-model voor gekozen kan worden. Een vliegtuig dat bij de eerste ronde onbekend is, verschijnt bij de volgende zodra zijn adres is opgezocht.
- Een verkeersbron kiezen volstaat nu om die in de simulator te injecteren. Het vinkje ‘Netwerkverkeer in MSFS injecteren’ verdwijnt uit de instellingen: de laagknop is de enige schakelaar, en wat die toont is wat er vliegt.

## Opgelost

- Geparkeerde OpenSky-toestellen blijven injecteerbaar wanneer hun transponder barometrische hoogte, snelheid of koers weglaat: NaviXav gebruikt eerst de geometrische hoogte en vult daarna alleen ontbrekende grondgegevens aan.
- OpenSky-echtverkeer in MSFS: toestellen zonder ADS-B-type gebruiken onmiddellijk een veilig algemeen FSLTL-model in plaats van onzichtbaar te blijven en nemen hun exacte model over zodra het ICAO24-register antwoordt; de injectie werkt hun positie nu elke seconde bij.
- Vloeiender IVAO- en OpenSky-verkeer in MSFS: NaviXav extrapoleert de positie elke seconde tussen netwerkmetingen en houdt een door de bron kort overgeslagen toestel tijdelijk vast, zodat het niet meer verdwijnt en terugkomt; de vaste aftelling van 15 seconden, die voor deze bronnen onjuist was, is uit de interface verwijderd.
- Netwerkverkeer bij gates en op taxibanen: wanneer VATSIM de grondstatus niet publiceert, leidt NaviXav die nu af uit een snelheid van maximaal 50 kt; geparkeerde en taxiënde vliegtuigen worden geïnjecteerd in plaats van overgeslagen.
- Vliegtuiginventaris: Vernieuwen detecteert nu vliegbare add-ons met een onjuist isAirTraffic-vlag, zoals de Rafale M, en elk toestel toont zijn eigen lokale miniatuur in plaats van de afbeelding van het geladen toestel te hergebruiken.
- Taxiplan bij aankomst: de werkelijke vliegtuigpositie en baankoers sluiten reeds gepasseerde afritten voortaan uit; na een landing op 24R stelt NaviXav niet langer voor terug te rijden naar een afrit achter het toestel.
- Kaart: het en-routegedeelte van het vliegplan blijft violet, maar gebruikt nu een doorgetrokken lijn die bij lage zoomniveaus beter leesbaar is.
- Aircraft-pagina: lange ICAO-uitrustingsreeksen lopen nu binnen hun tegel door in plaats van over het aangrenzende profiel heen.
- SimConnect-identiteit: tekstvariabelen zoals TITLE en ATC MODEL worden nu gedeclareerd met de null-eenheid die de MSFS-SDK verwacht, in plaats van de letterlijke tekenreeks NULL die ongemerkt een lege waarde opleverde.
- Aircraft-pagina: de primaire identiteit volgt nu live het toestel dat werkelijk in MSFS is geladen en valt automatisch terug op ATC MODEL wanneer een add-on TITLE leeg laat; het in SimBrief geplande toestel blijft duidelijk gescheiden voor de OFP-gewichten en prestaties.
- Buitenverlichting: NaviXav vergelijkt nu de zeven afzonderlijke SimVars met het officiële MSFS-masker LIGHT STATES; complexe toestellen die alleen de gezamenlijke status publiceren tonen hun indicatoren weer en activeren waarschuwingen correct, met automatische terugval op de vorige uitlezing als het masker niet beschikbaar is.
- Vluchtvolging: de nieuwe synoptiek voor Vliegtuigconfiguratie is nu strikt beperkt tot het eigen blok en vergroot of verstoort de realtime-tegels niet langer.
- De Demo-modus is verwijderd: NaviXav gebruikt voortaan uitsluitend het nieuwste SimBrief-vluchtplan en echte vluchtgegevens die MSFS via SimConnect levert.
- Begeleide interface: de horizontale routestrook blijft nu alleen in het menu Vluchtplan en overlapt de bovenste strook niet meer in andere modules; de klassieke interface behoudt de vertrouwde weergave.
- Navigatie tussen modules: de bovenste vluchtstrook meet nu de werkelijke hoogte van de werkbalk en blijft volledig zichtbaar in plaats van na een menuwissel te worden afgesneden.
- Module Procedures: een fase die alleen uit aandachtspunten bestaat, zoals de landing, wordt niet langer als voltooid getoond vóór de vlucht; de meter blijft leeg en de punten dragen het informatieteken in plaats van een groene bevestiging.
- Module Procedures: een fase die de vlucht nog niet heeft bereikt toont geen bevestigingen meer; aan de gate vinken de aangetrokken parkeerrem en gedoofde lichten de punten na de landing en bij het afzetten niet langer af.
- Taxiplan: de vertrektoegang wordt nu gekozen uit alle voor vliegtuigen bereikbare baanaansluitingen op basis van hun afstand tot de gevraagde drempel. Op CYYZ gebruikt een vertrek van gate 139 naar baan 23 nu AK, A, H en Q in plaats van baan 15L over te steken naar de H3-intersectie. Elke bevestigde baankruising wordt bij een expliciet wachtpunt gesplitst; ontbreekt die instructie, dan wordt de route geweigerd.
- Netwerkverkeer geïnjecteerd in MSFS: vliegtuigen die de simulator tijdens de vlucht liet vallen worden nu herkend en in de volgende cyclus opnieuw aangemaakt, in plaats van definitief te verdwijnen terwijl NaviXav dacht ze nog te volgen.
- Het logboek noteert nu elke wijziging in een injectiecyclus — gevolgde, opnieuw aangemaakte, verwijderde en overgeslagen vliegtuigen — waardoor een stil geworden injectie zichtbaar wordt.
- Het label van de injectieoptie noemt niet langer alleen VATSIM, maar het netwerkverkeer, ongeacht de gekozen bron.
- De echte bron heet nu ‘Echt verkeer · OpenSky’ in alle drie de keuzelijsten in plaats van alleen de naam van de aanbieder, en dat label volgt eindelijk de taal van de interface.
- Een vliegtuig op exact jouw plek wordt niet meer getoond of geïnjecteerd: het is bijna altijd je eigen toestel, weergegeven door het netwerk waarmee je verbonden bent. De naastgelegen opstelplaats blijft zichtbaar en een overvlucht wordt niet voor overlapping aangezien.
- Een vliegtuig dat geen roepnaam uitzendt, krijgt een stabiele generieke roepnaam in plaats van zijn hexadres of een leeg veld dat de simulator als ontbrekende registratie zou tonen.
- Verkeersinjectie heeft nu een eigen levenscyclus: de status is opvraagbaar in plaats van opgesloten in de webservice, zodat een gestopte injectie niet langer voor een gezonde kan doorgaan.

## Gewijzigd

- Integration trafic.

Het installatieprogramma wordt vóór elke automatische update geverifieerd aan de hand van zijn SHA-256-controlesom.
