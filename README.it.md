# NaviXav

**Documentazione:** [Français](README.md) · [English](README.en.md) ·
[Deutsch](README.de.md) · [Español](README.es.md) · Italiano ·
[Português](README.pt.md) · [Nederlands](README.nl.md) ·
[Polski](README.pl.md)

NaviXav è un assistente IFR locale per Microsoft Flight Simulator. Recupera
automaticamente l’ultimo OFP SimBrief, completa le informazioni terminali con
i dati del simulatore e presenta i valori utili alla preparazione del volo e
all’inserimento nel MCDU.

L’applicazione usa una finestra Windows dedicata e adattiva basata su Microsoft
WebView2. Non apre un browser esterno. Il servizio privato è accessibile solo
su `127.0.0.1`; impostazioni, dati di navigazione, carte e cache rimangono sul
computer.

> NaviXav è destinato esclusivamente alla simulazione di volo. Verificare sempre
> i dati con le pubblicazioni ufficiali aggiornate e le istruzioni ATC.

## Funzioni

- recupero automatico dell’ultimo piano di volo SimBrief;
- Pilot ID o nome utente SimBrief configurabile nell’interfaccia;
- rotta completa con avanzamento dell’aeromobile;
- scelta motivata di pista, SID, STAR, transizioni e avvicinamento;
- vincoli di quota/velocità, quota e livello di transizione, dati ILS,
  quota d’intercettazione e di mancato avvicinamento;
- informazioni aeromobile, dispatch, pesi, carburante e dati MCDU;
- QNH visualizzato sotto i dati del vento;
- monitoraggio MSFS in tempo reale e traccia locale riproducibile;
- rotta disegnata su mappa OpenStreetMap;
- accesso diretto ai PDF ufficiali di partenza e arrivo;
- sovrapposizione della carta solo con georeferenziazione convalidata;
- dati di navigazione direttamente da MSFS, senza Little Navmap, Navigraph o
  EUROCONTROL.

## Requisiti e installazione

- Windows 10 o 11 a 64 bit;
- Microsoft Flight Simulator per dati live e di navigazione;
- account SimBrief con OFP già generato;
- Internet per SimBrief, mappa e pubblicazioni AIS/FAA.

Avviare `NaviXav-Setup-0.1.0.exe`, controllare i prerequisiti e scegliere
**Installa**. Python e le librerie sono inclusi. WebView2 viene installato solo
se manca. È disponibile anche l’archivio portatile: estrarlo e avviare
`NaviXav.exe`.

### SimConnect autonomo

NaviXav non installa, registra, reinstalla o sostituisce mai SimConnect in
Windows. Una moderna `SimConnect.dll` privata è contenuta nella cartella
dell’applicazione. Un’installazione già presente rimane invariata. MSFS deve
essere in esecuzione perché il connettore comunica con il servizio SimConnect
del simulatore.

## Prima configurazione

In **Impostazioni**, scegliere la lingua, inserire Pilot ID o utente SimBrief e
configurare sorgente METAR e preferenze di avvicinamento, pista e aeromobile.
La lingua si applica subito e viene memorizzata localmente. Sono disponibili
francese, inglese, tedesco, spagnolo, italiano, portoghese, olandese e polacco.

All’avvio NaviXav cerca sempre l’ultimo OFP disponibile. La generazione del
piano rimane sul sito web SimBrief.

## Carte ufficiali

La scheda **Carte ufficiali** propone i documenti di partenza e arrivo dalle
fonti supportate, tra cui SIA, ENAIRE, LVNL e FAA d-TPP. I PDF possono essere
visualizzati in NaviXav. Il pulsante di sovrapposizione resta nascosto quando
l’allineamento geografico non è stato convalidato.

## Sorgenti e distribuzione

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Per creare la distribuzione:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

Installer, archivio portatile e checksum SHA-256 vengono creati in `release\`.
Il SimConnect SDK di MSFS serve solo sul computer di compilazione.

## Risoluzione dei problemi e privacy

- Nessun piano: verificare identificativo SimBrief, OFP e Internet.
- Indicatore MSFS rosso: avviare MSFS, caricare il volo e attendere.
- Finestra assente: usare l’installer completo per riparare WebView2.
- Porta 8765 occupata: chiudere la precedente istanza NaviXav.

NaviXav non invia telemetria. Impostazioni, cache e cronologia restano sul
computer; vengono contattati solo SimBrief, OpenStreetMap e le fonti ufficiali
richieste.

Il registro diagnostico a rotazione si trova in
`%LOCALAPPDATA%\NaviXav\logs\navixav.log`. Contiene errori e tempi, ma non
l’identificativo SimBrief né la rotta completa.

## Funzionamento dettagliato

### Piano di volo e procedure

All’avvio NaviXav recupera l’ultimo OFP generato in SimBrief: partenza,
destinazione, alternato, rotta, livello di crociera, aeromobile, carburante,
pesi e METAR. La generazione del piano rimane su SimBrief. I dati letti
direttamente da MSFS completano pista, SID, transizione, STAR e avvicinamento;
un’assegnazione ATIS o ATC diversa può essere impostata nell’interfaccia. Il
blocco Partenza–Rotta–Arrivo è comprimibile e il waypoint attivo cambia colore.

### Guida, avvicinamento e MCDU

La guida mostra distanza, rilevamento, quota prevista, prossimo vincolo,
velocità al suolo (GS) e velocità indicata (IAS). Se disponibili, mostra
frequenza e corso ILS, angolo di discesa, quota d’intercettazione, elevazione
soglia, minime e quota di mancato avvicinamento. Carta ufficiale e ATC hanno
sempre priorità.

La scheda MCDU raggruppa i valori per INIT, F-PLN, RAD NAV, PERF TAKEOFF e PERF
APPR: aeroporti, volo, cost index, crociera, piste, procedure, transizioni, ILS,
QNH, vento, temperatura, minime e dati di decollo conosciuti.

### Mappa, registrazione e documenti ufficiali

La rotta SimBrief è disegnata su OpenStreetMap con stili distinti per SID,
tratta, STAR e avvicinamento. I dettagli a terra sono filtrati secondo lo zoom.
La traccia locale è riproducibile e non viene mai caricata.

Partenza e arrivo sono preselezionati per i PDF ufficiali. Sono supportati SIA
Francia, ENAIRE Spagna, LVNL Paesi Bassi e FAA d-TPP USA. Il pulsante overlay
appare solo con georeferenziazione verificata; un PDF normale resta leggibile,
ma non viene sovrapposto in modo approssimativo.

### Dati locali e cache

Le impostazioni sono in `%LOCALAPPDATA%\NaviXav\user_settings.json`, i dati di
navigazione in `%LOCALAPPDATA%\NaviXav\navixav.sqlite` e i log sotto
`%LOCALAPPDATA%\NaviXav\logs`. Il primo caricamento di aeroporto o procedura può
durare diverse decine di secondi mentre viene popolata la cache MSFS.

## Aggiornamenti automatici e Release

All’avvio NaviXav controlla l’ultima Release pubblica di `xalacaga/NaviXav`.
Se è più recente appare **Aggiorna**. Dopo conferma, l’installer viene scaricato
in `%LOCALAPPDATA%\NaviXav\updates`, verificato con lo SHA-256 pubblicato e
avviato. Un errore di rete non blocca le funzioni di volo.

Il repository è pubblico in lettura; solo i collaboratori autorizzati possono
scrivere. Le versioni seguono `MAJOR.MINOR.PATCH`: `feat:` incrementa minor,
`fix:` patch e `BREAKING CHANGE` o `!:` major. Le note sono in
`RELEASE_NOTES.md` e lo storico in `CHANGELOG.md`.

```powershell
.\scripts\prepare_release.ps1 -Bump auto
.\scripts\publish_release.ps1 -Bump auto
```

La pubblicazione richiede repository pulito e GitHub CLI autenticato. Lo script
esegue test e build, crea tag e pubblica installer, archivio portatile, SHA-256
e note.

## Comandi diagnostici

```powershell
.\NaviXav.bat
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
.\scripts\build_windows.ps1
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```
