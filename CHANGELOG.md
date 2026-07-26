# Journal des modifications

## [0.2.1] - 2026-07-26

## Corrections de bugs

- Activation du contrôle du profil vertical uniquement pendant la descente ou
  l’approche.
- Affichage « En attente du TOD » avant le début de la descente.
- Tolérance du profil stabilisée à 500 ft pour éviter les alertes oscillantes.

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.2.0] - 2026-07-26

### Nouvelles fonctionnalités

- Mise à jour automatique depuis les Releases GitHub avec confirmation et
  validation SHA-256.
- Versionnement sémantique et génération automatisée des notes de Release.
- Fenêtre Windows responsive et interface en huit langues.
- Dernier OFP SimBrief, route cartographique, cartes officielles, fiche MCDU,
  QNH, minima et données d’approche.
- Suivi MSFS avec progression, vitesse sol GS, vitesse indiquée IAS et
  enregistrement local.
- Journaux rotatifs respectant la confidentialité.

### Corrections

- Libération réelle du processus et du port `8765` à la fermeture.
- Correction de l’erreur JavaScript `stage is not defined`.
- Information pendant le remplissage initial du cache MSFS.
- Filtrage des détails au sol trop denses.
- Contrôle de WebView2 et connecteur SimConnect autonome non intrusif.

### Maintenance

- Installateur, archive portable et empreintes SHA-256.
- Documentation détaillée en français, anglais, allemand, espagnol, italien,
  portugais, néerlandais et polonais.
- Exclusion Git des données locales Claude, Codex, Graphify, caches et
  livrables.
