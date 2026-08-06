# NaviXav 1.4.10

Veröffentlicht am 2026-08-06.

## Neu

- Die Einstellungen öffnen jetzt den vollständigen Versionsverlauf: alle wichtigen Änderungen seit Beginn der Verfolgung, Version für Version, mit Datum und einer Markierung der installierten. Der Verlauf wird mit der Anwendung ausgeliefert und ist ohne Verbindung lesbar. Die Änderungstexte bleiben englisch; Rahmen und Rubriken folgen der gewählten Sprache.
- Die Flugverfolgung unterscheidet jetzt eine pausierte von einer verlorenen Simulation: die MSFS-Anzeige und die Verfolgungsplakette zeigen „MSFS pausiert“, statt eine abgebrochene Verbindung vorzutäuschen. Ein Simulator, der diesen Zustand nicht bereitstellt, wird weiterhin normal verfolgt.
- Beim Überfahren von Piste, SID, STAR, ihren Übergängen und dem Anflug erscheint ein unauffälliger Stift: er öffnet die Liste der übrigen veröffentlichten Prozeduren und erlaubt, die Wahl nachträglich zu ändern, auch wenn sich das System seiner Sache sicher ist. Die Liste ist nicht mehr auf drei Einträge begrenzt, sie zeigt alles von der gewählten Piste aus Fliegbare, und „Zurück zur automatischen Auswahl“ gibt die Entscheidung an das System zurück. Bei einer erzwungenen Wahl bleibt der Stift hervorgehoben.

## Behoben

- Eine fehlende Prozedur beansprucht nicht mehr den Platz einer echten. Ist für die Piste keine STAR veröffentlicht, ersetzt die Begründung den Strich auf einer einzigen enger gesetzten Zeile, und die Übergangszeile, die das Fehlen nur wiederholte, entfällt. Ebenso enger bei einer SID oder einem Anflug ohne Übergang.
- Eine SID oder STAR, die für die gewählte Piste nicht veröffentlicht ist, wird nicht mehr eingebunden: sie beginnt an einer anderen Schwelle oder führt zum IAF auf der gegenüberliegenden Flughafenseite. NaviXav meldet jetzt einen radargeführten Abflug oder einen direkten Anflug, und die verworfene Prozedur bleibt in der Auswahlliste verfügbar. In Brive-Souillac auf Piste 29 zeigt der Plan BSC und dann ILS RWY 29 statt einer nicht fliegbaren STAR.
- Ohne STAR schließen Anflug und Übergang jetzt an den letzten Streckenpunkt an, statt ohne Verbindung zu bleiben. Ein genau auf diesem Punkt veröffentlichter Übergang wird erkannt und nicht mehr als unsichere Wahl dargestellt.
- Anflugpunkte, die SimBrief unmarkiert im Navigationslog belässt, etwa CF29 oder RW11, zählen nicht mehr als Streckenpunkte: sie werden nicht mehr auf der Route gezeichnet und nicht mehr zur Verknüpfung des Anflugs verwendet.
- Wenn eine STAR die Landepiste zwar bedient, aber auf einem Punkt endet, der keinen Anflug eröffnet, sagt NaviXav dies ausdrücklich, statt den Bruch erst im Flug entdecken zu lassen.
- Der Versionsverlauf liegt nicht mehr dauerhaft über der Oberfläche: er öffnet sich nur beim Klick auf sein Symbol in den Einstellungen und schließt vollständig.
- Das Einstellungsfenster hat keine waagerechte Bildlaufleiste mehr: ein unsichtbares Feld ragte über die gesamte Breite des Kastens hinaus, unabhängig von der Fenstergröße.

## Geändert

- Correction bug et améliorations diverses.

Das Installationsprogramm wird vor jeder automatischen Aktualisierung anhand seiner SHA-256-Prüfsumme verifiziert.
