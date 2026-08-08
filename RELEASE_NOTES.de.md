# NaviXav 1.4.15

Veröffentlicht am 2026-08-08.

## Behoben

- Anfragen zu kommerziellen Lizenzen und Beiträgen verwenden jetzt die eigene NaviXav-Kontaktadresse.
- Die automatische Aktualisierung installiert sich jetzt wirklich: Das Hilfsprogramm, das auf das Schließen von NaviXav wartet, wurde ohne Konsole gestartet und starb sofort, sodass die Aktualisierung als geplant gemeldet wurde und die Anwendung mit der alten Version wieder öffnete. Das Hilfsprogramm führt zudem ein eigenes Protokoll neben dem Installationsprogramm, damit ein künftiger Fehler nachvollziehbar bleibt.
- Heruntergeladene Installationsprogramme häufen sich nicht mehr an: Jede Aktualisierung löscht die vorherigen, und das Installationsprogramm tut nach Abschluss dasselbe. Auf einem seit den ersten Versionen begleiteten Rechner hatte sich ein halbes Gigabyte angesammelt. Die Protokolle bleiben erhalten, damit ein Fehler weiterhin untersucht werden kann.

## Geändert

- Nettoyage des installateurs telecharges.
- Correctif mise a jour automatique.
- Update NaviXav contact email.

Das Installationsprogramm wird vor jeder automatischen Aktualisierung anhand seiner SHA-256-Prüfsumme verifiziert.
