# NaviXav 0.2.0

Publication du 2026-07-26.

## Nouvelles fonctionnalités

- Mise à jour automatique depuis les Releases publiques de
  `xalacaga/NaviXav`, avec confirmation avant installation.
- Vérification obligatoire de l’installateur par empreinte SHA-256 avant son
  exécution.
- Versionnement sémantique, génération des notes et publication GitHub
  automatisés par les scripts de Release.
- Fenêtre Windows dédiée et responsive, sans navigateur externe, avec icône
  d’avion NaviXav.
- Interface en français, anglais, allemand, espagnol, italien, portugais,
  néerlandais et polonais.
- Récupération automatique du dernier OFP SimBrief configuré.
- Carte OpenStreetMap avec route complète, progression du vol et mise en
  évidence du point actif.
- Accès intégré aux cartes officielles SIA, ENAIRE, LVNL et FAA d-TPP pour le
  départ et l’arrivée.
- Calque de carte proposé uniquement lorsque sa géoréférence a été validée.
- Fiche de préparation MCDU, données avion, QNH, contraintes, minima et
  informations d’approche.
- Suivi MSFS affichant la vitesse sol GS et la vitesse indiquée IAS.
- Enregistrement local et relecture de la trajectoire.
- Journaux rotatifs pour les erreurs et mesures de performance, sans Pilot ID
  ni route complète.

## Corrections de bugs

- Arrêt propre de la fenêtre, du serveur local et de SimConnect afin de libérer
  réellement le port `8765`.
- Correction du blocage de chargement SimBrief provoqué par la variable
  JavaScript `stage` non définie.
- Avertissement clair pendant le premier remplissage du cache MSFS.
- Réduction des traits de voies de circulation et de parking qui rendaient la
  carte illisible.
- Détection de WebView2 et utilisation d’un connecteur SimConnect privé sans
  réinstaller ou modifier un connecteur déjà présent.

## Maintenance

- Documentation française et sept traductions détaillées.
- Installateur autonome, archive portable et sommes SHA-256 générés par la
  chaîne de construction Windows.
- Dépôt public en lecture ; secrets, caches, données Claude/Codex/Graphify et
  livrables locaux restent exclus de Git.

L’application reste destinée exclusivement à la simulation de vol. Les cartes
officielles à jour et les instructions ATC restent prioritaires.
