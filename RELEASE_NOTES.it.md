# NaviXav 1.6.0

Pubblicato il 2026-08-30.

## Novità

- Comandi più chiari: Monitoraggio volo offre ora un interruttore visibile per disattivare o riattivare tutti gli allarmi NaviXav, compresi i messaggi MASTER WARNING e MASTER CAUTION, senza interrompere il monitoraggio; dopo un aggiornamento, la cronologia delle versioni si apre automaticamente al primo riavvio e resta poi disponibile su richiesta.
- Cambio immediato della sorgente traffico dalle barre Mappa e Rullaggio: i selettori VATSIM, IVAO e OpenSky restano sincronizzati, riavviano correttamente il rilevamento e salvano la scelta localmente.
- Traffico reale OpenSky: NaviXav può mostrare vettori di stato ADS-B pubblici entro 100 NM dal velivolo, con attribuzione della fonte e cache rispettosa dell’API; questa vista reale resta rigorosamente separata dall’iniezione in MSFS.
- Le impostazioni sono riorganizzate in categorie richiudibili adatte alle finestre compatte, con percorso FSLTL manuale, accesso all’installer ufficiale FlyByWire quando mancano i modelli e IVAO come seconda fonte pubblica e gratuita di traffico di rete accanto a VATSIM.
- Compatibilità esclusiva con MSFS 2024: NaviXav usa ora l’API SimConnect AI EX1 nativa di MSFS 2024 e rifiuta una vecchia DLL di MSFS 2020 all’avvio o in compilazione, invece di proseguire con una connessione o funzioni inadatte.
- Iniezione del traffico VATSIM in MSFS: NaviXav rileva automaticamente FSLTL Base Models nella cartella Community, indicizza i file aircraft.cfg e le regole VMR senza modificarli, seleziona il modello esatto o generico più sicuro e crea, aggiorna e rimuove esclusivamente i propri oggetti SimConnect entro un’area limitata attorno al giocatore. L’opzione è disattivata per impostazione predefinita e l’interfaccia mostra la versione FSLTL rilevata.
- Traffico circostante: un pulsante «Traffico VATSIM» nella barra della mappa e «Traffico del simulatore» in quella del rullaggio mostra gli altri velivoli. Sulla mappa ogni velivolo della rete è una sagoma orientata alla prua con il nominativo sotto, e un clic apre la sua scheda: tipo, frequenza, pilota, aeroporti di partenza e di arrivo denominati secondo la banca dati MSFS, velocità al suolo e quota. La mappa di rullaggio mostra il traffico del simulatore, l’unico esatto al metro. Spento per impostazione predefinita, finché lo è non parte alcuna chiamata.
- Profilo verticale: il TOD usa ora in via prioritaria il punto prestazionale dell’ultimo OFP SimBrief dopo averne verificato le coordinate sulla rotta attiva; restano applicati i limiti massimi della STAR e dell’avvicinamento e il calcolo geometrico a 3° subentra automaticamente se il punto manca o non corrisponde più alla rotta.
- Posizioni VATSIM online: attivato nelle impostazioni, NaviXav contrassegna con un punto le frequenze dell’aeroporto la cui postazione è presidiata e mostra al passaggio del mouse il nominativo del controllore e la sua frequenza — quella della rete non è sempre quella pubblicata dal simulatore. L’impostazione è disattivata per impostazione predefinita e finché lo è non parte alcuna chiamata.
- Frequenze dell’aeroporto: la frequenza di partenza completa ora la riga e un ruolo con più frequenze lo segnala con un «+n» invece di lasciar credere che ce ne sia una sola; il dettaglio di ogni postazione, piazzali compresi, si legge al passaggio del mouse.
- Monitoraggio del volo: un secondo indicatore annuncia la frequenza prevista nella fase in corso e si evidenzia quando la radio è già impostata. Resta muto quando l’aeroporto pubblica più frequenze per lo stesso ruolo, non sapendo quale serva la pista in uso.
- Monitoraggio del volo: un indicatore radio mostra la frequenza impostata su COM1 e nomina la postazione corrispondente dell’aeroporto, compreso il ground per pista — per verificare a colpo d’occhio di aver digitato la frequenza comunicata.
- Diagnostica: il comando «navixav airport» elenca le frequenze dell’aeroporto accanto al numero con cui il simulatore designa ciascun ruolo e segnala un ruolo che non sa tradurre invece di tacerlo.
- Frequenze dell’aeroporto: le schede Partenza e Arrivo del piano di volo mostrano ora la catena radio pubblicata da MSFS, nell’ordine in cui viene usata — ATIS, DEL, GND, TWR in partenza, ATIS, APP, TWR, GND in arrivo. Quando un aeroporto pubblica più frequenze per lo stesso ruolo, le altre si leggono al passaggio del mouse.
- Preparazione TOD: a 50 NM, il sistema di avvisi chiede di preparare la discesa ed evidenzia la scheda TOD; a 10 NM si attiva un avviso TOD imminente separato che resta attivo fino all’inizio della discesa.
- Configurazione dell'aereo: l'interfaccia guidata adotta un sinottico cockpit più leggibile con schede equilibrate, un'icona per sistema, un indicatore di stato e vere spie per le luci; l'interfaccia classica conserva il design precedente.
- Nuova interfaccia guidata dal volo: una barra persistente evidenzia fase, pista o procedura, prossima azione e modulo consigliato; le carte di partenza, arrivo e avvicinamento vengono preparate in una barra e il Rullaggio dispone di più spazio. L'impostazione Organizzazione interfaccia ripristina subito la vista classica senza riavvio.
- Piano di rullaggio: la partenza da una piazzola con il muso al terminal inizia con un pushback, tracciato in viola e a tratteggio fitto sul piano e annunciato nella fascia con la distanza e la prua una volta allineato; piazzola aperta, rullaggio ripreso o arrivo non ne mostrano alcuno.
- Preparazione del piano: la fascia che annuncia il riempimento della cache MSFS mostra ora un aeromobile che attraversa il riquadro, con la sua scia, per tutta la durata della lettura. L'attesa poteva raggiungere diverse decine di secondi senza che nulla si muovesse.
- Scheda MCDU: NaviXav recupera ora lo ZFWCG da SimBrief e mostra il centro di gravità a massa senza carburante insieme al numero di passeggeri nella pagina dei pesi; lo ZFWCG appare anche nel Dispatch.
- Scegliere una sorgente di traffico basta ora a iniettarla in MSFS: l'iniezione è attiva per impostazione predefinita e la casella nelle impostazioni serve solo a rinunciarvi.
- Un indicatore «solo mappa» compare nella barra della mappa quando il traffico è mostrato senza essere iniettato, e il suggerimento ne indica il motivo: iniezione disattivata, FSLTL assente o sorgente reale.
- Il traffico reale ADS-B entra finalmente in MSFS: il tipo di ogni aeromobile è risolto da due registri pubblici complementari, ciò che permette finalmente di sceglierne un modello FSLTL. Un aeromobile ignoto al primo rilevamento compare al successivo, una volta risolto il suo indirizzo.
- Scegliere una sorgente di traffico basta ora a iniettarla nel simulatore. La casella «Iniettare il traffico di rete in MSFS» sparisce dalle impostazioni: il pulsante del livello è l'unico interruttore, e ciò che mostra è ciò che vola.

## Correzioni

- Gli aeromobili OpenSky parcheggiati restano iniettabili quando il transponder omette quota barometrica, velocità o prua: NaviXav usa prima la quota geometrica e poi completa soltanto i dati a terra mancanti.
- Traffico reale OpenSky in MSFS: gli aeromobili senza tipo ADS-B usano subito un modello FSLTL generico sicuro invece di restare invisibili, poi adottano il modello esatto non appena risponde il registro ICAO24; l’iniezione aggiorna ora la loro posizione ogni secondo.
- Traffico IVAO e OpenSky più fluido in MSFS: NaviXav estrapola la posizione ogni secondo tra due rilevamenti di rete e mantiene brevemente un aeromobile omesso dalla sorgente, evitando che scompaia e ricompaia; il conto alla rovescia fisso di 15 secondi, inesatto per queste sorgenti, è stato rimosso dall’interfaccia.
- Traffico di rete ai gate e sulle vie di rullaggio: quando VATSIM non pubblica lo stato a terra, NaviXav lo deduce ora da una velocità pari o inferiore a 50 kt; gli aeromobili parcheggiati e in rullaggio vengono iniettati invece di essere scartati.
- Inventario velivoli: Aggiorna rileva ora gli add-on pilotabili con isAirTraffic configurato male, come il Rafale M, e ogni velivolo mostra la propria miniatura locale invece di riutilizzare l'immagine dell'aereo caricato.
- Piano di rullaggio all’arrivo: la posizione reale dell’aereo e la prua pista escludono ora le uscite già superate; dopo un atterraggio sulla 24R, NaviXav non propone più di tornare contromano verso un’uscita rimasta alle spalle.
- Mappa: la parte in rotta del piano di volo mantiene il colore viola ma ora usa una linea continua, più leggibile a bassi livelli di zoom.
- Pagina Aircraft: le stringhe lunghe dell’equipaggiamento ICAO ora vanno a capo nella propria scheda invece di invadere il profilo vicino.
- Identità SimConnect: le variabili di testo come TITLE e ATC MODEL sono ora dichiarate con l’unità nulla prevista dall’SDK MSFS, invece della stringa letterale NULL che produceva silenziosamente un valore vuoto.
- Pagina Aircraft: l’identità principale segue ora in tempo reale l’aereo effettivamente caricato in MSFS e usa automaticamente ATC MODEL quando un add-on lascia TITLE vuoto; l’aereo previsto in SimBrief resta chiaramente separato per pesi e prestazioni dell’OFP.
- Luci esterne: NaviXav confronta ora le sette SimVar individuali con la maschera ufficiale LIGHT STATES di MSFS; gli aerei complessi che pubblicano solo lo stato aggregato mostrano di nuovo le spie e attivano correttamente gli avvisi, con ritorno automatico alla lettura precedente se la maschera non è disponibile.
- Monitoraggio del volo: il nuovo sinottico Configurazione dell'aereo è ora strettamente limitato al proprio blocco e non ingrandisce né altera più le schede del monitoraggio in tempo reale.
- La modalità Demo è stata rimossa: NaviXav ora utilizza esclusivamente l'ultimo piano SimBrief e i dati di volo reali forniti da MSFS tramite SimConnect.
- Interfaccia guidata: la barra orizzontale della rotta ora rimane solo nel menu Piano di volo e non si sovrappone più alla barra superiore negli altri moduli; l'interfaccia classica conserva la visualizzazione precedente.
- Navigazione tra i moduli: la barra guidata superiore ora misura l'altezza reale della barra degli strumenti e resta completamente visibile invece di essere tagliata dopo un cambio di menu.
- Modulo Procedure: una fase composta solo da promemoria, come l'atterraggio, non risulta più completata prima del volo; il suo indicatore resta vuoto e i suoi punti portano il segno di informazione invece di una conferma verde.
- Modulo Procedure: una fase che il volo non ha ancora raggiunto non mostra più conferme; al parcheggio, il freno inserito e le luci spente non convalidano più i punti del dopo atterraggio e dello spegnimento.
- Piano di rullaggio: l'ingresso di partenza viene ora scelto tra tutte le giunzioni di pista accessibili agli aeromobili in base alla vicinanza alla soglia richiesta. A CYYZ, una partenza dalla piazzola 139 verso la pista 23 usa ora AK, A, H e Q invece di attraversare la pista 15L per raggiungere l'intersezione H3. Ogni attraversamento di pista confermato viene diviso su un punto di attesa esplicito e il percorso viene rifiutato se tale istruzione manca.
- Traffico di rete iniettato in MSFS: gli aeromobili che il simulatore lasciava cadere in volo vengono ora rilevati e ricreati al ciclo successivo, invece di sparire definitivamente mentre NaviXav credeva di seguirli.
- Il registro annota ora ogni cambiamento di un ciclo di iniezione — aeromobili seguiti, ricreati, rimossi, scartati — rendendo visibile un'iniezione diventata muta.
- L'etichetta dell'opzione di iniezione non parla più del solo VATSIM: nomina il traffico di rete, qualunque sia la sorgente scelta.
- La sorgente reale si chiama ora «Traffico reale · OpenSky» nei tre elenchi di scelta, invece del solo nome del fornitore, e questa etichetta segue finalmente la lingua dell'interfaccia.
- Un aeromobile posto esattamente dove si trova il tuo non è più mostrato né iniettato: è quasi sempre il tuo, restituito dalla rete a cui sei connesso. La piazzola vicina resta visibile e un sorvolo non è confuso con una sovrapposizione.
- Un aeromobile che non pubblica alcun nominativo ne riceve uno generico e stabile, invece del suo indirizzo esadecimale o di un campo vuoto che il simulatore mostrerebbe come immatricolazione mancante.
- L'iniezione del traffico possiede ora il proprio ciclo di vita: il suo stato è interrogabile invece di restare chiuso nel servizio web, così un'iniezione ferma non può più passare per una sana.

## Modifiche

- Integration trafic.

Il programma di installazione è verificato tramite il suo checksum SHA-256 prima di ogni aggiornamento automatico.
