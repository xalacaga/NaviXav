# NaviXav 1.4.10

Opublikowano 2026-08-06.

## Nowości

- Ustawienia otwierają teraz pełną historię wersji: wszystkie ważne zmiany od początku śledzenia, wersja po wersji, z datą i oznaczeniem tej zainstalowanej. Historia jest dostarczana z aplikacją i czyta się ją bez połączenia. Teksty zmian pozostają po angielsku; ramy i rubryki podążają za wybranym językiem.
- Śledzenie lotu odróżnia teraz symulację wstrzymaną od utraconej: wskaźnik MSFS i plakietka śledzenia pokazują „MSFS wstrzymany” zamiast sugerować zerwane połączenie. Symulator, który nie udostępnia tego stanu, jest nadal śledzony normalnie.
- Po najechaniu na pas, procedurę SID, STAR, ich transitions oraz podejście pojawia się dyskretny ołówek: otwiera listę pozostałych opublikowanych procedur i pozwala zmienić wybór po fakcie, nawet gdy silnik jest pewny. Lista nie jest już ograniczona do trzech pozycji, pokazuje wszystko, co da się wykonać z wybranego pasa, a „Powrót do wyboru automatycznego” oddaje decyzję silnikowi. Przy wyborze narzuconym ołówek pozostaje podświetlony.

## Poprawki

- Brakująca procedura nie zajmuje już miejsca procedury rzeczywistej. Gdy dla pasa nie opublikowano żadnej STAR, powód zastępuje myślnik w jednym zwartym wierszu, a wiersz transition, który tylko powtarzał brak, znika. Takie samo zwężenie dla SID lub podejścia bez transition.
- Procedura SID lub STAR, która nie jest opublikowana dla wybranego pasa, nie jest już łączona: zaczyna się od innego progu albo prowadzi do IAF po przeciwnej stronie lotniska. NaviXav zgłasza teraz odlot z prowadzeniem radarowym lub przylot bezpośredni, a odrzucona procedura pozostaje dostępna na liście wyborów. W Brive-Souillac na pasie 29 plan wskazuje BSC, a następnie ILS RWY 29 zamiast niewykonalnej STAR.
- Bez STAR podejście i jego transition łączą się teraz z ostatnim punktem trasy, zamiast pozostawać bez powiązania. Transition opublikowana dokładnie na tym punkcie jest rozpoznawana i nie jest już przedstawiana jako niepewny wybór.
- Punkty podejścia, które SimBrief pozostawia w dzienniku nawigacyjnym bez oznaczenia, takie jak CF29 czy RW11, nie liczą się już jako punkty trasy: nie są rysowane na trasie ani używane do połączenia przylotu.
- Gdy STAR rzeczywiście obsługuje pas lądowania, ale kończy się na punkcie, który nie otwiera żadnego podejścia, NaviXav mówi o tym wprost, zamiast pozostawiać odkrycie przerwy na czas lotu.
- Historia wersji nie wyświetla się już stale na wierzchu interfejsu: otwiera się wyłącznie po kliknięciu jej ikony w ustawieniach i zamyka się całkowicie.
- Okno ustawień nie ma już poziomego paska przewijania: niewidoczne pole wychodziło poza całą szerokość ramki, niezależnie od rozmiaru okna.

## Zmiany

- Correction bug et améliorations diverses.

Instalator jest weryfikowany za pomocą sumy kontrolnej SHA-256 przed każdą automatyczną aktualizacją.
