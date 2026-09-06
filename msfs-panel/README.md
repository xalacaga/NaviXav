# Panneau NaviXav pour la barre d'outils MSFS

Ce dossier contient les **sources de compilation** du paquet. Le paquet
lui-même — celui qui est livré avec NaviXav et copié dans `Community` — vit
dans `navixav/msfs_panel/navixav-toolbar/`.

## Ce que fait le panneau

Une icône dans la barre d'outils du simulateur ouvre une fenêtre qui interroge
le service local de NaviXav sur `http://127.0.0.1:8765` — et les dix ports
suivants, la plage que `desktop.py` peut prendre si le premier est occupé. Elle affiche le jeu de
modèles détecté, l'état du trafic et celui de l'injection, et commande
l'interrupteur, la source et le retour à la fenêtre NaviXav.

Le panneau ne calcule rien. Tout ce qu'il montre vient de `/api/panel/state`,
tout ce qu'il commande existe déjà dans l'application.

Les quatre sources sont VATSIM, IVAO, OpenSky et Static. Les commandes de
trafic préservent les autres paramètres, notamment les identifiants SimBrief.
La fenêtre NaviXav relit ces choix toutes les trois secondes.

Le panneau MSFS affiche désormais Mon vol : prochain point et distance, temps restant, prochaine contrainte et TOD, synchronisés avec la fenêtre NaviXav et sa langue. Les valeurs de vol sont masquées après dix secondes sans actualisation. Le trafic affiche les avions confirmés, sélectionnés et écartés ainsi que le chargement, les erreurs et les états anciens ; le voyant vert exige des créations confirmées. Le bouton de retour ouvre la fenêtre pour les détails.

Le panneau MSFS 1.2.1 retrouve automatiquement NaviXav après une interruption ou un changement de port. Une connexion indisponible n’est plus présentée comme une application arrêtée. Les requêtes expirent réellement et une erreur d’affichage ne coupe plus la reconnexion. Après la mise à jour du panneau depuis les réglages, redémarrer MSFS pour charger ses nouveaux fichiers.

Le panneau 1.2.2 distingue un quota quotidien OpenSky épuisé d’une erreur d’injection générique et indique que NaviXav attend automatiquement la reprise. Réinstaller le panneau depuis les paramètres, puis redémarrer MSFS pour charger cette version.

La synthèse est publiée localement par la fenêtre NaviXav, sans recalcul dans le panneau. Les nouvelles rubriques suivent sa langue ; certaines anciennes commandes restent en anglais.

## Installer et mettre à jour le panneau

Lancer NaviXav, puis utiliser **Installer le panneau MSFS** dans les paramètres.
Seul `navixav-toolbar` est copié dans Community ; l'application Windows reste
installée séparément. **Retirer** enlève le paquet. Une opération affiche son
état et verrouille les boutons jusqu'à sa fin.

Les paramètres comparent la version du manifeste installé avec celle du paquet
livré. Si elles diffèrent, le bouton d'installation permet de remplacer le
paquet installé. Mettre à jour NaviXav ne recopie pas automatiquement le panneau
dans Community. Après un changement de ses fichiers, augmenter aussi la version
du manifeste : à version identique, l'interface ne détecte pas la modification.
Redémarrer MSFS si nécessaire pour recharger le panneau.

Le retour à la fenêtre restaure et affiche NaviXav ; le mode plein écran
exclusif du simulateur peut conserver le focus. Utiliser le mode fenêtré ou
sans bordure dans ce cas. Si un injecteur concurrent bloque le trafic, le
fermer puis désactiver et réactiver Trafic pour relancer l'injection NaviXav.

## Reconstruire la déclaration compilée

Le fichier `InGamePanels/navixav-toolbar.spb` est la déclaration du panneau,
compilée depuis `build/PackageSources/navixav-toolbar.xml`. Il est versionné :
**personne n'a besoin du SDK pour installer le panneau**, seulement pour le
reconstruire, et seulement si cette déclaration change.

`fspackagetool.exe` n'est qu'un lanceur : il s'attache à l'exécutable du
simulateur, qui fait le travail. Un code de sortie 0 ne suffit pas : le script
vérifie qu'un `.spb` a effectivement été produit. Si la compilation en ligne de
commande n'en produit pas, utiliser l'éditeur de projet :

1. MSFS 2024, mode développeur actif ;
2. barre de menus → **File → Open project…** → `msfs-panel/build/navixav-toolbar.xml` ;
3. dans l'éditeur de projet, **Build All** ;
4. puis, dans le dépôt :

```powershell
./scripts/build_msfs_panel.ps1 -SkipCompile
```

Le script cherche le `.spb` où que l'éditeur l'ait déposé — `-AlsoSearch` ajoute un dossier à la recherche — et le copie dans le paquet livré. Tant qu'il est
absent, `navixav.msfs_panel.status()` rend `complete: false` et l'interface ne
propose pas l'installation : un paquet sans déclaration se copierait sans
jamais apparaître dans la barre.

## Conventions vérifiées sur des paquets réels

Relevées sur les panneaux installés d'un poste de vol — GSX, Navigraph, FSLTL,
Flow — plutôt que devinées :

- l'identifiant du panneau est propre à chaque paquet (`PANEL_NAVIXAV`) ;
- le nom d'élément passé à `customElements.define` doit l'être aussi
  (`ingamepanel-navixav`) : deux paquets qui partagent `ingamepanel-custom`
  s'excluent dans la barre d'outils ;
- l'icône est déposée en deux endroits, `html_ui/Textures/Menu/toolbar/` et
  `html_ui/icons/toolbar/` ;
- un `fetch` vers `localhost` depuis le panneau fonctionne en MSFS 2024 —
  FSLTL Traffic Injector n'utilise rien d'autre.
