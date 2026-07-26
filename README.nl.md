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
