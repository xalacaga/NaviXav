# NaviXav

**Dokumentacja:** [Français](README.md) · [English](README.en.md) ·
[Deutsch](README.de.md) · [Español](README.es.md) ·
[Italiano](README.it.md) · [Português](README.pt.md) ·
[Nederlands](README.nl.md) · Polski

NaviXav to lokalna aplikacja wspomagająca lot IFR dla Microsoft Flight
Simulator. Pobiera najnowszy plan lotu z SimBrief, uzupełnia informacje
terminalowe danymi z symulatora i przedstawia całość w interfejsie
dostosowanym do przygotowania lotu oraz do wprowadzania danych w MCDU.

Aplikacja posiada własne okno systemu Windows. Interfejs jest renderowany przez
Microsoft WebView2 i komunikuje się wyłącznie z lokalną usługą powiązaną z
adresem `127.0.0.1`. Żadna zewnętrzna przeglądarka nie jest otwierana.
Ustawienia, baza nawigacyjna i pamięci podręczne pozostają na komputerze.

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
- Top of Descent oraz orientacyjną prędkość zniżania na ścieżce 3°;
- odchylenie od zaplanowanego profilu pionowego.

Ślad lotu jest zapisywany lokalnie co pięć sekund. Można go wstrzymać, usunąć
lub odtworzyć z poziomu interfejsu. Żadna historia nie jest wysyłana do usług
zewnętrznych.

### Karta MCDU

Karta **Karta MCDU** zbiera informacje przeznaczone do wprowadzenia w FMS
Airbusa:

- `FROM/TO`, numer lotu i lotnisko zapasowe;
- Cost Index i poziom przelotowy;
- ZFW, paliwo blokowe, kołowania, przelotu i rezerwy;
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
- pobierać lotniska, drogi startowe, procedury, punkty nawigacyjne i pomoce
  radionawigacyjne;
- stopniowo budować lokalną bazę w pliku `data/navixav.sqlite`.

Symulator musi być uruchomiony z wczytanym lotem, aby pobrać nowe dane.
Informacje już zapisane w pamięci podręcznej pozostają dostępne offline.

### Mapa

Mapa obejmuje:

- podkład OpenStreetMap;
- trasę SimBrief narysowaną wraz z jej punktami;
- odrębne kolory dla SID, części trasowej, STAR i podejścia;
- drogi startowe oraz wybraną drogę startową;
- pozycję i kurs samolotu;
- ślad przemieszczenia;
- tryb automatycznego śledzenia;
- powiększanie, przesuwanie i dopasowanie do lotniska lub trasy;
- opcjonalne szczegóły naziemne dla dróg kołowania i stanowisk postojowych.

Szczegóły naziemne są domyślnie ukryte, aby mapa pozostała czytelna. Przycisk
**Szczegóły naziemne** wyświetla je w razie potrzeby.

### Oficjalne krajowe mapy AIS

NaviXav odpytuje bezpośrednio publikacje władz krajowych, z pominięciem
EUROCONTROL/EAD:

- Francja: SIA eAIP (`LF`);
- Hiszpania i Wyspy Kanaryjskie: AIP ENAIRE (`LE`, `GC`, `GE`);
- Holandia: LVNL eAIP (`EH`);
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
wypróbować tryb Demo lub przejrzeć już zapisane dane.

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

1. sprawdza 64-bitowy system Windows, Pythona i SDK SimConnect;
2. instaluje brakujące narzędzia budowania;
3. pobiera oficjalny bootstrapper WebView2 i weryfikuje jego podpis Microsoft;
4. wykonuje testy z pominięciem integracji z działającym MSFS;
5. tworzy instalator, archiwum przenośne oraz ich sumy SHA-256 w folderze
   `release\`.

SDK SimConnect wymienione w punkcie 1 dotyczy wyłącznie komputera, na którym
budowany jest NaviXav. Nie jest instalowane na komputerach użytkowników.

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

Interfejs pozwala również skonfigurować:

- źródło METAR;
- kolejność preferencji podejść;
- maksymalną składową wiatru tylnego;
- maksymalną składową wiatru bocznego;
- minimalną długość drogi startowej;
- zdolność RNP statku powietrznego.

W wersji zainstalowanej wartości są przechowywane w pliku
`%LOCALAPPDATA%\NaviXav\user_settings.json`.

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
- **Szczegóły naziemne**: pokazuje drogi kołowania i stanowiska.
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

NaviXav automatycznie dostosowuje interfejs przy zmianie rozmiaru:

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

## Tryb Demo

Przełącznik **Demo** wczytuje przykładowy lot i symuluje przemieszczanie się po
ziemi. Pozwala poznać interfejs bez konta SimBrief i bez symulatora.

Tryb Demo jest przy uruchomieniu zawsze wyłączony, aby NaviXav dawał
pierwszeństwo najnowszemu planowi SimBrief.

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

- sprawdzić, czy przedrostek ICAO jest objęty przez SIA, ENAIRE, LVNL lub FAA;
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

## Testy

Powtarzalny profil używany do zbudowania dystrybucji:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```

Testy oznaczone `live_msfs` odpytują faktycznie uruchomiony symulator i nie są
zatem częścią automatycznej kontroli instalatora.
