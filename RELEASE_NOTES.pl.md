# NaviXav 1.4.16

Opublikowano 2026-08-08.

## Poprawki

- Hamulce aerodynamiczne Fenix A319/A320/A321 pokazują teraz poprawnie ARMED, nawet gdy nazwa samolotu w SimBrief jest ogólna.
- Top of Descent jest teraz stałym punktem trasy, wyznaczanym na podstawie poziomu przelotowego: wartość maleje do zera, a następnie pokazuje przekroczenie. Wcześniej mogła zatrzymać się podczas zniżania 3° lub nawet rosnąć, gdy zniżanie rozpoczęto zbyt wcześnie.
- Odchylenie od profilu zniżania pozostaje widoczne podczas lotu poziomego poniżej poziomu przelotowego. Wcześniej znikało, gdy tylko prędkość pionowa wracała do zera, czyli dokładnie wtedy, gdy samolot był głęboko pod profilem.
- Top of Descent uwzględnia teraz opublikowane pułapy wysokości procedury STAR i podejścia oraz odczytuje wysokość w atmosferze wzorcowej, tak jak poziom lotu.
- Prędkość pionowa wymagana do spełnienia następnego ograniczenia jest teraz porównywana z wysokością wskazywaną, jedyną porównywalną z ograniczeniem opublikowanym.

## Zmiany

- Correction bug TOD.

Instalator jest weryfikowany za pomocą sumy kontrolnej SHA-256 przed każdą automatyczną aktualizacją.
