# Journal des modifications

## [1.4.4] - 2026-08-01

## Nouvelles fonctionnalités

- Nouvel onglet « Roulage » : un plan d'aérodrome dédié sur fond aéronautique sombre, avec quadrillage métrique et indication du nord, sans fond routier ni route de vol.
- Le plan de roulage occupe toute la zone disponible et reste lisible dans les fenêtres compactes. Les voies secondaires sont masquées par défaut et le bouton « Secondaires » les affiche à la demande.
- Au départ, NaviXav reconnaît automatiquement le poste proche de l'avion et propose son itinéraire vers la piste retenue. Cliquer un autre poste remplace immédiatement cette proposition.
- Seules les voies de l'itinéraire portent leur nom : le chemin se lit d'un coup d'œil.
- La consigne du moment s'affiche en grand sur le plan de roulage, avec le chemin restant et la distance jusqu'au bout.
- L’onglet Roulage, le suivi du vol, le journal local, les phases de vol, les états de la carte et la commande de création SimBrief suivent désormais immédiatement la langue choisie. Les identifiants et la phraséologie aéronautiques normalisés restent inchangés.
- Les fiches Départ, Route et Arrivée traduisent aussi leurs libellés, les composantes de vent, les justifications du moteur et les avertissements, sans modifier les procédures, repères ni valeurs issus de SimBrief.

## Corrections de bugs

- La carte redevient lisible : les voies de circulation, les postes et leurs étiquettes ne s'affichent plus par-dessus les tuiles, la route et l'avion. Le détail du sol est passé dans le nouvel onglet « Roulage ».
- Changer de poste de stationnement annule désormais les anciennes demandes : une réponse réseau ou de guidage retardée ne peut plus restaurer le premier itinéraire.
- Les chemins de parking SimConnect ne sont plus confondus avec des segments de taxiway. Ils ne peuvent donc plus créer de longues diagonales artificielles à travers le terrain, comme entre T41 et N1 à LFBO.
- Le recalcul après un écart reste sur le réseau principal praticable et ne sélectionne plus un point isolé ou une route de service.

## Autres changements

- Ajout roulage et amélioration traductions.

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [1.4.3] - 2026-07-31

## Nouvelles fonctionnalités

- Le plan de terrain retient désormais le nom des voies de circulation, la nature de chaque segment et les points d'attente avant piste : c'est la base du guidage du parking à la piste.
- Les terrains déjà enregistrés sont repris automatiquement à la prochaine ouverture du simulateur, et restent consultables entre-temps.
- NaviXav calcule l'itinéraire de roulage entre un poste de stationnement et la piste : il suit les voies de circulation, contourne les segments fermés et les routes de service, n'emprunte une piste qu'en dernier recours et signale devant quelle piste s'arrêter.
- La carte dessine enfin les voies de circulation et les postes de stationnement, avec le nom des voies.
- Cliquer un poste sur la carte trace l'itinéraire de roulage vers la piste retenue par le plan : vert derrière l'avion, bleu devant, avec les barres d'arrêt et la distance restante. Rien à saisir.
- Au départ, le point d'attente est celui du seuil réellement utilisé ; à l'arrivée, la sortie de piste la plus proche du poste est choisie automatiquement.
- Pendant le roulage, NaviXav annonce la manœuvre suivante — « Tournez à gauche sur Q », « Arrêt avant la piste 05 » — et affiche la distance restante.
- S'écarter de l'itinéraire ne bloque plus rien : un nouveau tracé est calculé depuis la position de l'avion, sans le renvoyer à son point de départ.

## Autres changements

- Ajout taxiway et suivi roulage.

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [1.4.2] - 2026-07-30

## Corrections de bugs

- Le fond de carte ne laisse plus apparaître la grille des tuiles : sa transparence s'applique désormais à l'ensemble du calque et les tuiles ne se chevauchent plus.

## Autres changements

- Optimisation carte.
- Optimisation carte.

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [1.4.1] - 2026-07-30

## Autres changements

- Optimisation carte.

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [1.4.0] - 2026-07-30

## Nouvelles fonctionnalités

- Le suivi du vol affiche une ligne départ vers arrivée sur laquelle l'avion avance en temps réel, avec le pourcentage parcouru et la distance restante.
- L'altitude courante suit l'avion sur cette ligne, en niveau de vol au-dessus de l'altitude de transition et en pieds en dessous, avec la tendance verticale.
- Le temps de vol prévu par SimBrief, le temps écoulé et le temps restant avant l'arrivée sont affichés sous la trajectoire.
- Le mode démonstration rejoue désormais un vol complet du plan, du roulage au départ jusqu'à l'arrêt au parking d'arrivée, en passant par la montée, la croisière, la descente et l'approche.
- Le bandeau de la carte indique la vitesse indiquée, l'altitude, la vitesse verticale, la température extérieure et la phase de vol.

## Corrections de bugs

- Prise en compte de RELEASE_HIGHLIGHTS.md dans le commit de version.

## Autres changements

- Mise à jour fonctionnalités.

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [1.3.0] - 2026-07-30

## Nouvelles fonctionnalités

- mises Ã  jour de l'application

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [1.2.0] - 2026-07-29

## Nouvelles fonctionnalités

- mises Ã  jour de l'application

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [1.1.0] - 2026-07-29

## Nouvelles fonctionnalités

- mises Ã  jour de l'application

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [1.0.0] - 2026-07-29

## Corrections de bugs

- restaurer la trace en mémoire et les crans Airbus

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.13.0] - 2026-07-29

## Nouvelles fonctionnalités

- mises Ã  jour de l'application
- mises Ã  jour de l'application

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.12.0] - 2026-07-29

## Nouvelles fonctionnalités

- mises Ã  jour de l'application

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.11.0] - 2026-07-29

## Nouvelles fonctionnalités

- mises Ã  jour de l'application

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.10.0] - 2026-07-29

## Nouvelles fonctionnalités

- mises Ã  jour de l'application

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.9.0] - 2026-07-29

## Nouvelles fonctionnalités

- mises Ã  jour de l'application

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.8.0] - 2026-07-29

## Nouvelles fonctionnalités

- mises Ã  jour de l'application

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.7.0] - 2026-07-29

## Nouvelles fonctionnalités

- mises à jour de la configuration et des tests

## Autres changements

- release updates

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.6.0] - 2026-07-29

## Nouvelles fonctionnalités

- mises à jour de la configuration et des tests

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.5.0] - 2026-07-26

## Nouvelles fonctionnalités

- personnaliser la carte et fiabiliser la distribution

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.4.2] - 2026-07-26

## Corrections de bugs

- relancer l'application après mise à jour

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.4.1] - 2026-07-26

## Corrections de bugs

- forcer le rafraichissement de l'interface

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.4.0] - 2026-07-26

## Nouvelles fonctionnalités

- personnaliser la carte et fiabiliser la distribution

## Corrections de bugs

- nettoyer les effets secondaires du build

## Autres changements

- detailler la documentation polonaise

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.3.2] - 2026-07-26

## Corrections de bugs

- afficher correctement les accents PowerShell
- ajouter un lanceur de publication Windows
- fiabiliser la detection des releases GitHub

## Autres changements

- detailler la documentation neerlandaise
- detailler les traductions europeennes

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.3.1] - 2026-07-26

## Corrections de bugs

- fiabiliser la publication GitHub
- locate GitHub CLI after winget installation

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

## [0.3.0] - 2026-07-26

## Nouvelles fonctionnalités

- Progression temps réel sur la géométrie complète SID–route–STAR–approche.
- Affichage et activation successive des fixes de procédure.
- Protection monotone contre les sauts de progression aux croisements.
- Bouton permanent de recherche manuelle des mises à jour.
- Icône avion appliquée explicitement à la fenêtre et à l’identité Windows.

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.

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
