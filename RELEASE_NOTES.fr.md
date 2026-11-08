# NaviXav 1.8.0

Publié le 2026-11-08.

## Nouveautés

- Annonces vocales : NaviXav annonce les alarmes MASTER CAUTION et MASTER WARNING, le top de descente à 50, 10 et 0 NM et les consignes de roulage comme les points d’arrêt avant piste ; à activer dans les Paramètres ou depuis Suivi du vol.
- Suivi du carburant : Suivi du vol compare le carburant à bord à l’OFP SimBrief à votre position sur la route, estime le carburant à l’arrivée (EFOB) et lève une alarme lorsqu’il passe sous la réserve finale augmentée du carburant de dégagement.
- Journal de diagnostic : chaque perte et chaque rétablissement de la connexion à MSFS sont désormais consignés avec leur raison, la durée de la lecture en échec et celle de la coupure, pour faciliter l’analyse des problèmes de connexion.
- Carte et plan de roulage : votre avion est désormais représenté par la même silhouette d’avion de ligne dans les deux vues, orientée au cap, avec réacteurs, pare-brise et une ombre légère, à la place de la flèche.
- Voix NaviXav : les annonces sont dites par des voix neuronales de haute qualité livrées avec l’application, dans les huit langues, entièrement hors ligne et sans rien à installer ; les termes aéronautiques restent en anglais et trois voix sont proposées en anglais.
- SIGMET sur la carte : les SIGMET en vigueur près de la route sont dessinés en zones colorées avec leurs niveaux, ceux que la route traverse sont mis en évidence, l’onglet météo les liste avec leur texte complet et une alarme prévient quand l’avion va en traverser un à son niveau.
- Approche stabilisée : sous le portail (1000 ft IMC, 500 ft VMC), NaviXav contrôle le train, les volets, la vitesse, le taux de descente et les aiguilles ILS, annonce « Stabilisé » quand tout est en ordre et déclenche sinon une alarme d’approche non stabilisée ; une tuile du suivi de vol affiche les critères en défaut.
- Panneau MSFS 1.2.3 : le panneau du simulateur affiche les alarmes en cours, colorées selon leur gravité, et l’état de stabilisation en finale ; mettez-le à jour depuis les réglages de NaviXav.

## Corrections

- Un avion qui ne publie pas sa quantité de carburant n’affiche plus 0 kg et ne déclenche plus de faux MASTER WARNING de carburant sous la réserve.
- L’enregistrement des paramètres est de nouveau immédiat : les vignettes de la liste des avions installés ne relisent plus chacune des milliers de fichiers de Community et ne retiennent plus le reste de l’application.
- Les avertissements météo « en conditions LIFR » et « météo indisponible » ne restent plus en français lorsqu’une autre langue d’interface est choisie.

## Modifications

- Mettre en cache la lecture des aircraft.cfg de Community.

L'installateur est vérifié par sa somme de contrôle SHA-256 avant toute mise à jour automatique.
