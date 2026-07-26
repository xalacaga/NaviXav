# NaviXav

**Dokumentacja:** [Français](README.md) · [English](README.en.md) ·
[Deutsch](README.de.md) · [Español](README.es.md) ·
[Italiano](README.it.md) · [Português](README.pt.md) ·
[Nederlands](README.nl.md) · Polski

NaviXav jest lokalnym asystentem lotu IFR dla Microsoft Flight Simulator.
Automatycznie pobiera najnowszy OFP z SimBrief, uzupełnia informacje terminalowe
danymi z symulatora i przedstawia wartości potrzebne do przygotowania lotu oraz
wprowadzenia do MCDU.

Aplikacja działa we własnym, responsywnym oknie Windows opartym na Microsoft
WebView2. Nie otwiera zewnętrznej przeglądarki. Prywatna usługa nasłuchuje
wyłącznie na `127.0.0.1`; ustawienia, dane nawigacyjne, mapy i pamięć podręczna
pozostają na komputerze.

> NaviXav jest przeznaczony wyłącznie do symulacji lotu. Dane należy zawsze
> sprawdzać w aktualnych publikacjach urzędowych i instrukcjach ATC.

## Funkcje

- automatyczne pobieranie najnowszego planu lotu SimBrief;
- Pilot ID lub nazwa użytkownika SimBrief ustawiane w interfejsie;
- pełna trasa z pozycją i postępem samolotu;
- uzasadniony wybór pasa, SID, STAR, przejść i podejścia;
- ograniczenia wysokości/prędkości, wysokość i poziom przejściowy, dane ILS,
  wysokość przechwycenia i nieudanego podejścia;
- informacje o samolocie, dispatchu, masie, paliwie i ustawieniach MCDU;
- QNH wyświetlane pod informacją o wietrze;
- śledzenie MSFS w czasie rzeczywistym i lokalny zapis lotu do odtworzenia;
- trasa na podkładzie OpenStreetMap;
- bezpośredni dostęp do oficjalnych PDF dla odlotu i przylotu;
- nakładka mapy tylko po zatwierdzeniu georeferencji;
- nawigacja bezpośrednio z MSFS, bez Little Navmap, Navigraph i EUROCONTROL.

## Wymagania i instalacja

- 64-bitowy Windows 10 lub Windows 11;
- Microsoft Flight Simulator dla danych na żywo i nawigacji;
- konto SimBrief z już wygenerowanym OFP;
- Internet dla SimBrief, mapy i publikacji AIS/FAA.

Uruchom `NaviXav-Setup-0.1.0.exe`, sprawdź wymagania i wybierz **Zainstaluj**.
Python i biblioteki są dołączone. WebView2 jest instalowany tylko wtedy, gdy go
brakuje. Można też rozpakować archiwum przenośne i uruchomić `NaviXav.exe`.

### Autonomiczny SimConnect

NaviXav nigdy nie instaluje, rejestruje, ponownie instaluje ani zastępuje
systemowego SimConnect. Nowoczesna prywatna `SimConnect.dll` znajduje się tylko
w katalogu NaviXav. Istniejąca instalacja pozostaje bez zmian. MSFS musi być
uruchomiony, ponieważ prywatny łącznik komunikuje się z usługą SimConnect
symulatora.

## Pierwsza konfiguracja

W **Ustawieniach** wybierz język, wprowadź Pilot ID lub użytkownika SimBrief i
ustaw źródło METAR oraz preferencje podejścia, pasa i samolotu. Język jest
stosowany natychmiast i zapisywany lokalnie. Dostępne są: francuski, angielski,
niemiecki, hiszpański, włoski, portugalski, niderlandzki i polski.

Przy uruchomieniu NaviXav zawsze wyszukuje najnowszy dostępny OFP. Plan lotu
nadal generuje się w serwisie SimBrief.

## Oficjalne mapy

Zakładka **Oficjalne mapy** proponuje dokumenty odlotu i przylotu z obsługiwanych
źródeł, takich jak SIA, ENAIRE, LVNL i FAA d-TPP. Pliki PDF można oglądać w
NaviXav. Przycisk nakładki jest ukryty, jeśli wyrównanie geograficzne nie
zostało zatwierdzone.

## Kod źródłowy i dystrybucja

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Budowanie dystrybucji:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

Instalator, archiwum przenośne i sumy SHA-256 powstają w `release\`. MSFS
SimConnect SDK jest wymagany tylko na komputerze kompilującym.

## Rozwiązywanie problemów i prywatność

- Brak planu: sprawdź identyfikator SimBrief, OFP i Internet.
- Czerwony status MSFS: uruchom MSFS, całkowicie załaduj lot i poczekaj.
- Brak okna: użyj pełnego instalatora, aby naprawić WebView2.
- Port 8765 zajęty: zamknij poprzednią instancję NaviXav.

NaviXav nie wysyła telemetrii. Ustawienia, pamięć podręczna i historia lotu
pozostają lokalne; łączy się tylko z SimBrief, OpenStreetMap i żądanymi
oficjalnymi źródłami.

Rotacyjny dziennik diagnostyczny znajduje się w
`%LOCALAPPDATA%\NaviXav\logs\navixav.log`. Zawiera błędy i czasy operacji, ale
nie zapisuje identyfikatora SimBrief ani pełnej trasy.

## Szczegółowe działanie

### Plan lotu i procedury

Przy uruchomieniu NaviXav pobiera ostatni wygenerowany OFP SimBrief: odlot,
cel, lotnisko zapasowe, trasę, poziom przelotowy, samolot, paliwo, masy i
METAR. Sam plan nadal tworzy się w SimBrief. Dane odczytane bezpośrednio z
MSFS uzupełniają pas, SID, przejście, STAR i podejście; inną zgodę ATIS lub ATC
można wymusić w interfejsie. Blok Odlot–Trasa–Przylot można zwinąć, a aktywny
punkt trasy zmienia kolor.

### Prowadzenie, podejście i MCDU

Prowadzenie pokazuje odległość, namiar, wymaganą wysokość, następne
ograniczenie, prędkość względem ziemi (GS) i prędkość wskazywaną (IAS). Gdy są
dostępne, pokazuje częstotliwość i kurs ILS, kąt ścieżki, wysokość przechwycenia,
wysokość progu, minima i wysokość nieudanego podejścia. Oficjalna karta i ATC
zawsze mają pierwszeństwo.

Karta MCDU grupuje dane dla INIT, F-PLN, RAD NAV, PERF TAKEOFF i PERF APPR:
lotniska, numer lotu, cost index, przelot, pasy, procedury, przejścia, ILS, QNH,
wiatr, temperaturę, minima i znane dane startowe.

### Mapa, zapis i dokumenty oficjalne

Trasa SimBrief jest rysowana na OpenStreetMap, osobno dla SID, trasy, STAR i
podejścia. Szczegóły naziemne są filtrowane zależnie od powiększenia. Lokalny
ślad lotu można odtworzyć i nigdy nie jest wysyłany.

Odlot i przylot są domyślnie wybrane dla oficjalnych PDF. Obsługiwane są SIA
Francja, ENAIRE Hiszpania, LVNL Holandia i FAA d-TPP USA. Przycisk nakładki
pojawia się tylko po zatwierdzonej georeferencji; zwykły PDF można czytać, ale
nie jest przybliżenie nakładany na mapę.

### Dane lokalne i pamięć podręczna

Ustawienia są w `%LOCALAPPDATA%\NaviXav\user_settings.json`, dane nawigacyjne w
`%LOCALAPPDATA%\NaviXav\navixav.sqlite`, a logi pod
`%LOCALAPPDATA%\NaviXav\logs`. Pierwsze wczytanie lotniska lub procedury może
trwać kilkadziesiąt sekund podczas zapełniania pamięci podręcznej MSFS.

## Automatyczne aktualizacje i Releases

Przy starcie NaviXav sprawdza najnowszą publiczną Release
`xalacaga/NaviXav`. Gdy wersja jest nowsza, pojawia się **Aktualizacja**. Po
potwierdzeniu instalator trafia do `%LOCALAPPDATA%\NaviXav\updates`, jest
sprawdzany opublikowanym SHA-256 i uruchamiany. Błąd sieci nie blokuje funkcji
lotu.

Repozytorium jest publiczne do odczytu; zapisywać mogą tylko upoważnieni
współpracownicy. Wersje mają format `MAJOR.MINOR.PATCH`: `feat:` zwiększa
minor, `fix:` patch, a `BREAKING CHANGE` lub `!:` major. Notatki są w
`RELEASE_NOTES.md`, historia w `CHANGELOG.md`.

```powershell
.\scripts\prepare_release.ps1 -Bump auto
.\scripts\publish_release.ps1 -Bump auto
```

Publikowanie wymaga czystego repozytorium i zalogowanego GitHub CLI. Skrypt
testuje, buduje, taguje i publikuje instalator, archiwum przenośne, pliki
SHA-256 oraz notatki.

## Polecenia diagnostyczne

```powershell
.\NaviXav.bat
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
.\scripts\build_windows.ps1
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```
