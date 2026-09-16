# NaviXav 1.7.3

Pubblicato il 2026-09-16.

## Novità

- Piani di volo MSFS: NaviXav legge ora il piano preparato nel pianificatore di MSFS, per i piloti che non usano SimBrief. Un'impostazione «Origine del piano di volo» sceglie tra SimBrief e un piano MSFS (.PLN); il volo caricato in MSFS viene letto automaticamente e un pulsante «Apri un file .PLN» permette di sceglierne un altro. Aeroporti, rotta, aerovie, SID, STAR e piste previste sono usati come un OFP SimBrief; il meteo è preso in diretta. Il primo avvio propone questa scelta e non richiede più un account SimBrief.
- Diagnostica: il comando «navixav probe-fms» rileva ciò che l'aereo caricato espone del suo FMS — il piano di volo del simulatore via SimConnect e, sul Fenix A320, il piano del FMGC pubblicato dal gateway locale dell'EFB — in un rapporto separato, in sola lettura.
- Fenix A320: NaviXav legge il piano di volo attivo dell'FMGC tramite il gateway locale dell'EFB Fenix, in sola lettura. Sulla mappa, la rotta FMS è tracciata in giallo solo dove si discosta dalla rotta NaviXav (DIRECT TO, nuova STAR), con la sua voce di legenda, e il piano alternato si mostra a richiesta; il T/C e il T/D dell'FMGC sostituiscono le stime (fonte «FMGC dell'aereo»); in volo la fase dell'FMGC sostituisce quella dedotta dalla telemetria. Il monitoraggio del volo guadagna il punto attivo FMGC, l'ETA e le masse FMS, più due avvisi: limite di velocità 250 kt e punto di decelerazione. La scheda MCDU si apre con una verifica riga per riga di ciò che l'FMGC contiene (FROM/TO, alternato, numero di volo, livello, piste, SID, rotta, STAR, avvicinamento, ZFW, velocità di decollo) e si chiude con uno specchio dei MCDU 1 e 2. Il registro di volo conserva il numero di volo e l'ETA dell'FMGC.
- FlyByWire e PMDG: lo specchio MCDU funziona anche su A32NX/A380X (schermi letti tramite SimBridge, fase FMGC tramite la variabile dell'aereo) e sui PMDG 737/777 (schermi CDU diffusi dall'SDK una volta attivato EnableCDUBroadcast). In sola lettura, fonte indicata nello specchio; il comando «navixav probe-fms» indica quale canale risponde.

## Correzioni

- Mappa: il riferimento TOC non segue più l'aereo. Viene fissato dove la salita termina davvero, anche se ATC ha assegnato un livello diverso da quello pianificato, e viene ricalcolato solo se la salita riprende (step climb). Riavviato in volo, NaviXav non colloca più il TOC sotto l'aereo: riprende quello del profilo SimBrief oppure non lo mostra. Con un piano MSFS, il volo è riconosciuto dal suo contenuto e non dalla data del file, che MSFS riscrive a ogni caricamento: il registro di volo e il TOC ritrovato sopravvivono a un riavvio.
- Avvisi: l'avviso «Apertura pericolosa rilevata», ripreso dal segnale di sicurezza di MSFS, è rimosso. Scattava su porte o botole che il pilota apre volutamente a terra.

## Modifiche

- News.

Il programma di installazione è verificato tramite il suo checksum SHA-256 prima di ogni aggiornamento automatico.
