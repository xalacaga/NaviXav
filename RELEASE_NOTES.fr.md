# NaviXav 1.5.0

Publié le 2026-08-28.

## Nouveautés

- Un clic sur une photo d’appareil l’ouvre maintenant en grand dans NaviXav ; l’aperçu se ferme avec son bouton, un clic extérieur ou la touche Échap.
- La fiche et l’inventaire Aircraft affichent maintenant une vraie photo libre à côté du nom pour chaque famille d’appareil prise en charge ; les avions supplémentaires installés dans Community utilisent automatiquement leur vignette locale lorsqu’elle existe.
- Lorsqu’une carte ChartFox ne peut pas être intégrée, NaviXav propose maintenant le catalogue national officiel dans la même fiche quand l’aérodrome est couvert.
- Le suivi du vol estime désormais le Top of Climb à partir du niveau de croisière, du vario et de la vitesse sol ; les points calculés TOC et TOD apparaissent sur la carte comme des repères distincts.
- ChartFox peut désormais être relié depuis les paramètres avec un compte VATSIM ; ses cartes à la demande sont proposées comme source facultative pour les aérodromes de départ et d’arrivée.
- Le menu Charts indique maintenant qu’un compte ChartFox/VATSIM est requis pour accéder aux cartes AIRAC ChartFox et propose un lien direct vers les paramètres.

## Corrections

- Les photos d’appareils ne restent plus masquées derrière le cartouche du type ICAO dans la fiche et l’inventaire Aircraft.
- L’ouverture du PDF d’un aérodrome dans Charts ne repousse plus l’autre aérodrome sous le document : Départ et Arrivée restent côte à côte sur écran large, et la fiche non ouverte reste prioritaire en fenêtre compacte.
- La mention « simulation uniquement » de ChartFox dans les paramètres suit maintenant la langue de l’interface.
- Les cartes ChartFox dont la source interdit l’intégration n’affichent plus une zone blanche : NaviXav explique la restriction et propose de les ouvrir directement sur ChartFox.
- Les repères calculés TOC et TOD utilisent maintenant leurs propres couleurs magenta et rouge, distinctes de tous les waypoints de la route.
- Les fonds de carte CartoDB Positron et Dark Matter sont retirés : leur service gratuit tatoue désormais chaque tuile de la mention « API key required ». Le choix se fait entre OpenStreetMap Standard et OpenTopoMap, et un réglage devenu invalide revient automatiquement sur OpenStreetMap.
- Le briefing météo ne s’affiche plus partiellement en français dans une interface d’une autre langue : les points d’attention et les phénomènes METAR suivent désormais la langue choisie.
- Les orages sans précipitation observée sont désormais signalés : les groupes TS, VCTS et VCSH étaient ignorés par le décodage du METAR. Au passage, le « PO » de « TEMPO » n’est plus lu comme des tourbillons de poussière.
- Les SID s’affichent enfin sur la carte : leur tracé, leurs repères et leurs contraintes publiées manquaient dès qu’une même procédure desservait deux seuils, ce qui est le cas de presque tous les grands terrains. Le départ se réduisait alors à une ligne droite jusqu’au premier point de la route. Les STAR retrouvent au passage leur partie finale, propre à la piste d’atterrissage. La base de navigation est reprise automatiquement au simulateur à la prochaine ouverture.

## Modifications

- Reformuler l'annonce ChartFox de la 1.5.0.
- Ajout fonctionnalite et correction bugs.

L'installateur est vérifié par sa somme de contrôle SHA-256 avant toute mise à jour automatique.
