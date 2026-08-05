# NaviXav

**Offizielle Website:** [navixav.fr](https://navixav.fr/en)

**Dokumentation:** [Français](README.fr.md) · [English](README.md) · Deutsch ·
[Español](README.es.md) · [Italiano](README.it.md) ·
[Português](README.pt.md) · [Nederlands](README.nl.md) ·
[Polski](README.pl.md)

NaviXav ist eine lokale Anwendung zur IFR-Flugunterstützung für Microsoft
Flight Simulator. Sie ruft den letzten SimBrief-Flugplan ab, ergänzt die
Terminalinformationen mit Daten aus dem Simulator und stellt alles in einer
Oberfläche dar, die auf die Flugvorbereitung und die MCDU-Eingabe zugeschnitten
ist.

Die Anwendung besitzt ein eigenes Windows-Fenster. Ihre Oberfläche wird von
Microsoft WebView2 dargestellt und kommuniziert ausschließlich mit einem
lokalen Dienst auf `127.0.0.1`. Ein externer Browser wird nur geöffnet, wenn
der Benutzer **SimBrief-Plan erstellen** anklickt, um den offiziellen Editor zu öffnen.
Einstellungen, Navigationsdatenbank und Caches verbleiben auf dem Rechner.

Das Fenster ist vollständig skalierbar. Die Oberfläche ordnet Bereiche,
Bedienelemente, Registerkarten und die Kartenhöhe je nach verfügbarem Platz neu
an, bis zu einer Mindestgröße von 720 × 560 Pixeln.

> NaviXav ist ausschließlich für die Flugsimulation bestimmt. Die angezeigten
> Informationen müssen mit den amtlichen Veröffentlichungen und den geltenden
> ATC-Anweisungen abgeglichen werden.

## Funktionen

### SimBrief-Flugplan

- automatischer Abruf des letzten OFP beim Start;
- Unterstützung der SimBrief-Pilot-ID oder des Benutzernamens;
- Anzeige der vollständigen Route vom Start- bis zum Zielort;
- Hervorhebung des nächsten Streckenpunkts anhand der tatsächlichen
  Flugzeugposition, bereits überflogene Punkte werden abgeschwächt;
- Massen, Kraftstoff, Flugzeit, Ausweichflughafen und Dispatch-Daten;
- Angaben zum Luftfahrzeug, Kennzeichen und gemeldete Ausrüstung.

### Flugwetter

- wesentliche METAR- und TAF-Daten für Abflug, Ankunft und Ausweichflugplatz;
- Wind und Temperatur im Reiseflug aus dem SimBrief-OFP;
- im Modus **Live-METAR** automatische Aktualisierung alle fünf Minuten über
  aviationweather.gov sowie eine Schaltfläche zur sofortigen Aktualisierung;
- grafische Darstellung von Wetter, Wind, Sicht und Wolkenuntergrenze, ohne
  Startbahn oder Verfahren des Flugplans automatisch zu ändern.

### IFR-Vorbereitung

NaviXav ergänzt und zeigt:

- die Startbahn und die Landebahn;
- die SID und ihre Transition;
- die STAR und ihre Transition;
- den Anflug und seine VIA;
- Frequenz und Kennung des ILS;
- Höhen- und Geschwindigkeitsbeschränkungen;
- die Transition Altitude und das Transition Level;
- die Intercept-Höhe des Anflugs;
- die Höhe des Fehlanflugs;
- die Begründung und das Vertrauensniveau jeder Auswahl.

Die Blöcke **Abflug · Route · Ankunft** lassen sich einklappen, um Platz in der
Oberfläche zu gewinnen.

### Flugverfolgung

Die Registerkarte **Flugverfolgung** nutzt die MSFS-Position in Echtzeit und
zeigt:

- die automatisch erkannte Flugphase;
- die von MSFS gelieferte Geschwindigkeit über Grund (GS) und die angezeigte
  Fluggeschwindigkeit (IAS);
- den nächsten Punkt und dessen Entfernung;
- die seitliche Abweichung vom aktiven Segment;
- die Restentfernung;
- die nächste Höhen- oder Geschwindigkeitsbeschränkung;
- die zum Erreichen dieser Beschränkung erforderliche Vertikalrate;
- den Top of Descent und eine Richt-Sinkrate auf einem 3°-Profil;
- die Abweichung vom geplanten Vertikalprofil.

#### Flugzeugkonfiguration

Der Block **Flugzeugkonfiguration** liest Fahrwerk, Klappen, Bremsklappen,
Parkbremse und die sieben Außenlichter direkt aus MSFS, ebenso die
Höhenmessereinstellung, die Autopilotmodi, die gewählte Höhe, den Kraftstoff an
Bord und den tatsächlichen Wind. Die Einheiten werden beim Simulator angefragt
und nie nachträglich umgerechnet.

Für Klappen, Bremsklappen und Parkbremse vergleicht NaviXav die offiziellen
SimVars für Hebel, effektive Position, Flächenposition und Cockpitanzeige.
Flugzeugkonfiguration und Flugereignisse bleiben dadurch aktiv, wenn ein
Drittanbieterflugzeug einen MSFS-Standardwert einfriert.
Ein eigener Adapter für die Fenix A319/A320/A321 liest alle drei Cockpithebel
direkt aus. Änderungen an Klappen, Bremsklappen und Parkbremse werden daher auch
bei abgeschalteten Triebwerken und Hydrauliksystemen gemeldet.

#### Visuelle Warnungen

NaviXav überwacht diese Konfiguration und meldet Versäumnisse: Fahrwerk im
Anflug nicht ausgefahren, Klappen oder Bremsklappen nicht konfiguriert, Strobes
oder Landescheinwerfer aus, Parkbremse noch gesetzt, QNH oder Standardeinstellung
beim Überschreiten der Übergangshöhe nicht gesetzt, gewählte Höhe über der
nächsten Beschränkung, ILS-Frequenz abweichend von der geplanten,
Enteisung in Vereisungsbedingungen abgeschaltet, Kraftstoff unter der
Endreserve.

Drei Vorkehrungen verhindern Fehlalarme:

- Regeln, die ein einfahrbares Fahrwerk, Klappen oder Bremsklappen
  voraussetzen, werden nur bewertet, wenn der Simulator deren Vorhandensein
  bestätigt;
- eine Bedingung muss einige Sekunden anliegen, bevor eine Warnung ausgelöst
  wird — das verhindert Flackern beim Überschreiten einer Schwelle;
- Warnungen sind bei beschleunigter Simulationsgeschwindigkeit ausgesetzt.

Jede Warnung wird automatisch gelöscht und erneut aktiviert, sobald die
Korrektur stabil ist; ein Klick quittiert sie weiterhin sofort. Eine Plakette
`MASTER CAUTION` oder `MASTER WARNING` fasst die
Lage zusammen, und das gesamte System lässt sich im Panel abschalten. Das
Blinken, das kritischen Warnungen vorbehalten ist, entfällt, wenn das System
reduzierte Bewegung anfordert.

Nach der Landung speichert das lokale Logbuch eine kurze Flugzusammenfassung
und eine begrenzte Ereigniszeitleiste: Flugphasen, Start- und Landebahn mit dem
beobachteten Wind sowie stabile Änderungen an Fahrwerk, Klappen, Spoilern,
Parkbremse, Beleuchtung und Autopilotmodi. Die Ereignisse werden als Daten
gespeichert und in der aktuell gewählten Sprache wiedergegeben. Alle
Zusammenfassungen können in der Oberfläche gelöscht werden; Flugdaten werden
nicht an externe Dienste gesendet.

### MCDU-Blatt

Die Registerkarte **MCDU-Blatt** passt ihre Seiten an den Flugzeugtyp an:
Airbus-MCDU, Boeing-CDU oder ein allgemeines FMS für andere Flugzeuge.
Nicht automatisierbare Startleistungswerte werden nicht angeboten:

- `FROM/TO`, Flugnummer und Ausweichflughafen;
- Cost Index und Reiseflugfläche;
- ZFW, Block-, Roll-, Strecken- und Reservekraftstoff;
- Bahn, SID, Transition und Transition Altitude;
- Route `VIA/TO`;
- STAR, Transition, Anflug und VIA;
- QNH, Temperatur, Wind, ILS-Frequenz und Endanflugkurs;
- RADIO- oder BARO-Minima und RVR.

### Direkte Verbindung zu MSFS

NaviXav nutzt SimConnect, um:

- das Vorhandensein des Simulators zu erkennen;
- eine grüne oder rote Anzeige in der oberen Leiste darzustellen;
- die Flugzeugposition in Echtzeit zu verfolgen;
- Höhe, Höhe über Grund, Steuerkurs, Geschwindigkeit über Grund und
  Vertikalgeschwindigkeit auszulesen;
- Flughäfen, Bahnen, Verfahren, Wegpunkte und Funknavigationsanlagen
  abzurufen;
- schrittweise eine lokale Datenbank in `data/navixav.sqlite` aufzubauen.

Der Simulator muss mit geladenem Flug laufen, um neue Daten abzurufen. Bereits
zwischengespeicherte Informationen bleiben offline verfügbar.

Wenn das ausführliche SimBrief-Navlog validierte Koordinaten enthält, verwendet
NaviXav sie sofort für die Streckendarstellung und fragt MSFS Facilities nur
für fehlende Positionen ab. Veröffentlichte Verfahrensverknüpfungen vermeiden
ebenfalls unnötige Positionsabfragen. Dadurch wird der erste Plan schneller
geladen; Korridorprüfungen und der lokale MSFS-Cache bleiben als Absicherung
erhalten.

### Karte

Die Karte umfasst:

- einen OpenStreetMap-Hintergrund;
- die SimBrief-Route mit ihren Punkten;
- unterschiedliche Farben für SID, Streckenteil, STAR und Anflug;
- die Bahnen und die ausgewählte Bahn;
- Position und Steuerkurs des Flugzeugs;
- eine Spur der Bewegung;
- einen automatischen Folgemodus;
- Zoom, Verschieben und Einpassen auf Flughafen oder Route;
- die vollständige tatsächlich geflogene Spur von Abflug bis Ankunft;
- eine frei wählbare Farbe der Flugspur;
- die Wahl zwischen OpenStreetMap Standard, OpenTopoMap, CartoDB Positron
  (hell) und CartoDB Dark Matter (dunkel, Cockpit) – direkt in der Kartenleiste
  oder in den Einstellungen.

### Rollen am Boden

Die Registerkarte **Rollen** zeigt einen eigenen Flugplatzplan, getrennt von
der Flugkarte und ausschließlich aus nativen MSFS-Einrichtungen aufgebaut:

- die Zeichenfläche nutzt den gesamten verfügbaren Platz, auch in kompakten Fenstern;
- ein dunkler Luftfahrthintergrund mit metrischem Raster und Nordpfeil liefert
  Maßstab und Orientierung ohne den Ballast einer Straßenkarte;
- Bahnen, Hauptrollwege, Standplätze und Flugzeug werden visuell priorisiert;
- benannte Rollwege bleiben auch dann sichtbar, wenn MSFS sie als allgemeine
  `path`-Segmente einstuft; nur unbenannte Nebenverbindungen und
  Standplatzzufahrten sind standardmäßig verborgen und werden mit
  **Nebenwege** bei Bedarf eingeblendet;
- beim Abflug schlägt NaviXav innerhalb von 180 m um einen Standplatz automatisch
  eine Route von dort zur gewählten Bahn vor;
- ein Klick auf einen anderen Standplatz ersetzt den Vorschlag sofort; bei der
  Ankunft bleibt der Zielstandplatz eine manuelle Auswahl;
- Route, Haltepunkte, nächste Anweisung und Reststrecke werden klar dargestellt;
- nach einer Abweichung wird ab der tatsächlichen Flugzeugposition neu geplant.

SimConnect-Parkwege dienen nur zur Zuordnung eines Standplatzes zum Rollnetz.
Sie können nicht als künstliche Abkürzung quer über Bahnen verwendet werden.

### Amtliche nationale AIS-Karten

NaviXav fragt die Veröffentlichungen der nationalen Behörden direkt ab, ohne
den Umweg über EUROCONTROL/EAD:

- Frankreich: SIA eAIP (`LF`);
- Spanien und Kanarische Inseln: ENAIRE AIP (`LE`, `GC`, `GE`);
- Niederlande: LVNL eAIP (`EH`);
- Schweden: LFV eAIP (`ES`);
- Belgien und Luxemburg: skeyes eAIP (`EB`, `EL`);
- Österreich: Austro Control eAIP (`LO`);
- Vereinigtes Königreich: NATS eAIP (`EG`);
- Vereinigte Staaten und abgedeckte Gebiete: FAA d-TPP.

Für diese Flugplätze kann NaviXav:

- in der Registerkarte **Amtliche Karten** alle PDFs von Abflug und Ankunft
  nach Typ geordnet darstellen;
- jedes Dokument in der Oberfläche oder separat öffnen;
- standardmäßig die zum aktuellen Flug passende SID, STAR oder den Anflug
  auswählen;
- die Anflugkarte automatisch finden, die zur gewählten Bahn und Anflugart
  passt;
- nur die tatsächlich eingesehenen PDFs bei Bedarf herunterladen;
- die Veröffentlichung im lokalen AIRAC-Cache behalten;
- die amtliche Karte im MCDU-Blatt anzeigen;
- SIA-Minima für ILS CAT I auslesen, sofern das Format erkannt wird;
- DA, DH und RVR vor der Bestätigung vorschlagen.

Ausgelesene Werte werden niemals stillschweigend übernommen: Sie müssen in der
Oberfläche bestätigt werden. Die Schaltfläche **Amtliche Überlagerung** wird nur
für ein Dokument mit geprüfter Georeferenzierung angeboten. Sie folgt der
Kartenauswahl: Das PDF des Abflugs kann nur über den Abflug gelegt werden, das
der Ankunft nur über die Ankunft. Diese Regel gilt für alle Quellen gleich.

Ein Land wird erst dann in die automatische Liste aufgenommen, wenn ein
direkter und stabiler Zugriff auf seine amtlichen PDFs geprüft wurde. Eine
fehlende Quelle wird daher nie stillschweigend durch einen fremden Aggregator
ersetzt.

## Voraussetzungen

- Windows 10 oder Windows 11, 64 Bit;
- Microsoft WebView2 Runtime, vom Installationsprogramm automatisch
  eingerichtet;
- Microsoft Flight Simulator für Daten und Echtzeitverfolgung;
- ein SimBrief-Konto mit erzeugtem OFP;
- eine Internetverbindung für SimBrief, den Kartenhintergrund und die
  nationalen AIS- oder FAA-Veröffentlichungen.

Das Installationsprogramm enthält Python, die Bibliotheken, pywebview, den
eigenständigen SimConnect-Konnektor von NaviXav und den signierten Microsoft
WebView2-Bootstrapper. Keines dieser Werkzeuge muss separat installiert werden.
MSFS ist nicht erforderlich, um den Demo-Modus auszuprobieren oder bereits
gespeicherte Daten einzusehen.

SimConnect wird von NaviXav niemals in Windows installiert oder neu
installiert. Die Anwendung führt eine private Kopie der modernen DLL in ihrem
eigenen Ordner mit. Ist SimConnect auf dem Rechner bereits vorhanden, werden
Installation, Version und Einstellungen weder ersetzt noch verändert. Diese
private DLL kommuniziert mit dem SimConnect-Dienst von MSFS: Nur der Simulator
muss installiert und gestartet sein, um Live-Daten zu empfangen.

### Sprachen der Oberfläche

Die Sprache wird unter **Einstellungen** gewählt, wirkt sofort und bleibt auf
dem Rechner gespeichert. NaviXav bietet die Oberflächen auf Französisch,
Englisch, Deutsch, Spanisch, Italienisch, Portugiesisch, Niederländisch und
Polnisch. Luftfahrtabkürzungen, Verfahrenskennungen, METAR und MCDU-Werte
bleiben bewusst in ihrer internationalen Schreibweise.

## Schnellinstallation unter Windows

1. Die Datei `NaviXav-Setup-<Version>.exe` aus dem neuesten
   [GitHub-Release](https://github.com/xalacaga/NaviXav/releases/latest)
   herunterladen.
2. Das Installationsprogramm starten.
3. Die Seite zur Prüfung der Voraussetzungen kontrollieren.
4. Den vorgeschlagenen Ordner beibehalten oder ändern, dann auf
   **Installieren** klicken.
5. NaviXav über das Startmenü oder die optionale Desktopverknüpfung starten.

Das Installationsprogramm prüft Microsoft WebView2 und installiert es
automatisch, falls es fehlt. Die Installation erfolgt für den aktuellen
Benutzer und erfordert normalerweise keine Administratorrechte.

Ein portables Archiv steht ebenfalls bereit: `NaviXav-<Version>-windows-x64-portable.zip`
entpacken, dann `NaviXav.exe` starten. Auf einem Rechner ohne WebView2 zuerst
das vollständige Installationsprogramm verwenden.

### Aus den Quellen

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Beim ersten Start führt das Skript Folgendes aus:

1. Python suchen;
2. die virtuelle Umgebung `.venv` anlegen;
3. NaviXav und seine Abhängigkeiten installieren;
4. den privaten lokalen Dienst starten;
5. die Oberfläche im NaviXav-Fenster öffnen.

Spätere Starts verwenden die bereits installierte Umgebung erneut.

### Eine Distribution erstellen

In PowerShell, im Projektordner:

```powershell
.\scripts\build_windows.ps1
```

Das Skript:

1. prüft 64-Bit-Windows, Python und das SimConnect-SDK;
2. installiert fehlende Build-Werkzeuge;
3. lädt den offiziellen WebView2-Bootstrapper und prüft dessen
   Microsoft-Signatur;
4. führt die Tests ohne die Live-MSFS-Integration aus;
5. erzeugt das Installationsprogramm, das portable Archiv und deren
   SHA-256-Prüfsummen in `release\`.

Das in Schritt 1 genannte SimConnect-SDK betrifft nur den Rechner, der NaviXav
erstellt. Es wird nicht auf Benutzerrechnern installiert.

### Distributionsdateien

Nach einem erfolgreichen Build:

| Datei | Verwendung |
|---|---|
| `release\NaviXav-Setup-<Version>.exe` | empfohlenes Windows-Installationsprogramm |
| `release\NaviXav-<Version>-windows-x64-portable.zip` | portable Fassung |
| `release\*.sha256` | Prüfsummen der ausgelieferten Dateien |

Der Ordner `release\` wird von Git bewusst ignoriert. Die ausführbaren Dateien
sind Build-Artefakte, die in einem GitHub-Release veröffentlicht werden, keine
zu versionierenden Quellen.

## Manuelle Installation

In PowerShell, im Projektordner:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m navixav.desktop
```

Dieser Befehl öffnet das NaviXav-Fenster. Für eine Diagnose des lokalen
Dienstes ohne Fenster:

```powershell
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
```

Der Dienst ist dann nur noch über `http://127.0.0.1:8765` erreichbar.

## Konfiguration

Die laufende Konfiguration erfolgt über die Schaltfläche **Einstellungen** in
der Oberfläche.

### SimBrief-Konto

Eines der beiden Felder ausfüllen:

- **SimBrief-Pilot-ID**: numerische Kennung aus den Einstellungen des
  SimBrief-Kontos;
- **SimBrief-Benutzername**: Alias des Kontos.

Die Pilot-ID wird empfohlen. Nach dem Speichern ruft NaviXav sofort den letzten
verfügbaren OFP ab. Bei jedem weiteren Start wird dieser letzte Plan
automatisch geladen.

### Verfügbare Einstellungen

In der Oberfläche lassen sich außerdem einstellen:

- die METAR-Quelle;
- die Rangfolge der Anflugarten;
- die maximale Rückenwindkomponente;
- die maximale Seitenwindkomponente;
- die Mindestbahnlänge;
- die RNP-Fähigkeit des Luftfahrzeugs.

In der installierten Fassung werden die Werte in
`%LOCALAPPDATA%\NaviXav\user_settings.json` gespeichert.

## Erste Verwendung

1. Einen Flugplan in SimBrief erzeugen.
2. Microsoft Flight Simulator starten und einen Flug laden.
3. NaviXav über das Startmenü starten, im Entwicklungsmodus mit `NaviXav.bat`.
4. **Einstellungen** öffnen und die SimBrief-Pilot-ID speichern.
5. Das automatische Laden des letzten OFP abwarten.
6. Die Anzeige **MSFS verbunden** oben rechts prüfen.
7. Die Auswahl von Bahn, SID, STAR und Anflug kontrollieren.
8. Beschränkungen und amtliche Karte einsehen.
9. Die Minima prüfen, bevor sie in die MCDU übertragen werden.

Die Schaltfläche **Plan vervollständigen** ruft den letzten OFP erneut ab,
nachdem ein Flug in SimBrief erzeugt oder geändert wurde.

## Verwendung der Karte

- **Kartenhintergrund**: blendet die gewählte freie Karte ein oder aus.
- **Hintergrundauswahl**: wechselt direkt auf der Karte zwischen OpenStreetMap
  Standard, OpenTopoMap, CartoDB Positron (hell) und CartoDB Dark Matter
  (dunkel, Cockpit). Die Wahl wird in den Einstellungen gespeichert.
- **Einstellungen**: bietet dieselbe Hintergrundauswahl sowie die Farbe der
  vollständigen Flugspur.
- **Amtliche Überlagerung**: erscheint nur für das georeferenzierte Blatt des
  aktuell angezeigten Flugplatzes und regelt dessen Deckkraft.
- **Gesamte Route**: rahmt die vollständige Flugroute ein.
- **Folgen**: hält das Flugzeug in der Mitte.
- **Einpassen**: rahmt den ausgewählten Flughafen ein.
- **+ / −**: ändert die Zoomstufe.
- **Mausrad**: zoomt unter dem Zeiger.
- **Ziehen**: verschiebt die Karte.

Mit den Flughafenschaltflächen wechselt man schnell zwischen Start- und
Zielflugplatz.

## Fenster und responsive Darstellung

### Zugriff über Telefon und Tablet im lokalen Netzwerk

**Zugriff für Telefon und Tablet** in den **Einstellungen** aktivieren,
speichern und NaviXav neu starten. Die auf dem PC angezeigte geschützte Adresse
wird auf einem Gerät im selben WLAN geöffnet. Die mobile Oberfläche bietet
Live-Verfolgung, Karte, Einschränkungen, MCDU-, Flugzeug- und amtliche
Kartendaten. Einstellungen, Beenden und Updates bleiben dem PC vorbehalten.
Wenn Windows fragt, NaviXav nur für private Netzwerke zulassen.

Auf entfernten Bildschirmen unter 760 px wird der MSFS-Verbindungsstatus auf
den farbigen Statuspunkt reduziert, damit `MSFS connected` nicht aus der
Werkzeugleiste herausragt. Die übersetzte Bezeichnung bleibt für assistive
Technologien verfügbar. Die mobile Werkzeugleiste bietet außerdem eine eigene
Sprachauswahl, ohne die PC-exklusiven Einstellungen freizugeben.

NaviXav passt seine Oberfläche beim Skalieren automatisch an:

- über 1100 px wechselt die Modulnavigation in eine kompakte schwebende Leiste
  oben links mit einer klaren Aktivmarkierung; der kurze Eintrag **Flugplan** öffnet
  Abflug, Route und Ankunft als normales exklusives Modul ohne Einklappen, ist standardmäßig ausgewählt und
  jede Auswahl springt direkt zum Inhalt. Der Hauptbereich nutzt die gesamte
  Restbreite und ein geöffnetes offizielles PDF spannt die ganze Kartengruppe
  auf. Schmalere Desktopfenster behalten die horizontale Auswahl und
  Mobilgeräte ihren barrierearmen Drawer. Fügt ein globaler Flugalarm dem Header
  eine zweite Zeile hinzu, weicht die Desktopleiste automatisch nach unten aus
  und kehrt nach Ende des Alarms nach oben zurück;
- über 1100 px können die Karten Abflug, Route und Ankunft nebeneinander
  stehen;
- unter 1100 px wechseln diese Karten in eine einzige Spalte;
- unter 980 px nehmen Werkzeugleiste und Kartensteuerung die volle verfügbare
  Breite ein;
- unter 760 px werden die Registerkarten scrollbar, Schaltflächen neu verteilt
  und Tabellen bleiben waagerecht lesbar;
- unter 520 px wechseln Statistiken und komplexe Bereiche in eine Spalte.

Die Karte reagiert auf jede Größenänderung des Fensters und berechnet ihre
Zeichenfläche sofort neu. Die Mindestgröße des nativen Fensters beträgt
720 × 560 Pixel.

## Demo-Modus

Der Schalter **Demo** lädt einen Beispielflug und simuliert eine Bewegung am
Boden. So lässt sich die Oberfläche ohne SimBrief-Konto und ohne Simulator
erkunden.

Der Demo-Modus ist beim Start stets deaktiviert, damit NaviXav dem letzten
SimBrief-Plan den Vorrang gibt.

## Beenden der Anwendung

Die Schaltfläche **Beenden** in der oberen Leiste verwenden. NaviXav fährt den
Server sauber herunter, schließt Fenster und SimConnect-Verbindung und gibt
anschließend den Port `8765` frei. Das direkte Schließen des Fensters führt zum
selben Ergebnis.

Im Diagnosemodus `--no-open` bewirkt auch `Strg+C` in der Konsole ein normales
Beenden.

## Startoptionen

Der Windows-Starter akzeptiert folgende Optionen:

```powershell
.\NaviXav.bat --port 9000
.\NaviXav.bat --no-open
```

- `--port` ändert den lokalen Port;
- `--no-open` startet nur den lokalen Dienst, zur Diagnose.

Die Abhöradresse bleibt bewusst auf `127.0.0.1` festgelegt.

## Ergänzende Befehle

NaviXav lässt sich auch aus PowerShell verwenden:

```powershell
# Den letzten SimBrief-Plan anzeigen
.\.venv\Scripts\navixav.exe plan

# Ein MCDU-Blatt als Text erzeugen
.\.venv\Scripts\navixav.exe plan --mcdu

# Eine JSON-Ausgabe erzeugen
.\.venv\Scripts\navixav.exe plan --json

# Flughäfen aus MSFS importieren
.\.venv\Scripts\navixav.exe import LFBO LFPO

# Die lokale Datenbank untersuchen
.\.venv\Scripts\navixav.exe navdata

# Die Informationen eines Flughafens anzeigen
.\.venv\Scripts\navixav.exe airport LFBO --runway 32R
```

## Lokale Daten

NaviXav verwendet folgende Speicherorte:

| Speicherort | Inhalt |
|---|---|
| `%LOCALAPPDATA%\NaviXav\user_settings.json` | Konfiguration der installierten Fassung |
| `%LOCALAPPDATA%\NaviXav\navixav.sqlite` | aus MSFS aufgebaute Navigationsdatenbank |
| `%LOCALAPPDATA%\NaviXav\cache\` | zwischengespeicherte nationale AIS- und FAA-Karten |
| `%LOCALAPPDATA%\NaviXav\webview\` | lokaler Speicher des WebView2-Fensters |
| `%LOCALAPPDATA%\NaviXav\logs\navixav.log` | Protokoll der installierten Fassung |
| `data\` und `.venv\` | Daten und Umgebung des Entwicklungsmodus |

Diese lokalen Daten, die Geheimnisse und die Caches sind nicht zur
Versionierung bestimmt.

Das Protokoll erfasst Starts und Beendigungen, Fehler, langsame API-Aufrufe,
SimBrief-Abrufzeiten, MSFS-Vervollständigungszeiten und Cache-Füllvorgänge. Es
erfasst weder die Pilot-ID noch den Benutzernamen noch die vollständige Route.
Seine Größe ist auf 2 MB begrenzt, wobei fünf ältere Fassungen erhalten bleiben
(`navixav.log.1` bis `navixav.log.5`).

Beim ersten Zugriff auf einen Flugplatz oder ein Verfahren weist die Oberfläche
darauf hin, dass der MSFS-Cache gefüllt wird und der Vorgang mehrere Dutzend
Sekunden dauern kann. Spätere Zugriffe verwenden die lokalen Daten erneut.

## Git-Versionierung

Das Quell-Repository ist für folgende Adresse vorgesehen:
`https://github.com/xalacaga/NaviXav.git`.

Die Datei `.gitignore` schließt insbesondere aus:

- `.env`, Benutzereinstellungen und lokale Datenbanken;
- `.claude/`, `CLAUDE.md`, `.codex/`, `AGENTS.md` und `CODEX.md`;
- Graphify-Daten und `graphify-out/`;
- Python-Umgebungen, Test-Caches und Build-Ausgaben;
- `dist\`, `build\` und `release\`.

Die Claude-/Codex-Erinnerungen können daher lokal gepflegt werden, ohne im
Git-Repository veröffentlicht zu werden.

### Automatische Aktualisierungen

Beim Start fragt NaviXav ausschließlich das neueste öffentliche Release des
Repositorys `xalacaga/NaviXav` ab. Ist dessen Version höher als die
installierte, erscheint eine Schaltfläche **Aktualisierung** in der oberen
Leiste. Die Installation beginnt erst nach Bestätigung durch den Benutzer.

Das Installationsprogramm wird nach `%LOCALAPPDATA%\NaviXav\updates\`
heruntergeladen, anschließend wird seine SHA-256-Prüfsumme mit der von GitHub
veröffentlichten verglichen. Fehlt die Prüfsumme oder weicht sie ab, wird die
Datei gelöscht und niemals ausgeführt. Ein Ausfall von GitHub oder des
Internets blockiert weder den Start noch die Flugfunktionen.

Das Repository ist öffentlich lesbar. Nutzer können den Code einsehen und
Releases ohne GitHub-Konto herunterladen, aber nur berechtigte Mitwirkende
können in das Repository schreiben.

### Version und Release-Notizen

Die Version folgt dem semantischen Format `HAUPT.NEBEN.KORREKTUR`.
Konventionelle Commit-Nachrichten bestimmen die nächste Stufe automatisch:

- `feat:` ergibt normalerweise eine Nebenversion;
- `fix:` ergibt eine Korrekturversion;
- `BREAKING CHANGE` oder `!:` ergibt eine Hauptversion;
- alle übrigen Änderungen ergeben eine Korrekturversion.

Version und Notizen lokal vorbereiten:

```powershell
.\scripts\prepare_release.ps1 -Bump auto
```

Installationsprogramm, portables Archiv, deren Prüfsummen und die Notizen in
einem GitHub-Release veröffentlichen:

```powershell
.\scripts\publish_release.ps1 -Bump auto
```

Das zweite Skript setzt ein sauberes Repository und eine authentifizierte
GitHub-CLI voraus. Es führt die Tests aus, erstellt die Auslieferungen, legt
Commit und Tag der Version an, überträgt `main` und den Tag und erstellt
anschließend das GitHub-Release. `CHANGELOG.md` bewahrt die Historie,
`RELEASE_NOTES.md` enthält die Notizen der aktuellen Version.

## Fehlerbehebung

### Port 8765 ist bereits belegt

Wahrscheinlich ist noch eine NaviXav-Instanz geöffnet. Deren Fenster schließen
oder in der Oberfläche auf **Beenden** klicken. Die ausführbare Datei erkennt
eine vorhandene Instanz; belegt eine andere Anwendung den Port 8765, wählt sie
automatisch einen freien Port zwischen 8766 und 8775.

Zur Ermittlung des Prozesses:

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

Die Anwendung lässt sich auch auf einem anderen Port starten:

```powershell
.\NaviXav.bat --port 9000
```

### Das NaviXav-Fenster öffnet sich nicht

- das vollständige Installationsprogramm erneut ausführen, damit es WebView2
  prüft;
- sicherstellen, dass Windows und die Microsoft Edge WebView2 Runtime aktuell
  sind;
- `%LOCALAPPDATA%\NaviXav\logs\navixav.log` einsehen;
- prüfen, ob ein Virenschutz `NaviXav.exe` oder die Prozesse
  `msedgewebview2.exe` blockiert.

Das portable Archiv kann WebView2 nicht selbst installieren. Auf einem Rechner
ohne diese Komponente `NaviXav-Setup-<Version>.exe` verwenden.

### Die MSFS-Anzeige bleibt rot

- prüfen, ob der Simulator läuft;
- einen Flug vollständig laden;
- einige Sekunden warten und dann auf die Anzeige klicken;
- das Installationsprogramm erneut ausführen, falls die mit NaviXav gelieferte
  private Kopie von `SimConnect.dll` gelöscht oder von einem Virenschutz in
  Quarantäne verschoben wurde.

### Es wird kein SimBrief-Plan geladen

- Pilot-ID oder Benutzernamen unter **Einstellungen** prüfen;
- vor einem erneuten Abruf einen OFP in SimBrief erzeugen;
- die Internetverbindung prüfen.

### Eine amtliche Karte ist nicht verfügbar

- prüfen, ob das ICAO-Präfix von SIA, ENAIRE, LVNL, LFV, skeyes,
  Austro Control, NATS oder FAA abgedeckt ist;
- die Internetverbindung prüfen;
- bestätigen, dass Bahn und Anflug bestimmt wurden;
- die manuelle Eingabe der Minima verwenden, wenn die Auswertung nicht
  verfügbar ist.

## Aktuelle Grenzen

- das tatsächlich freigegebene Verfahren kann je nach ATIS, Wetter und
  ATC-Anweisungen vom Plan abweichen;
- die Minima hängen von der Flugzeugkategorie, ihrer Ausrüstung und den
  betrieblichen Bedingungen ab;
- die automatische Auswertung der Minima beschränkt sich auf erkannte
  SIA-Formate;
- ein PDF ohne geprüfte Georeferenzierung bleibt lesbar, kann aber nicht als
  Überlagerung verwendet werden;
- neue MSFS-Daten setzen voraus, dass der Simulator erreichbar ist.

Wichtige Informationen stets bestätigen, bevor sie in den Simulator eingegeben
werden.

## Architektur und Vertraulichkeit

- `navixav/desktop.py` steuert das native Fenster und den Prozesslebenszyklus;
- `navixav/web/app.py` stellt die FastAPI-Schnittstelle bereit, ausschließlich
  an `127.0.0.1` gebunden;
- `navixav/web/static/` enthält die responsive HTML/CSS/JavaScript-Oberfläche;
- `navixav/planner/` vervollständigt den IFR-Plan;
- `navixav/navdata/` baut die aus MSFS gewonnene Datenbank auf und fragt sie
  ab;
- `navixav/live/` übernimmt die SimConnect-Verfolgung;
- `navixav/sia.py`, `navixav/faa.py` und `navixav/national_aip.py` verwalten
  die amtlichen Veröffentlichungen.

Der lokale Dienst hört niemals auf dem externen Netzwerk. Die
SimBrief-Pilot-ID, die Einstellungen, die Flugzusammenfassungen und die zwischengespeicherten
PDFs verbleiben auf dem Rechner. Nur die für SimBrief, OpenStreetMap, das
Wetter und die amtlichen AIS-Veröffentlichungen erforderlichen Anfragen
verlassen den Computer.

## Lizenz

NaviXav ist freie Software und wird unter der Lizenz
[Apache 2.0](LICENSE) verbreitet.

Copyright 2026 Xavier BEGUE (xalacaga)

Du darfst NaviXav frei verwenden, ändern, weitergeben und einbinden, auch in
einem kommerziellen Projekt. Im Gegenzug verlangt die Lizenz, den **Autor zu
nennen**:

- den Copyright-Hinweis und eine Kopie der Lizenz bei jeder Weitergabe
  beibehalten;
- die Datei [NOTICE](NOTICE) und ihren Attributionsinhalt beibehalten;
- **jede von dir geänderte Datei deutlich kennzeichnen**, gemäß Abschnitt 4(b)
  der Lizenz.

Die Lizenz gewährt außerdem eine Patentlizenz und schließt jede Gewährleistung
aus. Navigationsdaten, amtliche Karten und der Kartenhintergrund fallen nicht
unter diese Lizenz: Für sie gelten weiterhin die Bedingungen ihrer jeweiligen
Anbieter, die in der Datei NOTICE aufgeführt sind.

## Tests

Das reproduzierbare Profil, das zum Erstellen der Distribution verwendet wird:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```

Die mit `live_msfs` markierten Tests fragen einen tatsächlich gestarteten
Simulator ab und gehören daher nicht zur automatischen Prüfung des
Installationsprogramms.
