# Nouveautés de la prochaine version

À compléter à **chaque modification du code**, pas seulement avant de publier :
une puce par changement, en français et du point de vue de l'utilisateur. Ce
fichier remplace les sujets de commit dans les notes de version, puis il est
réinitialisé par `scripts\prepare_release.ps1`.

<!-- Exemple, à supprimer :
- Le suivi du vol affiche le temps restant avant l'arrivée.
-->

- Le plan de terrain retient désormais le nom des voies de circulation, la
  nature de chaque segment et les points d'attente avant piste : c'est la base
  du guidage du parking à la piste.
- Les terrains déjà enregistrés sont repris automatiquement à la prochaine
  ouverture du simulateur, et restent consultables entre-temps.
- NaviXav calcule l'itinéraire de roulage entre un poste de stationnement et la
  piste : il suit les voies de circulation, contourne les segments fermés et les
  routes de service, n'emprunte une piste qu'en dernier recours et signale
  devant quelle piste s'arrêter.
- La carte dessine enfin les voies de circulation et les postes de
  stationnement, avec le nom des voies.
- Cliquer un poste sur la carte trace l'itinéraire de roulage vers la piste
  retenue par le plan : vert derrière l'avion, bleu devant, avec les barres
  d'arrêt et la distance restante. Rien à saisir.
- Au départ, le point d'attente est celui du seuil réellement utilisé ; à
  l'arrivée, la sortie de piste la plus proche du poste est choisie
  automatiquement.
- Pendant le roulage, NaviXav annonce la manœuvre suivante — « Tournez à gauche
  sur Q », « Arrêt avant la piste 05 » — et affiche la distance restante.
- S'écarter de l'itinéraire ne bloque plus rien : un nouveau tracé est calculé
  depuis la position de l'avion, sans le renvoyer à son point de départ.

## Corrections

<!-- Exemple, à supprimer :
- Le fond de carte ne laisse plus apparaître la grille des tuiles.
-->
