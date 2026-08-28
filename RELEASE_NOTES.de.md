# NaviXav 1.5.0

Veröffentlicht am 2026-08-28.

## Neu

- Ein Klick auf ein Flugzeugfoto öffnet nun eine große Vorschau in NaviXav; sie lässt sich über die Schaltfläche, einen Klick außerhalb oder die Escape-Taste schließen.
- Die Aircraft-Karte und das Inventar zeigen nun für jede unterstützte Flugzeugfamilie ein echtes frei lizenziertes Foto neben dem Namen; zusätzliche in Community installierte Flugzeuge verwenden automatisch ihr lokales Vorschaubild, sofern vorhanden.
- Wenn eine ChartFox-Karte nicht eingebettet werden kann, bietet NaviXav nun den amtlichen nationalen Katalog in derselben Karte an, sofern der Flugplatz abgedeckt ist.
- Die Flugverfolgung schätzt nun den Top of Climb aus Reiseflughöhe, Vertikalgeschwindigkeit und Geschwindigkeit über Grund; die berechneten Punkte TOC und TOD erscheinen als eigene Wegpunkte auf der Karte.
- ChartFox kann jetzt in den Einstellungen mit einem VATSIM-Konto verknüpft werden; seine Karten auf Abruf stehen als optionale Quelle für Abflug und Ankunft bereit.
- Das Menü Charts weist nun darauf hin, dass für den Zugriff auf ChartFox-AIRAC-Karten ein ChartFox-/VATSIM-Konto erforderlich ist, und bietet einen direkten Link zu den Einstellungen.

## Behoben

- Flugzeugfotos werden in der Aircraft-Karte und im Inventar nicht mehr von der ICAO-Typkachel verdeckt.
- Beim Öffnen eines Flugplatz-PDFs in Charts wird der andere Flugplatz nicht mehr unter das Dokument verschoben: Abflug und Ankunft bleiben auf breiten Bildschirmen nebeneinander, und die nicht geöffnete Karte bleibt in kompakten Fenstern zuerst sichtbar.
- Der ChartFox-Hinweis „nur für Simulation“ in den Einstellungen folgt nun der Sprache der Benutzeroberfläche.
- ChartFox-Karten, deren Quelle das Einbetten verbietet, zeigen keinen leeren Bereich mehr: NaviXav erklärt die Einschränkung und bietet an, sie direkt auf ChartFox zu öffnen.
- Die berechneten Punkte TOC und TOD verwenden nun eigene Farben in Magenta und Rot, die sich von allen Wegpunkten der Route unterscheiden.
- Die Kartenhintergründe CartoDB Positron und Dark Matter wurden entfernt: Ihr kostenloser Dienst versieht jede Kachel nun mit dem Wasserzeichen „API key required“. Die Wahl besteht zwischen OpenStreetMap Standard und OpenTopoMap; eine ungültig gewordene Einstellung fällt automatisch auf OpenStreetMap zurück.
- Das Wetterbriefing erscheint nicht mehr teilweise auf Französisch, wenn die Oberfläche auf eine andere Sprache eingestellt ist: Hinweise und METAR-Erscheinungen folgen nun der gewählten Sprache.
- Gewitter ohne beobachteten Niederschlag werden nun gemeldet: Die Gruppen TS, VCTS und VCSH wurden bei der METAR-Auswertung übergangen. Zudem wird das „PO“ in „TEMPO“ nicht mehr als Staubwirbel gelesen.
- SID werden endlich auf der Karte dargestellt: Verlauf, Wegpunkte und veröffentlichte Beschränkungen fehlten, sobald eine Prozedur zwei Pistenrichtungen bediente, was auf nahezu allen großen Flugplätzen der Fall ist. Der Abflug schrumpfte damit auf eine gerade Linie bis zum ersten Streckenpunkt. STAR erhalten zudem ihren pistenabhängigen Endteil zurück. Die Navigationsdatenbank wird beim nächsten Start automatisch neu aus dem Simulator übernommen.

## Geändert

- Reformuler l'annonce ChartFox de la 1.5.0.
- Ajout fonctionnalite et correction bugs.

Das Installationsprogramm wird vor jeder automatischen Aktualisierung anhand seiner SHA-256-Prüfsumme verifiziert.
