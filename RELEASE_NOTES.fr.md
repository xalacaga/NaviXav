# NaviXav 1.4.15

Publié le 2026-08-08.

## Corrections

- Les demandes de licence commerciale et de contribution utilisent désormais l'adresse de contact dédiée à NaviXav.
- La mise à jour automatique s'installe désormais réellement : l'assistant qui attend la fermeture de NaviXav était lancé sans aucune console et mourait aussitôt, si bien que la mise à jour était annoncée comme planifiée et que l'application rouvrait sur la version précédente. L'assistant tient de plus son propre journal à côté de l'installateur, afin qu'une panne future soit analysable.
- Les installateurs téléchargés ne s'accumulent plus : chaque mise à jour efface les précédents, et l'installateur fait de même en fin d'installation. Un demi-gigaoctet s'était accumulé sur une machine suivie depuis les premières versions. Les journaux sont conservés, afin qu'une panne reste analysable.

## Modifications

- Nettoyage des installateurs telecharges.
- Correctif mise a jour automatique.
- Update NaviXav contact email.

L'installateur est vérifié par sa somme de contrôle SHA-256 avant toute mise à jour automatique.
