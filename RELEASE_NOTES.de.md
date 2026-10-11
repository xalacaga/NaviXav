# NaviXav 1.7.4

Veröffentlicht am 2026-10-11.

## Neu

- VATSIM-, IVAO- und OpenSky-Verkehr nimmt Kurven vorweg: Ein Flugzeug, das bei der letzten Abfrage im Kurvenflug war, dreht auf der Karte und im Simulator allmählich auslaufend weiter, statt bis zur nächsten Abfrage geradeaus zu fliegen.
- Landeanalyse: Beim Aufsetzen zeigt NaviXav die von MSFS gespeicherte Sinkrate, Längs- und Querneigung, die Distanz nach der Schwelle und die Abweichung von der Mittellinie der tatsächlich benutzten Landebahn, Gegen- und Seitenwind, Sprünge und die Stabilität des Endanflugs, mit einer Bewertung von 100 Punkten. Die Analyse wird dem Flug im Flugbuch zugeordnet, und ein teilbares Bild kann kopiert oder gespeichert werden.
- Das Flugbuch wird jetzt im NaviXav-Datenordner statt im Fenster gespeichert: Es übersteht eine Neuinstallation oder ein Zurücksetzen von WebView2, und ein über das lokale Netzwerk verbundenes Tablet zeigt dasselbe Flugbuch schreibgeschützt an. Bereits aufgezeichnete Flüge werden beim ersten Start automatisch übernommen.
- Flugbuch-Statistiken: Anzahl der Flüge, gesamte Flugstunden und Distanz, durchschnittliches Aufsetzen und durchschnittliche Bewertung, beste Landung, meistgeflogene Flugzeuge und meistbesuchte Flugplätze. Das vollständige Flugbuch lässt sich für eine Tabellenkalkulation als CSV exportieren.

## Behoben

- OpenSky-Verkehr bewegt sich zwischen zwei Abfragen jetzt flüssig auf der Karte und im Simulator weiter, statt stehen zu bleiben und dann mehrere Seemeilen zu springen.
- OpenSky wird zu Beginn eines Flugs deutlich häufiger abgefragt, etwa alle 30 Sekunden: Das öffentliche Kontingent wird auf die Dauer eines Flugs statt auf einen ganzen Tag verteilt.
- Das erste Laden eines Flugplatzes dauert nicht mehr fast eine Minute: NaviXav sucht ILS und Wegpunkte jetzt in der Region des Flugplatzes, statt die aller bereits bekannten Flugplätze zu durchlaufen, und findet ILS-Frequenzen wieder, die fälschlich als nicht vorhanden gemeldet wurden, etwa die der Piste 23R in EGCC.

## Geändert

- Correction bug et ajout logbook.

Das Installationsprogramm wird vor jeder automatischen Aktualisierung anhand seiner SHA-256-Prüfsumme verifiziert.
