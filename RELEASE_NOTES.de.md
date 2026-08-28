# NaviXav 1.5.3

Veröffentlicht am 2026-08-28.

## Behoben

- Flugplätze, die im Cache fehlen, werden wieder aus dem Simulator importiert: Die Pistenbefeuerung wurde mit falscher Feldbreite gelesen, wodurch der gesamte Flugplatz verloren ging und sein Flughafenplan nicht verfügbar war.
- Ein nicht verfügbarer Flughafenplan nennt jetzt den Grund — Flugplatz fehlt in der Datenbank — statt einen Netzwerkfehler zu melden, und eine unbekannte Befeuerungsstärke wird nicht mehr als ausgeschaltet angezeigt.

## Geändert

- Bug correction.

Das Installationsprogramm wird vor jeder automatischen Aktualisierung anhand seiner SHA-256-Prüfsumme verifiziert.
