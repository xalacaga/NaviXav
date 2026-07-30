# Nouveautés de la prochaine version

Décrivez ici, en français et du point de vue de l'utilisateur, ce que la
prochaine version apporte. Une puce par nouveauté. Ce fichier remplace les
sujets de commit dans la section « Nouvelles fonctionnalités » des notes de
version, puis il est réinitialisé par `scripts\prepare_release.ps1`.

- Le suivi du vol affiche une ligne départ vers arrivée sur laquelle l'avion
  avance en temps réel, avec le pourcentage parcouru et la distance restante.
- L'altitude courante suit l'avion sur cette ligne, en niveau de vol au-dessus
  de l'altitude de transition et en pieds en dessous, avec la tendance
  verticale.
- Le temps de vol prévu par SimBrief, le temps écoulé et le temps restant
  avant l'arrivée sont affichés sous la trajectoire.
- Le mode démonstration rejoue désormais un vol complet du plan, du roulage au
  départ jusqu'à l'arrêt au parking d'arrivée, en passant par la montée, la
  croisière, la descente et l'approche.
- Le bandeau de la carte indique la vitesse indiquée, l'altitude, la vitesse
  verticale, la température extérieure et la phase de vol.
