# NaviXav 1.4.16

Veröffentlicht am 2026-08-08.

## Behoben

- Die Speedbrakes der Fenix A319/A320/A321 zeigen jetzt zuverlässig ARMED an, auch wenn der Flugzeugname in SimBrief generisch ist.
- Der Top of Descent ist jetzt ein fester Punkt auf der Route, berechnet aus der Reiseflughöhe: Der Wert zählt bis null herunter und wird danach als überschritten angezeigt. Zuvor konnte er während eines Sinkflugs mit 3° einfrieren oder sogar ansteigen, wenn der Sinkflug zu früh begonnen wurde.
- Die Abweichung vom Sinkflugprofil wird jetzt auch während eines Zwischenniveaus unterhalb der Reiseflughöhe angezeigt. Bisher verschwand sie, sobald die Vertikalgeschwindigkeit auf null zurückging, also genau dann, wenn das Flugzeug weit unter dem Profil lag.
- Der Top of Descent berücksichtigt jetzt die veröffentlichten Höhenobergrenzen der STAR und des Anflugs und liest die Höhe wie eine Flugfläche in der Standardatmosphäre.
- Die für die nächste Beschränkung erforderliche Vertikalgeschwindigkeit wird jetzt mit der angezeigten Höhe verglichen, der einzigen, die mit einer veröffentlichten Beschränkung vergleichbar ist.

## Geändert

- Correction bug TOD.

Das Installationsprogramm wird vor jeder automatischen Aktualisierung anhand seiner SHA-256-Prüfsumme verifiziert.
