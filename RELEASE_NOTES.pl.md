# NaviXav 1.4.15

Opublikowano 2026-08-08.

## Poprawki

- Zapytania dotyczące licencji komercyjnych i współtworzenia korzystają teraz z dedykowanego adresu kontaktowego NaviXav.
- Automatyczna aktualizacja naprawdę się teraz instaluje: pomocnik czekający na zamknięcie NaviXav był uruchamiany bez żadnej konsoli i natychmiast kończył pracę, więc aktualizacja była zgłaszana jako zaplanowana, a aplikacja otwierała się ponownie na poprzedniej wersji. Pomocnik prowadzi też własny dziennik obok instalatora, aby przyszłą awarię dało się zbadać.
- Pobrane instalatory nie gromadzą się już: każda aktualizacja usuwa poprzednie, a instalator robi to samo po zakończeniu. Na komputerze używanym od pierwszych wersji zebrało się pół gigabajta. Dzienniki są zachowywane, aby awarię nadal dało się zbadać.

## Zmiany

- Nettoyage des installateurs telecharges.
- Correctif mise a jour automatique.
- Update NaviXav contact email.

Instalator jest weryfikowany za pomocą sumy kontrolnej SHA-256 przed każdą automatyczną aktualizacją.
