# NaviXav

Compléteur de plan de vol IFR. Récupère le dernier OFP généré dans SimBrief,
puis reconstitue localement ce que SimBrief ne fournit pas de façon fiable :
**piste en service, SID, STAR, approche et transitions** — le contenu du panneau
gauche de Navigraph, sans Navigraph.

```text
DÉPART   LFST · Entzheim
Piste    05              élevée    [SimBrief] face +6 kt · trav. 1 kt · ILS ENT
SID      EPIK8M          élevée    [SimBrief] SID filée par SimBrief et validée en base
Trans.   EPIKO           élevée    [calculé]  point de sortie de la SID ; rejoint la route

ROUTE    EPIK8M EPIKO LIRKO MOKIP GERVA AFRIC AFRI8N

ARRIVÉE  LFBO · Blagnac
Piste    32R             modérée   [calculé]  face +8 kt · configuration préférentielle
STAR     AFRI8N          élevée    [SimBrief] STAR filée par SimBrief et validée en base
Trans.   AFRIC           élevée    [calculé]  point d'entrée de la STAR
Approche ILS Z RWY 32R   élevée    [calculé]  préférence ILS et transition depuis ADIMO
Tr. app. ADIMO           élevée    [calculé]  transition partant de la sortie de la STAR
ILS      108.35 MHz
```

## Principe

Le chaînage est celui d'un FMS, par égalité de points de raccord :

```text
SID  --[fix de sortie]-->  premier point en route
dernier point en route  --[fix d'entrée]-->  STAR
STAR --[fix de sortie]-->  transition d'approche  -->  approche
```

Sur l'exemple LFST → LFBO : la STAR `AFRI8N` se termine à **ADIMO**, et
`ILS Z RWY 32R` publie précisément une transition **ADIMO**. Le maillon est
exact, donc la confiance est élevée.

Chaque élément retenu porte sa **source** (`SimBrief`, `calculé`, `imposé`), sa
**justification** et un **niveau de confiance** :

| Confiance | Signification |
|-----------|---------------|
| élevée    | maillon retrouvé par égalité de fix, ou valeur SimBrief validée en base |
| modérée   | reconstitué par proximité géographique, ou choix serré |
| faible    | aucun lien trouvé ; à vérifier avant utilisation |

Le moteur ne masque jamais un choix incertain, et liste les alternatives dans
la sortie JSON.

## Démarrage rapide

Double-cliquer sur **`NaviXav.bat`**. Au premier lancement il crée
l'environnement virtuel, installe les dépendances et génère `.env` ; ensuite il
démarre directement l'application et ouvre le navigateur.

Il accepte les mêmes options que la commande `web` :

```powershell
NaviXav.bat --port 9000
NaviXav.bat --no-open
```

## Application web locale

```powershell
navixav web
```

Ouvre `http://127.0.0.1:8765` — le serveur n'écoute que sur la boucle locale,
le Pilot ID et le dispatch ne quittent pas la machine.

- **Onglet Carte** : plan de terrain et suivi de l'avion en temps réel.
- **Bandeau de route** : la chaîne complète en pastilles, de `LFST` à `LFBO`,
  comme le fil d'Ariane de Navigraph.
- **Trois cartes terminales** : départ, route, arrivée. Chaque élément porte une
  pastille de confiance et sa justification.
- **Onglet Contraintes** : altitudes et vitesses publiées de la SID, de la STAR
  et de l'approche, VIA comprise.
- **Onglet Dispatch** : masses et carburant de l'OFP, avec jauges de marge par
  rapport aux maximums.
- **Onglet Fiche MCDU** : rendu écran vert, prêt à recopier.
- **Onglet JSON** : la sortie brute.

Le commutateur **Démo** charge le vol de référence LFST → LFBO, utile tant
qu'aucun OFP n'existe sur le compte SimBrief.

Options : `--port`, `--host`, `--no-open`.

## Fiche de saisie MCDU

`navixav plan --mcdu` traduit le plan dans le vocabulaire du FMS Airbus, prêt à
être saisi à la main après un import SimBrief dans l'EFB.

```text
F-PLN › ARRIVAL
RWY         32R ⚠             330°/8 kt
APPR        ILS Z RWY 32R
VIA         ADIMO             transition d'APPROCHE
STAR        AFRI8N
TRANS       AFRIC             transition d'entrée de STAR

À confirmer à l'ATIS avant saisie : piste arrivée
```

Le piège de la page ARRIVAL est là : **`VIA` et `TRANS` sont deux transitions
différentes, aux deux extrémités de la STAR.**

| Champ MCDU | Contenu | Exemple |
|---|---|---|
| `APPR` | procédure d'approche | ILS Z RWY 32R |
| `VIA` | transition d'**approche** — fin de STAR vers l'approche | ADIMO |
| `STAR` | arrivée normalisée | AFRI8N |
| `TRANS` | transition d'**entrée de STAR** — depuis la route | AFRIC |

Le marqueur ⚠ signale les éléments dont la confiance ne suffit pas pour saisir
sans vérifier l'ATIS — ici la piste, retenue par départage entre 32R et 32L.

## Carte et suivi temps réel

L'onglet **Carte** dessine le plan du terrain depuis la navdata — pistes, voies
de circulation, postes de stationnement — et y superpose ta position réelle,
rafraîchie chaque seconde.

- La **piste retenue par le moteur** est mise en évidence : on voit d'un coup
  d'œil vers quel seuil rouler.
- Molette pour zoomer, glisser pour déplacer, **Suivre** pour centrer sur
  l'avion, **Ajuster** pour revoir tout le terrain.
- Une trace suit le roulage, avec échelle et rose des vents.

### Source de position

Une seule source, sans configuration : **SimConnect**, en lecture directe dans
MSFS. Rien à installer côté simulateur et aucune application intermédiaire.

Sans simulateur, la carte reste utilisable et l'état est annoncé clairement.
Le commutateur **Démo** rejoue un roulage du parking vers le seuil de piste.

### Géométrie du sol

Les pistes, voies de circulation et parkings sont récupérés directement depuis
MSFS et conservés dans le cache local NaviXav.

## Choisir entre ILS X, Y et Z

Quand plusieurs procédures du même type desservent la même piste, l'OACI les
distingue par une lettre attribuée **en partant de Z, à rebours** : Z, puis Y,
puis X. Deux conséquences contre-intuitives :

- **Z est la première publiée, pas la dernière.**
- **La lettre ne porte aucune notion de priorité.** Elle n'est qu'un identifiant.

NaviXav ne s'y fie donc jamais. Il classe sur la **structure**, que la base
décrit précisément. À LFBO piste 32R :

| | **ILS Z RWY 32R** | **ILS Y RWY 32R** |
|---|---|---|
| Entrée | `IO32R` — IAF publié | `CF32R` — repère d'interception fictif |
| Transitions | ADIMO, AGENO, FUZAP, OGRIL, SULIT | aucune |
| Approche interrompue | 5 legs `TF` publiés | `CA` puis `VM` — montée dans l'axe, puis vecteurs |
| Équipement | **RNP 1 requis** | aucune exigence |

La raison d'être de Y est dans la dernière ligne : permettre à un avion non RNP
de faire l'ILS avec une remise de gaz conventionnelle.

Le classement applique donc, dans l'ordre :

1. **Équipement** — une approche exigeant le RNP est éliminée si l'avion n'est
   pas qualifié (`AIRCRAFT_RNP_CAPABLE`, ou `--no-rnp`).
2. **Raccord à la STAR** — la STAR `AFRI8N` finit à ADIMO, que seule Z publie.
3. **Mode d'arrivée** — avec une STAR on veut une entrée publiée ; sans STAR on
   sera vectoré, donc la variante à repère d'interception.
4. **Type d'approche** — `APPROACH_PREFERENCE`.

La lettre n'intervient qu'en tout dernier ressort, pour rendre le tri
déterministe, jamais comme préférence.

## Base de navigation NaviXav

NaviXav lit **directement MSFS 2024** par l'API Facilities de SimConnect, et
constitue sa propre base. Ni Navigraph, ni Little Navmap.

```powershell
navixav import LFST LFBO
```

```text
┌──────┬───────────┬────────┬─────┬──────┬───────────┬───────┐
│ OACI │ Terrain   │ Pistes │ SID │ STAR │ Approches │   Sol │
├──────┼───────────┼────────┼─────┼──────┼───────────┼───────┤
│ LFST │ Entzheim  │      2 │  13 │   13 │         7 │   378 │
│ LFBO │ Blagnac   │      4 │  23 │   14 │        14 │ 2 953 │
└──────┴───────────┴────────┴─────┴──────┴───────────┴───────┘
```

**À la demande, pas en masse.** Importer les 84 000 terrains prendrait des
heures pour une base qui vieillit aussitôt. Un vol en concerne deux ou trois,
récupérés en **0,4 s chacun** avec le simulateur ouvert, puis conservés dans
`data/navixav.sqlite` et consultables simulateur fermé.

Les repères, installations radio et routes aériennes se résolvent de la même
façon, au fil des besoins.

### Champs établis par sondage

Le SDK MSFS installé ne contient aucune documentation locale. Les définitions de
[navixav/msfs/fields.py](navixav/msfs/fields.py) ont donc été obtenues en
interrogeant le simulateur champ par champ, le type étant déduit de la taille de
réponse. Trois pièges que la supposition aurait manqués :

- **Tout est en mètres**, les fréquences en hertz, les suffixes de procédure en
  code ASCII (48 = pas de suffixe).
- Les blocs enfants arrivent en **messages distincts et typés**, pas dans la
  charge du parent.
- **Une transition de piste n'a ni nom ni type** : elle s'identifie par la piste.
  Les trois sortes de transition n'ont pas la même forme.

Le décodeur **vérifie la taille de charge** avant tout découpage : un champ
refusé décalerait sinon toutes les valeurs suivantes, sans le dire.

### Reconstruction des procédures

MSFS ne publie aucun segment au niveau de la procédure : tout est réparti dans
les transitions de piste. Mesuré sur LFPO : une SID en a exactement **une** (216
sur 216), une STAR en a **trois** (32 sur 32). NaviXav reconstitue donc le tronc
commun et ne conserve en branches que ce qui diverge — d'où `AGOP2A → sortie
AGOPA` et `AMB9E → entrée AMB`, conformes à la convention de nommage.

### Validation

L'extraction a été confrontée à Little Navmap sur LFPO : **zéro divergence** sur
le nom, la position, l'altitude, l'altitude de transition, les six extrémités de
piste, les 216 SID et les 32 STAR. Les fréquences ILS et les positions de
repères se recoupent également au chiffre près.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.example .env
```

Renseigner ensuite `SIMBRIEF_PILOT_ID` dans `.env` (SimBrief → *Account
Settings* → *SimBrief Pilot ID*). Le fichier `.env` est ignoré par git : le
Pilot ID n'est jamais versionné.

## Utilisation

```powershell
# Compléter le dernier OFP SimBrief
navixav plan

# Fiche de saisie MCDU (vocabulaire Airbus)
navixav plan --mcdu

# Sortie JSON, ou fichier
navixav plan --json
navixav plan --out plan.json

# Travailler hors ligne sur un OFP enregistré
navixav plan --save-ofp ofp.json
navixav plan --ofp ofp.json

# Forcer un élément
navixav plan --arr-rwy 14L --approach "ILS Z RWY 14L"
navixav plan --metar-arr "LFBO 260730Z 14015KT CAVOK 21/11 Q1018"

# Alimenter et inspecter la base (simulateur ouvert pour l'import)
navixav import LFST LFBO
navixav navdata
navixav airport LFBO --runway 32R
```

## Configuration

Tout est dans `.env` (voir [.env.example](.env.example)) :

| Variable | Rôle |
|----------|------|
| `SIMBRIEF_PILOT_ID` | identifiant SimBrief (ou `SIMBRIEF_USERNAME`) |
| `NAVDATA_STORE` | base NaviXav ; vide = `data/navixav.sqlite` |
| `METAR_SOURCE` | `simbrief` (METAR de l'OFP), `awc` (temps réel), `none` |
| `AIRCRAFT_RNP_CAPABLE` | qualification RNP de l'avion |
| `APPROACH_PREFERENCE` | ordre de préférence des approches |
| `MAX_TAILWIND_KT`, `MAX_CROSSWIND_KT` | limites de vent |
| `MIN_RUNWAY_LENGTH_FT` | longueur minimale exigée |
| `AIRPORT_PREFERENCES` | fichier des configurations préférentielles |

### Configurations préférentielles

Le vent et la longueur ne suffisent pas à reproduire la réalité opérationnelle.
À LFBO, 32L est plus longue que 32R, mais les **arrivées** se font en 32R et les
**départs** en 32L. Cette répartition ne figure dans aucun cycle AIRAC ; elle est
déclarée dans [data/airport_preferences.json](data/airport_preferences.json) :

```json
{
  "LFBO": {
    "arrival":   ["32R", "14L"],
    "departure": ["32L", "14R"],
    "note": "arrivées sur la piste sud-est, départs sur la piste nord-ouest"
  }
}
```

La préférence n'intervient qu'**en départage**. Elle ne retiendra jamais une
piste hors limites de vent : avec un vent de 140°/25 kt à LFBO, le moteur bascule
en 14 malgré la préférence.

## Architecture

```text
navixav/
├── config.py            variables d'environnement et réglages de l'interface
├── models.py            plan de vol, Choice (valeur + confiance + justification)
├── constraints.py       contraintes d'altitude et de vitesse (ARINC 424)
├── preferences.py       configurations préférentielles de pistes
├── chart.py             plan de terrain projeté en mètres locaux
├── geo.py · format.py   distance orthodromique, mise en forme
├── simbrief/
│   ├── client.py        endpoint « dernier OFP », sans clé API
│   └── parser.py        normalisation du JSON, dispatch, points de raccord
├── weather/metar.py     lecture du vent (METAR = nord vrai)
├── msfs/                extraction depuis MSFS
│   ├── client.py        client ctypes unique : Facilities + variables de vol
│   ├── fields.py        champs et types établis par sondage
│   └── extract.py       aéroport, installations radio, repères, routes
├── navdata/
│   ├── base.py          types + protocole NavdataProvider
│   ├── msfs_store.py    schéma et écriture de la base NaviXav
│   └── msfs.py          lecture, complétée à la demande depuis le simulateur
├── live/                position temps réel (SimConnect, source de démo)
├── planner/
│   ├── runway.py        composantes de vent, score, préférences
│   └── engine.py        chaînage SID / STAR / approche / transitions
├── render.py · mcdu.py  panneau terminal, fiche de saisie Airbus
├── web/                 API locale et interface (FastAPI + canvas)
└── cli.py               plan / import / navdata / airport / web
```

## Diagnostic

SimBrief renvoie ses erreurs métier avec un code HTTP 400 et le détail dans le
corps JSON. NaviXav lit ce corps et traduit les cas courants :

| Réponse SimBrief | Cause |
|------------------|-------|
| `No flight plan on file for the specified user` | Le Pilot ID est **correct** — SimBrief le renvoie dans sa réponse. Mais aucun OFP n'existe sur le compte. L'endpoint ne fait que relire le dernier plan produit : il faut d'abord générer un vol sur simbrief.com. |
| `Unknown UserID` | Pilot ID inexistant. Vérifier *Account Settings → SimBrief Pilot ID*. Pour un alias, utiliser `SIMBRIEF_USERNAME`. |

Pour distinguer les deux, comparer le champ `fetch.userid` de la réponse : s'il
contient l'identifiant envoyé, celui-ci est reconnu.

## Points d'attention

- **Le vent METAR est référencé au nord vrai**, contrairement au vent annoncé
  par la tour ou l'ATIS qui est magnétique. Les caps de piste de la base étant
  eux aussi vrais, la comparaison est cohérente.
- **Les rafales sont prises en compte** dans le calcul des composantes : le
  choix de piste est volontairement conservateur.
- **L'approche réelle peut changer** avec la météo ou l'ATC après le calcul du
  plan. Le niveau de confiance signale les cas incertains, mais ne remplace
  pas la vérification de l'ATIS.
- **Décalage de cycle AIRAC** : si le cycle SimBrief diffère de la base locale,
  un avertissement est émis. Une procédure peut avoir été renommée ou supprimée
  entre deux cycles.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest
```

161 tests, sans simulateur ni réseau : ils s'appuient sur
[tests/data/navdata_test.sqlite](tests/data/navdata_test.sqlite), une base
NaviXav de référence contenant LFST, LFBO et LFPO extraits de MSFS 2024. Les
tests qui interrogent réellement le simulateur s'ignorent proprement s'il est
fermé.

Le test de bout en bout [tests/test_engine.py](tests/test_engine.py) vérifie que
l'OFP de référence LFST → LFBO reproduit exactement le panneau cible.

Pour régénérer la base de test :

```powershell
navixav import LFST LFBO LFPO --store tests\data\navdata_test.sqlite --refresh
```

## Suites possibles

- Export `.pln` (MSFS), `.fms` (X-Plane), format Fenix / PMDG
- Injection directe du plan dans le simulateur via SimConnect
- Calcul de route sur le graphe des airways, pour se passer aussi de la route
  SimBrief
