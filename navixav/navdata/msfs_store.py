"""Base de navigation propre à NaviXav, alimentée depuis MSFS.

Le simulateur ne se laisse interroger que terrain par terrain, et seulement
lorsqu'il tourne. Plutôt qu'un import massif des 84 000 aéroports — des heures
de requêtes pour une base qui vieillit aussitôt — on récupère à la demande les
deux ou trois terrains d'un vol, en 0,4 s chacun, et on les conserve ici. La
base reste ensuite consultable simulateur fermé.
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from navixav.paths import user_data_path

DEFAULT_STORE = user_data_path("navixav.sqlite")
SCHEMA_VERSION = 1

EARTH_RADIUS_M = 6378137.0
METRES_TO_FEET = 3.280839895

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS airport (
    icao TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    altitude_ft REAL,
    transition_altitude_ft INTEGER,
    transition_level_ft INTEGER,
    source TEXT NOT NULL DEFAULT 'MSFS',
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runway (
    icao TEXT NOT NULL REFERENCES airport(icao) ON DELETE CASCADE,
    name TEXT NOT NULL,
    heading_true REAL NOT NULL,
    length_ft REAL NOT NULL,
    width_ft REAL,
    surface TEXT,
    ils_ident TEXT,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    PRIMARY KEY (icao, name)
);

CREATE TABLE IF NOT EXISTS procedure (
    id INTEGER PRIMARY KEY,
    icao TEXT NOT NULL REFERENCES airport(icao) ON DELETE CASCADE,
    kind TEXT NOT NULL,              -- SID | STAR | APPROACH
    ident TEXT NOT NULL,
    proc_type TEXT,
    suffix TEXT,
    runway_name TEXT,
    runways TEXT NOT NULL DEFAULT '[]',
    missed_altitude_ft INTEGER,
    requires_rnp INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS procedure_by_airport ON procedure(icao, kind);

CREATE TABLE IF NOT EXISTS transition (
    id INTEGER PRIMARY KEY,
    procedure_id INTEGER NOT NULL REFERENCES procedure(id) ON DELETE CASCADE,
    ident TEXT NOT NULL,
    kind TEXT NOT NULL               -- APPROACH | RUNWAY | ENROUTE
);
CREATE INDEX IF NOT EXISTS transition_by_procedure ON transition(procedure_id);

CREATE TABLE IF NOT EXISTS leg (
    id INTEGER PRIMARY KEY,
    procedure_id INTEGER REFERENCES procedure(id) ON DELETE CASCADE,
    transition_id INTEGER REFERENCES transition(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    is_missed INTEGER NOT NULL DEFAULT 0,
    leg_type INTEGER,
    fix_ident TEXT,
    fix_region TEXT,
    course REAL,
    distance_nm REAL,
    altitude1_ft INTEGER,
    altitude2_ft INTEGER,
    speed_limit_kt INTEGER,
    fly_over INTEGER NOT NULL DEFAULT 0,
    is_iaf INTEGER NOT NULL DEFAULT 0,
    is_faf INTEGER NOT NULL DEFAULT 0,
    rnp REAL
);
CREATE INDEX IF NOT EXISTS leg_by_procedure ON leg(procedure_id, sequence);
CREATE INDEX IF NOT EXISTS leg_by_transition ON leg(transition_id, sequence);

CREATE TABLE IF NOT EXISTS taxi_point (
    icao TEXT NOT NULL REFERENCES airport(icao) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    PRIMARY KEY (icao, idx)
);

CREATE TABLE IF NOT EXISTS taxi_path (
    icao TEXT NOT NULL REFERENCES airport(icao) ON DELETE CASCADE,
    start_idx INTEGER NOT NULL,
    end_idx INTEGER NOT NULL,
    width_m REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS taxi_path_by_airport ON taxi_path(icao);

CREATE TABLE IF NOT EXISTS parking (
    icao TEXT NOT NULL REFERENCES airport(icao) ON DELETE CASCADE,
    label TEXT NOT NULL,
    kind TEXT,
    x REAL NOT NULL,
    y REAL NOT NULL,
    radius_m REAL NOT NULL,
    heading REAL
);
CREATE INDEX IF NOT EXISTS parking_by_airport ON parking(icao);

CREATE TABLE IF NOT EXISTS navaid (
    ident TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT '',
    frequency_mhz REAL,
    name TEXT NOT NULL DEFAULT '',
    has_glide_slope INTEGER NOT NULL DEFAULT 0,
    has_dme INTEGER NOT NULL DEFAULT 0,
    localizer_course REAL,
    glide_slope REAL,
    lat REAL,
    lon REAL,
    PRIMARY KEY (ident, region)
);

CREATE TABLE IF NOT EXISTS waypoint (
    ident TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT '',
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    PRIMARY KEY (ident, region)
);

CREATE TABLE IF NOT EXISTS airway_segment (
    airway TEXT NOT NULL,
    from_ident TEXT NOT NULL,
    to_ident TEXT,
    to_region TEXT
);
CREATE INDEX IF NOT EXISTS airway_by_name ON airway_segment(airway);
CREATE INDEX IF NOT EXISTS airway_by_fix ON airway_segment(from_ident);

-- Repères cherchés sans succès : évite de réinterroger le simulateur en boucle
-- pour un identifiant qu'il ne connaît pas.
CREATE TABLE IF NOT EXISTS lookup_miss (
    ident TEXT NOT NULL,
    kind TEXT NOT NULL,
    PRIMARY KEY (ident, kind)
);
"""

# Noms de postes de stationnement : SIMCONNECT_AIRPORT_PARKING_NAME.
PARKING_NAMES = {
    0: "", 1: "parking", 2: "N", 3: "NE", 4: "E", 5: "SE", 6: "S",
    7: "SW", 8: "W", 9: "NW", 10: "porte", 11: "dock", 12: "porte A",
    13: "porte B", 14: "porte C", 15: "porte D", 16: "porte E", 17: "porte F",
    18: "porte G", 19: "porte H", 20: "porte I", 21: "porte J", 22: "porte K",
    23: "porte L", 24: "porte M", 25: "porte N", 26: "porte O", 27: "porte P",
    28: "porte Q", 29: "porte R", 30: "porte S", 31: "porte T", 32: "porte U",
    33: "porte V", 34: "porte W", 35: "porte X", 36: "porte Y", 37: "porte Z",
}

# Types de stationnement : SIMCONNECT_AIRPORT_PARKING_TYPE.
PARKING_TYPES = {
    0: None, 1: "rampe GA", 2: "rampe GA", 3: "rampe GA", 4: "rampe cargo",
    5: "rampe militaire", 6: "porte petite", 7: "porte moyenne",
    8: "porte grande", 9: "dock", 10: "carburant", 11: "dégivrage",
}


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Ouvre la base NaviXav, en la créant au besoin."""
    target = Path(path) if path else DEFAULT_STORE
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    connection.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    connection.commit()
    return connection


def store_airport(connection: sqlite3.Connection, extracted: dict[str, Any]) -> None:
    """Écrit un aéroport extrait de MSFS, en remplaçant toute version antérieure."""
    icao = extracted["icao"]
    with connection:
        connection.execute("DELETE FROM airport WHERE icao = ?", (icao,))
        connection.execute(
            """
            INSERT INTO airport (icao, name, lat, lon, altitude_ft,
                                 transition_altitude_ft, transition_level_ft,
                                 source, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'MSFS', ?)
            """,
            (
                icao,
                extracted.get("name", ""),
                extracted["lat"],
                extracted["lon"],
                extracted.get("altitude_ft"),
                extracted.get("transition_altitude_ft"),
                extracted.get("transition_level_ft"),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        _store_runways(connection, extracted)
        _store_procedures(connection, extracted)
        _store_ground(connection, extracted)


# --------------------------------------------------------------------------- #
# Écriture
# --------------------------------------------------------------------------- #


def _store_runways(connection: sqlite3.Connection, extracted: dict[str, Any]) -> None:
    icao = extracted["icao"]
    for runway in extracted["runways"]:
        # MSFS donne le centre de la piste : les deux seuils s'en déduisent en
        # remontant d'une demi-longueur de part et d'autre de l'axe.
        half_m = (runway["length_ft"] / METRES_TO_FEET) / 2
        heading = runway["heading_true"]
        primary = _offset(runway["lat"], runway["lon"], heading + 180, half_m)
        secondary = _offset(runway["lat"], runway["lon"], heading, half_m)

        for name, end_heading, position, ils in (
            (runway["primary"], heading, primary, runway.get("primary_ils")),
            (runway["secondary"], (heading + 180) % 360, secondary, runway.get("secondary_ils")),
        ):
            connection.execute(
                """
                INSERT OR REPLACE INTO runway
                    (icao, name, heading_true, length_ft, width_ft, surface,
                     ils_ident, lat, lon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    icao, name, end_heading, runway["length_ft"],
                    runway.get("width_ft"), runway.get("surface"), ils,
                    position[0], position[1],
                ),
            )


def _store_procedures(connection: sqlite3.Connection, extracted: dict[str, Any]) -> None:
    icao = extracted["icao"]

    for kind, entries in (("SID", extracted["departures"]), ("STAR", extracted["arrivals"])):
        for procedure in entries:
            trunk, branches = _split_trunk(procedure, kind)
            runways = sorted({t["ident"] for t in procedure["runway_transitions"]})
            procedure_id = _insert_procedure(
                connection, icao, kind, procedure["ident"],
                proc_type=None, suffix=None, runway_name=None,
                runways=runways, missed_altitude_ft=None,
                requires_rnp=_needs_rnp(trunk),
            )
            _insert_legs(connection, procedure_id, None, trunk)
            for ident, legs in branches:
                transition_id = _insert_transition(
                    connection, procedure_id, ident, "RUNWAY"
                )
                _insert_legs(connection, procedure_id, transition_id, legs)
            for transition in procedure["enroute_transitions"]:
                transition_id = _insert_transition(
                    connection, procedure_id, transition["ident"], "ENROUTE"
                )
                _insert_legs(connection, procedure_id, transition_id, transition["legs"])

    for approach in extracted["approaches"]:
        legs = approach.get("legs", []) + [
            leg for transition in approach["transitions"] for leg in transition["legs"]
        ]
        procedure_id = _insert_procedure(
            connection, icao, "APPROACH", approach["runway"],
            proc_type=approach["type"], suffix=approach["suffix"],
            runway_name=approach["runway"], runways=[approach["runway"]],
            missed_altitude_ft=approach.get("missed_altitude_ft"),
            requires_rnp=_needs_rnp(legs),
        )
        _insert_legs(connection, procedure_id, None, approach.get("legs", []))
        _insert_legs(
            connection, procedure_id, None, approach.get("missed_legs", []), missed=True
        )
        for transition in approach["transitions"]:
            transition_id = _insert_transition(
                connection, procedure_id, transition["ident"], "APPROACH"
            )
            _insert_legs(connection, procedure_id, transition_id, transition["legs"])


def _store_ground(connection: sqlite3.Connection, extracted: dict[str, Any]) -> None:
    icao = extracted["icao"]
    connection.executemany(
        "INSERT OR REPLACE INTO taxi_point (icao, idx, x, y) VALUES (?, ?, ?, ?)",
        [(icao, index, point["x"], point["y"])
         for index, point in enumerate(extracted["taxi_points"])],
    )
    connection.executemany(
        "INSERT INTO taxi_path (icao, start_idx, end_idx, width_m) VALUES (?, ?, ?, ?)",
        [(icao, path["start"], path["end"], path["width_m"])
         for path in extracted["taxi_paths"]],
    )
    connection.executemany(
        """INSERT INTO parking (icao, label, kind, x, y, radius_m, heading)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                icao,
                _parking_label(parking),
                PARKING_TYPES.get(parking["type"]),
                parking["x"], parking["y"],
                parking["radius_m"], parking["heading"],
            )
            for parking in extracted["taxi_parkings"]
        ],
    )


def _insert_procedure(
    connection: sqlite3.Connection, icao: str, kind: str, ident: str, *,
    proc_type: str | None, suffix: str | None, runway_name: str | None,
    runways: list[str], missed_altitude_ft: int | None, requires_rnp: bool,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO procedure (icao, kind, ident, proc_type, suffix,
                               runway_name, runways, missed_altitude_ft,
                               requires_rnp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (icao, kind, ident, proc_type, suffix, runway_name,
         json.dumps(runways), missed_altitude_ft, int(requires_rnp)),
    )
    return int(cursor.lastrowid)


def _insert_transition(
    connection: sqlite3.Connection, procedure_id: int, ident: str, kind: str
) -> int:
    cursor = connection.execute(
        "INSERT INTO transition (procedure_id, ident, kind) VALUES (?, ?, ?)",
        (procedure_id, ident, kind),
    )
    return int(cursor.lastrowid)


def _insert_legs(
    connection: sqlite3.Connection,
    procedure_id: int,
    transition_id: int | None,
    legs: Iterable[dict[str, Any]],
    missed: bool = False,
) -> None:
    connection.executemany(
        """
        INSERT INTO leg (procedure_id, transition_id, sequence, is_missed,
                         leg_type, fix_ident, fix_region, course, distance_nm,
                         altitude1_ft, altitude2_ft, speed_limit_kt, fly_over,
                         is_iaf, is_faf, rnp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                procedure_id, transition_id, index, int(missed),
                leg.get("type"), leg.get("fix"), leg.get("region"),
                leg.get("course"), leg.get("distance_nm"),
                leg.get("altitude1_ft"), leg.get("altitude2_ft"),
                leg.get("speed_limit_kt"), int(leg.get("fly_over", False)),
                int(leg.get("is_iaf", False)), int(leg.get("is_faf", False)),
                leg.get("rnp"),
            )
            for index, leg in enumerate(legs)
        ],
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def store_navaid(connection: sqlite3.Connection, navaid: dict[str, Any]) -> None:
    with connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO navaid
                (ident, region, frequency_mhz, name, has_glide_slope, has_dme,
                 localizer_course, glide_slope, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                navaid["ident"], navaid["region"], navaid["frequency_mhz"],
                navaid["name"], int(navaid["has_glide_slope"]),
                int(navaid["has_dme"]), navaid["localizer_course"],
                navaid["glide_slope"], navaid["lat"], navaid["lon"],
            ),
        )


def store_waypoint(connection: sqlite3.Connection, waypoint: dict[str, Any]) -> None:
    with connection:
        connection.execute(
            "INSERT OR REPLACE INTO waypoint (ident, region, lat, lon) "
            "VALUES (?, ?, ?, ?)",
            (waypoint["ident"], waypoint["region"], waypoint["lat"], waypoint["lon"]),
        )
        connection.execute(
            "DELETE FROM airway_segment WHERE from_ident = ?", (waypoint["ident"],)
        )
        connection.executemany(
            "INSERT INTO airway_segment (airway, from_ident, to_ident, to_region) "
            "VALUES (?, ?, ?, ?)",
            [
                (route["airway"], waypoint["ident"], route["next"], route["next_region"])
                for route in waypoint.get("routes", [])
                if route["airway"]
            ],
        )


def store_miss(connection: sqlite3.Connection, ident: str, kind: str) -> None:
    with connection:
        connection.execute(
            "INSERT OR REPLACE INTO lookup_miss (ident, kind) VALUES (?, ?)",
            (ident.upper(), kind),
        )


def _split_trunk(
    procedure: dict[str, Any], kind: str
) -> tuple[list[dict[str, Any]], list[tuple[str, list[dict[str, Any]]]]]:
    """Sépare le tronc commun d'une procédure de ses branches par piste.

    MSFS ne publie aucun segment au niveau de la procédure : tout est réparti
    dans les transitions de piste. Une SID n'en a qu'une, elle constitue donc
    la procédure entière. Une STAR en a plusieurs, qui partagent un début et
    divergent en finale : le tronc donne le point d'entrée, chaque branche
    conserve sa sortie propre.
    """
    transitions = procedure["runway_transitions"]
    common = procedure.get("legs", [])

    if not transitions:
        return common, []
    if len(transitions) == 1:
        return common + transitions[0]["legs"], [(transitions[0]["ident"], [])]

    sequences = [transition["legs"] for transition in transitions]
    shared = _common_prefix(sequences)
    # Une STAR se lit dans le sens du vol ; le tronc précède les branches.
    trunk = common + shared if kind == "STAR" else common
    offset = len(shared) if kind == "STAR" else 0
    branches = [
        (transition["ident"], transition["legs"][offset:])
        for transition in transitions
    ]
    return trunk, branches


def _common_prefix(
    sequences: list[list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Plus long début partagé par toutes les séquences, comparé par repère."""
    if not sequences:
        return []
    shortest = min(len(sequence) for sequence in sequences)
    length = 0
    while length < shortest:
        fixes = {sequence[length].get("fix") for sequence in sequences}
        if len(fixes) != 1:
            break
        length += 1
    return sequences[0][:length]


def _needs_rnp(legs: Iterable[dict[str, Any]]) -> bool:
    return any((leg.get("rnp") or 0) > 0 for leg in legs)


def _parking_label(parking: dict[str, Any]) -> str:
    name = PARKING_NAMES.get(parking["name_index"], "")
    number = parking.get("number")
    parts = [part for part in (name, str(number) if number else "") if part]
    return " ".join(parts) or "poste"


def _offset(
    latitude: float, longitude: float, bearing_deg: float, distance_m: float
) -> tuple[float, float]:
    """Point situé à `distance_m` dans la direction `bearing_deg`."""
    bearing = math.radians(bearing_deg)
    delta_north = distance_m * math.cos(bearing)
    delta_east = distance_m * math.sin(bearing)
    new_latitude = latitude + math.degrees(delta_north / EARTH_RADIUS_M)
    new_longitude = longitude + math.degrees(
        delta_east / (EARTH_RADIUS_M * math.cos(math.radians(latitude)))
    )
    return (new_latitude, new_longitude)
