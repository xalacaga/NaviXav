# NaviXav 1.8.0

Opublikowano 2026-11-08.

## Nowości

- Komunikaty głosowe: NaviXav ogłasza alarmy MASTER CAUTION i MASTER WARNING, początek zniżania na 50, 10 i 0 NM oraz instrukcje kołowania, takie jak punkty oczekiwania przed drogą startową; włącz je w Ustawieniach lub w Śledzeniu lotu.
- Monitorowanie paliwa: Śledzenie lotu porównuje paliwo na pokładzie z OFP SimBrief w Twojej pozycji na trasie, szacuje paliwo w miejscu docelowym (EFOB) i ostrzega, gdy spadnie ono poniżej rezerwy końcowej powiększonej o paliwo na lotnisko zapasowe.
- Dziennik diagnostyczny: każda utrata i każde przywrócenie połączenia z MSFS są teraz zapisywane wraz z przyczyną, czasem nieudanego odczytu i długością przerwy, aby łatwiej analizować problemy z połączeniem.
- Mapa i plan kołowania: Twój samolot jest teraz przedstawiany w obu widokach tą samą sylwetką samolotu pasażerskiego zwróconą zgodnie z kursem, z silnikami, szybą kokpitu i delikatnym cieniem, zamiast strzałki.
- Głos NaviXav: komunikaty wypowiadają wysokiej jakości głosy neuronowe dostarczane z aplikacją, we wszystkich ośmiu językach, całkowicie offline i bez instalacji; terminy lotnicze pozostają po angielsku, a w języku angielskim dostępne są trzy głosy.
- SIGMET na mapie: obowiązujące SIGMET w pobliżu trasy są rysowane jako kolorowe strefy z poziomami, te przecinane przez trasę są wyróżnione, karta pogody wymienia je z pełną treścią, a alarm ostrzega, gdy samolot ma wlecieć w jeden z nich na swoim poziomie.
- Podejście ustabilizowane: poniżej bramki (1000 ft IMC, 500 ft VMC) NaviXav sprawdza podwozie, klapy, prędkość, prędkość opadania i wskazania ILS, ogłasza „Ustabilizowane”, gdy wszystko jest w porządku, a w przeciwnym razie włącza alarm niestabilizowanego podejścia; kafelek śledzenia lotu pokazuje niespełnione kryteria.
- Panel MSFS 1.2.3: panel w symulatorze pokazuje aktywne alarmy, oznaczone kolorem według wagi, oraz stan stabilizacji na prostej do lądowania; zaktualizuj go w ustawieniach NaviXav.

## Poprawki

- Samolot, który nie publikuje ilości paliwa, nie pokazuje już 0 kg i nie wywołuje fałszywego MASTER WARNING o paliwie poniżej rezerwy.
- Zapisywanie ustawień znów jest natychmiastowe: miniatury na liście zainstalowanych samolotów nie wczytują już każda z osobna tysięcy plików z Community i nie blokują reszty aplikacji.
- Ostrzeżenia pogodowe „w warunkach LIFR” i „pogoda niedostępna” nie są już wyświetlane po francusku po wybraniu innego języka interfejsu.

## Zmiany

- Mettre en cache la lecture des aircraft.cfg de Community.

Instalator jest weryfikowany za pomocą sumy kontrolnej SHA-256 przed każdą automatyczną aktualizacją.
