# NaviXav

**Documentatie:** [Français](README.md) · [English](README.en.md) ·
[Deutsch](README.de.md) · [Español](README.es.md) ·
[Italiano](README.it.md) · [Português](README.pt.md) · Nederlands ·
[Polski](README.pl.md)

NaviXav is een lokale applicatie voor IFR-vluchtondersteuning bij Microsoft
Flight Simulator. Ze haalt het laatste SimBrief-vluchtplan op, vult de
terminalinformatie aan met gegevens uit de simulator en presenteert alles in een
interface die is afgestemd op de vluchtvoorbereiding en de MCDU-invoer.

De applicatie heeft een eigen Windows-venster. De interface wordt weergegeven
door Microsoft WebView2 en communiceert uitsluitend met een lokale dienst
gebonden aan `127.0.0.1`. Er wordt geen externe browser geopend. Instellingen,
de navigatiedatabase en caches blijven op de computer.

Het venster is volledig schaalbaar. De interface herschikt haar panelen,
bedieningselementen, tabbladen en de kaarthoogte afhankelijk van de beschikbare
ruimte, tot een minimale grootte van 720 × 560 pixels.

> NaviXav is uitsluitend bedoeld voor vluchtsimulatie. De weergegeven
> informatie moet worden geverifieerd aan de hand van de officiële publicaties
> en de geldende ATC-instructies.

## Functies

### SimBrief-vluchtplan

- automatisch ophalen van het laatste OFP bij het opstarten;
- ondersteuning van de SimBrief Pilot ID of gebruikersnaam;
- weergave van de volledige route, van vertrek tot bestemming;
- markering van het volgende routepunt op basis van de werkelijke positie van
  het vliegtuig, waarbij reeds gepasseerde punten worden gedimd;
- massa's, brandstof, vluchttijd, uitwijkhaven en dispatchgegevens;
- informatie over het toestel, registratie en opgegeven uitrusting.

### IFR-voorbereiding

NaviXav vult aan en toont:

- de vertrekbaan en de aankomstbaan;
- de SID en de bijbehorende transitie;
- de STAR en de bijbehorende transitie;
- de nadering en de bijbehorende VIA;
- de ILS-frequentie en -identificatie;
- de hoogte- en snelheidsbeperkingen;
- de transitiehoogte en het transitieniveau;
- de onderscheppingshoogte van de nadering;
- de hoogte bij doorstart;
- de motivering en het betrouwbaarheidsniveau van elke keuze.

De blokken **Vertrek · Route · Aankomst** kunnen worden ingeklapt om ruimte vrij
te maken in de interface.

### Vluchtopvolging

Het tabblad **Vluchtopvolging** gebruikt de MSFS-positie in realtime om te
tonen:

- de automatisch herkende vluchtfase;
- de grondsnelheid (GS) en de aangewezen snelheid (IAS) die MSFS levert;
- het volgende punt en de afstand ertoe;
- de laterale afwijking ten opzichte van het actieve segment;
- de resterende afstand;
- de volgende hoogte- of snelheidsbeperking;
- de verticale snelheid die nodig is om die beperking te halen;
- het Top of Descent en een indicatieve daalsnelheid op een helling van 3°;
- de afwijking ten opzichte van het geplande verticale profiel.

Het vluchtspoor wordt elke vijf seconden lokaal opgeslagen. Het kan vanuit de
interface worden gepauzeerd, gewist of afgespeeld. Er wordt geen geschiedenis
naar een externe dienst verzonden.

### MCDU-kaart

Het tabblad **MCDU-kaart** bundelt de gegevens die in een Airbus-FMS moeten
worden ingevoerd:

- `FROM/TO`, vluchtnummer en uitwijkhaven;
- Cost Index en kruisniveau;
- ZFW, blok-, taxi-, traject- en reservebrandstof;
- baan, SID, transitie en transitiehoogte;
- route `VIA/TO`;
- STAR, transitie, nadering en VIA;
- QNH, temperatuur, wind, ILS-frequentie en eindkoers;
- RADIO- of BARO-minima en RVR.

### Directe verbinding met MSFS

NaviXav gebruikt SimConnect om:

- de aanwezigheid van de simulator te detecteren;
- een groen of rood lampje in de bovenbalk te tonen;
- de positie van het vliegtuig in realtime te volgen;
- hoogte, hoogte boven de grond, koers, grondsnelheid en verticale snelheid uit
  te lezen;
- luchthavens, banen, procedures, waypoints en radionavigatiemiddelen op te
  halen;
- geleidelijk een lokale database op te bouwen in `data/navixav.sqlite`.

De simulator moet draaien met een geladen vlucht om nieuwe gegevens op te
halen. Reeds gecachete informatie blijft offline beschikbaar.

### Kaart

De kaart omvat:

- een OpenStreetMap-achtergrond;
- de SimBrief-route met haar punten;
- afzonderlijke kleuren voor de SID, het en-routedeel, de STAR en de nadering;
- de banen en de geselecteerde baan;
- de positie en de koers van het vliegtuig;
- een spoor van de verplaatsing;
- een automatische volgmodus;
- zoomen, verschuiven en aanpassen aan de luchthaven of de route;
- optionele gronddetails voor taxibanen en opstelplaatsen.

De gronddetails zijn standaard verborgen om de kaart leesbaar te houden. De knop
**Gronddetails** toont ze wanneer dat nodig is.

### Officiële nationale AIS-kaarten

NaviXav raadpleegt rechtstreeks de publicaties van de nationale autoriteiten,
zonder tussenkomst van EUROCONTROL/EAD:

- Frankrijk: SIA eAIP (`LF`);
- Spanje en de Canarische Eilanden: ENAIRE AIP (`LE`, `GC`, `GE`);
- Nederland: LVNL eAIP (`EH`);
- Verenigde Staten en gedekte gebieden: FAA d-TPP.

Voor deze luchthavens kan NaviXav:

- in het tabblad **Officiële kaarten** alle PDF's van vertrek en aankomst
  tonen, gerangschikt op type;
- elk document in de interface of afzonderlijk openen;
- standaard de SID, STAR of nadering selecteren die bij de huidige vlucht past;
- automatisch de naderingskaart vinden die overeenkomt met de gekozen baan en
  het gekozen naderingstype;
- op verzoek alleen de daadwerkelijk geraadpleegde PDF's downloaden;
- de publicatie in de lokale AIRAC-cache bewaren;
- de officiële kaart in de MCDU-kaart tonen;
- de SIA ILS CAT I-minima uitlezen wanneer het formaat wordt herkend;
- de DA, de DH en de RVR voorstellen vóór validatie.

Uitgelezen waarden worden nooit stilzwijgend toegepast: ze moeten in de
interface worden gevalideerd. De knop **Officiële laag** wordt alleen
aangeboden voor een document met gevalideerde georeferentie. Ze volgt de
kaartkeuze: de PDF van het vertrek kan alleen over het vertrek worden gelegd en
die van de aankomst alleen over de aankomst. Deze regel geldt voor alle bronnen.

Een land wordt pas aan de automatische lijst toegevoegd nadat directe en
stabiele toegang tot zijn officiële PDF's is gevalideerd. Een ontbrekende bron
wordt dus nooit stilzwijgend vervangen door een externe aggregator.

## Vereisten

- Windows 10 of Windows 11, 64-bit;
- Microsoft WebView2 Runtime, automatisch geïnstalleerd door het
  installatieprogramma;
- Microsoft Flight Simulator voor de gegevens en de realtime opvolging;
- een SimBrief-account met een gegenereerd OFP;
- een internetverbinding voor SimBrief, de kaartachtergrond en de nationale
  AIS- of FAA-publicaties.

Het installatieprogramma bevat Python, de bibliotheken, pywebview, de zelfstandige
SimConnect-connector van NaviXav en de ondertekende Microsoft
WebView2-bootstrapper. Geen van deze onderdelen hoeft afzonderlijk te worden
geïnstalleerd. MSFS is niet verplicht om de Demo-modus uit te proberen of om
reeds opgeslagen gegevens te raadplegen.

SimConnect wordt door NaviXav nooit in Windows geïnstalleerd of opnieuw
geïnstalleerd. De applicatie draagt een privékopie van de moderne DLL in haar
eigen map. Als de machine al over SimConnect beschikt, worden de installatie,
de versie en de instellingen daarvan niet vervangen of gewijzigd. Deze
privé-DLL communiceert met de SimConnect-dienst van MSFS: alleen de simulator
moet geïnstalleerd en gestart zijn om live gegevens te ontvangen.

### Talen van de interface

De taal wordt gekozen in **Instellingen**, is meteen actief en blijft op de
computer bewaard. NaviXav biedt interfaces in het Frans, Engels, Duits, Spaans,
Italiaans, Portugees, Nederlands en Pools. Luchtvaartafkortingen,
procedure-identificaties, METAR's en MCDU-waarden blijven bewust in hun
internationale notatie.

## Snelle installatie op Windows

1. Het bestand `NaviXav-Setup-<versie>.exe` downloaden van de laatste
   [GitHub-release](https://github.com/xalacaga/NaviXav/releases/latest).
2. Het installatieprogramma starten.
3. De pagina met de controle van de vereisten nakijken.
4. De voorgestelde map behouden of wijzigen en op **Installeren** klikken.
5. NaviXav starten via het menu Start of de optionele snelkoppeling op het
   bureaublad.

Het installatieprogramma controleert Microsoft WebView2 en installeert het
automatisch als het ontbreekt. De installatie gebeurt voor de huidige gebruiker
en vereist normaal gezien geen beheerdersrechten.

Er is ook een draagbaar archief beschikbaar: pak
`NaviXav-<versie>-windows-x64-portable.zip` uit en start `NaviXav.exe`. Gebruik
op een machine zonder WebView2 eerst het volledige installatieprogramma.

### Vanaf de broncode

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Bij de eerste start doet het script het volgende:

1. Python zoeken;
2. de virtuele omgeving `.venv` aanmaken;
3. NaviXav en de afhankelijkheden installeren;
4. de private lokale dienst starten;
5. de interface openen in het NaviXav-venster.

Volgende starts hergebruiken de reeds geïnstalleerde omgeving.

### Een distributie bouwen

Vanuit PowerShell, in de projectmap:

```powershell
.\scripts\build_windows.ps1
```

Het script:

1. controleert 64-bits Windows, Python en de SimConnect-SDK;
2. installeert ontbrekende bouwgereedschappen;
3. haalt de officiële WebView2-bootstrapper op en verifieert de
   Microsoft-handtekening;
4. voert de tests uit zonder de live MSFS-integratie;
5. levert het installatieprogramma, het draagbare archief en hun
   SHA-256-controlesommen in `release\`.

De in stap 1 genoemde SimConnect-SDK betreft alleen de machine die NaviXav
bouwt. Ze wordt niet op gebruikersmachines geïnstalleerd.

### Distributiebestanden

Na een geslaagde build:

| Bestand | Gebruik |
|---|---|
| `release\NaviXav-Setup-<versie>.exe` | aanbevolen Windows-installatieprogramma |
| `release\NaviXav-<versie>-windows-x64-portable.zip` | draagbare versie |
| `release\*.sha256` | controlesommen van de gedistribueerde bestanden |

De map `release\` wordt bewust genegeerd door Git. De uitvoerbare bestanden zijn
bouwartefacten die in een GitHub-release worden gepubliceerd, geen bronnen die
onder versiebeheer horen.

## Handmatige installatie

Vanuit PowerShell, in de projectmap:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m navixav.desktop
```

Dit commando opent het NaviXav-venster. Voor een diagnose van de lokale dienst
zonder venster:

```powershell
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
```

De dienst blijft dan alleen bereikbaar op `http://127.0.0.1:8765`.

## Configuratie

De dagelijkse configuratie gebeurt via de knop **Instellingen** in de interface.

### SimBrief-account

Vul een van de twee velden in:

- **SimBrief Pilot ID**: numerieke identificatie die in de instellingen van het
  SimBrief-account wordt getoond;
- **SimBrief-gebruikersnaam**: alias van het account.

De Pilot ID wordt aanbevolen. Na het opslaan haalt NaviXav onmiddellijk het
laatst beschikbare OFP op. Bij elke volgende start wordt dat laatste plan
automatisch geladen.

### Beschikbare instellingen

De interface laat ook toe om in te stellen:

- de METAR-bron;
- de voorkeursvolgorde van de naderingen;
- de maximale staartwindcomponent;
- de maximale zijwindcomponent;
- de minimale baanlengte;
- de RNP-capaciteit van het toestel.

In de geïnstalleerde versie worden de waarden bewaard in
`%LOCALAPPDATA%\NaviXav\user_settings.json`.

## Eerste gebruik

1. Een vluchtplan aanmaken in SimBrief.
2. Microsoft Flight Simulator starten en een vlucht laden.
3. NaviXav starten via het menu Start, of met `NaviXav.bat` in
   ontwikkelingsmodus.
4. **Instellingen** openen en de SimBrief Pilot ID opslaan.
5. Wachten tot het laatste OFP automatisch is geladen.
6. Het lampje **MSFS verbonden** rechtsboven controleren.
7. De keuzes voor baan, SID, STAR en nadering nakijken.
8. De beperkingen en de officiële kaart raadplegen.
9. De minima valideren voordat ze in de MCDU worden overgenomen.

Met de knop **Plan aanvullen** kan het laatste OFP opnieuw worden opgehaald
nadat in SimBrief een vlucht is aangemaakt of gewijzigd.

## Gebruik van de kaart

- **Kaartachtergrond**: toont of verbergt OpenStreetMap.
- **Gronddetails**: toont de taxibanen en de opstelplaatsen.
- **Officiële laag**: verschijnt alleen voor de gegeorefereerde kaart van de
  momenteel getoonde luchthaven en regelt de dekking ervan.
- **Volledige route**: kadert de volledige vluchtroute in.
- **Volgen**: houdt het vliegtuig gecentreerd.
- **Aanpassen**: kadert de geselecteerde luchthaven in.
- **+ / −**: wijzigt het zoomniveau.
- **Muiswiel**: zoomt onder de aanwijzer.
- **Slepen**: verschuift de kaart.

Met de luchthavenknoppen schakel je snel tussen de vertrek- en de
aankomstluchthaven.

## Venster en responsieve weergave

NaviXav past de interface automatisch aan bij het schalen:

- boven 1100 px kunnen de kaarten Vertrek, Route en Aankomst naast elkaar
  worden getoond;
- onder 1100 px gaan deze kaarten naar één kolom;
- onder 980 px nemen de werkbalk en de kaartbediening de volledige beschikbare
  breedte in;
- onder 760 px worden de tabbladen scrollbaar, worden de knoppen herverdeeld en
  blijven de tabellen horizontaal raadpleegbaar;
- onder 520 px gaan de statistieken en de complexe panelen naar één kolom.

De kaart reageert op elke wijziging van de venstergrootte en herberekent haar
canvas onmiddellijk. De minimale grootte van het native venster is
720 × 560 pixels.

## Demo-modus

De schakelaar **Demo** laadt een voorbeeldvlucht en simuleert een verplaatsing
op de grond. Zo kun je de interface verkennen zonder SimBrief-account of
simulator.

De Demo-modus staat bij het opstarten altijd uit, zodat NaviXav voorrang geeft
aan het laatste SimBrief-plan.

## De applicatie afsluiten

Gebruik de knop **Afsluiten** in de bovenbalk. NaviXav stopt de server netjes,
sluit het venster en de SimConnect-verbinding en geeft daarna poort `8765` vrij.
Het venster rechtstreeks sluiten geeft hetzelfde resultaat.

In de diagnosemodus `--no-open` zorgt ook `Ctrl+C` in de console voor een
normale afsluiting.

## Startopties

De Windows-starter aanvaardt de volgende opties:

```powershell
.\NaviXav.bat --port 9000
.\NaviXav.bat --no-open
```

- `--port` wijzigt de lokale poort;
- `--no-open` start alleen de lokale dienst, voor diagnose.

Het luisteradres blijft bewust vastgelegd op `127.0.0.1`.

## Aanvullende commando's

NaviXav kan ook vanuit PowerShell worden gebruikt:

```powershell
# Het laatste SimBrief-plan tonen
.\.venv\Scripts\navixav.exe plan

# Een tekstuele MCDU-kaart genereren
.\.venv\Scripts\navixav.exe plan --mcdu

# JSON-uitvoer produceren
.\.venv\Scripts\navixav.exe plan --json

# Luchthavens importeren uit MSFS
.\.venv\Scripts\navixav.exe import LFBO LFPO

# De lokale database bekijken
.\.venv\Scripts\navixav.exe navdata

# De gegevens van een luchthaven tonen
.\.venv\Scripts\navixav.exe airport LFBO --runway 32R
```

## Lokale gegevens

NaviXav gebruikt de volgende locaties:

| Locatie | Inhoud |
|---|---|
| `%LOCALAPPDATA%\NaviXav\user_settings.json` | configuratie van de geïnstalleerde versie |
| `%LOCALAPPDATA%\NaviXav\navixav.sqlite` | navigatiedatabase opgebouwd vanuit MSFS |
| `%LOCALAPPDATA%\NaviXav\cache\` | gecachete nationale AIS- en FAA-kaarten |
| `%LOCALAPPDATA%\NaviXav\webview\` | lokale opslag van het WebView2-venster |
| `%LOCALAPPDATA%\NaviXav\logs\navixav.log` | logboek van de geïnstalleerde versie |
| `data\` en `.venv\` | gegevens en omgeving van de ontwikkelingsmodus |

Deze lokale gegevens, de geheimen en de caches zijn niet bedoeld voor
versiebeheer.

Het logboek registreert starts en afsluitingen, fouten, trage API-oproepen,
ophaaltijden van SimBrief, aanvultijden van MSFS en cachevullingen. Het
registreert noch de Pilot ID, noch de gebruikersnaam, noch de volledige route.
De omvang is beperkt tot 2 MB, met vijf oudere versies die bewaard blijven
(`navixav.log.1` tot `navixav.log.5`).

Bij een eerste toegang tot een luchthaven of een procedure meldt de interface
dat de MSFS-cache wordt gevuld en dat dit enkele tientallen seconden kan duren.
Volgende toegangen hergebruiken de lokale gegevens.

## Git-versiebeheer

De bronrepository is bedoeld om te worden gehost op:
`https://github.com/xalacaga/NaviXav.git`.

Het bestand `.gitignore` sluit met name uit:

- `.env`, de gebruikersinstellingen en de lokale databases;
- `.claude/`, `CLAUDE.md`, `.codex/`, `AGENTS.md` en `CODEX.md`;
- de Graphify-gegevens en `graphify-out/`;
- de Python-omgevingen, testcaches en bouwuitvoer;
- `dist\`, `build\` en `release\`.

De Claude-/Codex-geheugens kunnen dus lokaal worden bijgehouden zonder in de
Git-repository te worden gepubliceerd.

### Automatische updates

Bij het opstarten raadpleegt NaviXav uitsluitend de laatste publieke release
van de repository `xalacaga/NaviXav`. Als de versie hoger is dan de
geïnstalleerde, verschijnt er een knop **Update** in de bovenbalk. De
installatie begint pas na bevestiging door de gebruiker.

Het installatieprogramma wordt gedownload naar
`%LOCALAPPDATA%\NaviXav\updates\`, waarna de SHA-256-controlesom wordt
vergeleken met de door GitHub gepubliceerde. Ontbreekt de controlesom of wijkt
ze af, dan wordt het bestand verwijderd en nooit uitgevoerd. Een storing van
GitHub of van het internet blokkeert noch het opstarten, noch de vluchtfuncties.

De repository is openbaar leesbaar. Een gebruiker kan de code inzien en releases
downloaden zonder GitHub-account, maar alleen gemachtigde medewerkers kunnen
naar de repository schrijven.

### Versie en releasenotities

De versie volgt het semantische formaat `MAJOR.MINOR.PATCH`. Conventionele
commitberichten bepalen automatisch het volgende niveau:

- `feat:` levert normaal gezien een minor-versie op;
- `fix:` levert een patch-versie op;
- `BREAKING CHANGE` of `!:` levert een major-versie op;
- de overige wijzigingen leveren een patch-versie op.

De versie en de notities lokaal voorbereiden:

```powershell
.\scripts\prepare_release.ps1 -Bump auto
```

Het installatieprogramma, het draagbare archief, de controlesommen en de
notities publiceren in een GitHub-release:

```powershell
.\scripts\publish_release.ps1 -Bump auto
```

Het tweede script vereist een schone repository en een geauthenticeerde GitHub
CLI. Het voert de tests uit, bouwt de leveringen, maakt de commit en de tag van
de versie aan, pusht `main` en de tag en maakt vervolgens de GitHub-release aan.
`CHANGELOG.md` bewaart de geschiedenis en `RELEASE_NOTES.md` bevat de notities
van de huidige versie.

## Probleemoplossing

### Poort 8765 is al in gebruik

Waarschijnlijk staat er nog een NaviXav-instantie open. Sluit het venster ervan
of klik op **Afsluiten** in de interface. Het uitvoerbaar bestand detecteert een
bestaande instantie; als een andere applicatie 8765 bezet, kiest het automatisch
een vrije poort tussen 8766 en 8775.

Om het proces te identificeren:

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

Het is ook mogelijk om de applicatie op een andere poort te starten:

```powershell
.\NaviXav.bat --port 9000
```

### Het NaviXav-venster opent niet

- het volledige installatieprogramma opnieuw uitvoeren zodat het WebView2
  controleert;
- nagaan of Windows en Microsoft Edge WebView2 Runtime up-to-date zijn;
- `%LOCALAPPDATA%\NaviXav\logs\navixav.log` raadplegen;
- nagaan of een antivirusprogramma `NaviXav.exe` of de processen
  `msedgewebview2.exe` niet blokkeert.

Het draagbare archief kan WebView2 niet zelf installeren. Gebruik op een machine
zonder dit onderdeel `NaviXav-Setup-<versie>.exe`.

### Het MSFS-lampje blijft rood

- nagaan of de simulator draait;
- een vlucht volledig laden;
- enkele seconden wachten en daarna op het lampje klikken;
- het installatieprogramma opnieuw uitvoeren als de privékopie van
  `SimConnect.dll` die met NaviXav wordt geleverd, is verwijderd of door een
  antivirusprogramma in quarantaine is geplaatst.

### Er wordt geen SimBrief-plan geladen

- de Pilot ID of de gebruikersnaam controleren in **Instellingen**;
- een OFP aanmaken op SimBrief voordat het ophalen opnieuw wordt geprobeerd;
- de internetverbinding controleren.

### Een officiële kaart is niet beschikbaar

- nagaan of het ICAO-voorvoegsel gedekt is door SIA, ENAIRE, LVNL of FAA;
- de internetverbinding controleren;
- bevestigen dat de baan en de nadering zijn bepaald;
- de minima handmatig invoeren als het uitlezen niet beschikbaar is.

## Huidige beperkingen

- de werkelijk toegestane procedure kan afwijken van het plan naargelang de
  ATIS, het weer en de ATC-instructies;
- de minima hangen af van de categorie van het vliegtuig, de uitrusting en de
  operationele omstandigheden;
- het automatisch uitlezen van de minima is beperkt tot herkende SIA-formaten;
- een PDF zonder gevalideerde georeferentie blijft raadpleegbaar, maar kan niet
  als laag worden gebruikt;
- nieuwe MSFS-gegevens vereisen dat de simulator bereikbaar is.

Bevestig belangrijke informatie altijd voordat ze in de simulator wordt
ingevoerd.

## Architectuur en vertrouwelijkheid

- `navixav/desktop.py` beheert het native venster en de levenscyclus van het
  proces;
- `navixav/web/app.py` levert de FastAPI-API die uitsluitend aan `127.0.0.1` is
  gebonden;
- `navixav/web/static/` bevat de responsieve HTML/CSS/JavaScript-interface;
- `navixav/planner/` vult het IFR-plan aan;
- `navixav/navdata/` bouwt de uit MSFS afgeleide database op en bevraagt ze;
- `navixav/live/` verzorgt de SimConnect-opvolging;
- `navixav/sia.py`, `navixav/faa.py` en `navixav/national_aip.py` beheren de
  officiële publicaties.

De lokale dienst luistert nooit op het externe netwerk. De SimBrief Pilot ID, de
voorkeuren, het vluchtspoor en de gecachete PDF's blijven op de machine. Alleen
de verzoeken die nodig zijn voor SimBrief, OpenStreetMap, het weer en de
officiële AIS-publicaties verlaten de computer.

## Tests

Het reproduceerbare profiel dat wordt gebruikt om de distributie te bouwen:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```

De tests met de markering `live_msfs` bevragen een daadwerkelijk gestarte
simulator en maken dus geen deel uit van de automatische controle van het
installatieprogramma.
