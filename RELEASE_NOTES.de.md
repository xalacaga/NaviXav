# NaviXav 1.7.3

Veröffentlicht am 2026-09-16.

## Neu

- MSFS-Flugpläne: NaviXav liest jetzt den im MSFS-Planer vorbereiteten Plan, für Piloten ohne SimBrief. Die Einstellung „Quelle des Flugplans“ wählt zwischen SimBrief und einem MSFS-Plan (.PLN); der in MSFS geladene Flug wird automatisch gelesen und mit „.PLN-Datei öffnen“ wählst du einen anderen. Flugplätze, Strecke, Luftstraßen, SID, STAR und geplante Pisten werden wie ein SimBrief-OFP genutzt; das Wetter wird live abgerufen. Der erste Start bietet diese Wahl an und verlangt kein SimBrief-Konto mehr.
- Diagnose: Der Befehl „navixav probe-fms“ erfasst, was das geladene Flugzeug von seinem FMS preisgibt — den Flugplan des Simulators über SimConnect und beim Fenix A320 den FMGC-Plan des lokalen EFB-Gateways — in einem separaten, rein lesenden Bericht.
- Fenix A320: NaviXav liest den aktiven Flugplan des FMGC über das lokale Gateway des Fenix-EFB, nur lesend. Auf der Karte wird die FMS-Route nur dort gelb gezeichnet, wo sie von der NaviXav-Route abweicht (DIRECT TO, neue STAR), mit Legendeneintrag, und der Ausweichplan lässt sich auf Wunsch einblenden; T/C und T/D des FMGC ersetzen die Schätzungen (Quelle „FMGC des Flugzeugs“); im Flug ersetzt die FMGC-Phase die aus der Telemetrie abgeleitete. Die Flugverfolgung erhält den aktiven FMGC-Wegpunkt, die ETA und die FMS-Massen sowie zwei Warnungen: 250-kt-Geschwindigkeitslimit und Verzögerungspunkt. Die MCDU-Karte beginnt mit einer zeilenweisen Prüfung des FMGC-Inhalts (FROM/TO, Ausweichflugplatz, Flugnummer, Flughöhe, Pisten, SID, Route, STAR, Anflug, ZFW, Startgeschwindigkeiten) und endet mit einem Spiegel von MCDU 1 und 2. Das Logbuch behält Flugnummer und ETA des FMGC.
- FlyByWire und PMDG: Der MCDU-Spiegel funktioniert auch auf der A32NX/A380X (Bildschirme über SimBridge, FMGC-Phase über die Flugzeugvariable) und auf der PMDG 737/777 (vom SDK gesendete CDU-Bildschirme, sobald EnableCDUBroadcast gesetzt ist). Nur lesend, die Quelle wird im Spiegel angezeigt; der Befehl „navixav probe-fms“ meldet, welcher Kanal antwortet.

## Behoben

- Karte: Die TOC-Markierung folgt dem Flugzeug nicht mehr. Sie wird dort festgesetzt, wo der Steigflug tatsächlich endet, auch wenn ATC eine andere Fläche als die geplante zugewiesen hat, und nur bei einem erneuten Steigflug (Step Climb) neu berechnet. Nach einem Neustart im Flug setzt NaviXav den TOC nicht mehr unter das Flugzeug: Es übernimmt den TOC des SimBrief-Profils oder zeigt keinen an. Bei einem MSFS-Plan wird der Flug an seinem Inhalt erkannt, nicht am Dateidatum, das MSFS bei jedem Laden neu schreibt: Flugprotokoll und wiedergefundener TOC überstehen einen Neustart.
- Warnungen: Die Warnung „Gefährliche Öffnung erkannt“, die vom MSFS-Sicherheitssignal übernommen war, ist entfernt. Sie löste bei Türen oder Klappen aus, die der Pilot am Boden absichtlich öffnet.

## Geändert

- News.

Das Installationsprogramm wird vor jeder automatischen Aktualisierung anhand seiner SHA-256-Prüfsumme verifiziert.
