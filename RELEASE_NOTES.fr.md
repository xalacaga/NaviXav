# NaviXav 1.7.4

Publié le 2026-10-11.

## Nouveautés

- Le trafic VATSIM, IVAO et OpenSky anticipe les virages : un appareil en virage au dernier relevé continue de tourner en s’amortissant, sur la carte comme dans le simulateur, au lieu de filer tout droit jusqu’au relevé suivant.
- Analyse de l’atterrissage : au toucher, NaviXav affiche la vitesse verticale figée par MSFS, l’assiette et l’inclinaison, la distance après le seuil et l’écart à l’axe de la piste réellement utilisée, le vent de face et de travers, les rebonds et la stabilisation de la finale, avec une note sur 100. L’analyse est rattachée au vol dans le carnet de bord et une image prête à partager peut être copiée ou enregistrée.
- Le carnet de vol est désormais conservé dans le dossier de données de NaviXav plutôt que dans la fenêtre : il survit à une réinstallation ou à une réinitialisation de WebView2, et la tablette connectée en réseau local affiche le même carnet, en lecture seule. Les vols déjà enregistrés sont repris automatiquement au premier lancement.
- Statistiques du carnet de vol : nombre de vols, heures de vol et distance totales, toucher et note moyens, meilleur atterrissage, avions les plus pilotés et terrains les plus fréquentés. Le carnet complet s’exporte en CSV pour un tableur.

## Corrections

- Le trafic OpenSky avance désormais en continu sur la carte et dans le simulateur entre deux relevés, au lieu de rester figé puis de sauter de plusieurs nautiques.
- OpenSky est relevé bien plus souvent en début de vol, environ toutes les 30 secondes : le quota public est réparti sur la durée d’un vol plutôt que sur une journée entière.
- Le premier chargement d’un terrain n’attend plus près d’une minute : NaviXav cherche désormais l’ILS et les repères dans la région du terrain au lieu de parcourir celles de tous les terrains déjà connus, et retrouve les fréquences ILS qu’il déclarait à tort introuvables, comme celle de la 23R d’EGCC.

## Modifications

- Correction bug et ajout logbook.

L'installateur est vérifié par sa somme de contrôle SHA-256 avant toute mise à jour automatique.
