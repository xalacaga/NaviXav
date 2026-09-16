# NaviXav 1.7.3

Opublikowano 2026-09-16.

## Nowości

- Plany lotu z MSFS: NaviXav odczytuje teraz plan przygotowany w planerze MSFS, dla pilotów, którzy nie korzystają z SimBrief. Ustawienie „Źródło planu lotu” wybiera między SimBrief a planem MSFS (.PLN); lot wczytany w MSFS jest odczytywany automatycznie, a przycisk „Otwórz plik .PLN” pozwala wybrać inny. Lotniska, trasa, drogi lotnicze, SID, STAR i planowane pasy są wykorzystywane jak OFP z SimBrief; pogoda pobierana jest na żywo. Pierwsze uruchomienie proponuje ten wybór i nie wymaga już konta SimBrief.
- Diagnostyka: polecenie „navixav probe-fms” zapisuje, co załadowany samolot udostępnia ze swojego FMS — plan lotu symulatora przez SimConnect oraz, w Fenix A320, plan FMGC publikowany przez lokalną bramkę EFB — w osobnym raporcie, tylko do odczytu.
- Fenix A320: NaviXav odczytuje aktywny plan lotu FMGC przez lokalną bramkę EFB Fenix, tylko do odczytu. Na mapie trasa FMS jest rysowana na żółto tylko tam, gdzie odbiega od trasy NaviXav (DIRECT TO, nowa STAR), z pozycją w legendzie, a plan na lotnisko zapasowe można pokazać na żądanie; T/C i T/D z FMGC zastępują szacunki (źródło „FMGC samolotu”); w locie faza FMGC zastępuje fazę wyprowadzoną z telemetrii. Śledzenie lotu zyskuje aktywny punkt FMGC, ETA i masy FMS oraz dwa alerty: ograniczenie prędkości 250 kt i punkt wytracania prędkości. Karta MCDU otwiera się kontrolą wiersz po wierszu zawartości FMGC (FROM/TO, lotnisko zapasowe, numer lotu, poziom, pasy, SID, trasa, STAR, podejście, ZFW, prędkości startowe) i kończy lustrem MCDU 1 i 2. Dziennik lotów zachowuje numer lotu i ETA z FMGC.
- FlyByWire i PMDG: lustro MCDU działa także w A32NX/A380X (ekrany odczytywane przez SimBridge, faza FMGC przez zmienną samolotu) oraz w PMDG 737/777 (ekrany CDU nadawane przez SDK po włączeniu EnableCDUBroadcast). Tylko do odczytu, źródło pokazane w lustrze; polecenie „navixav probe-fms” wskazuje, który kanał odpowiada.

## Poprawki

- Mapa: znacznik TOC nie podąża już za samolotem. Zostaje ustalony tam, gdzie wznoszenie faktycznie się kończy, nawet jeśli ATC przydzieliło poziom inny niż planowany, i jest przeliczany tylko po wznowieniu wznoszenia (step climb). Po ponownym uruchomieniu w locie NaviXav nie umieszcza już TOC pod samolotem: przyjmuje TOC z profilu SimBrief albo go nie pokazuje. W przypadku planu MSFS lot jest rozpoznawany po treści, a nie po dacie pliku, którą MSFS nadpisuje przy każdym wczytaniu: dziennik lotu i odzyskany TOC przetrwają ponowne uruchomienie.
- Alerty: alert „Wykryto niebezpieczne otwarcie”, przejęty z sygnału bezpieczeństwa MSFS, został usunięty. Uruchamiał się przy drzwiach lub lukach, które pilot celowo otwiera na ziemi.

## Zmiany

- News.

Instalator jest weryfikowany za pomocą sumy kontrolnej SHA-256 przed każdą automatyczną aktualizacją.
