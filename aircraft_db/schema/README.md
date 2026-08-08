# NaviXav Aircraft Database — format

Ce dossier définit le contrat de la base. Le moteur NaviXav ne connaît aucun
avion : il charge une base, détecte l'appareil, évalue les étapes vérifiables
et affiche le reste. Toute la connaissance métier vit ici.

La base est du **JSON pur**. Aucun fichier n'exécute de code, ne contient de
SimVar, ni ne reproduit un extrait de manuel.

---

## Arborescence

```text
aircraft_db/
    VERSION.json                    version de la base
    schema/
        README.md                   ce document
        properties.json             vocabulaire fermé des propriétés
    tools/
        validate.py                 validateur, sans dépendance
        coverage.py                 comparaison avec une checklist publiée
    aircraft/
        <constructeur>/<famille>/
            metadata.json           identité et détection
            systems.json            systèmes déclarés
            procedures.json         procédures normales
            limitations.json        vitesses, masses, moteur
            mapping.json            origine des propriétés par variante
```

Une famille est le grain d'écriture des procédures : `c172` couvre les
variantes G1000 et analogique, qui ne diffèrent que par leur mapping et par
quelques étapes conditionnées à un système.

---

## Ajouter un avion sans toucher à NaviXav

Aucun catalogue ne couvrira les appareils installés chez les utilisateurs. Le
moteur lit donc **deux racines**, dans l'ordre :

```text
1. la base livrée        <application>/aircraft_db/
2. la base utilisateur   %LOCALAPPDATA%\NaviXav\aircraft_db\
```

Un dossier `aircraft/<constructeur>/<famille>/` déposé dans la seconde ajoute
une famille. **À identifiant égal, la seconde l'emporte** : corriger un avion
livré ne demande pas de modifier la base livrée, qu'une mise à jour de NaviXav
écraserait. L'appareil détecté porte alors `user_supplied`, que l'interface
affiche.

Rien d'autre n'est nécessaire : ni recompilation, ni version de NaviXav, ni
enregistrement. Le validateur s'exécute sur n'importe quelle racine :

```text
python aircraft_db/tools/validate.py "%LOCALAPPDATA%\NaviXav\aircraft_db"
```

---

## Le vocabulaire des propriétés

`schema/properties.json` liste **toutes** les propriétés qu'une procédure a le
droit d'observer. Le validateur rejette toute référence à une propriété absente
de cette liste.

C'est la pièce maîtresse du format. Une procédure écrit :

```json
{ "property": "configuration.parking_brake", "is": true }
```

Elle n'écrit **jamais** `BRAKE PARKING POSITION`, ni `L:S_MIP_PARKING_BRAKE`.
La correspondance entre une propriété et sa source réelle appartient à
`mapping.json`, et une même procédure fonctionne donc sur Asobo, FlyByWire,
Fenix ou iniBuilds sans être modifiée.

Chaque propriété déclare le champ Python qui l'alimente. `tests/test_aircraft_db.py`
vérifie que ces champs existent toujours dans `navixav.live.base` : renommer un
attribut du moteur sans mettre le vocabulaire à jour casse la suite de tests,
ce qui est exactement le comportement voulu.

---

## Les trois modes d'étape

| Mode | Sens | Comportement du moteur |
| --- | --- | --- |
| `auto` | Vérifiable depuis le simulateur | Évalue `check`, coche seul |
| `manual` | Le pilote confirme | Attend un clic |
| `info` | Rappel, rien à faire | Affiché, jamais bloquant |

Une étape `auto` **doit** porter un `check`. Une étape `manual` ou `info` ne
doit pas en porter.

### Règle de l'inconnu

Une propriété vaut `null` quand l'appareil ne la publie pas. Une étape `auto`
dont le `check` porte sur une propriété `null` reste **non vérifiée** : elle
n'est jamais déclarée fausse, et l'interface la propose en confirmation
manuelle. Un avion muet dégrade la base en checklist manuelle ; il ne produit
jamais d'alarme injustifiée.

---

## Les conditions

Une condition est un objet. Cinq formes de comparaison :

```json
{ "property": "configuration.parking_brake", "is": true }
{ "property": "configuration.flaps_handle_index", "at_least": 1 }
{ "property": "state.indicated_airspeed_kt", "at_most": 110 }
{ "property": "configuration.flaps_angle_deg", "between": [9, 11] }
{ "property": "configuration.flaps_handle_index", "one_of": [1, 2] }
```

Trois combinateurs :

```json
{ "all_of": [ ... ] }
{ "any_of": [ ... ] }
{ "not": { ... } }
```

Un combinateur propage l'inconnu : `all_of` est inconnu si une branche est
inconnue et qu'aucune n'est fausse ; `any_of` est inconnu si une branche est
inconnue et qu'aucune n'est vraie.

---

## Langue

Les libellés d'étape (`title`, `expected`) sont en **anglais**, dans la
notation du poste de pilotage, et ne sont pas traduits. C'est la convention
réelle : une checklist se lit en anglais quelle que soit la langue du pilote,
et `GEAR DOWN` traduit devient une source d'erreur, pas une aide.

Ce choix suit le précédent du journal des versions : le contenu reste en
anglais, le cadre suit la langue de l'interface. Les intitulés de phase, les
compteurs et les messages du moteur passent par `i18n.js` et sont traduits dans
les huit langues.

Le champ facultatif `note` accepte un objet localisé lorsqu'une explication
pédagogique se justifie :

```json
"note": { "en": "...", "fr": "..." }
```

---

## `metadata.json`

Identité et détection.

```json
{
  "id": "cessna/c172",
  "manufacturer": "Cessna",
  "family": "C172",
  "model": "172S Skyhawk SP",
  "icao_type": "C172",
  "category": "single_piston",
  "engine_count": 1,
  "propulsion": "piston",
  "crew": 1,
  "certification": "FAR 23",
  "match": {
    "title_contains": ["c172", "cessna 172", "skyhawk"],
    "priority": 10
  }
}
```

`maturity` est obligatoire et vaut :

| Valeur | Sens |
| --- | --- |
| `authored` | Procédures écrites depuis le manuel de l'appareil |
| `draft` | Canevas de classe : juste pour le type, pas pour le modèle |

Un pilote a le droit de savoir ce qu'il lit, donc l'information voyage jusqu'à
l'interface. Un canevas ne déclare **aucune** limitation : une V-speed fausse
est pire qu'une V-speed absente, et un test l'impose.

`match.title_contains` est comparé au titre MSFS de l'appareil, en minuscules.
`priority` départage les familles qui matchent toutes les deux : la plus haute
gagne. Une variante plus précise se déclare dans `mapping.json`.

---

## `systems.json`

Déclare ce que l'avion possède. Les noms viennent de la liste `systems` de
`properties.json`.

```json
{ "systems": { "flaps": true, "retractable_gear": false, "autopilot": true } }
```

**Préséance.** La base *déclare*, le simulateur *confirme*. Un système déclaré
absent n'est jamais surveillé, même si le simulateur publie la propriété — un
C172 à train fixe ne doit jamais déclencher d'alerte de train. Un système
déclaré présent mais muet suit la règle de l'inconnu.

Une étape peut se conditionner à un système :

```json
"requires_system": "autopilot"
```

L'étape disparaît de la checklist sur les variantes qui ne l'ont pas.

---

## `procedures.json`

```json
{
  "procedures": [
    {
      "id": "before_takeoff",
      "phase": "before_takeoff",
      "kind": "normal",
      "title": "BEFORE TAKEOFF",
      "steps": [
        {
          "id": "parking_brake",
          "title": "PARKING BRAKE",
          "expected": "SET",
          "mode": "auto",
          "check": { "property": "configuration.parking_brake", "is": true }
        }
      ]
    }
  ]
}
```

`phase` relie la procédure au suivi de vol et pilote le passage automatique
d'une procédure à la suivante. Phases reconnues :

```text
cold_and_dark   preflight       before_start    start
after_start     taxi            before_takeoff  takeoff
after_takeoff   climb           cruise          descent
approach        landing         after_landing   shutdown
```

`kind` vaut `normal` en V1. `abnormal` et `emergency` sont réservés pour la V2
et acceptés dès maintenant par le validateur : ce sont les trois onglets du
module *Procedures*, donc un filtre sur ce champ et rien de plus.

Une étape porte un `group` facultatif. C'est une respiration visuelle dans une
longue checklist — le moteur insère un blanc au changement de groupe, sans
autre effet : ni progression séparée, ni ordre imposé. `before_takeoff` du C172
sépare ainsi `runup`, `configuration` et `line_up`.

---

## `limitations.json`

Vitesses, masses, moteur. Chaque bloc porte sa source.

```json
{
  "source": "Cessna 172S POH, section 2",
  "speeds": { "vne": { "value": 163, "unit": "kt", "label": "Never exceed" } }
}
```

---

## `mapping.json`

La seule pièce qui parle du monde réel. Elle décrit, **par variante**, où
trouver une propriété quand la source par défaut ne convient pas.

```json
{
  "variants": [
    {
      "id": "asobo",
      "label": "Asobo / Microsoft",
      "match": { "title_contains": ["c172"] },
      "systems": {},
      "overrides": {}
    }
  ]
}
```

### Reconnaître une variante

Un bloc `match` porte deux disjonctions. Au moins un motif de `title_contains`
doit apparaître dans le titre, **et**, si `title_also_contains` est présente, au
moins un motif de cette seconde liste aussi. C'est ce « et » qui sépare une
variante précise d'une famille générique :

```json
{ "title_contains": ["c172", "skyhawk"], "title_also_contains": ["g1000", "nxi"] }
```

**L'ordre des variantes compte** : la première reconnue est retenue, donc les
variantes précises se placent avant la générique. Si aucune ne reconnaît le
titre, `default_variant` sert de repli.

Entre deux *familles* qui reconnaissent le même titre, le départage est
différent : `match.priority` d'abord, puis la longueur du motif reconnu —
`cessna 172` l'emporte sur `c172` — puis l'identifiant, pour qu'une même base
donne toujours le même résultat.

### Sources des propriétés

`overrides` est vide quand l'appareil publie les variables standard, ce qui est
le cas général. Un addon qui expose son état par LVar déclare :

```json
"overrides": {
  "configuration.parking_brake": { "lvar": "S_MIP_PARKING_BRAKE", "as": "boolean" },
  "configuration.flaps_handle_index": { "lvar": "S_FC_FLAPS", "as": "integer", "clamp": [0, 4] },
  "configuration.spoilers_armed": { "lvar": "A_FC_SPEEDBRAKE", "as": "boolean", "below": 0.5 },
  "configuration.spoilers_handle_pct": {
    "lvar": "A_FC_SPEEDBRAKE", "as": "number", "offset": -1.0, "scale": 50.0, "clamp": [0, 100]
  }
}
```

Une LVar est toujours lue comme un nombre. `as` dit comment la ramener au type
de la propriété, et doit s'accorder avec lui — le validateur refuse un `as`
numérique sur une propriété booléenne.

| `as` | Conversion | Clés admises |
| --- | --- | --- |
| `boolean` | `below` : vrai si la valeur est inférieure au seuil. `above` : supérieure. Sans seuil, vrai si la valeur est non nulle. | `below` **ou** `above` |
| `number`, `integer` | `offset` ajouté, puis `scale` multiplié, puis `clamp`. `integer` arrondit. | `offset`, `scale`, `clamp` |

Les deux jeux de clés s'excluent : un seuil n'a pas de sens sur un nombre, une
mise à l'échelle n'en a pas sur un booléen.

L'exemple ci-dessus est le cas Fenix **au complet**, celui que
[`navixav/live/simconnect.py`](../../navixav/live/simconnect.py) porte
aujourd'hui en dur : `A_FC_SPEEDBRAKE` vaut moins de 0,5 quand les aérofreins
sont armés, et se convertit sinon en pourcentage par `(v − 1) × 50`. Le
remplacer par ces données est l'objectif du lot « mapping dynamique » ;
`aircraft/airbus/a320/mapping.json` en est déjà la spécification.

**Le mapping n'est pas encore lu par le moteur.** Le format est figé et validé,
son exécution appartient au lot suivant.

---

## Valider

```text
python aircraft_db/tools/validate.py
```

Sans dépendance, sans réseau. Sortie non nulle au premier défaut. Le même
validateur tourne dans `tests/test_aircraft_db.py`.

---

## Mesurer la couverture

```text
python aircraft_db/tools/coverage.py cessna/c172 --source ~/clones/checklists/c172.json
```

Rapproche un avion de la base d'une checklist publiée et liste ce qui manque.
Deux formats sont lus : le JSON de `aircraft-multi-crew-checklists` (`.json`)
et le XML de FlightGear (`.xml`).

L'outil **compare, il ne traduit pas.** Il n'écrit aucun fichier, et il refuse
une source située dans `aircraft_db/`.

C'est délibéré. Les checklists publiées sont sous GPL, la base est sous
Apache-2.0 : elles se lisent depuis leur propre clone et ne sont jamais
versionnées ici. Surtout, aucune d'elles ne contient ce qui coûte le travail —
les prédicats `check`, les `systems`, les phases. `aircraft-multi-crew-checklists`
n'a que du texte (`checkpoint` + `value`), et les `<condition>` de FlightGear
visent son propre arbre de propriétés, sans correspondance avec le vocabulaire
d'ici. Un importeur mécanique ne rapatrierait donc que des libellés, au prix
d'un dérivé et d'un format amont à suivre.

Le rapprochement se fait sur la ressemblance du texte, pas sur le sens : une
étape signalée absente se lit, puis s'écrit depuis le POH.

`--strict` renvoie 1 s'il manque au moins une étape, pour un usage en
intégration continue.
