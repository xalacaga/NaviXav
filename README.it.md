# NaviXav

**Sito ufficiale:** [navixav.fr](https://navixav.fr/en)

**Documentazione:** [Français](README.fr.md) · [English](README.md) ·
[Deutsch](README.de.md) · [Español](README.es.md) · Italiano ·
[Português](README.pt.md) · [Nederlands](README.nl.md) ·
[Polski](README.pl.md)

NaviXav è un'applicazione locale di assistenza al volo IFR per Microsoft Flight
Simulator. Recupera l'ultimo piano di volo SimBrief, completa le informazioni
terminali con i dati del simulatore e presenta il tutto in un'interfaccia
pensata per la preparazione del volo e l'inserimento nell'MCDU.

L’applicazione ha una propria finestra Windows, resa da Microsoft WebView2 e
collegata al servizio locale su `127.0.0.1`. Impostazioni, dati di navigazione e
cache restano sul computer. Il browser di sistema si apre solo su richiesta
esplicita, ad esempio per SimBrief, autenticazione ChartFox, download FSLTL/AIG
o sostegno al progetto.

La finestra è completamente ridimensionabile. L'interfaccia riorganizza
pannelli, comandi, schede e l'altezza della mappa in funzione dello spazio
disponibile, fino a una dimensione minima di 720 × 560 pixel.

> NaviXav è destinato esclusivamente alla simulazione di volo. Le informazioni
> visualizzate devono essere verificate con le pubblicazioni ufficiali e le
> istruzioni ATC applicabili.

## Funzionalità

### Piano di volo SimBrief

- recupero automatico dell'ultimo OFP all'avvio;
- supporto del Pilot ID o del nome utente SimBrief;
- visualizzazione della rotta completa, dall'origine alla destinazione;
- evidenziazione del punto di rotta successivo in base alla posizione reale
  dell'aeromobile, con attenuazione dei punti già superati;
- masse, carburante, tempo di volo, alternato e dati di dispatch;
- informazioni sull'aeromobile, immatricolazione ed equipaggiamento dichiarato.
Il banner del volo attivo mostra il tempo rimanente da distanza residua e
velocità al suolo quando utilizzabili, altrimenti l’ETE SimBrief prima del
decollo. Dopo il salvataggio delle impostazioni, il piano si aggiorna in
background senza trattenere la finestra di dialogo. I comandi del pannello MSFS
preservano le altre impostazioni, inclusi gli identificativi SimBrief.


### Meteo del volo

- METAR e TAF essenziali per partenza, arrivo e alternato;
- vento e temperatura di crociera ricavati dall'OFP SimBrief;
- in modalità **METAR in diretta**, aggiornamento automatico ogni cinque minuti
  da aviationweather.gov e pulsante di aggiornamento immediato;
- rappresentazione grafica di condizioni, vento, visibilità e ceiling senza
  modificare automaticamente pista o procedure del piano.

### Preparazione IFR

NaviXav completa e presenta:

- la pista di partenza e la pista di arrivo;
- la SID e la sua transizione;
- la STAR e la sua transizione;
- l'avvicinamento e la sua VIA;
- la frequenza e l'identificativo ILS;
- i vincoli di altitudine e di velocità;
- l'altitudine di transizione e il livello di transizione;
- l'altitudine di intercettazione dell'avvicinamento;
- l'altitudine di mancato avvicinamento;
- la motivazione e il livello di confidenza di ogni scelta.

I blocchi **Partenza · Rotta · Arrivo** possono essere ridotti per liberare
spazio nell'interfaccia.

Ogni importazione SimBrief e ricalcolo verifica i raccordi SID–rotta–STAR–avvicinamento tramite gli estremi effettivamente percorsi nei dati MSFS, anche quando il nome della transizione differisce dal punto di raccordo. I raccordi mancanti richiedono conferma; nessuna transizione viene scelta arbitrariamente. I rami di pista che duplicano esattamente l’inizio della STAR non creano più un ritorno al suo ingresso; i vincoli distinti restano conservati. La rotta mantiene DCT e aerovie dell’OFP. Le transizioni scelte assenti dalla banca dati sono indicate come non verificate.

### Monitoraggio del volo

La scheda **Monitoraggio del volo** sfrutta la posizione MSFS in tempo reale per
visualizzare:

- la fase di volo rilevata automaticamente;
- la velocità al suolo (GS) e la velocità indicata (IAS) fornite da MSFS;
- il punto successivo e la sua distanza;
- lo scostamento laterale rispetto al segmento attivo;
- la distanza rimanente;
- il vincolo successivo di altitudine o di velocità;
- il rateo verticale necessario per raggiungere tale vincolo;
- il Top of Descent del profilo prestazionale dell’ultimo OFP SimBrief dopo la
  verifica sulla rotta attiva, con una stima a 3° come ripiego e mantenendo i
  limiti massimi pubblicati della STAR e dell’avvicinamento;
- lo scostamento rispetto al profilo verticale previsto.

Dopo l'atterraggio, il giornale locale conserva un riepilogo conciso e una
cronologia limitata degli eventi: fasi di volo, pista di decollo e atterraggio
con il vento osservato, e cambiamenti stabili di carrello, flap, spoiler, freno
di parcheggio, luci e modalità dell'autopilota. Gli eventi sono memorizzati come
dati e vengono riprodotti nella lingua selezionata al momento. Tutti i
riepiloghi possono essere eliminati dall'interfaccia e nessun dato di volo
viene inviato a servizi esterni.

Nell’interfaccia guidata questi valori sono presentati come un sinottico da
cockpit, con strumenti equilibrati, stati espliciti e spie luminose.
L’interfaccia classica conserva le schede compatte originali.
La pagina Aircraft usa come identità principale il titolo comunicato in tempo
reale da MSFS e si aggiorna automaticamente quando viene caricato un altro
aereo. L’aereo SimBrief resta visibile separatamente, perché pesi e prestazioni
del dispatch appartengono ancora all’OFP importato.
Se un aereo di terze parti lascia `TITLE` vuoto, NaviXav usa automaticamente il
suo valore ufficiale `ATC MODEL`.
Per le luci esterne, NaviXav confronta anche le SimVar dei singoli interruttori
con la maschera ufficiale `LIGHT STATES` di MSFS. Gli aerei complessi che
pubblicano solo lo stato aggregato non lasciano quindi più tutte le spie e gli
avvisi erroneamente spenti.
Da 50 NM prima del TOD, il normale sistema di avvisi chiede di preparare la
discesa; a 10 NM compare un avviso TOD imminente separato che resta attivo fino
all’inizio della discesa.

In **Aircraft**, **Documentazione PDF** appare solo quando i manuali Community
corrispondono all’aeromobile del piano SimBrief, anche senza connessione a MSFS. Il nome
del profilo può indicare il fornitore, ad esempio Fenix; un profilo generico ambiguo non
seleziona un fornitore a caso. Sono elencati solo i PDF di quell’aeromobile. Il lettore
sostituisce le informazioni nella pagina Aircraft; **Torna ad Aircraft** le ripristina.
La ricerca mostra estratti con accesso diretto alla pagina. I PDF scansionati senza
testo restano leggibili, ma non consentono questa ricerca.

Per flap, spoiler e freno di parcheggio, NaviXav confronta le SimVar ufficiali
di leva, posizione effettiva, superficie e indicatore cockpit. Configurazione
dell’aereo ed eventi di volo continuano così ad aggiornarsi quando un velivolo
di terze parti lascia bloccato un valore standard MSFS.
Un adattatore dedicato ai Fenix A319/A320/A321 legge direttamente i tre comandi
del cockpit, così le modifiche a flap, aerofreni e freno di parcheggio vengono
segnalate anche con motori e impianti idraulici spenti.

Sui Fenix A319/A320/A321, NaviXav legge la modalità STD dell’EFIS del comandante per la visualizzazione e gli avvisi QNH/STD. Una SimVar generica MSFS discordante non sostituisce più tale modalità. Se la lettura Fenix è indisponibile o non valida, la regolazione resta sconosciuta e questi avvisi non vengono attivati dalla pressione generica. Questa lettura non sorveglia il lato del copilota.

Su questi Fenix vengono letti direttamente anche entrambi i comandi antighiaccio
motore. Se la lettura non è disponibile, lo stato resta sconosciuto invece di
generare un falso allarme dalla SimVar standard.

Sui Fenix A319/A320/A321, il rilevamento STD legge lo stato reale del barometro del comandante (B_FCU_EFIS1_BARO_STD), anziché il comando S_FCU_EFIS1_BARO_STD. Il ritorno a zero del comando non causa più falsi allarmi con STD visualizzato. Le letture mancanti o non valide restano indeterminate.

Il controllo ILS usa il ricevitore assegnato dall’aereo caricato. Fenix A319/A320/A321 e FlyByWire A32NX usano il NAV3 del comandante; gli altri aerei usano l’indice NAV1–NAV4 selezionato da MSFS. Se indice o frequenza non sono disponibili, l’avviso resta silenzioso invece di confrontare un altro ricevitore.

Il TOD mostrato è una stima SimBrief o NaviXav, non una lettura del MCDU. Il profilo FMS può indicare un punto diverso con la stessa rotta e livello. Se i vincoli anticipano il punto SimBrief, la fonte diventa una stima calcolata.

Il monitoraggio e il pannello nel simulatore mostrano «Discesa in corso» al posto del TOD durante la discesa, poi «Avvicinamento». I tratti livellati mantengono l’indicazione se la perdita di quota conferma la discesa. Lo stato proviene dalla telemetria, non dalla modalità DES del FMS.

### Scheda MCDU

La scheda **Scheda MCDU** adatta le pagine al tipo di aeromobile: MCDU Airbus,
CDU Boeing o FMS generico per gli altri velivoli. Non propone prestazioni di
decollo che non possono essere automatizzate:

- `FROM/TO`, numero di volo e alternato;
- Cost Index e livello di crociera;
- ZFW, ZFWCG, numero di passeggeri, carburante di blocco, rullaggio, tratta e riserve;
- pista, SID, transizione e altitudine di transizione;
- rotta `VIA/TO`;
- STAR, transizione, avvicinamento e VIA;
- QNH, temperatura, vento, frequenza ILS e rotta finale;
- minime RADIO o BARO e RVR.

### Connessione diretta a MSFS

NaviXav utilizza SimConnect per:

- rilevare la presenza del simulatore;
- mostrare una spia verde o rossa nella barra superiore;
- seguire la posizione dell'aeromobile in tempo reale;
- leggere altitudine, altezza dal suolo, prua, velocità al suolo e velocità
  verticale;
- distinguere STD dal QNH conservato sull’altimetro e segnalare facoltativamente
  una porta, un portello o un tettuccio aperto pericoloso;
- recuperare aeroporti, piste e relative luci di bordo e asse, procedure, punti
  di riporto e radioassistenze;
- costruire progressivamente una base locale in `data/navixav.sqlite`.

Il pulsante **Traffico** su Mappa o Rullaggio controlla visualizzazione e
iniezione in MSFS; è disattivato per impostazione iniziale. Le sorgenti sono
VATSIM, IVAO, OpenSky (traffico ADS-B reale) e traffico statico. I selettori
condividono l’impostazione locale; la finestra legge anche le modifiche del
pannello MSFS ogni tre secondi.

Cambiare un’impostazione estranea al traffico non riavvia più l’iniezione o gli
aerei presenti. Restano applicate le modifiche a sorgente, modelli e traffico
statico attivo. I moduli condividono un rilevamento MSFS con riferimento
temporale per un massimo di 250 ms; posizione e quota del giocatore provengono
dallo stesso stato per l’iniezione. Un rilevamento scaduto o una connessione
fallita non presenta una vecchia posizione come attuale.

Le impostazioni offrono **FSLTL Base Models** oppure **AIG AI Traffic**, un set
alla volta. Entrambe le installazioni sono rilevate; i percorsi FSLTL, AIG e
Community si possono inserire manualmente. NaviXav legge `aircraft.cfg` e regole
VMR senza installare o modificare le librerie. FSLTL apre il [download
FlyByWire](https://flybywiresim.com/downloads/) per **FSLTL Traffic Base
Models**; AIG apre il [sito ufficiale](https://www.alpha-india.net/). AI Manager
installa `aig-aitraffic-oci`; i pacchetti complementari mancanti sono segnalati.

OpenSky cerca traffico reale entro il raggio configurato. L’accesso anonimo viene aggiornato ogni quattro minuti per rispettare la quota pubblica giornaliera. Se OpenSky restituisce HTTP 429, NaviXav mostra esplicitamente **Quota giornaliera OpenSky esaurita** in entrambe le interfacce e rispetta il tempo di attesa indicato invece di riprovare continuamente; l’animazione del traffico esistente continua fino al ripristino della sorgente. L’iniezione dipende dai modelli
disponibili: FSLTL può usare un modello generico per tipi sconosciuti; AIG non
offre questo ripiego. Un aereo sulla mappa non è necessariamente iniettato.
NaviXav blocca o ferma la propria iniezione se rileva FSLTL Traffic Injector o
AIG Traffic Controller. Dopo averlo chiuso, disattivare e riattivare Traffico;
la ripresa non è automatica.

Le impostazioni mostrano sempre il raggio e il numero massimo di aerei per tutte le sorgenti. I valori predefiniti sono **40 NM** e **10 aerei**, regolabili da 1 a 100 NM e da 1 a 200 aerei. Gli aerei più vicini hanno la priorità.

Il **traffico statico** usa solo parcheggi già presenti nella cache di
navigazione MSFS. Servono un volo caricato e dati di parcheggio; scegliere la
sorgente non scarica le strutture mancanti. I posti vicini sono occupati per
primi. Mappa e iniezione condividono la cache; un risultato vuoto
viene ritentato dopo tre secondi. Gli aerei statici restano parcheggiati: non
rullano e non decollano.

Mappa e Rullaggio distinguono caricamento, creazioni confermate da MSFS, assenza
di traffico iniettabile, errori e stato obsoleto. Il suggerimento mostra aerei
selezionati ed esclusi. La conferma riguarda la creazione dell’oggetto, non
visibilità o fluidità garantita. Le creazioni avvengono a gruppi; il catalogo è
riutilizzato fino a un minuto nei cambi rapidi. Una connessione SimConnect
indipendente anima con un obiettivo di 30 aggiornamenti al secondo; le posizioni
sul Rullaggio sono interpolate. I log locali misurano frequenza e pause.
Disattivazione e chiusura liberano le connessioni e rimuovono solo gli oggetti
creati da NaviXav.

Il tracciamento usa le marche temporali individuali valide delle posizioni OpenSky: ricevere un vecchio rilevamento non lo rende recente e le posizioni arrivate fuori ordine vengono ignorate. Senza una marca temporale individuale utilizzabile, NaviXav mantiene la propria stima locale prudente. Le viste Mappa e Rullaggio nascoste sospendono le letture del traffico e il disegno; mostrarle riavvia lettura e ridimensionamento. Il monitoraggio del volo e l’iniezione MSFS restano attivi.

Le letture periodiche di posizione, traffico, controllori VATSIM e stato del simulatore evitano richieste sovrapposte per la stessa lettura e scartano risposte obsolete dopo un cambio di contesto. Nel Rullaggio, un errore temporaneo conserva le ultime posizioni per un massimo di dieci secondi dall’ultimo rilevamento riuscito, con un avviso. Un rilevamento vuoto confermato o la disattivazione del traffico cancella subito le posizioni.

A terra, un rilevamento di arresto annulla la previsione e il movimento converge gradualmente verso la posizione di parcheggio ricevuta senza conservare inerzia. Senza un nuovo rilevamento di movimento, la previsione rallenta e la sua finestra è limitata a cinque secondi; i raccordi restano graduali. Le piccole variazioni di posizione di un aereo già parcheggiato vengono filtrate. Queste regole usano le posizioni della sorgente, senza rilevamento degli edifici.

Il pannello MSFS mostra ora Il mio volo: prossimo punto e distanza, tempo restante, prossimo vincolo e TOD, sincronizzati con la finestra NaviXav e la sua lingua. I valori vengono nascosti dopo dieci secondi senza aggiornamento. Il traffico mostra aerei confermati, selezionati e scartati, caricamento, errori e stati obsoleti; la spia verde richiede creazioni confermate. Il pulsante di ritorno apre la finestra per i dettagli. Reinstallare il pannello 1.2.1 dalle impostazioni e riavviare MSFS per caricare i nuovi file.

Il pannello MSFS 1.2.1 si riconnette automaticamente a NaviXav dopo un’interruzione o un cambio di porta. Una connessione non disponibile non viene più indicata come applicazione chiusa. Le richieste hanno un timeout effettivo e gli errori di visualizzazione non interrompono la riconnessione. Dopo l’aggiornamento del pannello dalle impostazioni, riavviare MSFS.

**Installa il
pannello MSFS** copia solo questo pacchetto in Community; **Rimuovi** lo
elimina. Se le versioni installata e fornita differiscono, le impostazioni
offrono la reinstallazione. I pulsanti restano bloccati e animati durante
l’operazione. Riavviare MSFS per ricaricare il pacchetto se necessario. Il
ritorno alla finestra funziona in modalità finestra o senza bordi; lo schermo
intero esclusivo può mantenere il focus.

Il simulatore deve essere avviato con un volo caricato per recuperare nuovi
dati. Le informazioni già memorizzate nella cache restano disponibili offline.

Quando il navlog dettagliato di SimBrief contiene coordinate convalidate,
NaviXav le usa subito per tracciare la rotta e interroga MSFS Facilities solo
per le posizioni mancanti. Anche i collegamenti pubblicati delle procedure
evitano ricerche di posizione superflue. Il primo caricamento del piano risulta
più rapido, mantenendo i controlli del corridoio e la cache MSFS locale come
ripiego.

### Mappa

La mappa comprende:

- uno sfondo OpenStreetMap;
- la rotta SimBrief disegnata con i suoi punti;
- colori distinti per la SID, la parte in rotta, la STAR e l'avvicinamento;
- le piste e la pista selezionata;
- la posizione e la prua dell'aeromobile;
- una traccia dello spostamento;
- una modalità di inseguimento automatico;
- lo zoom, lo spostamento e l'adattamento all'aeroporto o alla rotta.

Le barre di Mappa e Rullaggio raggruppano i comandi di vista, visualizzazione e traffico. I pulsanti sono alti 40 pixel, lo zoom resta raggruppato e i comandi si adattano alle finestre compatte. Autorizzazione al rullaggio e azioni del percorso restano insieme.

Nelle finestre ampie, i comandi di Mappa e Rullaggio restano sotto la barra di volo durante lo scorrimento, in base alla sua altezza effettiva. Il cambio di modulo aggiorna le misure prima dello scorrimento. Nelle finestre compatte barra e comandi scorrono normalmente.

L’animazione mantiene la cadenza dopo un fotogramma in ritardo senza aggiungere un’attesa completa. Gli aerei vicini hanno priorità a 30 Hz; oltre 10 NM si passa a 15 Hz, oltre 40 NM a 5 Hz. Gli aerei stabili al parcheggio non vengono ricalcolati a ogni fotogramma. Accelerazione graduale, virate sul percorso più breve e arresti immediati. Restano i limiti di previsione al parcheggio.

### Rullaggio a terra

La scheda **Rullaggio** offre un diagramma aeroportuale separato dalla mappa di
volo e costruito esclusivamente con le strutture native di MSFS:

- il canvas occupa tutto lo spazio disponibile, anche nelle finestre compatte;
- uno sfondo aeronautico scuro con griglia metrica e freccia nord fornisce scala
  e orientamento senza il rumore di una carta stradale;
- piste, vie principali, piazzole e aeromobile hanno priorità visiva;
- le vie di rullaggio con nome restano visibili anche quando MSFS le classifica
  come segmenti generici `path`; solo i collegamenti secondari senza nome e gli
  accessi alle piazzole sono nascosti per impostazione predefinita, e il
  pulsante **Secondarie** li mostra su richiesta;
- alla partenza, se l'aeromobile è a terra entro 180 m da una piazzola, NaviXav
  propone automaticamente il percorso verso la pista selezionata;
- l'ingresso di partenza è la giunzione accessibile agli aeromobili più vicina
  alla soglia selezionata, anche se MSFS marca come attesa una giunzione più lontana;
- un clic su un'altra piazzola sostituisce subito la proposta; all'arrivo la
  piazzola di destinazione resta una scelta manuale;
- percorso effettuato e restante, nomi utili, punti di attesa, prossima manovra
  e distanza residua sono presentati con chiarezza;
- ogni attraversamento di pista confermato dalla rete MSFS divide il percorso
  su un punto di attesa esplicito; il percorso viene rifiutato se non è rappresentabile;
- dopo una deviazione il percorso viene ricalcolato dalla posizione reale;
- la velocità al suolo compare in tempo reale sulla planimetria, con un avviso
  all’avvicinarsi della velocità massima di rullaggio e un allarme lampeggiante
  con segnale acustico oltre di essa; il limite si restringe in curva, prima di
  una barra d’arresto e alla piazzola, e non si applica mai su una pista.

I percorsi di parcheggio SimConnect servono solo a collegare le piazzole alla
rete e non possono creare scorciatoie artificiali attraverso le piste.

### Carte AIS nazionali ufficiali

NaviXav interroga direttamente le pubblicazioni delle autorità nazionali, senza
passare da EUROCONTROL/EAD:

- Francia: SIA eAIP (`LF`);
- Spagna e Canarie: AIP ENAIRE (`LE`, `GC`, `GE`);
- Paesi Bassi: LVNL eAIP (`EH`);
- Svezia: LFV eAIP (`ES`);
- Belgio e Lussemburgo: skeyes eAIP (`EB`, `EL`);
- Austria: Austro Control eAIP (`LO`);
- Regno Unito: NATS eAIP (`EG`);
- Stati Uniti e territori coperti: FAA d-TPP.

Per questi aerodromi, NaviXav può:

- presentare nella scheda **Carte ufficiali** tutti i PDF della partenza e
  dell'arrivo, ordinati per tipo;
- aprire ogni documento nell'interfaccia o separatamente;
- selezionare per impostazione predefinita la SID, la STAR o l'avvicinamento
  corrispondente al volo corrente;
- individuare automaticamente la carta di avvicinamento corrispondente alla
  pista e al tipo di avvicinamento scelti;
- scaricare su richiesta soltanto i PDF consultati;
- conservare la pubblicazione nella cache AIRAC locale;
- mostrare la carta ufficiale nella scheda MCDU;
- estrarre le minime ILS CAT I del SIA quando il formato è riconosciuto;
- proporre DA, DH e RVR prima della convalida.

I valori estratti non vengono mai applicati in modo silenzioso: devono essere
convalidati nell'interfaccia. Il pulsante **Livello ufficiale** viene proposto
solo per un documento con georeferenziazione convalidata. Segue la scelta della
carta: il PDF della partenza può essere sovrapposto solo alla partenza e quello
dell'arrivo solo all'arrivo. Questa regola è identica per tutte le fonti.

Un paese viene aggiunto all'elenco automatico solo dopo la convalida di un
accesso diretto e stabile ai suoi PDF ufficiali. Una fonte assente non viene
quindi mai sostituita in silenzio da un aggregatore di terze parti.

ChartFox è disponibile come fonte facoltativa nella stessa scheda **Carte**.
Collega il tuo account ChartFox/VATSIM dalle **Impostazioni**, quindi scegli
ChartFox per l'aeroporto di partenza o arrivo. L'accesso usa il browser di
sistema e OAuth 2.0 con PKCE; NaviXav non richiede mai le credenziali VATSIM e
protegge localmente il token utente con Windows DPAPI. I documenti vengono
caricati su richiesta, non sono salvati su disco, sono riservati alla
simulazione e mantengono l'attribuzione «Chart data powered by ChartFox». I
livelli ChartFox restano disattivati finché NaviXav non ottiene lo scope
`charts:geos`.
Quando una fonte vieta la visualizzazione integrata, NaviXav spiega la
restrizione e propone la pagina ChartFox della carta invece di un lettore vuoto.
Se un connettore nazionale copre l'aeroporto, NaviXav propone prima di passare
la scheda al catalogo ufficiale e continuare all'interno dell'applicazione.

## Prerequisiti

- Windows 10 o Windows 11 a 64 bit;
- Microsoft WebView2 Runtime, installato automaticamente dall'installer;
- Microsoft Flight Simulator per i dati e il monitoraggio in tempo reale;
- un account SimBrief con un OFP generato;
- una connessione a Internet per SimBrief, lo sfondo cartografico e le
  pubblicazioni AIS nazionali o FAA.

L'installer include Python, le librerie, pywebview, il connettore SimConnect
autonomo di NaviXav e il bootstrapper Microsoft WebView2 firmato. Nessuno di
questi strumenti va installato separatamente. MSFS non è obbligatorio per
consultare i dati già salvati.

SimConnect non viene mai installato né reinstallato in Windows da NaviXav.
L'applicazione incorpora una copia privata della DLL moderna nella propria
cartella. Se la macchina possiede già SimConnect, la sua installazione, la sua
versione e le sue impostazioni non vengono né sostituite né modificate. Questa
DLL privata dialoga con il servizio SimConnect di MSFS: solo il simulatore deve
essere installato e avviato per ricevere i dati in diretta.

### Lingue dell'interfaccia

La lingua si sceglie in **Impostazioni**, si applica immediatamente e resta
memorizzata sul computer. NaviXav fornisce le interfacce in francese, inglese,
tedesco, spagnolo, italiano, portoghese, neerlandese e polacco. Le abbreviazioni
aeronautiche, gli identificativi di procedura, i METAR e i valori MCDU restano
volutamente nella loro notazione internazionale.

## Installazione rapida su Windows

1. Scaricare il file `NaviXav-Setup-<versione>.exe` dall'ultima
   [Release GitHub](https://github.com/xalacaga/NaviXav/releases/latest).
2. Avviare l'installer.
3. Verificare la pagina di controllo dei prerequisiti.
4. Mantenere o modificare la cartella proposta, poi fare clic su **Installa**.
5. Avviare NaviXav dal menu Start o dal collegamento facoltativo sul desktop.

L'installer verifica Microsoft WebView2 e lo installa automaticamente se manca.
L'installazione avviene per l'utente corrente e normalmente non richiede
diritti di amministratore.

È disponibile anche un archivio portatile: estrarre
`NaviXav-<versione>-windows-x64-portable.zip`, quindi avviare `NaviXav.exe`. Su
una macchina priva di WebView2, utilizzare prima l'installer completo.

### Dai sorgenti

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Al primo avvio, lo script:

1. cerca Python;
2. crea l'ambiente virtuale `.venv`;
3. installa NaviXav e le sue dipendenze;
4. avvia il servizio locale privato;
5. apre l'interfaccia nella finestra NaviXav.

Gli avvii successivi riutilizzano l'ambiente già installato.

### Costruire una distribuzione

Da PowerShell, nella cartella del progetto:

```powershell
.\scripts\build_windows.ps1
```

Lo script:

1. verifica Windows a 64 bit, Python e l'SDK SimConnect di MSFS 2024;
2. installa gli strumenti di compilazione mancanti;
3. scarica il bootstrapper WebView2 ufficiale e ne verifica la firma Microsoft;
4. esegue i test escludendo l'integrazione MSFS in diretta;
5. produce l'installer, l'archivio portatile e le loro somme SHA-256 in
   `release\`.

L'SDK SimConnect di MSFS 2024 citato al punto 1 riguarda solo la macchina che
compila NaviXav. La DLL corrente viene inclusa privatamente con NaviXav e non
viene installata né registrata sulle macchine degli utenti. Una vecchia DLL di
MSFS 2020 viene rifiutata.

### File di distribuzione

Dopo una compilazione riuscita:

| File | Utilizzo |
|---|---|
| `release\NaviXav-Setup-<versione>.exe` | installer Windows consigliato |
| `release\NaviXav-<versione>-windows-x64-portable.zip` | versione portatile |
| `release\*.sha256` | impronte di controllo dei file distribuiti |

La cartella `release\` è volutamente ignorata da Git. Gli eseguibili sono
artefatti di compilazione da pubblicare in una Release GitHub, non sorgenti da
versionare.

## Installazione manuale

Da PowerShell, nella cartella del progetto:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m navixav.desktop
```

Questo comando apre la finestra NaviXav. Per una diagnosi del servizio locale
senza finestra:

```powershell
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
```

Il servizio resta allora accessibile solo su `http://127.0.0.1:8765`.

## Configurazione

La configurazione corrente si effettua dal pulsante **Impostazioni**
dell'interfaccia.

### Account SimBrief

Compilare uno dei due campi:

- **Pilot ID SimBrief**: identificativo numerico mostrato nelle impostazioni
  dell'account SimBrief;
- **Nome utente SimBrief**: alias dell'account.

Il Pilot ID è consigliato. Dopo il salvataggio, NaviXav recupera immediatamente
l'ultimo OFP disponibile. A ogni nuovo avvio, quest'ultimo piano viene caricato
automaticamente.

### Impostazioni disponibili

Durante il salvataggio delle impostazioni, il pulsante mostra un indicatore animato e «Salvataggio…». Resta disattivato fino al termine per evitare invii duplicati e torna disponibile anche in caso di errore. L’animazione rispetta la preferenza di movimento ridotto.

L'interfaccia consente inoltre di configurare:

- la fonte METAR;
- l'ordine di preferenza degli avvicinamenti;
- la componente massima di vento in coda;
- la componente massima di vento al traverso;
- la lunghezza minima di pista;
- l'aspetto dell'interfaccia: automatico, chiaro o scuro;
- l'organizzazione dell'interfaccia: guidata dal volo, con barra contestuale
  adattata alla fase e carte di partenza/arrivo/avvicinamento preparate, oppure
  classica per tornare subito alla presentazione precedente senza riavvio;
- la cartella Community di MSFS usata per censire le procedure per aeromobile;
- la velocità massima di rullaggio, il limite più basso applicato in curva e
  l’allarme sonoro della velocità di rullaggio;
- la capacità RNP dell'aeromobile.

Nella versione installata, i valori sono conservati in
`%LOCALAPPDATA%\NaviXav\user_settings.json`.

### Procedure per aeromobile

Il modulo **Procedure** associa l'aeromobile caricato in MSFS al database locale
di NaviXav. Presenta le procedure normali per fase di volo, il loro avanzamento
e gli elementi confermati automaticamente tramite SimConnect. La nota sulla fonte
segue la lingua scelta. La copertura è consultabile nella sezione compressa
**Procedure per aeromobile** delle impostazioni.

## Primo utilizzo

1. Generare un piano di volo in SimBrief.
2. Avviare Microsoft Flight Simulator e caricare un volo.
3. Avviare NaviXav dal menu Start, oppure con `NaviXav.bat` in modalità
   sviluppo.
4. Aprire **Impostazioni** e salvare il Pilot ID SimBrief.
5. Attendere il caricamento automatico dell'ultimo OFP.
6. Controllare la spia **MSFS connesso** in alto a destra.
7. Verificare le scelte di pista, SID, STAR e avvicinamento.
8. Consultare i vincoli e la carta ufficiale.
9. Convalidare le minime prima di ricopiarle nell'MCDU.

Il pulsante **Completa il piano** consente di recuperare nuovamente l'ultimo OFP
dopo aver generato o modificato un volo in SimBrief.

## Utilizzo della mappa

- **Sfondo mappa**: mostra o nasconde OpenStreetMap.
- **Rullaggio**: apre il piano del suolo dedicato; **Secondarie** mostra o
  nasconde gli accessi e le vie meno importanti.
- **Livello ufficiale**: compare solo per la carta georeferenziata
  dell'aerodromo attualmente visualizzato e ne regola l'opacità.
- **Rotta completa**: inquadra l'intera rotta del volo.
- **Segui**: mantiene l'aeromobile al centro.
- **Adatta**: inquadra l'aeroporto selezionato.
- **+ / −**: modifica il livello di zoom.
- **Rotella**: ingrandisce sotto il puntatore.
- **Trascina**: sposta la mappa.

I pulsanti aeroporto consentono di passare rapidamente dall'aerodromo di
partenza a quello di arrivo.

## Finestra e visualizzazione adattiva

### Accesso da telefono e tablet sulla rete locale

Attivare **Accesso telefono e tablet** nelle **Impostazioni**, salvare e
riavviare NaviXav. Aprire l’indirizzo protetto mostrato sul PC da un dispositivo
connesso allo stesso Wi-Fi. L’interfaccia mobile offre tracciamento in tempo
reale, mappa, vincoli, dati MCDU, dati dell’aereo e carte ufficiali.
Impostazioni, arresto e aggiornamenti restano riservati al PC. Se Windows lo
richiede, autorizzare NaviXav solo sulle reti private.

Sugli schermi remoti inferiori a 760 px, lo stato della connessione MSFS viene
ridotto al punto colorato, così `MSFS connected` non fuoriesce dalla barra degli
strumenti. L’etichetta tradotta resta disponibile per le tecnologie assistive.
La barra mobile offre inoltre un proprio selettore della lingua senza esporre
le impostazioni riservate al PC.

NaviXav adatta automaticamente la sua interfaccia al ridimensionamento:

- oltre 1100 px, la navigazione tra i moduli passa a una barra flottante
  compatta in alto a sinistra, con un indicatore attivo chiaro; la voce breve
  **Piano di volo** apre Partenza, Rotta e Arrivo come un normale modulo
  esclusivo, senza comando di riduzione, è selezionata per impostazione predefinita e ogni scelta porta direttamente al
  contenuto. L’area principale usa tutta la larghezza restante e un PDF
  ufficiale aperto occupa l’intera griglia. Le finestre più strette mantengono
  il selettore orizzontale e i dispositivi mobili il pannello accessibile. Quando
  un avviso di volo globale aggiunge una seconda riga all’intestazione, la barra
  desktop scende automaticamente e risale dopo la scomparsa dell’avviso;
- oltre 1100 px, le schede Partenza, Rotta e Arrivo possono essere affiancate;
- sotto 1100 px, queste schede passano su una sola colonna;
- sotto 980 px, la barra degli strumenti e i comandi della mappa occupano tutta
  la larghezza disponibile;
- sotto 760 px, le schede diventano scorrevoli, i pulsanti si ridistribuiscono
  e le tabelle restano consultabili in orizzontale;
- sotto 520 px, le statistiche e i pannelli complessi passano in colonna.

La mappa rileva ogni cambiamento di dimensione della finestra e ricalcola
immediatamente il proprio canvas. La dimensione minima della finestra nativa è
720 × 560 pixel.

## Chiusura dell'applicazione

Utilizzare il pulsante **Esci** nella barra superiore. NaviXav arresta
correttamente il server, chiude la finestra e la connessione SimConnect, quindi
libera la porta `8765`. Chiudere direttamente la finestra produce lo stesso
risultato.

In modalità diagnostica `--no-open`, anche la combinazione `Ctrl+C` nella
console esegue un arresto normale.

## Opzioni di avvio

Il lanciatore Windows accetta le opzioni seguenti:

```powershell
.\NaviXav.bat --port 9000
.\NaviXav.bat --no-open
```

- `--port` cambia la porta locale;
- `--no-open` avvia solo il servizio locale, per la diagnosi.

L'indirizzo di ascolto resta volutamente fissato a `127.0.0.1`.

## Comandi complementari

NaviXav può essere utilizzato anche da PowerShell:

```powershell
# Mostrare l'ultimo piano SimBrief
.\.venv\Scripts\navixav.exe plan

# Generare una scheda MCDU testuale
.\.venv\Scripts\navixav.exe plan --mcdu

# Produrre un output JSON
.\.venv\Scripts\navixav.exe plan --json

# Importare aeroporti da MSFS
.\.venv\Scripts\navixav.exe import LFBO LFPO

# Esaminare la base locale
.\.venv\Scripts\navixav.exe navdata

# Mostrare le informazioni di un aeroporto
.\.venv\Scripts\navixav.exe airport LFBO --runway 32R
```

## Dati locali

NaviXav utilizza le posizioni seguenti:

| Posizione | Contenuto |
|---|---|
| `%LOCALAPPDATA%\NaviXav\user_settings.json` | configurazione della versione installata |
| `%LOCALAPPDATA%\NaviXav\navixav.sqlite` | base di navigazione costruita da MSFS |
| `%LOCALAPPDATA%\NaviXav\cache\` | carte AIS nazionali e FAA in cache |
| `%LOCALAPPDATA%\NaviXav\webview\` | archiviazione locale della finestra WebView2 |
| `%LOCALAPPDATA%\NaviXav\logs\navixav.log` | registro della versione installata |
| `data\` e `.venv\` | dati e ambiente della modalità sviluppo |

Questi dati locali, i segreti e le cache non sono destinati al versionamento.

Il registro annota avvii e arresti, errori, chiamate API lente, tempi di
recupero SimBrief, tempi di completamento MSFS e riempimenti della cache. Non
annota né il Pilot ID, né il nome utente, né la rotta completa. La sua
dimensione è limitata a 2 MB, con cinque versioni precedenti conservate
(`navixav.log.1` a `navixav.log.5`).

Al primo accesso a un aerodromo o a una procedura, l'interfaccia avvisa che la
cache MSFS è in fase di riempimento e che l'operazione può richiedere alcune
decine di secondi. Gli accessi successivi riutilizzano i dati locali.

## Versionamento Git

Il repository sorgente è previsto per essere ospitato su:
`https://github.com/xalacaga/NaviXav.git`.

Il file `.gitignore` esclude in particolare:

- `.env`, le impostazioni utente e le basi locali;
- `.claude/`, `CLAUDE.md`, `.codex/`, `AGENTS.md` e `CODEX.md`;
- i dati Graphify e `graphify-out/`;
- gli ambienti Python, le cache dei test e gli output di compilazione;
- `dist\`, `build\` e `release\`.

Le memorie Claude/Codex possono quindi essere mantenute localmente senza essere
pubblicate nel repository Git.

### Aggiornamenti automatici

All'avvio, NaviXav interroga soltanto l'ultima Release pubblica del repository
`xalacaga/NaviXav`. Se la sua versione è superiore a quella installata, compare
un pulsante **Aggiornamento** nella barra superiore. L'installazione inizia solo
dopo la conferma dell'utente.

L'installer viene scaricato in `%LOCALAPPDATA%\NaviXav\updates\`, quindi la sua
impronta SHA-256 viene confrontata con quella pubblicata da GitHub. In caso di
impronta assente o diversa, il file viene eliminato e non viene mai eseguito.
Un guasto di GitHub o di Internet non blocca né l'avvio né le funzioni di volo.
Prima dell'installazione, un helper Windows indipendente attende la chiusura
completa del processo NaviXav. Aggiorna quindi la cartella realmente utilizzata,
riavvia l'applicazione e conserva un file `.install.log` accanto all'installer
scaricato.

Al primo riavvio, la **Cronologia delle versioni** si apre automaticamente una
sola volta per mostrare le modifiche; in seguito resta accessibile
dall’interfaccia.

Il repository è pubblico in lettura. Un utente può consultare il codice e
scaricare le Release senza account GitHub, ma solo i collaboratori autorizzati
possono scrivere nel repository.

### Versione e note di Release

La versione segue il formato semantico `MAJOR.MINOR.PATCH`. I messaggi di
commit convenzionali determinano automaticamente il livello successivo:

- `feat:` produce normalmente una versione minore;
- `fix:` produce una versione correttiva;
- `BREAKING CHANGE` o `!:` produce una versione maggiore;
- le altre modifiche producono una versione correttiva.

Preparare localmente la versione e le sue note:

```powershell
.\scripts\prepare_release.ps1 -Bump auto
```

Pubblicare l'installer, l'archivio portatile, le loro impronte e le note in una
Release GitHub:

```powershell
.\scripts\publish_release.ps1 -Bump auto
```

Il secondo script richiede un repository pulito e GitHub CLI autenticato.
Esegue i test, costruisce i deliverable, crea il commit e il tag di versione,
invia `main` e il tag, quindi crea la Release GitHub. `CHANGELOG.md` conserva
lo storico e `RELEASE_NOTES.md` contiene le note della versione corrente.

## Risoluzione dei problemi

### La porta 8765 è già in uso

Probabilmente un'istanza di NaviXav è ancora aperta. Chiudere la sua finestra o
fare clic su **Esci** nell'interfaccia. L'eseguibile rileva un'istanza
esistente; se un'altra applicazione occupa la 8765, sceglie automaticamente una
porta libera tra 8766 e 8775.

Per identificare il processo:

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

È anche possibile avviare l'applicazione su un'altra porta:

```powershell
.\NaviXav.bat --port 9000
```

### La finestra NaviXav non si apre

- rilanciare l'installer completo affinché controlli WebView2;
- verificare che Windows e Microsoft Edge WebView2 Runtime siano aggiornati;
- consultare `%LOCALAPPDATA%\NaviXav\logs\navixav.log`;
- verificare che un antivirus non blocchi `NaviXav.exe` o i processi
  `msedgewebview2.exe`.

L'archivio portatile non può installare WebView2 da solo. Su una macchina priva
di questo componente, utilizzare `NaviXav-Setup-<versione>.exe`.

### La spia MSFS resta rossa

- verificare che il simulatore sia avviato;
- caricare completamente un volo;
- attendere qualche secondo e poi fare clic sulla spia;
- rilanciare l'installer se la copia privata di `SimConnect.dll` fornita con
  NaviXav è stata eliminata o messa in quarantena da un antivirus.

### Nessun piano SimBrief viene caricato

- verificare il Pilot ID o il nome utente in **Impostazioni**;
- generare un OFP su SimBrief prima di ritentare il recupero;
- verificare la connessione a Internet.

### Una carta ufficiale non è disponibile

- verificare che il prefisso ICAO sia coperto da SIA, ENAIRE, LVNL, LFV,
  skeyes, Austro Control, NATS o FAA;
- verificare la connessione a Internet;
- confermare che pista e avvicinamento siano stati determinati;
- utilizzare l'inserimento manuale delle minime se l'estrazione non è
  disponibile.

## Limiti attuali

- la procedura realmente autorizzata può differire dal piano a seconda
  dell'ATIS, della meteorologia e delle istruzioni ATC;
- le minime dipendono dalla categoria dell'aeromobile, dal suo equipaggiamento
  e dalle condizioni operative;
- l'estrazione automatica delle minime è limitata ai formati SIA riconosciuti;
- un PDF privo di georeferenziazione convalidata resta consultabile, ma non può
  essere utilizzato come livello;
- i nuovi dati MSFS richiedono che il simulatore sia raggiungibile.

Confermare sempre le informazioni importanti prima di inserirle nel simulatore.

## Architettura e riservatezza

- `navixav/desktop.py` gestisce la finestra nativa e il ciclo di vita del
  processo;
- `navixav/web/app.py` fornisce l'API FastAPI associata soltanto a
  `127.0.0.1`;
- `navixav/web/static/` contiene l'interfaccia adattiva HTML/CSS/JavaScript;
- `navixav/planner/` completa il piano IFR;
- `navixav/navdata/` costruisce e interroga la base derivata da MSFS;
- `navixav/live/` assicura il monitoraggio SimConnect;
- `navixav/sia.py`, `navixav/faa.py` e `navixav/national_aip.py` gestiscono le
  pubblicazioni ufficiali.

Il servizio locale non è mai in ascolto sulla rete esterna. Il Pilot ID
SimBrief, le preferenze, i riepiloghi dei voli e i PDF in cache restano sulla
macchina. Lasciano il computer solo le richieste necessarie a SimBrief,
OpenStreetMap, la meteorologia e le pubblicazioni AIS ufficiali.

## Licenza

Il codice sorgente attuale di NaviXav è disponibile con la
[licenza PolyForm Noncommercial 1.0.0](LICENSE). È una licenza
**source available**, non una licenza open source.

Copyright 2026 Xavier BEGUE (xalacaga)

La licenza consente l'uso, la modifica e la ridistribuzione per gli scopi non
commerciali da essa definiti. Ogni uso commerciale richiede una licenza
scritta separata dal titolare dei diritti. Ciò include l'integrazione di tutto
o parte del codice attuale in un'applicazione a pagamento o che genera ricavi,
la vendita di una versione modificata o la ridistribuzione commerciale.

Consulta [Licenze commerciali](COMMERCIAL_LICENSE.md) per l'ambito e i dati di
contatto. I contributi di codice richiedono un accordo preventivo perché
NaviXav combina licenze non commerciali e commerciali; consulta
[Contribuire](CONTRIBUTING.md).

Le versioni Git con tag v1.4.12 e precedenti sono state pubblicate separatamente
con Apache 2.0; i diritti già concessi restano validi. I componenti di terze
parti, i dati di navigazione, le carte ufficiali e gli sfondi cartografici
mantengono le proprie condizioni, descritte in [NOTICE](NOTICE) e
[THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES).

## Test

Il profilo riproducibile utilizzato per costruire la distribuzione è:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```

I test contrassegnati `live_msfs` interrogano un simulatore realmente avviato e
non fanno quindi parte del controllo automatico dell'installer.

## Ringraziamenti

NaviXav cresce grazie a ciò che segnala chi lo usa. Grazie a
[Cojarop](https://flightsim.to/profile/Cojarop) per aver proposto i
vincoli di quota e velocità sulla mappa e il rullaggio dettato dal
controllore.
