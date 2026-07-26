# NaviXav

**Dokumentation:** [Français](README.md) · [English](README.en.md) · Deutsch ·
[Español](README.es.md) · [Italiano](README.it.md) ·
[Português](README.pt.md) · [Nederlands](README.nl.md) ·
[Polski](README.pl.md)

NaviXav ist ein lokaler IFR-Flugassistent für Microsoft Flight Simulator. Die
Anwendung lädt automatisch den letzten SimBrief-OFP, ergänzt die
Terminalinformationen mit Daten aus dem Simulator und bereitet die Angaben
für Flugvorbereitung und MCDU-Eingabe auf.

NaviXav besitzt ein eigenes, responsives Windows-Fenster auf Basis von
Microsoft WebView2. Es wird kein externer Browser geöffnet. Der private lokale
Dienst ist nur über `127.0.0.1` erreichbar; Einstellungen, Navigationsdaten,
Karten und Cache bleiben auf dem Computer.

> NaviXav ist ausschließlich für die Flugsimulation bestimmt. Alle Angaben
> müssen mit aktuellen amtlichen Veröffentlichungen und ATC-Anweisungen
> abgeglichen werden.

## Funktionen

- automatischer Abruf des letzten SimBrief-Flugplans;
- SimBrief Pilot ID oder Benutzername direkt in der Oberfläche;
- vollständige Route mit Fortschrittsanzeige des Flugzeugs;
- Auswahl und Begründung von Pisten, SID, STAR, Transition und Anflug;
- Höhen-/Geschwindigkeitsbeschränkungen, Transition Altitude/Level,
  ILS-, Intercept- und Fehlanflughöhe;
- Flugzeug-, Dispatch-, Gewichts-, Kraftstoff- und MCDU-Daten;
- QNH-Anzeige unter den Winddaten;
- Echtzeitverfolgung aus MSFS und lokale, abspielbare Flugspur;
- Route auf einer OpenStreetMap-Grundkarte;
- direkter Zugriff auf amtliche PDF-Karten für Abflug und Ankunft;
- Karten-Overlay nur bei bestätigter Georeferenzierung;
- Navigationsdaten direkt aus MSFS, ohne Little Navmap, Navigraph oder
  EUROCONTROL.

## Voraussetzungen und Installation

- 64-Bit Windows 10 oder Windows 11;
- Microsoft Flight Simulator für Live- und Navigationsdaten;
- SimBrief-Konto mit bereits erzeugtem OFP;
- Internet für SimBrief, Kartenkacheln und amtliche Veröffentlichungen.

`NaviXav-Setup-0.1.0.exe` starten, die Prüfung der Voraussetzungen kontrollieren
und anschließend **Installieren** wählen. Python und alle Bibliotheken sind
enthalten. Microsoft WebView2 wird nur installiert, wenn es fehlt. Alternativ
kann das portable Archiv entpackt und `NaviXav.exe` gestartet werden.

### Autonomes SimConnect

NaviXav installiert, registriert oder ersetzt niemals das systemweite
SimConnect. Eine moderne private `SimConnect.dll` liegt ausschließlich im
NaviXav-Verzeichnis. Eine vorhandene SimConnect-Installation bleibt
unverändert. Für Live-Daten muss MSFS laufen, da der private Connector mit dem
SimConnect-Dienst des Simulators kommuniziert.

## Erste Einrichtung

Unter **Einstellungen** Sprache, SimBrief Pilot ID oder Benutzername,
METAR-Quelle sowie Anflug-, Pisten- und Flugzeugpräferenzen festlegen. Die
Sprache wird sofort übernommen und lokal gespeichert. Verfügbar sind
Französisch, Englisch, Deutsch, Spanisch, Italienisch, Portugiesisch,
Niederländisch und Polnisch.

Beim Start wird immer der neueste verfügbare SimBrief-OFP geladen. Der
Flugplan selbst wird weiterhin auf der SimBrief-Webseite erzeugt.

## Amtliche Karten

Die Registerkarte **Offizielle Karten** zeigt Dokumente für Abflug und Ankunft
aus unterstützten amtlichen Quellen wie SIA, ENAIRE, LVNL und FAA d-TPP.
PDFs lassen sich in NaviXav anzeigen. Die Overlay-Schaltfläche bleibt verborgen,
wenn keine geprüfte Georeferenzierung vorliegt.

## Aus dem Quellcode starten und bauen

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Distribution erstellen:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

Installer, portables Archiv und SHA-256-Prüfsummen werden in `release\`
erstellt. Das MSFS SimConnect SDK wird nur auf dem Build-Rechner benötigt.

## Fehlerbehebung und Datenschutz

- Kein Plan: SimBrief-Kennung, vorhandenen OFP und Internetverbindung prüfen.
- MSFS rot: Simulator starten, Flug vollständig laden und kurz warten.
- Kein Fenster: vollständigen Installer zur WebView2-Reparatur ausführen.
- Port 8765 belegt: vorherige NaviXav-Instanz schließen.

NaviXav sendet keine Telemetrie. Einstellungen, Cache und Flugverlauf bleiben
lokal; kontaktiert werden nur SimBrief, OpenStreetMap und angeforderte amtliche
Quellen.

Das rotierende Diagnoseprotokoll liegt unter
`%LOCALAPPDATA%\NaviXav\logs\navixav.log`. Es enthält Fehler und Zeitmessungen,
aber keine SimBrief-Kennung und keine vollständige Route.
