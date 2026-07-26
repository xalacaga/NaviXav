# NaviXav

**Documentation :** Français · [English](README.en.md) ·
[Deutsch](README.de.md) · [Español](README.es.md) ·
[Italiano](README.it.md) · [Português](README.pt.md) ·
[Nederlands](README.nl.md) · [Polski](README.pl.md)

NaviXav est une application locale d’assistance au vol IFR pour Microsoft
Flight Simulator. Elle récupère le dernier plan de vol SimBrief, complète les
informations terminales avec les données du simulateur et les présente dans
une interface adaptée à la préparation du vol et à la saisie du MCDU.

L’application possède sa propre fenêtre Windows. Son interface est rendue par
Microsoft WebView2 et communique uniquement avec un service local lié à
`127.0.0.1`. Aucun navigateur externe n’est ouvert. Les réglages, la base de
navigation et les caches restent sur l’ordinateur.

La fenêtre est entièrement redimensionnable. L’interface réorganise ses
panneaux, ses commandes, ses onglets et la hauteur de la carte selon l’espace
disponible, jusqu’à une taille minimale de 720 × 560 pixels.

> NaviXav est destiné à la simulation de vol uniquement. Les informations
> affichées doivent être vérifiées avec les publications officielles et les
> instructions ATC applicables.

## Fonctionnalités

### Plan de vol SimBrief

- récupération automatique du dernier OFP au démarrage ;
- prise en charge du Pilot ID ou du nom d’utilisateur SimBrief ;
- affichage de la route complète, de l’origine à la destination ;
- mise en évidence du prochain point de route selon la position réelle de
  l’avion, avec atténuation des points déjà franchis ;
- masses, carburant, temps de vol, dégagement et données de dispatch ;
- informations sur l’appareil, l’immatriculation et l’équipement déclaré.

### Préparation IFR

NaviXav complète et présente :

- la piste de départ et la piste d’arrivée ;
- la SID et sa transition ;
- la STAR et sa transition ;
- l’approche et sa VIA ;
- la fréquence et l’identifiant ILS ;
- les contraintes d’altitude et de vitesse ;
- l’altitude de transition et le niveau de transition ;
- l’altitude d’interception de l’approche ;
- l’altitude d’approche interrompue ;
- la justification et le niveau de confiance de chaque choix.

Les blocs **Départ · Route · Arrivée** peuvent être réduits afin de libérer de
l’espace dans l’interface.

### Suivi du vol

L’onglet **Suivi du vol** exploite la position MSFS en temps réel pour afficher :

- la phase de vol détectée automatiquement ;
- la vitesse sol (GS) et la vitesse air indiquée (IAS) fournies par MSFS ;
- le prochain point et sa distance ;
- l’écart latéral par rapport au segment actif ;
- la distance restante ;
- la prochaine contrainte d’altitude ou de vitesse ;
- le taux vertical nécessaire pour atteindre cette contrainte ;
- le Top of Descent et un taux de descente indicatif sur une pente de 3° ;
- l’écart par rapport au profil vertical prévu.

La trace du vol est enregistrée localement toutes les cinq secondes. Elle peut
être mise en pause, effacée ou rejouée depuis l’interface. Aucun historique
n’est envoyé vers un service externe.

### Fiche MCDU

L’onglet **Fiche MCDU** regroupe les informations à saisir dans un FMS Airbus :

- `FROM/TO`, numéro de vol et dégagement ;
- Cost Index et niveau de croisière ;
- ZFW, carburant bloc, roulage, trajet et réserves ;
- piste, SID, transition et altitude de transition ;
- route `VIA/TO` ;
- STAR, transition, approche et VIA ;
- QNH, température, vent, fréquence ILS et axe final ;
- minima RADIO ou BARO et RVR.

### Connexion directe à MSFS

NaviXav utilise SimConnect pour :

- détecter la présence du simulateur ;
- afficher un voyant vert ou rouge dans la barre supérieure ;
- suivre la position de l’avion en temps réel ;
- lire l’altitude, la hauteur sol, le cap, la vitesse sol et la vitesse
  verticale ;
- récupérer les aéroports, pistes, procédures, repères et installations radio ;
- constituer progressivement une base locale dans `data/navixav.sqlite`.

Le simulateur doit être lancé avec un vol chargé pour récupérer de nouvelles
données. Les informations déjà mises en cache restent disponibles hors ligne.

### Carte

La carte comprend :

- un fond OpenStreetMap ;
- la route SimBrief dessinée avec ses points ;
- des couleurs distinctes pour la SID, la partie en route, la STAR et
  l’approche ;
- les pistes et la piste sélectionnée ;
- la position et le cap de l’avion ;
- une trace du déplacement ;
- un mode de suivi automatique ;
- le zoom, le déplacement et l’ajustement au terrain ou à la route ;
- la trace complète réellement parcourue, conservée du départ à l’arrivée ;
- une couleur de trace personnalisable ;
- le choix entre OpenStreetMap Standard et OpenTopoMap.

### Cartes AIS nationales officielles

NaviXav interroge directement les publications des autorités nationales, sans
passer par EUROCONTROL/EAD :

- France : SIA eAIP (`LF`) ;
- Espagne et Canaries : ENAIRE AIP (`LE`, `GC`, `GE`) ;
- Pays-Bas : LVNL eAIP (`EH`) ;
- États-Unis et territoires couverts : FAA d-TPP.

Pour ces aérodromes, NaviXav peut :

- présenter dans l’onglet **Cartes officielles** tous les PDF du départ et de
  l’arrivée, classés par type ;
- ouvrir chaque document dans l’interface ou séparément ;
- sélectionner par défaut la SID, la STAR ou l’approche correspondant au vol
  courant ;
- retrouver automatiquement la carte d’approche correspondant à la piste et au
  type d’approche retenus ;
- télécharger à la demande uniquement les PDF consultés ;
- conserver la publication dans le cache AIRAC local ;
- afficher la carte officielle dans la fiche MCDU ;
- extraire les minima ILS CAT I SIA lorsque le format est reconnu ;
- proposer la DA, la DH et la RVR avant validation.

Les valeurs extraites ne sont jamais appliquées silencieusement : elles doivent
être validées dans l’interface. Le bouton **Calque officiel** n’est proposé que pour
un document possédant un géoréférencement validé. Il suit le choix de carte :
le PDF du départ ne peut être superposé que sur le départ, et celui de l’arrivée
que sur l’arrivée. Cette règle est identique pour toutes les sources.

Un pays n’est ajouté à la liste automatique qu’après validation d’un accès
direct et stable à ses PDF officiels. Une source absente n’est donc jamais
remplacée silencieusement par un agrégateur tiers.

## Prérequis

- Windows 10 ou Windows 11 en 64 bits ;
- Microsoft WebView2 Runtime, installé automatiquement par l’installateur ;
- Microsoft Flight Simulator pour les données et le suivi en temps réel ;
- un compte SimBrief avec un OFP généré ;
- une connexion Internet pour SimBrief, le fond cartographique et les
  publications AIS nationales ou FAA.

L’installateur inclut Python, les bibliothèques, pywebview, le connecteur
SimConnect autonome de NaviXav et le bootstrapper Microsoft WebView2 signé. Aucun de ces outils
n’est à installer séparément. MSFS n’est pas obligatoire pour essayer le mode
Démo ou consulter les données déjà enregistrées.

SimConnect n’est jamais installé ni réinstallé dans Windows par NaviXav.
L’application embarque une copie privée de la DLL moderne dans son propre
dossier. Si la machine possède déjà SimConnect, son installation, sa version et
ses réglages ne sont ni remplacés ni modifiés. Cette DLL privée dialogue avec le
service SimConnect de MSFS : seul le simulateur doit être installé et lancé pour
recevoir les données en direct.

### Langues de l’interface

La langue se choisit dans **Paramètres**, s’applique immédiatement et reste
mémorisée sur l’ordinateur. NaviXav fournit les interfaces française, anglaise,
allemande, espagnole, italienne, portugaise, néerlandaise et polonaise. Les
abréviations aéronautiques, identifiants de procédures, METAR et valeurs MCDU
restent volontairement dans leur notation internationale.

## Installation rapide sous Windows

1. Télécharger le fichier `NaviXav-Setup-<version>.exe` de la dernière
   [Release GitHub](https://github.com/xalacaga/NaviXav/releases/latest).
2. Lancer l’installateur.
3. Vérifier la page de contrôle des prérequis.
4. Conserver ou modifier le dossier proposé, puis cliquer sur **Installer**.
5. Lancer NaviXav depuis le menu Démarrer ou le raccourci facultatif du bureau.

L’installateur vérifie Microsoft WebView2 et l’installe automatiquement s’il
manque. L’installation se fait pour l’utilisateur courant et ne demande
normalement pas de droits administrateur.

Une archive portable est également disponible : extraire
`NaviXav-<version>-windows-x64-portable.zip`, puis lancer `NaviXav.exe`. Sur une
machine dépourvue de WebView2, utiliser d’abord l’installateur complet.

### Depuis les sources

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Au premier lancement, le script :

1. recherche Python ;
2. crée l’environnement virtuel `.venv` ;
3. installe NaviXav et ses dépendances ;
4. démarre le service local privé ;
5. ouvre l’interface dans la fenêtre NaviXav.

Les lancements suivants réutilisent l’environnement déjà installé.

### Construire une distribution

Depuis PowerShell, dans le dossier du projet :

```powershell
.\scripts\build_windows.ps1
```

Le script :

1. contrôle Windows 64 bits, Python et le SDK SimConnect ;
2. installe les outils de construction manquants ;
3. récupère le bootstrapper WebView2 officiel et vérifie sa signature
   Microsoft ;
4. exécute les tests hors intégration MSFS en direct ;
5. produit l’installateur, l’archive portable et leurs sommes SHA-256 dans
   `release\`.

Le SDK SimConnect mentionné à l’étape 1 concerne uniquement la machine qui
construit NaviXav. Il n’est pas installé sur les machines des utilisateurs.

### Fichiers de distribution

Après une construction réussie :

| Fichier | Usage |
|---|---|
| `release\NaviXav-Setup-<version>.exe` | installateur Windows recommandé |
| `release\NaviXav-<version>-windows-x64-portable.zip` | version portable |
| `release\*.sha256` | empreintes de contrôle des fichiers distribués |

Le dossier `release\` est volontairement ignoré par Git. Les exécutables sont
des artefacts de construction à publier dans une version GitHub, pas des
sources à versionner.

## Installation manuelle

Depuis PowerShell, dans le dossier du projet :

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m navixav.desktop
```

Cette commande ouvre la fenêtre NaviXav. Pour un diagnostic du service local
sans fenêtre :

```powershell
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
```

Le service reste alors accessible uniquement sur `http://127.0.0.1:8765`.

## Configuration

La configuration courante se fait depuis le bouton **Paramètres** de
l’interface.

### Compte SimBrief

Renseigner l’un des deux champs :

- **Pilot ID SimBrief** : identifiant numérique affiché dans les paramètres du
  compte SimBrief ;
- **Nom d’utilisateur SimBrief** : alias du compte.

Le Pilot ID est recommandé. Après enregistrement, NaviXav récupère
immédiatement le dernier OFP disponible. À chaque nouveau démarrage, ce dernier
plan est chargé automatiquement.

### Réglages disponibles

L’interface permet également de configurer :

- la source METAR ;
- l’ordre de préférence des approches ;
- la composante maximale de vent arrière ;
- la composante maximale de vent traversier ;
- la longueur minimale de piste ;
- la capacité RNP de l’appareil.

Dans la version installée, les valeurs sont conservées dans
`%LOCALAPPDATA%\NaviXav\user_settings.json`.

## Première utilisation

1. Générer un plan de vol dans SimBrief.
2. Lancer Microsoft Flight Simulator et charger un vol.
3. Démarrer NaviXav depuis le menu Démarrer, ou avec `NaviXav.bat` en mode
   développement.
4. Ouvrir **Paramètres** et enregistrer le Pilot ID SimBrief.
5. Attendre le chargement automatique du dernier OFP.
6. Vérifier le voyant **MSFS connecté** en haut à droite.
7. Contrôler les choix de piste, SID, STAR et approche.
8. Consulter les contraintes et la carte officielle.
9. Valider les minima avant de les recopier dans le MCDU.

Le bouton **Compléter le plan** permet de récupérer à nouveau le dernier OFP
après avoir généré ou modifié un vol dans SimBrief.

## Utilisation de la carte

- **Fond carte** : affiche ou masque le fond libre choisi dans les paramètres.
- **Paramètres** : choisit OpenStreetMap Standard ou OpenTopoMap et la couleur
  de la trace complète du vol.
- **Calque officiel** : apparaît uniquement pour la fiche géoréférencée de
  l’aérodrome actuellement affiché et règle son opacité.
- **Route complète** : cadre toute la route du vol.
- **Suivre** : maintient l’avion au centre.
- **Ajuster** : cadre l’aéroport sélectionné.
- **+ / −** : modifie le niveau de zoom.
- **Molette** : zoome sous le pointeur.
- **Glisser** : déplace la carte.

Les boutons d’aéroport permettent de passer rapidement du terrain de départ au
terrain d’arrivée.

## Fenêtre et affichage responsive

### Téléphone et tablette sur le réseau local

Active **Accès téléphone et tablette** dans **Paramètres**, enregistre puis
redémarre NaviXav. L’adresse protégée affichée sur le PC s’ouvre depuis un
téléphone ou une tablette connecté au même Wi-Fi. L’interface mobile donne
accès au suivi temps réel, à la carte, aux contraintes, au MCDU, aux données
avion et aux cartes officielles. Les réglages, l’arrêt et les mises à jour
restent réservés au PC. Si Windows le demande, autorise NaviXav uniquement sur
les réseaux privés.

NaviXav adapte automatiquement son interface au redimensionnement :

- au-dessus de 1100 px, les cartes Départ, Route et Arrivée peuvent être
  présentées côte à côte ;
- sous 1100 px, ces cartes passent sur une seule colonne ;
- sous 980 px, la barre d’outils et les commandes de carte occupent toute la
  largeur disponible ;
- sous 760 px, les onglets deviennent défilables, les boutons se redistribuent
  et les tableaux restent consultables horizontalement ;
- sous 520 px, les statistiques et les panneaux complexes passent en colonne.

La carte écoute chaque changement de taille de la fenêtre et recalcule
immédiatement son canevas. La taille minimale de la fenêtre native est
720 × 560 pixels.

## Mode Démo

Le commutateur **Démo** charge un vol d’exemple et simule un déplacement au
sol. Il permet de découvrir l’interface sans compte SimBrief ou sans
simulateur.

Le mode Démo est toujours désactivé au démarrage afin que NaviXav privilégie le
dernier plan SimBrief.

## Arrêt de l’application

Utiliser le bouton **Quitter** dans la barre supérieure. NaviXav arrête
proprement le serveur, ferme la fenêtre et la connexion SimConnect, puis libère
le port `8765`. Fermer directement la fenêtre produit le même résultat.

En mode diagnostic `--no-open`, la combinaison `Ctrl+C` dans la console
effectue également un arrêt normal.

## Options de démarrage

Le lanceur Windows accepte les options suivantes :

```powershell
.\NaviXav.bat --port 9000
.\NaviXav.bat --no-open
```

- `--port` change le port local ;
- `--no-open` lance uniquement le service local, pour le diagnostic.

L’adresse d’écoute reste volontairement fixée à `127.0.0.1`.

## Commandes complémentaires

NaviXav peut aussi être utilisé depuis PowerShell :

```powershell
# Afficher le dernier plan SimBrief
.\.venv\Scripts\navixav.exe plan

# Générer une fiche MCDU textuelle
.\.venv\Scripts\navixav.exe plan --mcdu

# Produire une sortie JSON
.\.venv\Scripts\navixav.exe plan --json

# Importer des aéroports depuis MSFS
.\.venv\Scripts\navixav.exe import LFBO LFPO

# Examiner la base locale
.\.venv\Scripts\navixav.exe navdata

# Afficher les informations d’un aéroport
.\.venv\Scripts\navixav.exe airport LFBO --runway 32R
```

## Données locales

NaviXav utilise les emplacements suivants :

| Emplacement | Contenu |
|---|---|
| `%LOCALAPPDATA%\NaviXav\user_settings.json` | configuration de la version installée |
| `%LOCALAPPDATA%\NaviXav\navixav.sqlite` | base de navigation construite depuis MSFS |
| `%LOCALAPPDATA%\NaviXav\cache\` | cartes AIS nationales et FAA mises en cache |
| `%LOCALAPPDATA%\NaviXav\webview\` | stockage local de la fenêtre WebView2 |
| `%LOCALAPPDATA%\NaviXav\logs\navixav.log` | journal de la version installée |
| `data\` et `.venv\` | données et environnement du mode développement |

Ces données locales, les secrets et les caches ne sont pas destinés à être
versionnés.

Le journal enregistre les démarrages et arrêts, erreurs, appels API lents,
durées de récupération SimBrief, temps de complétion MSFS et remplissages du
cache. Il n’enregistre ni le Pilot ID, ni le nom d’utilisateur, ni la route
complète. Sa taille est limitée à 2 Mo avec cinq anciennes versions conservées
(`navixav.log.1` à `navixav.log.5`).

Lors d’un premier accès à un aérodrome ou à une procédure, l’interface prévient
que le cache MSFS est en cours de remplissage et que l’opération peut prendre
plusieurs dizaines de secondes. Les accès suivants réutilisent les données
locales.

## Versionnement Git

Le dépôt source est prévu pour être hébergé sur :
`https://github.com/xalacaga/NaviXav.git`.

Le fichier `.gitignore` exclut notamment :

- `.env`, les réglages utilisateur et les bases locales ;
- `.claude/`, `CLAUDE.md`, `.codex/`, `AGENTS.md` et `CODEX.md` ;
- les données Graphify et `graphify-out/` ;
- les environnements Python, caches de tests et sorties de construction ;
- `dist\`, `build\` et `release\`.

Les mémoires Claude/Codex peuvent donc être maintenues localement sans être
publiées dans le dépôt Git.

### Mises à jour automatiques

Au démarrage, NaviXav interroge uniquement la dernière Release publique du
dépôt `xalacaga/NaviXav`. Si sa version est supérieure à la version installée,
un bouton **Mise à jour** apparaît dans la barre supérieure. L’installation ne
commence qu’après confirmation de l’utilisateur.

L’installateur est téléchargé dans
`%LOCALAPPDATA%\NaviXav\updates\`, puis son empreinte SHA-256 est comparée à
celle publiée par GitHub. En cas d’empreinte absente ou différente, le fichier
est supprimé et n’est jamais exécuté. Une panne de GitHub ou d’Internet ne
bloque ni le démarrage ni les fonctions de vol.

Le dépôt est public en lecture. Un utilisateur peut consulter le code et
télécharger les Releases sans compte GitHub, mais seuls les collaborateurs
autorisés peuvent écrire dans le dépôt.

### Version et notes de Release

La version suit le format sémantique `MAJEURE.MINEURE.CORRECTIF`. Les messages
de commit conventionnels déterminent automatiquement le niveau suivant :

- `feat:` produit normalement une version mineure ;
- `fix:` produit une version corrective ;
- `BREAKING CHANGE` ou `!:` produit une version majeure ;
- les autres changements produisent une version corrective.

Préparer localement la version et ses notes :

```powershell
.\scripts\prepare_release.ps1 -Bump auto
```

Publier l’installateur, l’archive portable, leurs empreintes et les notes dans
une Release GitHub :

```powershell
.\scripts\publish_release.ps1 -Bump auto
```

Le second script exige un dépôt propre et GitHub CLI authentifié. Il exécute
les tests, construit les livrables, crée le commit et le tag de version, pousse
`main` et le tag, puis crée la Release GitHub. `CHANGELOG.md` conserve
l’historique et `RELEASE_NOTES.md` contient les notes de la version courante.

## Dépannage

### Le port 8765 est déjà utilisé

Une instance de NaviXav est probablement encore ouverte. Fermer sa fenêtre ou
cliquer sur **Quitter** dans l’interface. L’exécutable détecte une instance
existante ; si une autre application occupe 8765, il choisit automatiquement
un port libre entre 8766 et 8775.

Pour identifier le processus :

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

Il est aussi possible de démarrer l’application sur un autre port :

```powershell
.\NaviXav.bat --port 9000
```

### La fenêtre NaviXav ne s’ouvre pas

- relancer l’installateur complet afin qu’il contrôle WebView2 ;
- vérifier que Windows et Microsoft Edge WebView2 Runtime sont à jour ;
- consulter `%LOCALAPPDATA%\NaviXav\logs\navixav.log` ;
- vérifier qu’un antivirus ne bloque pas `NaviXav.exe` ou les processus
  `msedgewebview2.exe`.

L’archive portable ne peut pas installer elle-même WebView2. Sur une machine
qui ne possède pas ce composant, utiliser `NaviXav-Setup-<version>.exe`.

### Le voyant MSFS reste rouge

- vérifier que le simulateur est lancé ;
- charger complètement un vol ;
- attendre quelques secondes puis cliquer sur le voyant ;
- relancer l’installateur si la copie privée de `SimConnect.dll` livrée avec
  NaviXav a été supprimée ou mise en quarantaine par un antivirus.

### Aucun plan SimBrief n’est chargé

- vérifier le Pilot ID ou le nom d’utilisateur dans **Paramètres** ;
- générer un OFP sur SimBrief avant de relancer la récupération ;
- vérifier la connexion Internet.

### Une carte officielle n’est pas disponible

- vérifier que le préfixe OACI est couvert par SIA, ENAIRE, LVNL ou FAA ;
- vérifier la connexion Internet ;
- confirmer que la piste et l’approche ont été déterminées ;
- utiliser la saisie manuelle des minima si l’extraction n’est pas disponible.

## Limites actuelles

- la procédure réellement autorisée peut différer du plan selon l’ATIS, la
  météo et les instructions ATC ;
- les minima dépendent de la catégorie de l’avion, de son équipement et des
  conditions opérationnelles ;
- l’extraction automatique des minima est limitée aux formats SIA reconnus ;
- un PDF sans géoréférencement validé reste consultable, mais ne peut pas être
  utilisé comme calque ;
- les nouvelles données MSFS nécessitent que le simulateur soit accessible.

Toujours confirmer les informations importantes avant leur saisie dans le
simulateur.

## Architecture et confidentialité

- `navixav/desktop.py` gère la fenêtre native et le cycle de vie du processus ;
- `navixav/web/app.py` fournit l’API FastAPI liée uniquement à
  `127.0.0.1` ;
- `navixav/web/static/` contient l’interface responsive HTML/CSS/JavaScript ;
- `navixav/planner/` complète le plan IFR ;
- `navixav/navdata/` construit et interroge la base issue de MSFS ;
- `navixav/live/` assure le suivi SimConnect ;
- `navixav/sia.py`, `navixav/faa.py` et `navixav/national_aip.py` gèrent les
  publications officielles.

Le service local n’écoute jamais sur le réseau extérieur. Le Pilot ID
SimBrief, les préférences, la trace du vol et les PDF mis en cache restent sur
la machine. Seules les requêtes nécessaires à SimBrief, OpenStreetMap, la
météo et aux publications AIS officielles quittent l’ordinateur.

## Licence

NaviXav est un logiciel libre distribué sous licence
[Apache 2.0](LICENSE).

Copyright 2026 Xavier BEGUE (xalacaga)

Tu peux librement utiliser, modifier, redistribuer et intégrer NaviXav, y
compris dans un projet commercial. En contrepartie, la licence impose de
**créditer l'auteur** :

- conserver la mention de copyright et une copie de la licence dans toute
  redistribution ;
- conserver le fichier [NOTICE](NOTICE) et son contenu d'attribution ;
- **signaler de manière visible tout fichier que tu as modifié**, conformément
  à la section 4(b) de la licence.

La licence accorde également une concession de brevets et exclut toute
garantie. Les données de navigation, les cartes officielles et le fond
cartographique ne sont pas couverts par cette licence : ils restent soumis aux
conditions de leurs fournisseurs respectifs, détaillées dans le fichier NOTICE.

## Tests

Le profil reproductible utilisé pour construire la distribution est :

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```

Les tests marqués `live_msfs` interrogent un simulateur réellement démarré et
ne font donc pas partie du contrôle automatique de l’installateur.
