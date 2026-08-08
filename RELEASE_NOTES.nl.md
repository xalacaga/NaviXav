# NaviXav 1.4.15

Uitgebracht op 2026-08-08.

## Opgelost

- Vragen over commerciële licenties en bijdragen gebruiken nu het speciale NaviXav-contactadres.
- De automatische update installeert zichzelf nu echt: het hulpprogramma dat wacht tot NaviXav sluit werd zonder console gestart en stierf meteen, waardoor de update als gepland werd gemeld en de toepassing weer opende op de vorige versie. Het hulpprogramma houdt bovendien een eigen logboek naast het installatieprogramma, zodat een toekomstige storing te onderzoeken is.
- Gedownloade installatieprogramma's stapelen zich niet meer op: elke update wist de vorige, en het installatieprogramma doet hetzelfde na afloop. Op een machine die sinds de eerste versies wordt gevolgd was een halve gigabyte samengekomen. De logboeken blijven bewaard, zodat een storing nog te onderzoeken is.

## Gewijzigd

- Nettoyage des installateurs telecharges.
- Correctif mise a jour automatique.
- Update NaviXav contact email.

Het installatieprogramma wordt vóór elke automatische update geverifieerd aan de hand van zijn SHA-256-controlesom.
