# NaviXav 1.7.4

Opublikowano 2026-10-11.

## Nowości

- Ruch VATSIM, IVAO i OpenSky przewiduje zakręty: samolot, który skręcał w chwili ostatniego odczytu, nadal skręca ze stopniowym wygaszaniem, na mapie i w symulatorze, zamiast lecieć prosto do następnego odczytu.
- Analiza lądowania: przy przyziemieniu NaviXav pokazuje prędkość pionową zapisaną przez MSFS, pochylenie i przechylenie, odległość za progiem i odchylenie od osi faktycznie użytego pasa, wiatr czołowy i boczny, odbicia oraz stabilność podejścia końcowego, z oceną w skali 100 punktów. Analiza jest dołączana do lotu w dzienniku, a gotowy do udostępnienia obraz można skopiować lub zapisać.
- Dziennik lotów jest teraz przechowywany w folderze danych NaviXav zamiast w oknie: przetrwa ponowną instalację lub zresetowanie WebView2, a tablet połączony przez sieć lokalną pokazuje ten sam dziennik, tylko do odczytu. Zapisane już loty są przenoszone automatycznie przy pierwszym uruchomieniu.
- Statystyki dziennika lotów: liczba lotów, łączne godziny lotu i odległość, średnie przyziemienie i ocena, najlepsze lądowanie, najczęściej latane samoloty i najczęściej odwiedzane lotniska. Cały dziennik można wyeksportować do CSV dla arkusza kalkulacyjnego.

## Poprawki

- Ruch OpenSky porusza się teraz płynnie na mapie i w symulatorze między dwoma odczytami, zamiast zamierać, a potem przeskakiwać o kilka mil morskich.
- OpenSky jest odpytywany znacznie częściej na początku lotu, mniej więcej co 30 sekund: publiczny limit jest rozkładany na czas lotu, a nie na cały dzień.
- Pierwsze wczytanie lotniska nie trwa już prawie minuty: NaviXav szuka teraz ILS i punktów w regionie lotniska, zamiast przeglądać regiony wszystkich znanych już lotnisk, i odzyskuje częstotliwości ILS błędnie zgłaszane jako nieznalezione, np. dla pasa 23R w EGCC.

## Zmiany

- Correction bug et ajout logbook.

Instalator jest weryfikowany za pomocą sumy kontrolnej SHA-256 przed każdą automatyczną aktualizacją.
