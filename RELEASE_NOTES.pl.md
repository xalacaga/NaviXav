# NaviXav 1.5.0

Opublikowano 2026-08-28.

## Nowości

- Kliknięcie zdjęcia samolotu otwiera teraz duży podgląd w NaviXav; można go zamknąć przyciskiem, kliknięciem poza nim lub klawiszem Escape.
- Karta i inwentarz Aircraft wyświetlają teraz obok nazwy każdej obsługiwanej rodziny samolotów prawdziwe zdjęcie na wolnej licencji; dodatkowe samoloty zainstalowane w Community automatycznie używają lokalnej miniatury, jeśli jest dostępna.
- Gdy mapy ChartFox nie można osadzić, NaviXav proponuje teraz oficjalny katalog krajowy na tej samej karcie, jeśli lotnisko jest obsługiwane.
- Śledzenie lotu szacuje teraz Top of Climb na podstawie poziomu przelotowego, prędkości pionowej i prędkości względem ziemi; obliczone punkty TOC i TOD są widoczne na mapie jako osobne punkty trasy.
- ChartFox można teraz połączyć w Ustawieniach z kontem VATSIM; jego mapy na żądanie są dostępne jako opcjonalne źródło dla lotniska odlotu i przylotu.
- Menu Charts informuje teraz, że dostęp do map AIRAC ChartFox wymaga konta ChartFox/VATSIM, i zawiera bezpośredni link do Ustawień.

## Poprawki

- Zdjęcia samolotów nie są już zasłaniane przez kafelek typu ICAO na karcie i w inwentarzu Aircraft.
- Otwarcie pliku PDF lotniska w Charts nie przesuwa już drugiego lotniska pod dokument: Odlot i Przylot pozostają obok siebie na szerokich ekranach, a nieotwarta karta jest wyświetlana jako pierwsza w kompaktowym oknie.
- Informacja ChartFox „tylko do symulacji” w Ustawieniach jest teraz wyświetlana w języku interfejsu.
- Mapy ChartFox, których źródło zabrania osadzania, nie pokazują już pustego obszaru: NaviXav wyjaśnia ograniczenie i umożliwia otwarcie ich bezpośrednio w ChartFox.
- Obliczone punkty TOC i TOD mają teraz własne kolory magenta i czerwony, odróżniające je od wszystkich punktów trasy.
- Podkłady mapowe CartoDB Positron i Dark Matter zostały usunięte: ich bezpłatna usługa oznacza teraz każdy kafelek znakiem wodnym „API key required”. Wybór obejmuje OpenStreetMap Standard i OpenTopoMap, a ustawienie, które utraciło ważność, automatycznie wraca do OpenStreetMap.
- Briefing pogodowy nie wyświetla się już częściowo po francusku, gdy interfejs jest ustawiony na inny język: uwagi operacyjne i zjawiska METAR podążają teraz za wybranym językiem.
- Burze bez obserwowanych opadów są teraz sygnalizowane: grupy TS, VCTS i VCSH były pomijane przy dekodowaniu METAR. Ponadto „PO” w „TEMPO” nie jest już odczytywane jako wiry pyłowe.
- SID-y wreszcie pojawiają się na mapie: ich przebieg, punkty i opublikowane ograniczenia znikały, gdy jedna procedura obsługiwała dwa progi, co zdarza się na niemal każdym dużym lotnisku. Odlot sprowadzał się wtedy do linii prostej do pierwszego punktu trasy. STAR-y odzyskują ponadto swoją końcową część, właściwą dla pasa lądowania. Baza nawigacyjna jest automatycznie wczytywana ponownie z symulatora przy następnym uruchomieniu.

## Zmiany

- Reformuler l'annonce ChartFox de la 1.5.0.
- Ajout fonctionnalite et correction bugs.

Instalator jest weryfikowany za pomocą sumy kontrolnej SHA-256 przed każdą automatyczną aktualizacją.
