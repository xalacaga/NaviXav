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
