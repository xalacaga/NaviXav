# NaviXav 1.4.5

Publication du 1 août 2026.

## Corrections de bugs

- Le tracé de l'approche ne part plus vers un repère homonyme situé à des centaines de milles du terrain : la finale d'Orly filait en Corse.
- Un repère nommé d'après une piste — « CF02 », « FI21L », « DER07 » — est reconnu comme tel sur n'importe quel aérodrome du monde, et ne peut plus emprunter la position de son homonyme sur un terrain voisin.
- Un point en route dont la base connaît plusieurs homonymes est désormais choisi près de la route, et écarté du tracé s'il l'allonge démesurément.
- À l'import du plan et à chaque nouvelle route, le tracé complet est vérifié : tout point hors de sa zone est retiré et signalé dans les avertissements du plan, quelle que soit l'origine de la position fautive.
- Une route qui franchit l'antiméridien se dessine d'un seul trait au lieu de traverser la carte à l'envers.
- Un vol qui revient à son terrain de départ conserve son point de virage : la distance annoncée par le plan prend le relais de la route directe.
- Les repères de procédure enregistrés à tort comme points de report sont supprimés de la base de navigation à l'ouverture.

## Autres changements

- Correction bug.
- Link official NaviXav website.

L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.
