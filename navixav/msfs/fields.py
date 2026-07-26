"""Champs Facilities de SimConnect, validés par sondage contre MSFS 2024.

Chaque entrée associe un nom de champ à son type binaire. Les tailles ont été
mesurées sur les réponses réelles du simulateur : le SDK installé ne fournit
aucune documentation locale, et supposer un type produirait des valeurs
silencieusement fausses.

Unités observées, invariables d'un champ à l'autre :

    distances et altitudes   mètres
    angles                   degrés
    fréquences               hertz
    suffixes de procédure    code ASCII (48 = « 0 », soit aucun suffixe)

Les positions du sol (`BIAS_X`, `BIAS_Z`) sont déjà exprimées en mètres
relatifs au point de référence de l'aéroport : c'est le repère qu'utilise le
plan de terrain, aucune projection n'est nécessaire.
"""

from __future__ import annotations

from dataclasses import dataclass

# Types de blocs, alignés sur SIMCONNECT_FACILITY_DATA_TYPE.
TYPE_AIRPORT = 0
TYPE_RUNWAY = 1
TYPE_START = 2
TYPE_FREQUENCY = 3
TYPE_HELIPAD = 4
TYPE_APPROACH = 5
TYPE_APPROACH_TRANSITION = 6
TYPE_APPROACH_LEG = 7
TYPE_FINAL_APPROACH_LEG = 8
TYPE_MISSED_APPROACH_LEG = 9
TYPE_DEPARTURE = 10
TYPE_ARRIVAL = 11
TYPE_RUNWAY_TRANSITION = 12
TYPE_ENROUTE_TRANSITION = 13
TYPE_TAXI_POINT = 14
TYPE_TAXI_PARKING = 15
TYPE_TAXI_PATH = 16
TYPE_TAXI_NAME = 17
TYPE_VOR = 19
TYPE_NDB = 20
TYPE_WAYPOINT = 21
TYPE_ROUTE = 22

TYPE_NAMES = {
    TYPE_AIRPORT: "AIRPORT",
    TYPE_RUNWAY: "RUNWAY",
    TYPE_START: "START",
    TYPE_FREQUENCY: "FREQUENCY",
    TYPE_HELIPAD: "HELIPAD",
    TYPE_APPROACH: "APPROACH",
    TYPE_APPROACH_TRANSITION: "APPROACH_TRANSITION",
    TYPE_APPROACH_LEG: "APPROACH_LEG",
    TYPE_FINAL_APPROACH_LEG: "FINAL_APPROACH_LEG",
    TYPE_MISSED_APPROACH_LEG: "MISSED_APPROACH_LEG",
    TYPE_DEPARTURE: "DEPARTURE",
    TYPE_ARRIVAL: "ARRIVAL",
    TYPE_RUNWAY_TRANSITION: "RUNWAY_TRANSITION",
    TYPE_ENROUTE_TRANSITION: "ENROUTE_TRANSITION",
    TYPE_TAXI_POINT: "TAXI_POINT",
    TYPE_TAXI_PARKING: "TAXI_PARKING",
    TYPE_TAXI_PATH: "TAXI_PATH",
    TYPE_TAXI_NAME: "TAXI_NAME",
    TYPE_VOR: "VOR",
    TYPE_NDB: "NDB",
    TYPE_WAYPOINT: "WAYPOINT",
    TYPE_ROUTE: "ROUTE",
}


@dataclass(frozen=True)
class Field:
    """Un champ d'une définition, avec son décodage."""

    name: str
    kind: str  # "f64" | "f32" | "i32" | "str8" | "str32" | "str64"

    @property
    def size(self) -> int:
        return {
            "f64": 8, "f32": 4, "i32": 4,
            "str8": 8, "str32": 32, "str64": 64,
        }[self.kind]


def f64(name: str) -> Field:
    return Field(name, "f64")


def f32(name: str) -> Field:
    return Field(name, "f32")


def i32(name: str) -> Field:
    return Field(name, "i32")


def s8(name: str) -> Field:
    return Field(name, "str8")


def s64(name: str) -> Field:
    return Field(name, "str64")


# --------------------------------------------------------------------------- #
# Définitions par type de bloc
# --------------------------------------------------------------------------- #

AIRPORT_FIELDS = (
    f64("LATITUDE"), f64("LONGITUDE"), f64("ALTITUDE"),
    s64("NAME64"),
    f32("TRANSITION_ALTITUDE"), f32("TRANSITION_LEVEL"),
    i32("N_RUNWAYS"), i32("N_DEPARTURES"), i32("N_ARRIVALS"),
    i32("N_APPROACHES"), i32("N_FREQUENCIES"),
    i32("N_TAXI_POINTS"), i32("N_TAXI_PARKINGS"), i32("N_TAXI_PATHS"),
)

RUNWAY_FIELDS = (
    f64("LATITUDE"), f64("LONGITUDE"), f64("ALTITUDE"),
    f32("HEADING"), f32("LENGTH"), f32("WIDTH"),
    i32("SURFACE"),
    i32("PRIMARY_NUMBER"), i32("PRIMARY_DESIGNATOR"), s8("PRIMARY_ILS_ICAO"),
    i32("SECONDARY_NUMBER"), i32("SECONDARY_DESIGNATOR"),
    s8("SECONDARY_ILS_ICAO"),
)

APPROACH_FIELDS = (
    i32("TYPE"), i32("SUFFIX"),
    i32("RUNWAY_NUMBER"), i32("RUNWAY_DESIGNATOR"),
    s8("FAF_ICAO"), f32("FAF_ALTITUDE"), f32("MISSED_ALTITUDE"),
    i32("N_TRANSITIONS"), i32("N_FINAL_APPROACH_LEGS"),
    i32("N_MISSED_APPROACH_LEGS"),
)

PROCEDURE_FIELDS = (  # DEPARTURE et ARRIVAL partagent la même forme
    s8("NAME"),
    i32("N_RUNWAY_TRANSITIONS"), i32("N_ENROUTE_TRANSITIONS"),
    i32("N_APPROACH_LEGS"),
)

LEG_FIELDS = (
    i32("TYPE"),
    s8("FIX_ICAO"), s8("FIX_REGION"), i32("FIX_TYPE"),
    i32("FLY_OVER"), i32("TURN_DIRECTION"),
    f32("COURSE"), f32("DISTANCE_MINUTE"), f32("TRUE_DEGREE"),
    f32("ALTITUDE1"), f32("ALTITUDE2"), f32("SPEED_LIMIT"),
    f32("VERTICAL_ANGLE"), f32("THETA"), f32("RHO"),
    i32("IS_IAF"), i32("IS_IF"), i32("IS_FAF"), i32("IS_MAP"),
    f32("REQUIRED_NAVIGATION_PERFORMANCE"),
)

# Les trois sortes de transition n'ont pas la même forme, contrairement à ce
# qu'on pourrait supposer : une transition de piste s'identifie par la piste
# elle-même et ne porte ni nom ni type.
APPROACH_TRANSITION_FIELDS = (
    i32("TYPE"), s8("NAME"),
    s8("IAF_ICAO"), s8("IAF_REGION"), f32("IAF_ALTITUDE"),
    i32("N_APPROACH_LEGS"),
)

RUNWAY_TRANSITION_FIELDS = (
    i32("RUNWAY_NUMBER"), i32("RUNWAY_DESIGNATOR"), i32("N_APPROACH_LEGS"),
)

ENROUTE_TRANSITION_FIELDS = (
    s8("NAME"), i32("N_APPROACH_LEGS"),
)

FREQUENCY_FIELDS = (
    i32("TYPE"), i32("FREQUENCY"), s64("NAME"),
)

TAXI_POINT_FIELDS = (
    i32("TYPE"), i32("ORIENTATION"), f32("BIAS_X"), f32("BIAS_Z"),
)

TAXI_PARKING_FIELDS = (
    i32("TYPE"), i32("NAME"), i32("SUFFIX"), i32("NUMBER"),
    f32("HEADING"), f32("RADIUS"), f32("BIAS_X"), f32("BIAS_Z"),
)

TAXI_PATH_FIELDS = (
    i32("TYPE"), f32("WIDTH"), i32("START"), i32("END"),
    i32("NAME_INDEX"), i32("RUNWAY_NUMBER"), i32("RUNWAY_DESIGNATOR"),
)

# --------------------------------------------------------------------------- #
# Installations hors aéroport
#
# Un ILS se lit comme un VOR : c'est la même famille d'installation côté
# simulateur, distinguée par HAS_GLIDE_SLOPE et par son nom (« ILS RWY 02 »).
# Les champs LATITUDE/LONGITUDE y sont refusés ; seule la position de
# l'alignement de descente est exposée.
# --------------------------------------------------------------------------- #

NAVAID_FIELDS = (
    i32("FREQUENCY"), i32("TYPE"), s64("NAME"),
    i32("IS_DME"), i32("HAS_GLIDE_SLOPE"),
    f32("LOCALIZER"), f32("GLIDE_SLOPE"),
    f64("GS_LATITUDE"), f64("GS_LONGITUDE"),
)

WAYPOINT_FIELDS = (
    f64("LATITUDE"), f64("LONGITUDE"), i32("TYPE"), i32("N_ROUTES"),
)

ROUTE_FIELDS = (
    Field("NAME", "str32"), i32("TYPE"),
    s8("PREV_ICAO"), s8("PREV_REGION"),
    s8("NEXT_ICAO"), s8("NEXT_REGION"),
)


# --------------------------------------------------------------------------- #
# Correspondances de codes
# --------------------------------------------------------------------------- #

# Suffixe de piste : SIMCONNECT_RUNWAY_DESIGNATOR.
RUNWAY_DESIGNATORS = {0: "", 1: "L", 2: "R", 3: "C", 4: "W", 5: "A", 6: "B"}

# Type d'approche : SIMCONNECT_APPROACH_TYPE.
APPROACH_TYPES = {
    0: "NONE", 1: "GPS", 2: "VOR", 3: "NDB", 4: "ILS", 5: "LOC",
    6: "SDF", 7: "LDA", 8: "VORDME", 9: "NDBDME", 10: "RNAV", 11: "BACKCOURSE",
}

# Surfaces de piste les plus courantes.
SURFACES = {
    0: "béton", 1: "herbe", 2: "eau", 3: "herbe (bumpy)", 4: "asphalte",
    5: "béton court", 6: "terre", 7: "gravier", 8: "gravier (huilé)",
    9: "acier", 10: "sable", 11: "terre battue", 12: "planches", 13: "brique",
    14: "macadam", 15: "planches", 16: "tarmac", 17: "neige", 18: "glace",
    19: "urbain", 20: "forêt", 21: "friche", 22: "corail",
}


def designator(code: int) -> str:
    return RUNWAY_DESIGNATORS.get(code, "")


def runway_name(number: int, designator_code: int) -> str:
    """« 2 » + code L -> « 02L »."""
    return f"{number:02d}{designator(designator_code)}"


def suffix_letter(code: int) -> str:
    """Le suffixe arrive en code ASCII ; « 0 » signifie aucun suffixe."""
    if not code or code == ord("0"):
        return ""
    try:
        letter = chr(code)
    except ValueError:
        return ""
    return letter if letter.isalpha() else ""
