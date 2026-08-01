# Nouveautés de la prochaine version

À compléter à **chaque modification du code**, pas seulement avant de publier :
une puce par changement, en français et du point de vue de l'utilisateur. Ce
fichier remplace les sujets de commit dans les notes de version, puis il est
réinitialisé par `scripts\prepare_release.ps1`.

<!-- Exemple, à supprimer :
- Le suivi du vol affiche le temps restant avant l'arrivée.
-->

- Nouvel onglet « Roulage » : un plan d'aérodrome dédié sur fond aéronautique
  sombre, avec quadrillage métrique et indication du nord, sans fond routier ni
  route de vol.
- Le plan de roulage occupe toute la zone disponible et reste lisible dans les
  fenêtres compactes. Les voies secondaires sont masquées par défaut et le
  bouton « Secondaires » les affiche à la demande.
- Au départ, NaviXav reconnaît automatiquement le poste proche de l'avion et
  propose son itinéraire vers la piste retenue. Cliquer un autre poste remplace
  immédiatement cette proposition.
- Seules les voies de l'itinéraire portent leur nom : le chemin se lit d'un
  coup d'œil.
- La consigne du moment s'affiche en grand sur le plan de roulage, avec le
  chemin restant et la distance jusqu'au bout.
- L’onglet Roulage, le suivi du vol, le journal local, les phases de vol, les
  états de la carte et la commande de création SimBrief suivent désormais
  immédiatement la langue choisie. Les identifiants et la phraséologie
  aéronautiques normalisés restent inchangés.
- Les fiches Départ, Route et Arrivée traduisent aussi leurs libellés, les
  composantes de vent, les justifications du moteur et les avertissements,
  sans modifier les procédures, repères ni valeurs issus de SimBrief.

## Corrections

<!-- Exemple, à supprimer :
- Le fond de carte ne laisse plus apparaître la grille des tuiles.
-->

- La carte redevient lisible : les voies de circulation, les postes et leurs
  étiquettes ne s'affichent plus par-dessus les tuiles, la route et l'avion.
  Le détail du sol est passé dans le nouvel onglet « Roulage ».
- Changer de poste de stationnement annule désormais les anciennes demandes :
  une réponse réseau ou de guidage retardée ne peut plus restaurer le premier
  itinéraire.
- Les chemins de parking SimConnect ne sont plus confondus avec des segments de
  taxiway. Ils ne peuvent donc plus créer de longues diagonales artificielles à
  travers le terrain, comme entre T41 et N1 à LFBO.
- Le recalcul après un écart reste sur le réseau principal praticable et ne
  sélectionne plus un point isolé ou une route de service.
