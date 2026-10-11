# NaviXav 1.7.4

Pubblicato il 2026-10-11.

## Novità

- Il traffico VATSIM, IVAO e OpenSky anticipa le virate: un aereo in virata all’ultimo rilevamento continua a virare, attenuandosi gradualmente, sulla mappa e nel simulatore, invece di proseguire dritto fino al rilevamento successivo.
- Analisi dell’atterraggio: al contatto, NaviXav mostra la velocità verticale registrata da MSFS, assetto e inclinazione, la distanza dalla soglia e lo scostamento dall’asse della pista effettivamente utilizzata, vento frontale e al traverso, i rimbalzi e la stabilità del finale, con un punteggio su 100. L’analisi è collegata al volo nel giornale di bordo e un’immagine pronta da condividere può essere copiata o salvata.
- Il giornale di bordo è ora conservato nella cartella dati di NaviXav anziché nella finestra: sopravvive a una reinstallazione o a un ripristino di WebView2, e un tablet collegato in rete locale mostra lo stesso giornale, in sola lettura. I voli già registrati vengono ripresi automaticamente al primo avvio.
- Statistiche del giornale di bordo: numero di voli, ore di volo e distanza totali, contatto e punteggio medi, miglior atterraggio, aerei più pilotati e aeroporti più frequentati. Il giornale completo si esporta in CSV per un foglio di calcolo.

## Correzioni

- Il traffico OpenSky ora continua a muoversi in modo fluido sulla mappa e nel simulatore tra due rilevamenti, invece di restare fermo e poi saltare di diverse miglia nautiche.
- OpenSky viene interrogato molto più spesso all’inizio di un volo, circa ogni 30 secondi: la quota pubblica è distribuita sulla durata di un volo anziché su un’intera giornata.
- Il primo caricamento di un aeroporto non richiede più quasi un minuto: NaviXav cerca ora l’ILS e i punti nella regione dell’aeroporto invece di scorrere quelle di tutti gli aeroporti già noti, e ritrova le frequenze ILS che indicava per errore come introvabili, come quella della pista 23R di EGCC.

## Modifiche

- Correction bug et ajout logbook.

Il programma di installazione è verificato tramite il suo checksum SHA-256 prima di ogni aggiornamento automatico.
