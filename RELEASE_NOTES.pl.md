# NaviXav 1.6.0

Opublikowano 2026-08-30.

## Nowości

- Czytelniejsze sterowanie: Śledzenie lotu ma teraz widoczny przełącznik do wyłączania i ponownego włączania wszystkich alarmów NaviXav, w tym komunikatów MASTER WARNING i MASTER CAUTION, bez zatrzymywania śledzenia; po aktualizacji historia wersji otwiera się automatycznie przy pierwszym ponownym uruchomieniu, a później pozostaje dostępna na żądanie.
- Natychmiastowa zmiana źródła ruchu na paskach Mapy i Kołowania: selektory VATSIM, IVAO i OpenSky pozostają zsynchronizowane, poprawnie wznawiają pobieranie ruchu i zapisują wybór lokalnie.
- Rzeczywisty ruch OpenSky: NaviXav może wyświetlać publiczne wektory stanu ADS-B w promieniu 100 NM wokół samolotu, z podaniem źródła i pamięcią podręczną przyjazną dla API; ten widok rzeczywisty pozostaje ściśle oddzielony od wstrzykiwania do MSFS.
- Ustawienia podzielono na zwijane kategorie dostosowane do kompaktowych okien, dodano ręczną ścieżkę FSLTL, dostęp do oficjalnego FlyByWire Installer przy braku modeli oraz IVAO jako drugie bezpłatne publiczne źródło ruchu sieciowego obok VATSIM.
- Wyłączna zgodność z MSFS 2024: NaviXav korzysta teraz z natywnego interfejsu SimConnect AI EX1 systemu MSFS 2024 i odrzuca starą bibliotekę DLL MSFS 2020 podczas uruchamiania lub budowania, zamiast kontynuować z nieodpowiednim połączeniem lub funkcjami.
- Wstrzykiwanie ruchu VATSIM do MSFS: NaviXav automatycznie wykrywa FSLTL Base Models w folderze Community, indeksuje pliki aircraft.cfg i reguły VMR bez ich modyfikowania, wybiera najbezpieczniejszy model dokładny lub ogólny, a następnie tworzy, aktualizuje i usuwa wyłącznie własne obiekty SimConnect w ograniczonej strefie wokół gracza. Opcja jest domyślnie wyłączona, a interfejs pokazuje wykrytą wersję FSLTL.
- Ruch w pobliżu: przycisk „Ruch VATSIM” na pasku mapy i „Ruch symulatora” na pasku kołowania pokazuje pozostałe statki powietrzne. Na mapie każdy statek z sieci to sylwetka ustawiona zgodnie z kursem ze znakiem wywoławczym pod spodem, a kliknięcie otwiera jego kartę: typ, częstotliwość, pilot, lotniska startu i lądowania nazwane według bazy MSFS, prędkość względem ziemi i wysokość. Plan kołowania pokazuje ruch z symulatora, jedyny dokładny co do metra. Domyślnie wyłączony; dopóki taki pozostaje, nie jest wykonywane żadne zapytanie.
- Profil pionowy: TOD korzysta teraz w pierwszej kolejności z punktu osiągów z najnowszego OFP SimBrief po sprawdzeniu jego współrzędnych względem aktywnej trasy; górne ograniczenia STAR i podejścia nadal obowiązują, a geometryczne obliczenie 3° przejmuje automatycznie, gdy punktu brakuje lub nie pasuje już do trasy.
- Stanowiska VATSIM online: po włączeniu w ustawieniach NaviXav oznacza kropką częstotliwości lotniska, których stanowisko jest obsadzone, i pokazuje po najechaniu kursorem znak wywoławczy kontrolera oraz jego częstotliwość — sieciowa nie zawsze pokrywa się z publikowaną przez symulator. Ustawienie jest domyślnie wyłączone i dopóki takie pozostaje, nie jest wykonywane żadne zapytanie.
- Częstotliwości lotniska: częstotliwość odlotu uzupełnia teraz wiersz, a rola obejmująca kilka częstotliwości sygnalizuje to znakiem „+n” zamiast sugerować, że jest tylko jedna; szczegóły każdego stanowiska, łącznie z płytami postojowymi, widać po najechaniu kursorem.
- Śledzenie lotu: drugi wskaźnik podaje częstotliwość oczekiwaną na bieżącym etapie i wyróżnia się, gdy radio jest już na niej ustawione. Milczy, gdy lotnisko publikuje kilka częstotliwości dla tej samej roli, bo nic nie mówi, która obsługuje używaną drogę startową.
- Śledzenie lotu: wskaźnik radiowy pokazuje częstotliwość ustawioną na COM1 i nazywa odpowiadające jej stanowisko lotniska, w tym ground dla danej drogi startowej — wystarczy rzut oka, by sprawdzić, czy wpisano podaną częstotliwość.
- Diagnostyka: polecenie „navixav airport” wypisuje częstotliwości lotniska wraz z liczbą, którą symulator oznacza każdą rolę, i zgłasza rolę, której nie potrafi przetłumaczyć, zamiast ją pomijać.
- Częstotliwości lotniska: karty Odlot i Przylot w planie lotu pokazują teraz łańcuch radiowy publikowany przez MSFS, w kolejności jego użycia — ATIS, DEL, GND, TWR przy odlocie, ATIS, APP, TWR, GND przy przylocie. Gdy lotnisko publikuje kilka częstotliwości dla tej samej roli, pozostałe widać po najechaniu kursorem.
- Przygotowanie TOD: przy 50 NM system alarmów prosi o przygotowanie zniżania i wyróżnia kafel TOD; przy 10 NM uruchamia się osobne ostrzeżenie o bliskim TOD, aktywne aż do rozpoczęcia zniżania.
- Konfiguracja samolotu: interfejs prowadzony otrzymał czytelniejszą synoptykę kokpitu z równymi kaflami, ikoną dla każdego systemu, oznaczeniem stanu i kontrolkami świateł; interfejs klasyczny zachowuje poprzedni wygląd.
- Nowy interfejs prowadzony lotem: stały pasek wyróżnia fazę, pas lub procedurę, następną czynność i zalecany moduł; karty odlotu, przylotu i podejścia są przygotowane na pasku, a Kołowanie zyskuje więcej miejsca. Ustawienie Układ interfejsu natychmiast przywraca klasyczny widok bez restartu.
- Plan kołowania: odlot ze stanowiska nosem do terminalu zaczyna się od wypychania, rysowanego na fioletowo gęstą kreską na planie i zapowiadanego w pasku wraz z odległością i kursem po ustawieniu; płyta GA, kołowanie podjęte w trakcie i przylot nie pokazują żadnego.
- Przygotowanie planu: pasek zapowiadający wypełnianie pamięci podręcznej MSFS pokazuje teraz samolot przelatujący przez ramkę wraz ze smugą, dopóki trwa odczyt. Oczekiwanie mogło sięgać kilkudziesięciu sekund bez żadnego ruchu na ekranie.
- Karta MCDU: NaviXav pobiera teraz ZFWCG z SimBrief i pokazuje środek ciężkości przy masie bez paliwa wraz z liczbą pasażerów na stronie mas; ZFWCG jest również widoczny w Dispatchu.
- Wybór źródła ruchu wystarczy teraz, aby wstrzyknąć go do MSFS: wstrzykiwanie jest domyślnie włączone, a pole w ustawieniach służy już tylko do rezygnacji.
- Znacznik „tylko mapa” pojawia się na pasku mapy, gdy ruch jest wyświetlany bez wstrzykiwania, a podpowiedź podaje powód: wyłączone wstrzykiwanie, brak FSLTL lub źródło rzeczywiste.
- Rzeczywisty ruch ADS-B trafia wreszcie do MSFS: typ każdego samolotu jest ustalany z dwóch uzupełniających się rejestrów publicznych, co pozwala wreszcie dobrać mu model FSLTL. Samolot nieznany przy pierwszym odczycie pojawia się przy kolejnym, gdy tylko jego adres zostanie ustalony.
- Wybór źródła ruchu wystarczy teraz, aby wstrzyknąć go do symulatora. Pole „Wstrzykuj ruch sieciowy do MSFS” znika z ustawień: przycisk warstwy jest jedynym przełącznikiem, a to, co pokazuje, faktycznie lata.

## Poprawki

- Zaparkowane samoloty OpenSky pozostają możliwe do wstrzyknięcia, gdy transponder pomija wysokość barometryczną, prędkość lub kurs: NaviXav najpierw używa wysokości geometrycznej, a następnie uzupełnia wyłącznie brakujące dane naziemne.
- Rzeczywisty ruch OpenSky w MSFS: samoloty bez typu ADS-B od razu używają bezpiecznego ogólnego modelu FSLTL zamiast pozostawać niewidoczne, a po odpowiedzi rejestru ICAO24 przechodzą na dokładny model; wstrzykiwanie aktualizuje teraz ich pozycję co sekundę.
- Płynniejszy ruch IVAO i OpenSky w MSFS: NaviXav co sekundę ekstrapoluje pozycję między odczytami sieciowymi i krótko zachowuje samolot pominięty przez źródło, zapobiegając jego znikaniu i ponownemu pojawianiu się; stałe odliczanie 15 sekund, niedokładne dla tych źródeł, usunięto z interfejsu.
- Ruch sieciowy przy bramkach i na drogach kołowania: gdy VATSIM nie publikuje stanu na ziemi, NaviXav określa go teraz na podstawie prędkości nieprzekraczającej 50 kt; zaparkowane i kołujące samoloty są wstrzykiwane zamiast pomijane.
- Inwentarz samolotów: Odśwież wykrywa teraz pilotowalne dodatki z błędną flagą isAirTraffic, takie jak Rafale M, a każdy samolot wyświetla własną lokalną miniaturę zamiast ponownie używać obrazu wczytanego samolotu.
- Plan kołowania po przylocie: rzeczywista pozycja samolotu i kurs pasa wykluczają teraz już minięte zjazdy; po lądowaniu na 24R NaviXav nie proponuje już zawracania do zjazdu znajdującego się za samolotem.
- Mapa: odcinek trasowy planu lotu zachowuje fioletowy kolor, ale jest teraz rysowany linią ciągłą, czytelniejszą przy małym powiększeniu.
- Strona Aircraft: długie ciągi wyposażenia ICAO są teraz zawijane wewnątrz kafla, zamiast nachodzić na sąsiedni profil.
- Tożsamość SimConnect: zmienne tekstowe, takie jak TITLE i ATC MODEL, są teraz deklarowane z jednostką null wymaganą przez SDK MSFS, zamiast dosłownego ciągu NULL, który bez komunikatu zwracał pustą wartość.
- Strona Aircraft: główna tożsamość śledzi teraz na żywo samolot rzeczywiście wczytany w MSFS i automatycznie używa ATC MODEL, gdy dodatek pozostawia TITLE pusty; samolot zaplanowany w SimBrief pozostaje wyraźnie oddzielony dla mas i osiągów OFP.
- Światła zewnętrzne: NaviXav porównuje teraz siedem osobnych SimVars z oficjalną maską MSFS LIGHT STATES; złożone samoloty publikujące tylko stan zbiorczy ponownie pokazują kontrolki i prawidłowo uruchamiają alarmy, z automatycznym powrotem do poprzedniego odczytu, gdy maska jest niedostępna.
- Śledzenie lotu: nowa synoptyka Konfiguracji samolotu jest teraz ściśle ograniczona do własnego bloku i nie powiększa ani nie zaburza kafli śledzenia w czasie rzeczywistym.
- Tryb Demo został usunięty: NaviXav korzysta teraz wyłącznie z najnowszego planu SimBrief i rzeczywistych danych lotu dostarczanych przez MSFS przez SimConnect.
- Interfejs prowadzony: poziomy pasek trasy pozostaje teraz tylko w menu Plan lotu i nie nakłada się już na górny pasek w innych modułach; interfejs klasyczny zachowuje dotychczasowy sposób wyświetlania.
- Nawigacja między modułami: górny pasek prowadzący mierzy teraz rzeczywistą wysokość paska narzędzi i po zmianie menu pozostaje w pełni widoczny zamiast być przycięty.
- Moduł Procedury: faza złożona wyłącznie z przypomnień, jak lądowanie, nie jest już pokazywana jako ukończona przed lotem; jej wskaźnik pozostaje pusty, a jej punkty mają znak informacji zamiast zielonego potwierdzenia.
- Moduł Procedury: faza, do której lot jeszcze nie dotarł, nie pokazuje już potwierdzeń; na postoju zaciągnięty hamulec i zgaszone światła nie zaliczają już punktów po lądowaniu ani wyłączania.
- Plan kołowania: wejście do odlotu jest teraz wybierane spośród wszystkich dostępnych dla samolotu połączeń z drogą startową według odległości od żądanego progu. W CYYZ odlot ze stanowiska 139 na pas 23 prowadzi teraz przez AK, A, H i Q zamiast przecinać pas 15L w drodze do skrzyżowania H3. Każde potwierdzone przecięcie pasa jest dzielone przy wyraźnym punkcie oczekiwania, a trasa zostaje odrzucona, jeśli tej instrukcji zabraknie.
- Ruch sieciowy wstrzykiwany do MSFS: samoloty porzucane przez symulator w trakcie lotu są teraz wykrywane i odtwarzane w kolejnym cyklu, zamiast znikać na dobre, podczas gdy NaviXav sądził, że wciąż je śledzi.
- Dziennik zapisuje teraz każdą zmianę cyklu wstrzykiwania — samoloty śledzone, odtworzone, usunięte i pominięte — dzięki czemu milczące wstrzykiwanie staje się widoczne.
- Etykieta opcji wstrzykiwania nie mówi już tylko o VATSIM: nazywa ruch sieciowy, niezależnie od wybranego źródła.
- Źródło rzeczywiste nosi teraz nazwę „Ruch rzeczywisty · OpenSky” we wszystkich trzech listach wyboru zamiast samej nazwy dostawcy, a etykieta ta wreszcie podąża za językiem interfejsu.
- Samolot znajdujący się dokładnie w miejscu twojego nie jest już pokazywany ani wstrzykiwany: to niemal zawsze twój własny, odwzorowany przez sieć, z którą jesteś połączony. Sąsiednie stanowisko pozostaje widoczne, a przelot nie jest mylony z nałożeniem.
- Samolot, który nie podaje znaku wywoławczego, otrzymuje ogólny i stały znak zamiast adresu szesnastkowego lub pustego pola, które symulator pokazałby jako brakującą rejestrację.
- Wstrzykiwanie ruchu ma teraz własny cykl życia: jego stan można sprawdzić, zamiast pozostawać zamkniętym w usłudze webowej, więc zatrzymane wstrzykiwanie nie może już uchodzić za sprawne.

## Zmiany

- Integration trafic.

Instalator jest weryfikowany za pomocą sumy kontrolnej SHA-256 przed każdą automatyczną aktualizacją.
