# NaviXav 1.4.10

Publié le 2026-08-06.

## Nouveautés

- Les paramètres ouvrent le journal complet des versions : toutes les évolutions importantes depuis le début du suivi, version par version, avec la date et un repère sur celle qui est installée. Le journal est livré avec l'application et se lit sans connexion. Le texte des changements reste en anglais ; le cadre et les rubriques suivent la langue choisie.
- Le suivi de vol distingue maintenant une simulation en pause d'une simulation perdue : l'indicateur MSFS et la pastille de suivi affichent « MSFS en pause » au lieu de laisser croire à une connexion coupée. Un simulateur qui n'expose pas cet état continue d'être suivi normalement.
- Un crayon discret apparaît au survol de la piste, de la SID, de la STAR, de leurs transitions et de l'approche : il ouvre la liste des autres procédures publiées et permet de changer le choix après coup, même quand le moteur est sûr de lui. La liste n'est plus limitée à trois entrées, elle montre tout ce qui est volable depuis la piste retenue, et « Revenir au choix automatique » rend la main au moteur. Le crayon reste allumé sur un choix imposé.

## Corrections

- Une procédure absente ne prend plus la place d'une procédure réelle. Quand aucune STAR n'est publiée pour la piste, la raison remplace le tiret sur une seule ligne resserrée, et la ligne de transition qui ne faisait que répéter l'absence disparaît. Même resserrement pour une SID ou une approche sans transition.
- Une SID ou une STAR qui n'est pas publiée pour la piste retenue n'est plus enchaînée : elle part d'un autre seuil ou mène à l'IAF de l'autre côté du terrain. NaviXav annonce désormais un départ en guidage radar ou une arrivée directe, et la procédure écartée reste proposée dans la liste des choix. À Brive-Souillac en piste 29, le plan indique BSC puis ILS RWY 29 au lieu d'une STAR involable.
- Sans STAR, l'approche et sa transition se raccordent maintenant au dernier point de la route au lieu de rester sans lien. Une transition publiée sur ce point précis est reconnue et n'est plus présentée comme un choix incertain.
- Les repères d'approche que SimBrief laisse dans le journal de navigation sans les marquer, comme CF29 ou RW11, ne comptent plus comme points en route : ils ne sont plus tracés sur la route et ne servent plus à raccorder l'arrivée.
- Quand une STAR dessert bien la piste d'atterrissage mais se termine sur un point qui n'ouvre aucune approche, NaviXav le dit explicitement au lieu de laisser découvrir la rupture en vol.
- Le journal des versions ne s'affiche plus en permanence par-dessus l'interface : il ne s'ouvre qu'au clic sur son icône dans les paramètres et se referme complètement.
- La fenêtre des paramètres n'a plus de barre de défilement horizontale : un champ invisible débordait sur toute la largeur de la boîte, quelle que soit la taille de la fenêtre.

## Modifications

- Correction bug et améliorations diverses.

L'installateur est vérifié par sa somme de contrôle SHA-256 avant toute mise à jour automatique.
