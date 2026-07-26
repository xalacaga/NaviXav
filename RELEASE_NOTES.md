# NaviXav 0.3.0

Publication du 2026-07-26.

## Nouvelles fonctionnalités

- Le suivi de progression utilise maintenant toute la géométrie du vol :
  SID, route, STAR et approche.
- Les fixes des procédures sont affichés dans le bandeau et deviennent actifs
  successivement au passage de l’avion.
- La progression est monotone afin d’éviter les sauts vers un segment futur
  lorsque deux portions de route sont géographiquement proches.
- Un bouton permanent **Rechercher MAJ** permet de vérifier manuellement les
  Releases GitHub ; il devient bouton d’installation lorsqu’une version plus
  récente est disponible.
- L’icône avion NaviXav est maintenant imposée à la fenêtre WebView et à son
  identité Windows, en plus de l’exécutable et de l’installateur.

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.
