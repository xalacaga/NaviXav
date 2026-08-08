# NaviXav 1.4.12

Publié le 2026-08-08.

## Corrections

- Les mises à jour automatiques attendent désormais la fermeture complète de l'ancien processus NaviXav, réinstallent dans le dossier réellement utilisé et conservent un journal d'installation, empêchant l'ancienne version de redémarrer et de reproposer la même mise à jour.
- La préparation d'une Release gère désormais une catégorie Nouveautés ou Corrections vide sans décaler les arguments PowerShell suivants ni interrompre la publication.

## Modifications

- Correction bug.
- Bug de versioning.

L'installateur est vérifié par sa somme de contrôle SHA-256 avant toute mise à jour automatique.
