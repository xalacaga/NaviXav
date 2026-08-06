# NaviXav 1.4.10

Pubblicato il 2026-08-06.

## Novità

- Le impostazioni aprono ora la cronologia completa delle versioni: tutte le modifiche importanti dall'inizio del tracciamento, versione per versione, con la data e un segno su quella installata. La cronologia è fornita con l'applicazione e si legge senza connessione. I testi delle modifiche restano in inglese; la cornice e le rubriche seguono la lingua scelta.
- Il monitoraggio del volo distingue ora una simulazione in pausa da una persa: l'indicatore MSFS e la pastiglia di monitoraggio mostrano «MSFS in pausa» invece di far credere a una connessione interrotta. Un simulatore che non espone questo stato continua a essere monitorato normalmente.
- Una matita discreta compare passando sulla pista, sulla SID, sulla STAR, sulle loro transizioni e sull'avvicinamento: apre l'elenco delle altre procedure pubblicate e permette di modificare la scelta a posteriori, anche quando il motore è sicuro. L'elenco non è più limitato a tre voci, mostra tutto ciò che è volabile dalla pista scelta, e «Torna alla scelta automatica» restituisce il comando al motore. La matita resta accesa su una scelta imposta.

## Correzioni

- Una procedura assente non occupa più lo spazio di una reale. Quando nessuna STAR è pubblicata per la pista, la motivazione sostituisce il trattino su una sola riga più stretta, e la riga di transizione che si limitava a ripetere l'assenza scompare. Stesso restringimento per una SID o un avvicinamento senza transizione.
- Una SID o STAR non pubblicata per la pista selezionata non viene più concatenata: parte da un'altra soglia o porta all'IAF dal lato opposto dell'aeroporto. NaviXav annuncia ora una partenza con guida radar o un arrivo diretto, e la procedura scartata resta proposta nell'elenco delle scelte. A Brive-Souillac in pista 29, il piano indica BSC poi ILS RWY 29 invece di una STAR non volabile.
- Senza STAR, l'avvicinamento e la sua transizione si collegano ora all'ultimo punto della rotta invece di restare senza legame. Una transizione pubblicata proprio su quel punto viene riconosciuta e non è più presentata come una scelta incerta.
- I punti di avvicinamento che SimBrief lascia nel registro di navigazione senza contrassegnarli, come CF29 o RW11, non contano più come punti in rotta: non vengono più tracciati sulla rotta né usati per collegare l'arrivo.
- Quando una STAR serve effettivamente la pista di atterraggio ma termina su un punto che non apre alcun avvicinamento, NaviXav lo dice esplicitamente invece di lasciar scoprire l'interruzione in volo.
- La cronologia delle versioni non resta più visibile in permanenza sopra l'interfaccia: si apre solo al clic sulla sua icona nelle impostazioni e si chiude completamente.
- La finestra delle impostazioni non ha più una barra di scorrimento orizzontale: un campo invisibile debordava per tutta la larghezza del riquadro, qualunque fosse la dimensione della finestra.

## Modifiche

- Correction bug et améliorations diverses.

Il programma di installazione è verificato tramite il suo checksum SHA-256 prima di ogni aggiornamento automatico.
