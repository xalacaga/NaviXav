# Nouveautés de la prochaine version

À compléter à **chaque modification du code**, pas seulement avant de publier :
une puce par changement, en français et du point de vue de l'utilisateur. Ce
fichier remplace les sujets de commit dans les notes de version, puis il est
réinitialisé par `scripts\prepare_release.ps1`.

<!-- Exemple, à supprimer :
- Le suivi du vol affiche le temps restant avant l'arrivée.
-->

- Un onglet « Météo » remplace l'onglet « JSON » et réunit le briefing du
  départ, de la croisière, de l'arrivée et du dégagement.
- Chaque terrain affiche l'essentiel décodé : vent, visibilité, plafond,
  température et point de rosée, QNH, phénomènes significatifs et catégorie de
  vol (VFR, MVFR, IFR, LIFR), avec l'ancienneté de l'observation.
- La tendance TAF est résumée aux créneaux qui changent la donne, et le METAR
  comme le TAF bruts restent accessibles d'un clic.
- La croisière reprend le vent moyen, la composante, l'écart ISA, la
  température extérieure et la tropopause calculés pour l'OFP.
- Le briefing signale les points d'attention : observation périmée, risque de
  brume ou de brouillard, rafales, températures basses et conditions IFR
  basses.
- En mode METAR direct, les observations sont actualisées au chargement puis
  toutes les cinq minutes, sans recalculer la route ni changer les procédures.
- Un résumé graphique représente les conditions, la direction du vent, la
  visibilité et le plafond de chaque terrain.
- L'onglet « Dispatch » compare en direct la prévision de l'OFP et ce que
  mesure le simulateur : carburant embarqué, quantité à bord, consommation
  réelle, masses au décollage et à l'atterrissage, temps et distance. Les
  valeurs se rafraîchissent toutes les deux secondes.
- Le carburant projeté à l'arrivée alerte dès qu'il passe sous la réserve
  finale augmentée du dégagement, et la masse d'atterrissage projetée alerte
  au-dessus de la masse maximale.
- La consommation horaire est mesurée sur une moyenne glissante de cinq
  minutes et reste juste lorsque le vol est accéléré.
- Le suivi survit à une fermeture en cours de vol : le carburant bloc et
  l'heure de décollage relevés au départ sont retrouvés à la réouverture.
- Les onglets « Dispatch » et « Avion » suivent enfin la langue choisie :
  intitulés, groupes et mentions y sont traduits, seuls les identifiants
  aéronautiques (ZFW, MTOW, MLW, SELCAL, cost index) restent tels quels.

## Corrections

<!-- Exemple, à supprimer :
- Le fond de carte ne laisse plus apparaître la grille des tuiles.
-->

- L'avertissement « SimBrief a prévu la piste X, le vent favoriserait Y » ne
  s'affiche plus. Par vent faible, calme ou variable, il attribuait au vent un
  classement décidé en réalité par la configuration préférentielle de la
  plateforme et par l'ILS. La piste de l'OFP reste retenue, avec une confiance
  modérée lorsqu'elle diffère du classement du moteur.
