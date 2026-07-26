# NaviXav

**Documentatie:** [Français](README.md) · [English](README.en.md) ·
[Deutsch](README.de.md) · [Español](README.es.md) ·
[Italiano](README.it.md) · [Português](README.pt.md) · Nederlands ·
[Polski](README.pl.md)

NaviXav is een lokale IFR-vluchtassistent voor Microsoft Flight Simulator. De
app haalt automatisch het laatste SimBrief-OFP op, vult terminalinformatie aan
met simulatorgegevens en toont de waarden voor vluchtvoorbereiding en
MCDU-invoer.

NaviXav gebruikt een eigen responsief Windows-venster op basis van Microsoft
WebView2. Er wordt geen externe browser geopend. De privéservice luistert
alleen op `127.0.0.1`; instellingen, navigatiegegevens, kaarten en caches
blijven op de computer.

> NaviXav is uitsluitend bedoeld voor vluchtsimulatie. Controleer de gegevens
> altijd aan de hand van actuele officiële publicaties en ATC-instructies.

## Functies

- automatisch ophalen van het laatste SimBrief-vluchtplan;
- SimBrief Pilot ID of gebruikersnaam instellen via de interface;
- volledige route met voortgang van het vliegtuig;
- gemotiveerde selectie van baan, SID, STAR, transities en nadering;
- hoogte-/snelheidsbeperkingen, transitiehoogte/-niveau, ILS,
  interceptiehoogte en hoogte voor de gemiste nadering;
- vliegtuig-, dispatch-, gewichts-, brandstof- en MCDU-gegevens;
- QNH onder de windgegevens;
- realtime MSFS-tracking en lokaal afspeelbaar vluchtspoor;
- route op een OpenStreetMap-achtergrond;
- directe toegang tot officiële pdf’s voor vertrek en aankomst;
- kaartoverlay alleen bij gevalideerde georeferentie;
- navigatie rechtstreeks uit MSFS, zonder Little Navmap, Navigraph of
  EUROCONTROL.

## Vereisten en installatie

- 64-bits Windows 10 of Windows 11;
- Microsoft Flight Simulator voor live- en navigatiegegevens;
- SimBrief-account met een reeds gegenereerd OFP;
- Internet voor SimBrief, kaart en officiële AIS/FAA-publicaties.

Start `NaviXav-Setup-0.1.0.exe`, controleer de vereisten en kies
**Installeren**. Python en bibliotheken zijn inbegrepen. WebView2 wordt alleen
geïnstalleerd als het ontbreekt. Je kunt ook het draagbare archief uitpakken en
`NaviXav.exe` starten.

### Autonome SimConnect

NaviXav installeert, registreert, herinstalleert of vervangt nooit de
systeemversie van SimConnect. Een moderne privé-`SimConnect.dll` staat alleen
in de NaviXav-map. Een bestaande installatie blijft onaangeroerd. MSFS moet
draaien omdat de connector communiceert met de SimConnect-service van de
simulator.

## Eerste configuratie

Kies in **Instellingen** de taal, voer de SimBrief Pilot ID of gebruikersnaam
in en stel METAR-bron en voorkeuren voor nadering, baan en vliegtuig in. De taal
wordt direct toegepast en lokaal opgeslagen. Frans, Engels, Duits, Spaans,
Italiaans, Portugees, Nederlands en Pools zijn beschikbaar.

Bij het opstarten zoekt NaviXav altijd het laatste beschikbare OFP. Het
vluchtplan wordt nog steeds op de SimBrief-website gegenereerd.

## Officiële kaarten

Het tabblad **Officiële kaarten** toont documenten voor vertrek en aankomst van
ondersteunde bronnen zoals SIA, ENAIRE, LVNL en FAA d-TPP. Pdf’s kunnen in
NaviXav worden bekeken. De overlayknop blijft verborgen wanneer de geografische
uitlijning niet is gevalideerd.

## Broncode en distributie

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Distributie bouwen:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

Installer, draagbaar archief en SHA-256-controlesommen worden in `release\`
gemaakt. De MSFS SimConnect SDK is alleen nodig op de buildcomputer.

## Problemen en privacy

- Geen plan: controleer SimBrief-identificatie, OFP en Internet.
- Rode MSFS-status: start MSFS, laad een vlucht volledig en wacht even.
- Geen venster: gebruik de volledige installer om WebView2 te herstellen.
- Poort 8765 bezet: sluit de vorige NaviXav-instantie.

NaviXav verzendt geen telemetrie. Instellingen, caches en vluchthistorie blijven
lokaal; alleen SimBrief, OpenStreetMap en aangevraagde officiële bronnen worden
benaderd.

Het roterende diagnoselogboek staat in
`%LOCALAPPDATA%\NaviXav\logs\navixav.log`. Het bevat fouten en tijdmetingen,
maar geen SimBrief-ID en geen volledige route.

## Gedetailleerde werking

### Vluchtplan en procedures

Bij het starten haalt NaviXav de laatst gemaakte SimBrief-OFP op: vertrek,
bestemming, uitwijkhaven, route, kruishoogte, vliegtuig, brandstof, gewichten
en METAR. Het vluchtplan zelf wordt nog op SimBrief gemaakt. Gegevens die
rechtstreeks uit MSFS komen vullen baan, SID, transitie, STAR en nadering aan;
een andere ATIS- of ATC-toewijzing kan in de interface worden opgelegd. Het
blok Vertrek–Route–Aankomst kan worden ingeklapt en het actieve routepunt
verandert van kleur.

### Begeleiding, nadering en MCDU

De begeleiding toont afstand, peiling, gewenste hoogte, volgende beperking,
grondsnelheid (GS) en indicated airspeed (IAS). Indien beschikbaar worden
ILS-frequentie en -koers, glijhoek, interceptiehoogte, baandrempelhoogte,
minima en missed-approachhoogte getoond. De officiële kaart en ATC blijven
leidend.

Het MCDU-blad groepeert waarden voor INIT, F-PLN, RAD NAV, PERF TAKEOFF en PERF
APPR: luchthavens, vluchtnummer, cost index, cruise, banen, procedures,
transities, ILS, QNH, wind, temperatuur, minima en bekende startgegevens.

### Kaart, opname en officiële documenten

De SimBrief-route wordt over OpenStreetMap getekend met aparte stijlen voor
SID, route, STAR en nadering. Gronddetails worden op zoomniveau gefilterd. Het
lokale vluchtspoor kan worden afgespeeld en wordt nooit geüpload.

Vertrek en aankomst zijn vooraf geselecteerd voor officiële pdf’s. Ondersteund
zijn SIA Frankrijk, ENAIRE Spanje, LVNL Nederland en FAA d-TPP Verenigde
Staten. De overlayknop verschijnt alleen bij gevalideerde georeferentie; een
gewone pdf blijft leesbaar, maar wordt niet bij benadering uitgelijnd.

### Lokale gegevens en cache

Instellingen staan in `%LOCALAPPDATA%\NaviXav\user_settings.json`,
navigatiegegevens in `%LOCALAPPDATA%\NaviXav\navixav.sqlite` en logboeken onder
`%LOCALAPPDATA%\NaviXav\logs`. De eerste keer dat een luchthaven of procedure
wordt geladen kan het vullen van de MSFS-cache tientallen seconden duren.

## Automatische updates en Releases

Bij het starten controleert NaviXav de nieuwste openbare Release van
`xalacaga/NaviXav`. Bij een nieuwere versie verschijnt **Bijwerken**. Na
bevestiging wordt de installer naar `%LOCALAPPDATA%\NaviXav\updates`
gedownload, met de gepubliceerde SHA-256 gecontroleerd en gestart. Een
netwerkfout blokkeert de vluchtfuncties niet.

De repository is openbaar leesbaar; alleen bevoegde medewerkers mogen
schrijven. Versies volgen `MAJOR.MINOR.PATCH`: `feat:` verhoogt minor, `fix:`
patch en `BREAKING CHANGE` of `!:` major. Notities staan in
`RELEASE_NOTES.md` en de geschiedenis in `CHANGELOG.md`.

```powershell
.\scripts\prepare_release.ps1 -Bump auto
.\scripts\publish_release.ps1 -Bump auto
```

Publicatie vereist een schone repository en aangemelde GitHub CLI. Het script
test, bouwt, tagt en publiceert installer, draagbaar archief, SHA-256-bestanden
en release-opmerkingen.

## Diagnoseopdrachten

```powershell
.\NaviXav.bat
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
.\scripts\build_windows.ps1
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```
