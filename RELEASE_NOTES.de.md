# NaviXav 1.6.0

Veröffentlicht am 2026-08-30.

## Neu

- Übersichtlichere Bedienung: Die Flugverfolgung bietet jetzt einen sichtbaren Schalter, um alle NaviXav-Alarme einschließlich MASTER WARNING und MASTER CAUTION aus- oder wieder einzuschalten, ohne die Flugverfolgung anzuhalten; nach einem Update öffnet sich der Versionsverlauf beim ersten Neustart automatisch und bleibt danach bei Bedarf verfügbar.
- Sofortiger Wechsel der Verkehrsquelle in den Karten- und Rollleisten: Die Auswahlfelder für VATSIM, IVAO und OpenSky bleiben synchron, starten die Verkehrsabfrage sauber neu und speichern die Wahl lokal.
- OpenSky-Echtverkehr: NaviXav kann öffentliche ADS-B-Zustandsvektoren im Umkreis von 100 NM um das Flugzeug mit Quellenangabe und API-schonendem Cache anzeigen; diese reale Ansicht bleibt strikt von der MSFS-Injektion getrennt.
- Die Einstellungen sind in einklappbare, für kompakte Fenster geeignete Kategorien gegliedert, mit manuellem FSLTL-Pfad, Zugriff auf den offiziellen FlyByWire Installer bei fehlenden Modellen und IVAO als zweiter kostenloser öffentlicher Netzwerkverkehrsquelle neben VATSIM.
- Ausschließliche MSFS-2024-Kompatibilität: NaviXav verwendet jetzt die native SimConnect-AI-EX1-API von MSFS 2024 und lehnt eine alte MSFS-2020-DLL beim Start oder Build ab, statt mit einer ungeeigneten Verbindung oder ungeeigneten Funktionen fortzufahren.
- VATSIM-Verkehrsinjektion in MSFS: NaviXav erkennt FSLTL Base Models automatisch im Community-Ordner, indiziert aircraft.cfg-Dateien und VMR-Regeln, ohne sie zu verändern, wählt das sicherste exakte oder generische Modell und erstellt, aktualisiert und entfernt ausschließlich eigene SimConnect-Objekte in einem begrenzten Umkreis um den Spieler. Die Option ist standardmäßig deaktiviert und die Oberfläche zeigt die erkannte FSLTL-Version.
- Umgebender Verkehr: Eine Schaltfläche „VATSIM-Verkehr“ in der Kartenleiste und „Simulator-Verkehr“ in der Rollleiste zeigt die anderen Luftfahrzeuge. Auf der Karte ist jedes Netzwerkflugzeug eine Silhouette in Steuerkursrichtung mit dem Rufzeichen darunter, und ein Klick öffnet seine Karte: Muster, Frequenz, Pilot, Start- und Zielflughafen benannt nach der MSFS-Datenbank, Geschwindigkeit über Grund und Höhe. Der Rollplan zeigt den Verkehr des Simulators, als einziger metergenau. Standardmäßig aus; solange das gilt, erfolgt kein Netzwerkaufruf.
- Vertikalprofil: Der TOD verwendet nun vorrangig den Leistungspunkt aus dem neuesten SimBrief-OFP, nachdem dessen Koordinaten gegen die aktive Route geprüft wurden; STAR- und Anflugobergrenzen bleiben berücksichtigt, und die geometrische 3°-Berechnung übernimmt automatisch, wenn der Punkt fehlt oder nicht mehr zur Route passt.
- VATSIM-Positionen online: In den Einstellungen aktiviert, markiert NaviXav die Platzfrequenzen mit besetzter Position und zeigt beim Überfahren Rufzeichen und Frequenz des Lotsen — die des Netzwerks ist nicht immer die vom Simulator veröffentlichte. Standardmäßig deaktiviert; solange das gilt, erfolgt kein Netzwerkaufruf.
- Platzfrequenzen: Die Abflugfrequenz ergänzt jetzt die Reihe, und eine Rolle mit mehreren Frequenzen zeigt dies mit einem „+n“, statt eine einzige vorzutäuschen; die Details jeder Stelle, Vorfeld eingeschlossen, erscheinen beim Überfahren mit der Maus.
- Flugverfolgung: Eine zweite Anzeige nennt die in der aktuellen Phase erwartete Frequenz und markiert sich, wenn das Funkgerät bereits darauf steht. Sie schweigt, wenn der Platz mehrere Frequenzen für dieselbe Rolle veröffentlicht, da nichts sagt, welche die betriebene Piste bedient.
- Flugverfolgung: Eine Funkanzeige zeigt die auf COM1 eingestellte Frequenz und benennt die zugehörige Platzstelle, einschließlich pistenbezogener Rollkontrolle — so lässt sich auf einen Blick prüfen, ob die genannte Frequenz richtig eingestellt wurde.
- Diagnose: Der Befehl „navixav airport“ listet die Platzfrequenzen zusammen mit der Zahl auf, mit der der Simulator jede Rolle bezeichnet, und weist auf eine nicht übersetzbare Rolle hin, statt sie zu verschweigen.
- Platzfrequenzen: Die Karten Abflug und Ankunft des Flugplans zeigen jetzt die von MSFS veröffentlichte Funkkette in der Reihenfolge ihrer Verwendung — ATIS, DEL, GND, TWR beim Abflug, ATIS, APP, TWR, GND bei der Ankunft. Veröffentlicht ein Platz mehrere Frequenzen für dieselbe Rolle, erscheinen die übrigen beim Überfahren mit der Maus.
- TOD-Vorbereitung: Bei 50 NM fordert das Warnsystem zur Vorbereitung des Sinkflugs auf und hebt die TOD-Kachel hervor; bei 10 NM wird eine eigene TOD-Warnung ausgelöst, die bis zum Einleiten des Sinkflugs aktiv bleibt.
- Flugzeugkonfiguration: Die geführte Oberfläche nutzt jetzt eine übersichtlichere Cockpit-Ansicht mit ausgewogenen Kacheln, einem Symbol pro System, Statusmarkierung und echten Lichtanzeigen; die klassische Oberfläche behält das bisherige Design.
- Neue fluggeführte Oberfläche: Eine dauerhafte Leiste hebt Phase, Piste oder Verfahren, nächste Aktion und empfohlenes Modul hervor; Abflug-, Ankunfts- und Anflugkarten werden in einer Kartenleiste vorbereitet und der Rollmodus erhält mehr Platz. Mit dem Oberflächenlayout kann ohne Neustart sofort zur klassischen Ansicht zurückgekehrt werden.
- Rollplan: Der Abflug von einer Position mit Nase zum Terminal beginnt nun mit einem Rückschub, im Plan violett und eng gestrichelt gezeichnet und im Band mit Entfernung und anliegendem Kurs angesagt; Rampe, wieder aufgenommenes Rollen und Ankunft zeigen keinen.
- Planvorbereitung: Das Band, das die Befüllung des MSFS-Caches ankündigt, zeigt nun ein Flugzeug, das mit Kondensstreifen den Rahmen durchquert, solange der Lesevorgang dauert. Die Wartezeit konnte mehrere Dutzend Sekunden erreichen, ohne dass sich etwas bewegte.
- MCDU-Blatt: NaviXav übernimmt jetzt den ZFWCG aus SimBrief und zeigt den Schwerpunkt bei Nullkraftstoffmasse zusammen mit der Passagierzahl auf der Gewichtsseite an; der ZFWCG erscheint auch im Dispatch.
- Die Wahl einer Verkehrsquelle genügt jetzt, um sie in MSFS zu injizieren: Die Injektion ist standardmäßig aktiv, und das Kontrollkästchen in den Einstellungen dient nur noch zum Abschalten.
- Ein Hinweis „nur Karte“ erscheint in der Kartenleiste, wenn Verkehr angezeigt, aber nicht injiziert wird; der Tooltip nennt den Grund: Injektion deaktiviert, FSLTL fehlt oder reale Quelle.
- Der reale ADS-B-Verkehr gelangt endlich in MSFS: Der Typ jedes Flugzeugs wird aus zwei sich ergänzenden öffentlichen Registern aufgelöst, wodurch endlich ein FSLTL-Modell gewählt werden kann. Ein beim ersten Durchgang unbekanntes Flugzeug erscheint im nächsten, sobald seine Adresse aufgelöst ist.
- Die Wahl einer Verkehrsquelle genügt jetzt, um sie in den Simulator zu injizieren. Das Kontrollkästchen „Netzwerkverkehr in MSFS injizieren“ entfällt in den Einstellungen: Die Ebenen-Schaltfläche ist der einzige Schalter, und was sie zeigt, fliegt auch.

## Behoben

- Abgestellte OpenSky-Flugzeuge bleiben injizierbar, wenn ihr Transponder barometrische Höhe, Geschwindigkeit oder Kurs auslässt: NaviXav verwendet zuerst die geometrische Höhe und ergänzt anschließend nur fehlende Bodendaten.
- OpenSky-Echtverkehr in MSFS: Flugzeuge ohne ADS-B-Typ verwenden sofort ein sicheres generisches FSLTL-Modell, statt unsichtbar zu bleiben, und wechseln zum exakten Modell, sobald das ICAO24-Register antwortet; die Injektion aktualisiert ihre Position nun jede Sekunde.
- Flüssigerer IVAO- und OpenSky-Verkehr in MSFS: NaviXav extrapoliert die Position zwischen Netzwerkabfragen jede Sekunde und behält ein von der Quelle kurz ausgelassenes Flugzeug bei, sodass es nicht mehr verschwindet und wieder erscheint; der für diese Quellen ungenaue feste 15-Sekunden-Countdown wurde aus der Oberfläche entfernt.
- Netzwerkverkehr an Gates und auf Rollwegen: Wenn VATSIM keinen Bodenzustand veröffentlicht, leitet NaviXav ihn jetzt aus einer Geschwindigkeit von höchstens 50 kt ab; abgestellte und rollende Flugzeuge werden injiziert statt übersprungen.
- Flugzeuginventar: Aktualisieren erkennt nun fliegbare Add-ons mit fehlerhaftem isAirTraffic-Kennzeichen, etwa die Rafale M, und jedes Flugzeug zeigt seine eigene lokale Vorschau statt des Bildes des geladenen Flugzeugs.
- Rollplan bei der Ankunft: Die tatsächliche Flugzeugposition und der Bahnkurs schließen bereits passierte Ausfahrten nun aus; nach einer Landung auf 24R schlägt NaviXav keine Rückfahrt zu einer hinter dem Flugzeug liegenden Ausfahrt mehr vor.
- Karte: Der Reiseflugabschnitt des Flugplans bleibt violett, wird aber nun als durchgezogene Linie dargestellt und ist bei kleiner Zoomstufe besser lesbar.
- Aircraft-Seite: Lange ICAO-Ausrüstungszeichenfolgen werden jetzt innerhalb ihrer Kachel umgebrochen, statt in das benachbarte Profil überzulaufen.
- SimConnect-Identität: Textvariablen wie TITLE und ATC MODEL werden jetzt mit der vom MSFS-SDK erwarteten Null-Einheit deklariert, statt mit der wörtlichen Zeichenfolge NULL, die unbemerkt einen leeren Wert lieferte.
- Aircraft-Seite: Die primäre Identität folgt jetzt live dem tatsächlich in MSFS geladenen Flugzeug und nutzt automatisch ATC MODEL, wenn ein Add-on TITLE leer lässt; das in SimBrief geplante Flugzeug bleibt für Gewichte und Leistungswerte des OFP klar getrennt.
- Außenlichter: NaviXav vergleicht jetzt die sieben einzelnen SimVars mit der offiziellen MSFS-Maske LIGHT STATES; komplexe Flugzeuge, die nur den Gesamtzustand veröffentlichen, zeigen ihre Anzeigen wieder an und lösen Warnungen korrekt aus, mit automatischem Rückfall auf die bisherige Abfrage, wenn die Maske nicht verfügbar ist.
- Flugverfolgung: Die neue Übersicht der Flugzeugkonfiguration ist nun strikt auf ihren eigenen Bereich begrenzt und vergrößert oder verschiebt die Echtzeit-Kacheln nicht mehr.
- Der Demomodus wurde entfernt: NaviXav verwendet jetzt ausschließlich den neuesten SimBrief-Flugplan und reale, über SimConnect von MSFS bereitgestellte Flugdaten.
- Geführte Oberfläche: Die horizontale Routenleiste bleibt jetzt ausschließlich im Menü Flugplan und überlagert in den anderen Modulen nicht mehr die obere Leiste; die klassische Oberfläche behält ihre bisherige Anzeige.
- Modulnavigation: Die obere geführte Leiste misst nun die tatsächliche Höhe der Werkzeugleiste und bleibt nach einem Menüwechsel vollständig sichtbar, statt abgeschnitten zu werden.
- Verfahrensmodul: Eine Phase, die nur aus Hinweisen besteht, etwa die Landung, wird vor dem Flug nicht mehr als abgeschlossen angezeigt; ihre Anzeige bleibt leer und ihre Punkte tragen das Hinweiszeichen statt einer grünen Bestätigung.
- Verfahrensmodul: Eine Phase, die der Flug noch nicht erreicht hat, zeigt keine Bestätigungen mehr; am Gate haken angezogene Feststellbremse und ausgeschaltete Lichter die Punkte nach der Landung und beim Abstellen nicht mehr ab.
- Rollplan: Der Abflugzugang wird jetzt aus allen für Flugzeuge erreichbaren Bahnverbindungen nach ihrer Nähe zur gewünschten Schwelle gewählt. In CYYZ führt ein Abflug von Gate 139 zur Bahn 23 nun über AK, A, H und Q, statt die Bahn 15L zur Kreuzung H3 zu überqueren. Jede bestätigte Bahnquerung wird an einem ausdrücklichen Haltepunkt geteilt; fehlt diese Anweisung, wird die Route abgelehnt.
- In MSFS injizierter Netzwerkverkehr: Flugzeuge, die der Simulator im Flug verwarf, werden nun erkannt und im nächsten Zyklus neu erstellt, statt endgültig zu verschwinden, während NaviXav sie weiter zu verfolgen glaubte.
- Das Protokoll verzeichnet nun jede Änderung eines Injektionszyklus — verfolgte, neu erstellte, entfernte und übergangene Flugzeuge — und macht eine stumm gewordene Injektion sichtbar.
- Die Beschriftung der Injektionsoption nennt nicht mehr nur VATSIM, sondern den Netzwerkverkehr, unabhängig von der gewählten Quelle.
- Die reale Quelle heißt in allen drei Auswahllisten nun „Echter Flugverkehr · OpenSky“ statt nur nach dem Anbieter, und diese Beschriftung folgt endlich der Sprache der Oberfläche.
- Ein Flugzeug genau an der Stelle deines eigenen wird nicht mehr angezeigt oder injiziert: Es ist fast immer dein eigenes, dargestellt vom Netzwerk, mit dem du verbunden bist. Die Nachbarposition bleibt sichtbar, und ein Überflug wird nicht mit einer Überlagerung verwechselt.
- Ein Flugzeug ohne veröffentlichtes Rufzeichen erhält ein stabiles generisches, statt seiner Hexadresse oder eines leeren Feldes, das der Simulator als fehlende Kennung anzeigen würde.
- Die Verkehrsinjektion besitzt nun ihren eigenen Lebenszyklus: Ihr Zustand ist abfragbar, statt im Webdienst eingeschlossen zu sein, sodass eine gestoppte Injektion nicht mehr als gesunde durchgehen kann.

## Geändert

- Integration trafic.

Das Installationsprogramm wird vor jeder automatischen Aktualisierung anhand seiner SHA-256-Prüfsumme verifiziert.
