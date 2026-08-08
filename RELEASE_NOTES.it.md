# NaviXav 1.4.16

Pubblicato il 2026-08-08.

## Correzioni

- Gli speedbrake dei Fenix A319/A320/A321 ora mostrano correttamente ARMED anche quando il nome dell’aeromobile in SimBrief è generico.
- Il Top of Descent è ora un punto fisso della rotta, calcolato dal livello di crociera: diminuisce fino a zero e poi viene indicato come superato. In precedenza poteva bloccarsi durante una discesa a 3° o addirittura aumentare quando la discesa veniva iniziata troppo presto.
- Lo scostamento dal profilo di discesa continua a essere segnalato durante un livellamento al di sotto del livello di crociera. Prima spariva non appena la velocità verticale tornava a zero, proprio quando l’aeromobile era molto sotto il profilo.
- Il Top of Descent tiene ora conto dei tetti di altitudine pubblicati della STAR e dell’avvicinamento e legge l’altitudine nell’atmosfera standard come un livello di volo.
- La velocità verticale richiesta per il vincolo successivo viene ora confrontata con l’altitudine indicata, l’unica comparabile con un vincolo pubblicato.

## Modifiche

- Correction bug TOD.

Il programma di installazione è verificato tramite il suo checksum SHA-256 prima di ogni aggiornamento automatico.
