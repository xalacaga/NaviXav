# Nouveautés de la prochaine version

À compléter à **chaque modification du code**, pas seulement avant de publier :
une puce par changement, en français et du point de vue de l'utilisateur. Ce
fichier remplace les sujets de commit dans les notes de version, puis il est
réinitialisé par `scripts\prepare_release.ps1`.

<!-- Exemple, à supprimer :
- Le suivi du vol affiche le temps restant avant l'arrivée.
-->

## Corrections

<!-- Exemple, à supprimer :
- Le fond de carte ne laisse plus apparaître la grille des tuiles.
-->

- Le tracé de l'approche ne part plus vers un repère homonyme situé à des
  centaines de milles du terrain : la finale d'Orly filait en Corse.
- Un repère nommé d'après une piste — « CF02 », « FI21L », « DER07 » — est
  reconnu comme tel sur n'importe quel aérodrome du monde, et ne peut plus
  emprunter la position de son homonyme sur un terrain voisin.
- Un point en route dont la base connaît plusieurs homonymes est désormais
  choisi près de la route, et écarté du tracé s'il l'allonge démesurément.
- À l'import du plan et à chaque nouvelle route, le tracé complet est vérifié :
  tout point hors de sa zone est retiré et signalé dans les avertissements du
  plan, quelle que soit l'origine de la position fautive.
- Une route qui franchit l'antiméridien se dessine d'un seul trait au lieu de
  traverser la carte à l'envers.
- Un vol qui revient à son terrain de départ conserve son point de virage : la
  distance annoncée par le plan prend le relais de la route directe.
- Les repères de procédure enregistrés à tort comme points de report sont
  supprimés de la base de navigation à l'ouverture.
