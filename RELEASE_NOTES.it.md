# NaviXav 1.5.0

Pubblicato il 2026-08-28.

## Novità

- Facendo clic sulla foto di un aeromobile si apre ora un’anteprima ingrandita in NaviXav; si chiude con il pulsante, un clic all’esterno o il tasto Esc.
- La scheda e l’inventario Aircraft ora mostrano una vera foto con licenza libera accanto al nome di ogni famiglia di aeromobili supportata; gli aerei aggiuntivi installati in Community usano automaticamente la loro miniatura locale quando disponibile.
- Quando una carta ChartFox non può essere integrata, NaviXav ora propone il catalogo nazionale ufficiale nella stessa scheda se l'aeroporto è coperto.
- Il monitoraggio del volo ora stima il Top of Climb in base al livello di crociera, alla velocità verticale e alla velocità al suolo; i punti calcolati TOC e TOD compaiono sulla mappa come punti distinti.
- ChartFox ora può essere collegato dalle Impostazioni con un account VATSIM; le sue carte su richiesta sono disponibili come fonte facoltativa per gli aeroporti di partenza e arrivo.
- Il menu Charts ora indica che per accedere alle carte AIRAC di ChartFox è necessario un account ChartFox/VATSIM e offre un collegamento diretto alle Impostazioni.

## Correzioni

- Le foto degli aeromobili non restano più nascoste dietro il riquadro del tipo ICAO nella scheda e nell’inventario Aircraft.
- L’apertura del PDF di un aeroporto in Charts non sposta più l’altro aeroporto sotto il documento: Partenza e Arrivo restano affiancati sugli schermi ampi e la scheda non aperta rimane per prima nelle finestre compatte.
- La dicitura «solo simulazione» di ChartFox nelle Impostazioni ora segue la lingua dell'interfaccia.
- Le carte ChartFox la cui fonte vieta l'integrazione non mostrano più un'area vuota: NaviXav spiega la restrizione e propone di aprirle direttamente su ChartFox.
- I punti calcolati TOC e TOD ora usano colori propri magenta e rosso, distinti da tutti i punti della rotta.
- Gli sfondi cartografici CartoDB Positron e Dark Matter sono stati rimossi: il loro servizio gratuito ora applica a ogni tassello la filigrana «API key required». La scelta è tra OpenStreetMap Standard e OpenTopoMap e un'impostazione non più valida torna automaticamente a OpenStreetMap.
- Il briefing meteo non appare più parzialmente in francese quando l'interfaccia è impostata su un'altra lingua: le note operative e i fenomeni METAR seguono ora la lingua selezionata.
- I temporali senza precipitazione osservata vengono ora segnalati: i gruppi TS, VCTS e VCSH erano ignorati dalla decodifica del METAR. Inoltre il «PO» di «TEMPO» non viene più letto come turbini di polvere.
- Le SID compaiono finalmente sulla mappa: il loro tracciato, i loro punti e i vincoli pubblicati mancavano non appena una stessa procedura serviva due testate, come accade in quasi tutti i grandi aeroporti. La partenza si riduceva a una linea retta fino al primo punto in rotta. Le STAR recuperano inoltre la loro parte finale, propria della pista di atterraggio. Il database di navigazione viene reimportato automaticamente dal simulatore al prossimo avvio.

## Modifiche

- Reformuler l'annonce ChartFox de la 1.5.0.
- Ajout fonctionnalite et correction bugs.

Il programma di installazione è verificato tramite il suo checksum SHA-256 prima di ogni aggiornamento automatico.
