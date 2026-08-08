# NaviXav 1.4.16

Publié le 2026-08-08.

## Corrections

- Les aérofreins des Fenix A319/A320/A321 affichent désormais correctement ARMÉS même lorsque le nom d’avion SimBrief est générique.
- Le Top of Descent est désormais un point fixe de la route, calculé depuis le niveau de croisière : il décroît jusqu’à zéro puis s’affiche comme dépassé. Il pouvait auparavant se figer pendant une descente à 3°, voire grandir lorsque la descente était entamée trop tôt.
- L’écart au profil de descente reste annoncé pendant un palier sous le niveau de croisière. Il disparaissait jusqu’ici dès que la vitesse verticale revenait à zéro, c’est-à-dire au moment précis où l’avion était très bas sur le profil.
- Le Top of Descent tient désormais compte des plafonds d’altitude publiés de la STAR et de l’approche, et lit l’altitude dans l’atmosphère standard comme un niveau de vol.
- La vitesse verticale requise pour la prochaine contrainte se compare désormais à l’altitude indiquée, la seule comparable à une contrainte publiée.

## Modifications

- Correction bug TOD.

L'installateur est vérifié par sa somme de contrôle SHA-256 avant toute mise à jour automatique.
