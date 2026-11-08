# NaviXav 1.8.0

Veröffentlicht am 2026-11-08.

## Neu

- Sprachansagen: NaviXav sagt MASTER-CAUTION- und MASTER-WARNING-Alarme, den Top of Descent bei 50, 10 und 0 NM sowie Rollanweisungen wie Haltepunkte vor der Piste an; einschaltbar in den Einstellungen oder in der Flugverfolgung.
- Kraftstoffüberwachung: Die Flugverfolgung vergleicht den Kraftstoff an Bord mit dem SimBrief-OFP an Ihrer Position auf der Route, schätzt den Kraftstoff am Ziel (EFOB) und warnt, sobald er unter Endreserve plus Ausweichkraftstoff fällt.
- Diagnoseprotokoll: Jeder Verlust und jede Wiederherstellung der Verbindung zu MSFS wird jetzt mit Ursache, Dauer des fehlgeschlagenen Lesevorgangs und Länge der Unterbrechung festgehalten, um Verbindungsprobleme leichter zu untersuchen.
- Karte und Rollplan: Ihr Flugzeug wird jetzt in beiden Ansichten als dieselbe Verkehrsflugzeug-Silhouette in Kursrichtung dargestellt, mit Triebwerken, Cockpitscheibe und leichtem Schatten, statt als Pfeil.
- NaviXav-Stimme: Ansagen werden von hochwertigen neuronalen Stimmen gesprochen, die mit der Anwendung geliefert werden, in allen acht Sprachen, vollständig offline und ohne Installation; Luftfahrtbegriffe bleiben englisch, und auf Englisch stehen drei Stimmen zur Wahl.
- SIGMET auf der Karte: Gültige SIGMETs nahe der Route werden als farbige Gebiete mit ihren Höhen gezeichnet, die von der Route durchquerten hervorgehoben, der Wetter-Tab listet sie mit ihrem vollständigen Text auf, und ein Alarm warnt, wenn das Flugzeug auf seiner Höhe gleich in eines einfliegt.
- Stabilisierter Anflug: Unterhalb des Gates (1000 ft IMC, 500 ft VMC) prüft NaviXav Fahrwerk, Klappen, Geschwindigkeit, Sinkrate und die ILS-Nadeln, sagt „Stabilisiert“ an, wenn alles stimmt, und löst sonst einen Alarm für instabilen Anflug aus; eine Kachel in der Flugverfolgung zeigt die fehlerhaften Kriterien.
- MSFS-Panel 1.2.3: Das Panel im Simulator zeigt die aktiven Alarme, farblich nach Schwere, und im Endanflug den Stabilisierungszustand; aktualisiere es in den NaviXav-Einstellungen.

## Behoben

- Ein Flugzeug, das seine Kraftstoffmenge nicht übermittelt, zeigt nicht mehr 0 kg an und löst keine falsche MASTER WARNING wegen Kraftstoff unter der Reserve mehr aus.
- Das Speichern der Einstellungen erfolgt wieder sofort: Die Vorschaubilder der Liste installierter Flugzeuge lesen nicht mehr jeweils Tausende Community-Dateien neu ein und blockieren den Rest der Anwendung nicht mehr.
- Die Wetterwarnungen „LIFR-Bedingungen“ und „Wetter nicht verfügbar“ erscheinen bei einer anderen Oberflächensprache nicht mehr auf Französisch.

## Geändert

- Mettre en cache la lecture des aircraft.cfg de Community.

Das Installationsprogramm wird vor jeder automatischen Aktualisierung anhand seiner SHA-256-Prüfsumme verifiziert.
