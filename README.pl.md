# NaviXav

**Oficjalna strona:** [navixav.fr](https://navixav.fr/en)

**Dokumentacja:** [Français](README.fr.md) · [English](README.md) ·
[Deutsch](README.de.md) · [Español](README.es.md) ·
[Italiano](README.it.md) · [Português](README.pt.md) ·
[Nederlands](README.nl.md) · Polski

NaviXav to lokalna aplikacja wspomagająca lot IFR dla Microsoft Flight
Simulator. Pobiera najnowszy plan lotu z SimBrief, uzupełnia informacje
terminalowe danymi z symulatora i przedstawia całość w interfejsie
dostosowanym do przygotowania lotu oraz do wprowadzania danych w MCDU.

Aplikacja ma własne okno Windows, renderowane przez Microsoft WebView2 i
połączone z lokalną usługą na `127.0.0.1`. Ustawienia, dane nawigacyjne i
pamięci podręczne pozostają na komputerze. Przeglądarka systemowa otwiera się
tylko na wyraźne żądanie, np. dla SimBrief, logowania ChartFox, pobierania
FSLTL/AIG i wsparcia projektu.

Okno można dowolnie skalować. Interfejs zmienia układ paneli, elementów
sterujących, kart i wysokości mapy stosownie do dostępnej przestrzeni, aż do
rozmiaru minimalnego 720 × 560 pikseli.

> NaviXav jest przeznaczony wyłącznie do symulacji lotu. Wyświetlane informacje
> należy weryfikować z oficjalnymi publikacjami i obowiązującymi instrukcjami
> ATC.

## Funkcje

### Plan lotu SimBrief

- automatyczne pobranie najnowszego OFP przy uruchomieniu;
- obsługa Pilot ID lub nazwy użytkownika SimBrief;
- wyświetlenie pełnej trasy, od lotniska startu do lotniska docelowego;
- wyróżnienie kolejnego punktu trasy na podstawie rzeczywistej pozycji
  samolotu, z wygaszeniem punktów już minionych;
- masy, paliwo, czas lotu, lotnisko zapasowe i dane dyspozytorskie;
- informacje o statku powietrznym, znaki rejestracyjne i zadeklarowane
  wyposażenie.
Baner aktywnego lotu pokazuje pozostały czas z pozostałej odległości i prędkości
względem ziemi, gdy są użyteczne, a przed startem zastępczo ETE SimBrief. Po
zapisaniu ustawień plan odświeża się w tle bez zatrzymywania okna dialogowego.
Polecenia panelu MSFS zachowują inne ustawienia, w tym identyfikatory SimBrief.


### Pogoda dla lotu

- najważniejsze dane METAR i TAF dla odlotu, przylotu i lotniska zapasowego;
- wiatr i temperatura w przelocie z OFP SimBrief;
- w trybie **METAR na żywo** automatyczne odświeżanie co pięć minut z
  aviationweather.gov oraz przycisk natychmiastowego odświeżenia;
- graficzna prezentacja pogody, wiatru, widzialności i podstawy chmur bez
  automatycznej zmiany drogi startowej lub procedur planu.

### Przygotowanie IFR

NaviXav uzupełnia i przedstawia:

- drogę startową odlotu i drogę startową przylotu;
- SID i jego przejście;
- STAR i jego przejście;
- podejście i jego VIA;
- częstotliwość i identyfikator ILS;
- ograniczenia wysokości i prędkości;
- wysokość przejściową i poziom przejściowy;
- wysokość przechwycenia podejścia;
- wysokość nieudanego podejścia;
- uzasadnienie i poziom pewności każdego wyboru.

Bloki **Odlot · Trasa · Przylot** można zwinąć, aby zwolnić miejsce w
interfejsie.

Każdy import SimBrief i ponowne obliczenie sprawdza połączenia SID–trasa–STAR–podejście według rzeczywiście przelatywanych punktów końcowych w danych MSFS, również gdy nazwa przejścia różni się od punktu połączenia. Brakujące połączenia wymagają potwierdzenia; przejście nie jest wybierane arbitralnie. Odgałęzienia drogi startowej dokładnie powielające początek STAR nie tworzą już powrotu do jej wejścia; odrębne ograniczenia pozostają zachowane. Trasa zachowuje DCT i drogi lotnicze z OFP. Wybrane przejścia nieobecne w bazie są oznaczane jako niezweryfikowane.

### Śledzenie lotu

Karta **Śledzenie lotu** wykorzystuje pozycję MSFS w czasie rzeczywistym, aby
wyświetlić:

- automatycznie wykrytą fazę lotu;
- prędkość względem ziemi (GS) i prędkość przyrządową (IAS) podawane przez
  MSFS;
- kolejny punkt i odległość do niego;
- odchylenie boczne względem aktywnego odcinka;
- pozostałą odległość;
- następne ograniczenie wysokości lub prędkości;
- prędkość pionową wymaganą do osiągnięcia tego ograniczenia;
- Top of Descent z profilu osiągów najnowszego OFP SimBrief po sprawdzeniu go
  względem aktywnej trasy, z oszacowaniem 3° jako rozwiązaniem awaryjnym oraz z
  zachowaniem opublikowanych górnych ograniczeń STAR i podejścia;
- odchylenie od zaplanowanego profilu pionowego.

Po lądowaniu lokalny dziennik zapisuje zwięzłe podsumowanie lotu i ograniczoną
oś zdarzeń: fazy lotu, drogę startową startu i lądowania z zaobserwowanym
wiatrem oraz stabilne zmiany podwozia, klap, spoilerów, hamulca postojowego,
świateł i trybów autopilota. Zdarzenia są zapisywane jako dane i odtwarzane w
aktualnie wybranym języku. Wszystkie podsumowania można usunąć z interfejsu,
a dane lotu nie są wysyłane do usług zewnętrznych.

W interfejsie prowadzonym wartości te są przedstawiane jako synoptyka kokpitu
z równymi kaflami przyrządów, wyraźnymi stanami i kontrolkami świateł. Interfejs
klasyczny zachowuje pierwotne kompaktowe kafle.
Strona Aircraft używa tytułu przekazywanego na żywo przez MSFS jako głównej
tożsamości i aktualizuje się automatycznie po wczytaniu innego samolotu. Samolot
z SimBrief pozostaje widoczny osobno, ponieważ masy i osiągi dispatchu nadal
należą do zaimportowanego OFP.
Jeśli samolot zewnętrzny pozostawia `TITLE` pusty, NaviXav automatycznie używa
jego oficjalnej wartości `ATC MODEL`.
Dla świateł zewnętrznych NaviXav porównuje także SimVars poszczególnych
przełączników z oficjalną maską MSFS `LIGHT STATES`. Dzięki temu złożone
samoloty publikujące tylko stan zbiorczy nie pozostawiają już wszystkich
kontrolek i alarmów błędnie wyłączonych.
Od 50 NM przed TOD standardowy system alarmów prosi o przygotowanie zniżania;
przy 10 NM pojawia się osobne ostrzeżenie o bliskim TOD, aktywne aż do
rozpoczęcia zniżania.

Dla klap, spoilerów i hamulca postojowego NaviXav porównuje oficjalne SimVars
dźwigni, pozycji efektywnej, powierzchni i wskaźnika kokpitu. Konfiguracja
samolotu i zdarzenia lotu są dzięki temu aktualizowane nawet wtedy, gdy samolot
zewnętrzny pozostawia jedną standardową wartość MSFS bez zmian.
Dedykowany adapter Fenix A319/A320/A321 odczytuje bezpośrednio trzy dźwignie w
kokpicie, dlatego zmiany klap, spoilerów i hamulca postojowego są rejestrowane
również przy wyłączonych silnikach i układach hydraulicznych.

W Fenix A319/A320/A321 NaviXav odczytuje tryb STD z EFIS kapitana na potrzeby wyświetlania i ostrzeżeń QNH/STD. Sprzeczna ogólna SimVar MSFS nie zastępuje już tego trybu. Jeśli odczyt Fenix jest niedostępny lub nieprawidłowy, ustawienie pozostaje nieznane, a ostrzeżenia nie są wyzwalane na podstawie ogólnego ciśnienia. Odczyt nie monitoruje strony drugiego pilota.

W tych Fenix odczytywane są także bezpośrednio oba przełączniki
przeciwoblodzeniowe silników. Gdy odczyt jest niedostępny, stan pozostaje
nieznany zamiast wywoływać fałszywy alarm ze standardowej SimVar.

W Fenix A319/A320/A321 wykrywanie STD odczytuje rzeczywisty stan barometru kapitana (B_FCU_EFIS1_BARO_STD), zamiast wejścia S_FCU_EFIS1_BARO_STD. Powrót wejścia do zera nie powoduje już fałszywego alarmu przy wyświetlanym STD. Niedostępne lub nieprawidłowe odczyty pozostają nieokreślone.

Monitorowanie ILS używa odbiornika przypisanego przez załadowany samolot. Fenix A319/A320/A321 i FlyByWire A32NX używają kapitańskiego NAV3; pozostałe samoloty używają indeksu NAV1–NAV4 wybranego przez MSFS. Gdy indeks lub częstotliwość są niedostępne, alarm pozostaje wyciszony zamiast porównywać inny odbiornik.

Wyświetlany TOD jest szacunkiem SimBrief lub NaviXav, a nie odczytem MCDU. Profil FMS może wskazać inny punkt przy tej samej trasie i poziomie lotu. Jeśli ograniczenia przyspieszą punkt SimBrief, źródło zmienia się na szacunek obliczony.

Śledzenie lotu i panel w symulatorze pokazują „Zniżanie w toku” zamiast TOD podczas zniżania, a następnie „Podejście”. Odcinki poziome zachowują komunikat, jeśli utrata wysokości potwierdza zniżanie. Status pochodzi z telemetrii, nie z trybu DES FMS.

### Karta MCDU

Karta **Karta MCDU** dostosowuje strony do typu samolotu: MCDU Airbusa, CDU
Boeinga lub ogólny FMS dla pozostałych maszyn. Nie pokazuje parametrów
startowych, których nie można zautomatyzować:

- `FROM/TO`, numer lotu i lotnisko zapasowe;
- Cost Index i poziom przelotowy;
- ZFW, ZFWCG, liczba pasażerów, paliwo blokowe, kołowania, przelotu i rezerwy;
- droga startowa, SID, przejście i wysokość przejściowa;
- trasa `VIA/TO`;
- STAR, przejście, podejście i VIA;
- QNH, temperatura, wiatr, częstotliwość ILS i kurs końcowy;
- minima RADIO lub BARO oraz RVR.

### Bezpośrednie połączenie z MSFS

NaviXav wykorzystuje SimConnect, aby:

- wykryć obecność symulatora;
- pokazać zieloną lub czerwoną kontrolkę na górnym pasku;
- śledzić pozycję samolotu w czasie rzeczywistym;
- odczytywać wysokość, wysokość nad terenem, kurs, prędkość względem ziemi i
  prędkość pionową;
- rozróżniać STD od QNH zachowanego na wysokościomierzu i opcjonalnie ostrzegać
  o niebezpiecznie otwartych drzwiach, luku lub osłonie kabiny;
- pobierać lotniska, drogi startowe wraz z oświetleniem krawędzi i osi,
  procedury, punkty nawigacyjne i pomoce radionawigacyjne;
- stopniowo budować lokalną bazę w pliku `data/navixav.sqlite`.

Przycisk **Ruch** na Mapie lub Kołowaniu steruje wyświetlaniem i wstrzykiwaniem
do MSFS; domyślnie jest wyłączony. Źródła to VATSIM, IVAO, OpenSky (rzeczywisty
ruch ADS-B) i ruch statyczny. Selektory współdzielą ustawienie lokalne; okno
odczytuje także zmiany z panelu MSFS co trzy sekundy.

Zmiana ustawienia niezwiązanego z ruchem nie uruchamia już ponownie
wstrzykiwania ani istniejących samolotów. Zmiany źródła, modeli i aktywnego
ruchu statycznego nadal są stosowane. Moduły współdzielą odczyt MSFS ze
znacznikiem czasu przez najwyżej 250 ms; pozycja i wysokość gracza pochodzą z
tego samego stanu dla wstrzykiwania. Wygasły odczyt lub błąd połączenia nie
przedstawia starej pozycji jako aktualnej.

Ustawienia oferują **FSLTL Base Models** lub **AIG AI Traffic**, jeden zestaw
naraz. Obie instalacje są wykrywane; ścieżki FSLTL, AIG i Community można podać
ręcznie. NaviXav odczytuje `aircraft.cfg` i reguły VMR bez instalowania lub
zmieniania bibliotek. FSLTL otwiera [pobieranie
FlyByWire](https://flybywiresim.com/downloads/) dla **FSLTL Traffic Base
Models**; AIG otwiera [oficjalną stronę](https://www.alpha-india.net/). AI
Manager instaluje `aig-aitraffic-oci`; brakujące pakiety dodatkowe są zgłaszane.

OpenSky wyszukuje rzeczywisty ruch w ustawionym promieniu. Dostęp anonimowy jest odświeżany co cztery minuty, aby przestrzegać dziennego limitu publicznego. Po odpowiedzi HTTP 429 NaviXav wyraźnie pokazuje **Dzienny limit OpenSky wyczerpany** w obu interfejsach i respektuje podany czas ponowienia zamiast stale wysyłać żądania; animacja istniejącego ruchu trwa do czasu odzyskania źródła. Wstrzykiwanie zależy od
dostępnych modeli: FSLTL może użyć ogólnego modelu przy nieznanym typie; AIG nie
ma takiego zastępstwa. Samolot na mapie nie musi być wstrzyknięty. NaviXav
blokuje lub zatrzymuje wstrzykiwanie po wykryciu FSLTL Traffic Injector albo AIG
Traffic Controller. Po zamknięciu tego programu wyłącz i ponownie włącz Ruch;
wznowienie nie jest automatyczne.

Ustawienia zawsze pokazują promień ruchu i maksymalną liczbę samolotów dla każdego źródła. Wartości domyślne to **40 NM** i **10 samolotów**, regulowane od 1 do 100 NM i od 1 do 200 samolotów. Najbliższe samoloty mają pierwszeństwo.

**Ruch statyczny** używa tylko stanowisk obecnych już w pamięci podręcznej
nawigacji MSFS. Potrzebny jest wczytany lot i dane stanowisk; wybór źródła nie
pobiera brakujących instalacji. Najbliższe miejsca są zajmowane najpierw. Mapa
i wstrzykiwanie współdzielą pamięć
podręczną; pusty wynik jest ponawiany po trzech sekundach. Samoloty statyczne
pozostają zaparkowane: nie kołują ani nie startują.

Mapa i Kołowanie rozróżniają wczytywanie, utworzenia potwierdzone przez MSFS,
brak odpowiedniego ruchu, błędy i nieaktualny stan. Podpowiedź podaje wybrane i
pominięte samoloty. Potwierdzenie dotyczy utworzenia obiektu, nie widoczności
lub gwarantowanej płynności. Tworzenie odbywa się partiami; katalog jest używany
ponownie do minuty przy szybkich zmianach. Osobne połączenie SimConnect animuje
z docelową częstotliwością 30 aktualizacji na sekundę; pozycje Kołowania są
interpolowane. Lokalne dzienniki mierzą częstotliwość i przerwy. Wyłączenie i
zamknięcie zwalnia połączenia i usuwa tylko obiekty utworzone przez NaviXav.

Śledzenie używa prawidłowych indywidualnych znaczników czasu pozycji OpenSky: otrzymanie starego odczytu nie czyni go aktualnym, a pozycje otrzymane poza kolejnością są ignorowane. Bez użytecznego indywidualnego znacznika czasu NaviXav zachowuje ostrożne lokalne oszacowanie. Ukryte widoki Mapy i Kołowania wstrzymują odczyty ruchu i rysowanie; ich pokazanie wznawia odczyty i dopasowanie rozmiaru. Śledzenie lotu i wstrzykiwanie do MSFS pozostają aktywne.

Okresowe odczyty pozycji, ruchu, kontrolerów VATSIM i stanu symulatora zapobiegają nakładaniu się żądań tego samego odczytu i odrzucają odpowiedzi nieaktualne po zmianie kontekstu. W widoku Kołowania błąd tymczasowy zachowuje ostatnie pozycje przez najwyżej dziesięć sekund od ostatniego udanego odczytu, z ostrzeżeniem. Potwierdzony pusty odczyt lub wyłączenie ruchu natychmiast usuwa pozycje.

Na ziemi zgłoszenie zatrzymania kończy przewidywanie, a wygładzanie prowadzi do otrzymanej pozycji parkingowej bez zachowania pędu. Bez nowego zgłoszenia ruchu przewidywanie zwalnia, a jego okno jest ograniczone do pięciu sekund; przejścia pozostają płynne. Drobne wahania pozycji już zaparkowanego samolotu są filtrowane. Reguły korzystają z pozycji źródła, bez wykrywania budynków.

Panel MSFS pokazuje teraz Mój lot: następny punkt i odległość, pozostały czas, następne ograniczenie i TOD, zsynchronizowane z oknem NaviXav i jego językiem. Wartości lotu są ukrywane po dziesięciu sekundach bez aktualizacji. Ruch pokazuje samoloty potwierdzone, wybrane i pominięte, ładowanie, błędy i nieaktualne stany; zielona kropka wymaga potwierdzonego utworzenia obiektów. Przycisk powrotu otwiera okno ze szczegółami. Zainstaluj ponownie panel 1.2.1 w ustawieniach i uruchom ponownie MSFS, aby wczytać nowe pliki.

Panel MSFS 1.2.1 automatycznie ponawia połączenie z NaviXav po przerwie lub zmianie portu. Niedostępne połączenie nie jest już przedstawiane jako zamknięta aplikacja. Żądania mają rzeczywisty limit czasu, a błędy wyświetlania nie zatrzymują ponownego łączenia. Po aktualizacji panelu w ustawieniach należy ponownie uruchomić MSFS.

**Zainstaluj panel MSFS** kopiuje tylko ten
pakiet do Community; **Usuń** go usuwa. Gdy wersja zainstalowana różni się od
dostarczonej, ustawienia proponują ponowną instalację. Przyciski pozostają
zablokowane i animowane podczas operacji. W razie potrzeby uruchom MSFS
ponownie, aby przeładować pakiet. Powrót do okna działa w trybie okienkowym lub
bez ramek; wyłączny pełny ekran może zachować fokus.

Symulator musi być uruchomiony z wczytanym lotem, aby pobrać nowe dane.
Informacje już zapisane w pamięci podręcznej pozostają dostępne offline.

Gdy szczegółowy dziennik nawigacyjny SimBrief zawiera zweryfikowane
współrzędne, NaviXav od razu wykorzystuje je do rysowania trasy i odpytuje
MSFS Facilities tylko o brakujące pozycje. Opublikowane powiązania procedur
również eliminują zbędne wyszukiwanie pozycji. Pierwsze wczytanie planu jest
dzięki temu szybsze, przy zachowaniu kontroli korytarza i lokalnej pamięci
podręcznej MSFS jako rozwiązania awaryjnego.

### Mapa

Mapa obejmuje:

- podkład OpenStreetMap;
- trasę SimBrief narysowaną wraz z jej punktami;
- odrębne kolory dla SID, części trasowej, STAR i podejścia;
- drogi startowe oraz wybraną drogę startową;
- pozycję i kurs samolotu;
- ślad przemieszczenia;
- tryb automatycznego śledzenia;
- powiększanie, przesuwanie i dopasowanie do lotniska lub trasy.

Paski Mapy i Kołowania grupują sterowanie widokiem, wyświetlaniem i ruchem. Przyciski mają 40 pikseli wysokości, zoom pozostaje zgrupowany, a układ dostosowuje się do małych okien. Zezwolenie na kołowanie i działania trasy pozostają razem.

W szerokich oknach elementy sterowania Mapą i Kołowaniem pozostają podczas przewijania pod paskiem lotu, zgodnie z jego zmierzoną wysokością. Zmiana modułu aktualizuje pomiary przed przewinięciem. W małych oknach pasek i elementy sterowania przewijają się normalnie.

Animacja zachowuje rytm po opóźnionej klatce bez dodatkowego pełnego oczekiwania. Bliskie samoloty mają priorytet przy 30 Hz; powyżej 10 NM stosowane jest 15 Hz, a powyżej 40 NM 5 Hz. Ustabilizowane samoloty na parkingu nie są przeliczane w każdej klatce. Przyspieszanie jest wygładzane, kurs zmienia się najkrótszą drogą, a zatrzymanie pozostaje natychmiastowe. Limity przewidywania na parkingu pozostają zachowane.

### Kołowanie

Karta **Kołowanie** przedstawia osobny plan lotniska, niezależny od mapy lotu
i zbudowany wyłącznie z natywnych obiektów MSFS:

- obszar rysowania wypełnia całe dostępne miejsce, także w małych oknach;
- ciemne tło lotnicze z siatką metryczną i strzałką północy daje skalę oraz
  orientację bez bałaganu mapy drogowej;
- drogi startowe, główne drogi kołowania, stanowiska i samolot mają priorytet wizualny;
- nazwane drogi kołowania pozostają widoczne nawet wtedy, gdy MSFS klasyfikuje
  je jako ogólne segmenty `path`; domyślnie ukryte są tylko nienazwane
  połączenia drugorzędne i dojazdy do stanowisk, a przycisk **Drugorzędne**
  pokazuje je na żądanie;
- przy odlocie NaviXav automatycznie proponuje trasę do wybranej drogi startowej,
  gdy samolot stoi na ziemi w odległości do 180 m od stanowiska;
- wejściem do odlotu jest dostępne dla samolotu połączenie najbliższe wybranemu
  progowi, nawet gdy MSFS oznacza dalsze połączenie jako punkt oczekiwania;
- kliknięcie innego stanowiska natychmiast zastępuje propozycję; po przylocie
  stanowisko docelowe wybiera się ręcznie;
- widoczne są część przebyta i pozostała, potrzebne nazwy, punkty oczekiwania,
  następny manewr i pozostała odległość;
- każde przecięcie pasa potwierdzone przez sieć MSFS dzieli trasę przy wyraźnym
  punkcie oczekiwania; trasa jest odrzucana, jeśli tej instrukcji nie da się przedstawić;
- po zjechaniu z trasy jest ona przeliczana od rzeczywistej pozycji samolotu;
- prędkość względem ziemi jest pokazywana na żywo na planie, z ostrzeżeniem
  przy zbliżaniu się do maksymalnej prędkości kołowania i migającym alarmem z
  sygnałem dźwiękowym po jej przekroczeniu; limit zaostrza się na zakrętach,
  przed poprzeczką zatrzymania i przy stanowisku, a na pasie nie obowiązuje.

Ścieżki parkingowe SimConnect służą wyłącznie do łączenia stanowisk z siecią i
nie mogą tworzyć sztucznych skrótów przez drogi startowe.

### Oficjalne krajowe mapy AIS

NaviXav odpytuje bezpośrednio publikacje władz krajowych, z pominięciem
EUROCONTROL/EAD:

- Francja: SIA eAIP (`LF`);
- Hiszpania i Wyspy Kanaryjskie: AIP ENAIRE (`LE`, `GC`, `GE`);
- Holandia: LVNL eAIP (`EH`);
- Szwecja: LFV eAIP (`ES`);
- Belgia i Luksemburg: skeyes eAIP (`EB`, `EL`);
- Austria: Austro Control eAIP (`LO`);
- Zjednoczone Królestwo: NATS eAIP (`EG`);
- Stany Zjednoczone i objęte terytoria: FAA d-TPP.

Dla tych lotnisk NaviXav może:

- przedstawić na karcie **Mapy oficjalne** wszystkie pliki PDF odlotu i
  przylotu, uporządkowane według typu;
- otworzyć każdy dokument w interfejsie lub osobno;
- domyślnie wybrać SID, STAR lub podejście odpowiadające bieżącemu lotowi;
- automatycznie odnaleźć mapę podejścia odpowiadającą wybranej drodze startowej
  i rodzajowi podejścia;
- pobierać na żądanie wyłącznie faktycznie przeglądane pliki PDF;
- zachować publikację w lokalnej pamięci podręcznej AIRAC;
- wyświetlić mapę oficjalną na karcie MCDU;
- odczytać minima ILS CAT I z SIA, gdy format zostanie rozpoznany;
- zaproponować DA, DH i RVR przed zatwierdzeniem.

Odczytane wartości nigdy nie są stosowane automatycznie: muszą zostać
zatwierdzone w interfejsie. Przycisk **Warstwa oficjalna** jest oferowany
wyłącznie dla dokumentu z zatwierdzonym georeferencjonowaniem. Podąża za
wyborem mapy: plik PDF odlotu można nałożyć tylko na odlot, a plik przylotu
tylko na przylot. Zasada ta jest identyczna dla wszystkich źródeł.

Kraj jest dodawany do listy automatycznej dopiero po zatwierdzeniu
bezpośredniego i stabilnego dostępu do jego oficjalnych plików PDF. Brakujące
źródło nigdy nie jest więc po cichu zastępowane agregatorem zewnętrznym.

ChartFox jest dostępny jako opcjonalne źródło na tej samej karcie **Mapy**.
Połącz konto ChartFox/VATSIM w **Ustawieniach**, a następnie wybierz ChartFox dla
lotniska odlotu lub przylotu. Logowanie odbywa się w przeglądarce systemowej
przez OAuth 2.0 z PKCE; NaviXav nigdy nie prosi o dane logowania VATSIM i chroni
token użytkownika lokalnie za pomocą Windows DPAPI. Dokumenty są pobierane na
żądanie, nie są zapisywane na dysku, służą wyłącznie do symulacji i zachowują
oznaczenie „Chart data powered by ChartFox”. Warstwy ChartFox pozostają
wyłączone, dopóki NaviXav nie otrzyma zakresu `charts:geos`.
Gdy źródło zabrania osadzania, NaviXav wyjaśnia ograniczenie i udostępnia stronę
mapy w ChartFox zamiast wyświetlać pusty podgląd.
Jeśli lotnisko obsługuje krajowy łącznik, NaviXav najpierw proponuje przełączenie
karty na oficjalny katalog i pozostanie w aplikacji.

## Wymagania

- Windows 10 lub Windows 11 w wersji 64-bitowej;
- Microsoft WebView2 Runtime, instalowany automatycznie przez instalator;
- Microsoft Flight Simulator dla danych i śledzenia w czasie rzeczywistym;
- konto SimBrief z wygenerowanym OFP;
- połączenie internetowe dla SimBrief, podkładu mapowego oraz krajowych
  publikacji AIS lub FAA.

Instalator zawiera Pythona, biblioteki, pywebview, autonomiczny łącznik
SimConnect firmy NaviXav oraz podpisany bootstrapper Microsoft WebView2. Żadne
z tych narzędzi nie wymaga osobnej instalacji. MSFS nie jest niezbędny, aby
przejrzeć już zapisane dane.

NaviXav nigdy nie instaluje ani nie instaluje ponownie SimConnect w systemie
Windows. Aplikacja zawiera prywatną kopię nowoczesnej biblioteki DLL we własnym
folderze. Jeśli komputer posiada już SimConnect, jego instalacja, wersja i
ustawienia nie są zastępowane ani zmieniane. Ta prywatna biblioteka DLL
komunikuje się z usługą SimConnect w MSFS: aby odbierać dane na żywo, wystarczy
zainstalowany i uruchomiony symulator.

### Języki interfejsu

Język wybiera się w **Ustawieniach**, stosuje się natychmiast i pozostaje
zapamiętany na komputerze. NaviXav udostępnia interfejsy w języku francuskim,
angielskim, niemieckim, hiszpańskim, włoskim, portugalskim, niderlandzkim i
polskim. Skróty lotnicze, identyfikatory procedur, METAR i wartości MCDU
pozostają celowo w zapisie międzynarodowym.

## Szybka instalacja w systemie Windows

1. Pobrać plik `NaviXav-Setup-<wersja>.exe` z najnowszego
   [wydania GitHub](https://github.com/xalacaga/NaviXav/releases/latest).
2. Uruchomić instalator.
3. Sprawdzić stronę kontroli wymagań.
4. Zachować lub zmienić proponowany folder, a następnie kliknąć
   **Zainstaluj**.
5. Uruchomić NaviXav z menu Start lub z opcjonalnego skrótu na pulpicie.

Instalator sprawdza Microsoft WebView2 i instaluje go automatycznie w razie
braku. Instalacja odbywa się dla bieżącego użytkownika i zwykle nie wymaga
uprawnień administratora.

Dostępne jest również archiwum przenośne: rozpakować
`NaviXav-<wersja>-windows-x64-portable.zip`, a następnie uruchomić
`NaviXav.exe`. Na komputerze bez WebView2 należy najpierw użyć pełnego
instalatora.

### Ze źródeł

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Przy pierwszym uruchomieniu skrypt:

1. wyszukuje Pythona;
2. tworzy środowisko wirtualne `.venv`;
3. instaluje NaviXav i jego zależności;
4. uruchamia prywatną usługę lokalną;
5. otwiera interfejs w oknie NaviXav.

Kolejne uruchomienia korzystają z już zainstalowanego środowiska.

### Budowanie dystrybucji

Z programu PowerShell, w folderze projektu:

```powershell
.\scripts\build_windows.ps1
```

Skrypt:

1. sprawdza 64-bitowy system Windows, Pythona i SDK SimConnect MSFS 2024;
2. instaluje brakujące narzędzia budowania;
3. pobiera oficjalny bootstrapper WebView2 i weryfikuje jego podpis Microsoft;
4. wykonuje testy z pominięciem integracji z działającym MSFS;
5. tworzy instalator, archiwum przenośne oraz ich sumy SHA-256 w folderze
   `release\`.

SDK SimConnect MSFS 2024 wymienione w punkcie 1 dotyczy wyłącznie komputera, na
którym budowany jest NaviXav. Aktualna biblioteka DLL jest prywatnie dołączana
do NaviXav i nie jest instalowana ani rejestrowana na komputerach użytkowników.
Stara biblioteka DLL MSFS 2020 jest odrzucana.

### Pliki dystrybucyjne

Po udanym zbudowaniu:

| Plik | Zastosowanie |
|---|---|
| `release\NaviXav-Setup-<wersja>.exe` | zalecany instalator Windows |
| `release\NaviXav-<wersja>-windows-x64-portable.zip` | wersja przenośna |
| `release\*.sha256` | sumy kontrolne dystrybuowanych plików |

Folder `release\` jest celowo pomijany przez Git. Pliki wykonywalne są
artefaktami budowania przeznaczonymi do publikacji w wydaniu GitHub, a nie
źródłami do wersjonowania.

## Instalacja ręczna

Z programu PowerShell, w folderze projektu:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m navixav.desktop
```

To polecenie otwiera okno NaviXav. Aby zdiagnozować usługę lokalną bez okna:

```powershell
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
```

Usługa pozostaje wówczas dostępna wyłącznie pod adresem
`http://127.0.0.1:8765`.

## Konfiguracja

Bieżącą konfigurację przeprowadza się przyciskiem **Ustawienia** w interfejsie.

### Konto SimBrief

Należy wypełnić jedno z dwóch pól:

- **Pilot ID SimBrief**: identyfikator liczbowy widoczny w ustawieniach konta
  SimBrief;
- **Nazwa użytkownika SimBrief**: alias konta.

Zalecany jest Pilot ID. Po zapisaniu NaviXav natychmiast pobiera najnowszy
dostępny OFP. Przy każdym kolejnym uruchomieniu ten ostatni plan jest wczytywany
automatycznie.

### Dostępne ustawienia

Podczas zapisywania ustawień przycisk wyświetla animowany wskaźnik i „Zapisywanie…”. Pozostaje wyłączony do zakończenia operacji, aby uniknąć podwójnego wysłania, a następnie jest dostępny również po błędzie. Animacja uwzględnia preferencję ograniczonego ruchu.

Interfejs pozwala również skonfigurować:

- źródło METAR;
- kolejność preferencji podejść;
- maksymalną składową wiatru tylnego;
- maksymalną składową wiatru bocznego;
- minimalną długość drogi startowej;
- wygląd interfejsu: automatyczny, jasny lub ciemny;
- układ interfejsu: prowadzony lotem, z paskiem kontekstowym zależnym od fazy
  oraz przygotowanymi kartami odlotu/przylotu/podejścia, albo klasyczny, aby
  bez restartu natychmiast wrócić do poprzedniego widoku;
- folder Community MSFS używany do inwentaryzacji procedur dla samolotów;
- maksymalną prędkość kołowania, niższy limit stosowany na zakrętach oraz
  alarm dźwiękowy prędkości kołowania;
- zdolność RNP statku powietrznego.

W wersji zainstalowanej wartości są przechowywane w pliku
`%LOCALAPPDATA%\NaviXav\user_settings.json`.

### Procedury dla samolotu

Moduł **Procedury** dopasowuje samolot załadowany w MSFS do lokalnej bazy
NaviXav. Pokazuje normalne procedury według faz lotu, ich postęp oraz punkty
potwierdzane automatycznie przez SimConnect. Informacja o źródle używa wybranego
języka. Pokrycie można sprawdzić w domyślnie zwiniętej sekcji
**Procedury dla samolotu** w ustawieniach.

## Pierwsze użycie

1. Wygenerować plan lotu w SimBrief.
2. Uruchomić Microsoft Flight Simulator i wczytać lot.
3. Uruchomić NaviXav z menu Start lub poleceniem `NaviXav.bat` w trybie
   deweloperskim.
4. Otworzyć **Ustawienia** i zapisać Pilot ID SimBrief.
5. Zaczekać na automatyczne wczytanie najnowszego OFP.
6. Sprawdzić kontrolkę **MSFS połączony** w prawym górnym rogu.
7. Zweryfikować wybory drogi startowej, SID, STAR i podejścia.
8. Sprawdzić ograniczenia i mapę oficjalną.
9. Zatwierdzić minima przed przepisaniem ich do MCDU.

Przycisk **Uzupełnij plan** pozwala ponownie pobrać najnowszy OFP po
wygenerowaniu lub zmodyfikowaniu lotu w SimBrief.

## Korzystanie z mapy

- **Podkład mapy**: pokazuje lub ukrywa OpenStreetMap.
- **Kołowanie**: otwiera osobny plan naziemny; **Drugorzędne** pokazuje lub
  ukrywa dojazdy i mniej istotne drogi kołowania.
- **Warstwa oficjalna**: pojawia się wyłącznie dla georeferencjonowanej mapy
  aktualnie wyświetlanego lotniska i reguluje jej krycie.
- **Cała trasa**: kadruje całą trasę lotu.
- **Śledź**: utrzymuje samolot na środku.
- **Dopasuj**: kadruje wybrane lotnisko.
- **+ / −**: zmienia poziom powiększenia.
- **Kółko myszy**: przybliża pod wskaźnikiem.
- **Przeciąganie**: przesuwa mapę.

Przyciski lotnisk pozwalają szybko przechodzić między lotniskiem odlotu a
lotniskiem przylotu.

## Okno i widok responsywny

### Dostęp z telefonu i tabletu w sieci lokalnej

Włącz **Dostęp z telefonu i tabletu** w **Ustawieniach**, zapisz i uruchom
NaviXav ponownie. Otwórz chroniony adres wyświetlany na komputerze na urządzeniu
podłączonym do tej samej sieci Wi-Fi. Interfejs mobilny udostępnia śledzenie na
żywo, mapę, ograniczenia, dane MCDU, samolotu i oficjalne mapy. Ustawienia,
zamykanie i aktualizacje pozostają dostępne tylko na komputerze. Jeśli Windows
zapyta, zezwól NaviXav wyłącznie w sieciach prywatnych.

Na ekranach zdalnych węższych niż 760 px stan połączenia MSFS jest pokazywany
wyłącznie jako kolorowa kropka, dzięki czemu `MSFS connected` nie wychodzi poza
pasek narzędzi. Przetłumaczona etykieta pozostaje dostępna dla technologii
wspomagających.
Mobilny pasek narzędzi zawiera również własny wybór języka bez udostępniania
ustawień przeznaczonych wyłącznie dla komputera.

NaviXav automatycznie dostosowuje interfejs przy zmianie rozmiaru:

- powyżej 1100 px nawigacja między modułami przechodzi do kompaktowego,
  pływającego panelu u góry po lewej z wyraźnym oznaczeniem aktywnej pozycji; krótka
  pozycja **Plan lotu** otwiera Odlot, Trasę i Przylot jako zwykły, wyłączny
  moduł bez zwijania, jest domyślnie wybrana, a każdy wybór przewija bezpośrednio do treści. Główna
  część wykorzystuje całą pozostałą szerokość, a otwarty oficjalny PDF zajmuje
  całą siatkę. Węższe okna zachowują wybór poziomy, a ekrany mobilne dostępny
  panel boczny. Gdy globalny alert lotu dodaje drugi wiersz nagłówka, panel
  pulpitu automatycznie przesuwa się niżej i wraca wyżej po zniknięciu alertu;
- powyżej 1100 px karty Odlot, Trasa i Przylot mogą być wyświetlane obok
  siebie;
- poniżej 1100 px karty te przechodzą do jednej kolumny;
- poniżej 980 px pasek narzędzi i elementy sterujące mapy zajmują całą dostępną
  szerokość;
- poniżej 760 px karty stają się przewijalne, przyciski są rozmieszczane na
  nowo, a tabele pozostają czytelne w poziomie;
- poniżej 520 px statystyki i złożone panele przechodzą do jednej kolumny.

Mapa reaguje na każdą zmianę rozmiaru okna i natychmiast przelicza swoje
płótno. Minimalny rozmiar okna natywnego wynosi 720 × 560 pikseli.

## Zamykanie aplikacji

Należy użyć przycisku **Zakończ** na górnym pasku. NaviXav poprawnie zatrzymuje
serwer, zamyka okno i połączenie SimConnect, a następnie zwalnia port `8765`.
Bezpośrednie zamknięcie okna daje ten sam efekt.

W trybie diagnostycznym `--no-open` kombinacja `Ctrl+C` w konsoli również
powoduje normalne zamknięcie.

## Opcje uruchamiania

Program uruchamiający dla systemu Windows przyjmuje następujące opcje:

```powershell
.\NaviXav.bat --port 9000
.\NaviXav.bat --no-open
```

- `--port` zmienia port lokalny;
- `--no-open` uruchamia wyłącznie usługę lokalną, na potrzeby diagnostyki.

Adres nasłuchu pozostaje celowo ustalony na `127.0.0.1`.

## Polecenia uzupełniające

NaviXav można również obsługiwać z programu PowerShell:

```powershell
# Wyświetlić najnowszy plan SimBrief
.\.venv\Scripts\navixav.exe plan

# Wygenerować tekstową kartę MCDU
.\.venv\Scripts\navixav.exe plan --mcdu

# Utworzyć dane wyjściowe JSON
.\.venv\Scripts\navixav.exe plan --json

# Zaimportować lotniska z MSFS
.\.venv\Scripts\navixav.exe import LFBO LFPO

# Przejrzeć bazę lokalną
.\.venv\Scripts\navixav.exe navdata

# Wyświetlić informacje o lotnisku
.\.venv\Scripts\navixav.exe airport LFBO --runway 32R
```

## Dane lokalne

NaviXav korzysta z następujących lokalizacji:

| Lokalizacja | Zawartość |
|---|---|
| `%LOCALAPPDATA%\NaviXav\user_settings.json` | konfiguracja wersji zainstalowanej |
| `%LOCALAPPDATA%\NaviXav\navixav.sqlite` | baza nawigacyjna zbudowana z MSFS |
| `%LOCALAPPDATA%\NaviXav\cache\` | krajowe mapy AIS i FAA w pamięci podręcznej |
| `%LOCALAPPDATA%\NaviXav\webview\` | lokalne dane okna WebView2 |
| `%LOCALAPPDATA%\NaviXav\logs\navixav.log` | dziennik wersji zainstalowanej |
| `data\` i `.venv\` | dane i środowisko trybu deweloperskiego |

Te dane lokalne, sekrety i pamięci podręczne nie są przeznaczone do
wersjonowania.

Dziennik zapisuje uruchomienia i zamknięcia, błędy, powolne wywołania API,
czasy pobierania z SimBrief, czasy uzupełniania z MSFS oraz zapełnianie pamięci
podręcznej. Nie zapisuje ani Pilot ID, ani nazwy użytkownika, ani pełnej trasy.
Jego rozmiar jest ograniczony do 2 MB, przy zachowaniu pięciu starszych wersji
(`navixav.log.1` do `navixav.log.5`).

Przy pierwszym dostępie do lotniska lub procedury interfejs ostrzega, że pamięć
podręczna MSFS jest zapełniana i że operacja może potrwać kilkadziesiąt sekund.
Kolejne odwołania korzystają z danych lokalnych.

## Wersjonowanie w Git

Repozytorium źródłowe jest przewidziane pod adresem:
`https://github.com/xalacaga/NaviXav.git`.

Plik `.gitignore` wyklucza w szczególności:

- `.env`, ustawienia użytkownika i bazy lokalne;
- `.claude/`, `CLAUDE.md`, `.codex/`, `AGENTS.md` i `CODEX.md`;
- dane Graphify oraz `graphify-out/`;
- środowiska Pythona, pamięci podręczne testów i wyniki budowania;
- `dist\`, `build\` i `release\`.

Pamięci Claude/Codex mogą więc być utrzymywane lokalnie bez publikowania ich w
repozytorium Git.

### Aktualizacje automatyczne

Przy uruchomieniu NaviXav odpytuje wyłącznie najnowsze publiczne wydanie
repozytorium `xalacaga/NaviXav`. Jeśli jego wersja jest wyższa od
zainstalowanej, na górnym pasku pojawia się przycisk **Aktualizacja**.
Instalacja rozpoczyna się dopiero po potwierdzeniu przez użytkownika.

Instalator jest pobierany do `%LOCALAPPDATA%\NaviXav\updates\`, a następnie jego
suma SHA-256 jest porównywana z sumą opublikowaną przez GitHub. W przypadku
braku lub niezgodności sumy plik jest usuwany i nigdy nie zostaje uruchomiony.
Awaria GitHuba lub internetu nie blokuje ani uruchomienia, ani funkcji lotu.
Przed instalacją niezależny pomocnik Windows czeka na całkowite zamknięcie
procesu NaviXav. Następnie aktualizuje rzeczywiście używany folder, ponownie
uruchamia aplikację i zapisuje plik `.install.log` obok pobranego instalatora.

Przy tym pierwszym ponownym uruchomieniu **Historia wersji** otwiera się
automatycznie jeden raz, aby pokazać zmiany; później pozostaje dostępna z
interfejsu.

Repozytorium jest publiczne do odczytu. Użytkownik może przeglądać kod i
pobierać wydania bez konta GitHub, ale tylko upoważnieni współpracownicy mogą
zapisywać w repozytorium.

### Wersja i informacje o wydaniu

Wersja stosuje format semantyczny `GŁÓWNA.POBOCZNA.POPRAWKA`. Konwencjonalne
komunikaty commitów automatycznie określają kolejny poziom:

- `feat:` daje zwykle wersję poboczną;
- `fix:` daje wersję poprawkową;
- `BREAKING CHANGE` lub `!:` daje wersję główną;
- pozostałe zmiany dają wersję poprawkową.

Przygotowanie wersji i jej informacji lokalnie:

```powershell
.\scripts\prepare_release.ps1 -Bump auto
```

Publikacja instalatora, archiwum przenośnego, ich sum kontrolnych i informacji
w wydaniu GitHub:

```powershell
.\scripts\publish_release.ps1 -Bump auto
```

Drugi skrypt wymaga czystego repozytorium i uwierzytelnionego GitHub CLI.
Wykonuje testy, buduje elementy dystrybucji, tworzy commit i tag wersji,
wypycha `main` oraz tag, a następnie tworzy wydanie GitHub. Plik `CHANGELOG.md`
przechowuje historię, a `RELEASE_NOTES.md` zawiera informacje o bieżącej wersji.

## Rozwiązywanie problemów

### Port 8765 jest już zajęty

Prawdopodobnie nadal działa inna instancja NaviXav. Należy zamknąć jej okno lub
kliknąć **Zakończ** w interfejsie. Plik wykonywalny wykrywa istniejącą
instancję; jeśli port 8765 zajmuje inna aplikacja, automatycznie wybiera wolny
port z zakresu od 8766 do 8775.

Aby zidentyfikować proces:

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

Aplikację można też uruchomić na innym porcie:

```powershell
.\NaviXav.bat --port 9000
```

### Okno NaviXav nie otwiera się

- uruchomić ponownie pełny instalator, aby sprawdził WebView2;
- upewnić się, że Windows i Microsoft Edge WebView2 Runtime są aktualne;
- sprawdzić plik `%LOCALAPPDATA%\NaviXav\logs\navixav.log`;
- sprawdzić, czy program antywirusowy nie blokuje `NaviXav.exe` ani procesów
  `msedgewebview2.exe`.

Archiwum przenośne nie może samodzielnie zainstalować WebView2. Na komputerze
bez tego składnika należy użyć pliku `NaviXav-Setup-<wersja>.exe`.

### Kontrolka MSFS pozostaje czerwona

- sprawdzić, czy symulator jest uruchomiony;
- wczytać lot w całości;
- odczekać kilka sekund, a następnie kliknąć kontrolkę;
- uruchomić ponownie instalator, jeśli prywatna kopia pliku `SimConnect.dll`
  dostarczana z NaviXav została usunięta lub poddana kwarantannie przez program
  antywirusowy.

### Żaden plan SimBrief nie jest wczytywany

- sprawdzić Pilot ID lub nazwę użytkownika w **Ustawieniach**;
- wygenerować OFP w SimBrief przed ponowną próbą pobrania;
- sprawdzić połączenie internetowe.

### Mapa oficjalna jest niedostępna

- sprawdzić, czy przedrostek ICAO jest objęty przez SIA, ENAIRE, LVNL, LFV,
  skeyes, Austro Control, NATS lub FAA;
- sprawdzić połączenie internetowe;
- potwierdzić, że droga startowa i podejście zostały ustalone;
- skorzystać z ręcznego wprowadzenia minimów, jeśli odczyt jest niedostępny.

## Bieżące ograniczenia

- procedura faktycznie zezwolona może różnić się od planu w zależności od ATIS,
  pogody i instrukcji ATC;
- minima zależą od kategorii samolotu, jego wyposażenia i warunków
  operacyjnych;
- automatyczny odczyt minimów ogranicza się do rozpoznanych formatów SIA;
- plik PDF bez zatwierdzonego georeferencjonowania pozostaje czytelny, ale nie
  może być użyty jako warstwa;
- nowe dane MSFS wymagają dostępności symulatora.

Zawsze należy potwierdzić istotne informacje przed wprowadzeniem ich do
symulatora.

## Architektura i poufność

- `navixav/desktop.py` obsługuje okno natywne i cykl życia procesu;
- `navixav/web/app.py` udostępnia interfejs API FastAPI powiązany wyłącznie z
  adresem `127.0.0.1`;
- `navixav/web/static/` zawiera responsywny interfejs HTML/CSS/JavaScript;
- `navixav/planner/` uzupełnia plan IFR;
- `navixav/navdata/` buduje i odpytuje bazę pochodzącą z MSFS;
- `navixav/live/` zapewnia śledzenie przez SimConnect;
- `navixav/sia.py`, `navixav/faa.py` i `navixav/national_aip.py` obsługują
  publikacje oficjalne.

Usługa lokalna nigdy nie nasłuchuje w sieci zewnętrznej. Pilot ID SimBrief,
preferencje, ślad lotu i pliki PDF w pamięci podręcznej pozostają na
komputerze. Komputer opuszczają wyłącznie zapytania niezbędne dla SimBrief,
OpenStreetMap, pogody i oficjalnych publikacji AIS.

## Licencja

Aktualny kod źródłowy NaviXav jest udostępniany na licencji
[PolyForm Noncommercial 1.0.0](LICENSE). Jest to licencja typu
**source available**, a nie licencja open source.

Copyright 2026 Xavier BEGUE (xalacaga)

Licencja zezwala na używanie, modyfikowanie i rozpowszechnianie w określonych
w niej celach niekomercyjnych. Każde użycie komercyjne wymaga oddzielnej
pisemnej licencji właściciela praw. Dotyczy to włączenia całości lub części
aktualnego kodu do płatnej albo generującej przychód aplikacji, sprzedaży
zmodyfikowanej wersji lub jej komercyjnego rozpowszechniania.

Zakres i dane kontaktowe opisano w dokumencie
[Licencjonowanie komercyjne](COMMERCIAL_LICENSE.md). Wkład w kod wymaga
wcześniejszego porozumienia, ponieważ NaviXav łączy licencjonowanie
niekomercyjne i komercyjne; zobacz [Współtworzenie](CONTRIBUTING.md).

Wydania Git oznaczone tagiem v1.4.12 i wcześniejsze opublikowano oddzielnie na
licencji Apache 2.0; wcześniej udzielone prawa pozostają ważne. Komponenty innych
autorów, dane nawigacyjne, oficjalne mapy i podkłady mapowe zachowują własne
warunki opisane w [NOTICE](NOTICE) i
[THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES).

## Testy

Powtarzalny profil używany do zbudowania dystrybucji:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```

Testy oznaczone `live_msfs` odpytują faktycznie uruchomiony symulator i nie są
zatem częścią automatycznej kontroli instalatora.

## Podziękowania

NaviXav rozwija się dzięki temu, co zgłaszają osoby z niego korzystające.
Podziękowania dla [Cojarop](https://flightsim.to/profile/Cojarop) za
zaproponowanie ograniczeń wysokości i prędkości na mapie oraz kołowania
podanego przez kontrolera.
