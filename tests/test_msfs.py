"""Couche MSFS : décodage des facilities et base NaviXav.

Les tests qui touchent le simulateur sont ignorés s'il ne tourne pas. Ceux qui
portent sur le décodage et la reconstruction s'exécutent toujours.
"""

from __future__ import annotations

import ctypes as ct
import sqlite3
import struct
import time

import pytest

from navixav.msfs import client as client_module
from navixav.msfs import extract
from navixav.msfs import fields as F
from navixav.msfs.client import (
    FacilityDefinition,
    SimConnectClient,
    SimConnectError,
    SimConnectRefused,
    decode,
)
from navixav.navdata import base, msfs_store
from navixav.navdata.base import ProcedureKind


# --------------------------------------------------------------------------- #
# Décodage binaire
# --------------------------------------------------------------------------- #


def test_decode_mixed_types():
    payload = struct.pack("<ddi", 48.5, 7.6, 3)
    values = decode(payload, (F.f64("LAT"), F.f64("LON"), F.i32("N")))
    assert values == {"LAT": 48.5, "LON": 7.6, "N": 3}


def test_decode_trims_fixed_length_strings():
    payload = b"OLN" + b"\x00" * 5
    assert decode(payload, (F.s8("IDENT"),)) == {"IDENT": "OLN"}


def test_decode_rejects_a_short_payload():
    """Un champ refusé raccourcit la charge : mieux vaut échouer que décaler."""
    with pytest.raises(SimConnectError, match="octets"):
        decode(struct.pack("<d", 1.0), (F.f64("A"), F.f64("B")))


def test_decode_rejects_a_long_payload():
    with pytest.raises(SimConnectError):
        decode(struct.pack("<dd", 1.0, 2.0), (F.f64("A"),))


# --------------------------------------------------------------------------- #
# Codes du simulateur
# --------------------------------------------------------------------------- #


def test_runway_name_from_number_and_designator():
    assert F.runway_name(2, 0) == "02"
    assert F.runway_name(32, 2) == "32R"
    assert F.runway_name(14, 1) == "14L"


def test_suffix_is_an_ascii_code():
    """« 0 » signale l'absence de suffixe, pas la lettre zéro."""
    assert F.suffix_letter(ord("0")) == ""
    assert F.suffix_letter(0) == ""
    assert F.suffix_letter(ord("Z")) == "Z"
    assert F.suffix_letter(ord("Y")) == "Y"


def test_facility_types_cover_navaids():
    """Les blocs hors aéroport doivent être nommés, sinon ils sont ignorés."""
    for code in (F.TYPE_VOR, F.TYPE_WAYPOINT, F.TYPE_ROUTE):
        assert code in F.TYPE_NAMES


# --------------------------------------------------------------------------- #
# Refus du simulateur
#
# Un identifiant inconnu est refusé immédiatement : attendre la fin du délai
# figeait la complétion d'un plan plusieurs dizaines de secondes.
# --------------------------------------------------------------------------- #


class _RefusingDll:
    """Simulateur qui refuse toute demande, sans jamais rien envoyer d'autre."""

    def __init__(self, code: int = 7) -> None:
        self.record = client_module._RECV_EXCEPTION()
        self.record.dwSize = ct.sizeof(self.record)
        self.record.dwID = client_module.RECV_ID_EXCEPTION
        self.record.dwException = code
        self._view = ct.cast(ct.byref(self.record), ct.POINTER(client_module._RECV))

    def __getattr__(self, _name):  # AddToFacilityDefinition, RequestFacilityData…
        return lambda *_args: 0

    def SimConnect_GetNextDispatch(self, _handle, pointer_ref, size_ref):
        pointer_ref._obj.contents = self._view.contents
        size_ref._obj.value = self.record.dwSize
        return 0


def _refused_client(code: int = 7) -> SimConnectClient:
    client = object.__new__(SimConnectClient)
    client._dll = _RefusingDll(code)
    client._handle = None
    client._next_id = 1
    client._simvar_definitions = {}
    return client


def test_a_refused_facility_gives_up_without_waiting():
    client = _refused_client()
    definition = FacilityDefinition()
    definition.open("WAYPOINT", F.TYPE_WAYPOINT, (F.f64("LATITUDE"),)).close_all()

    started = time.monotonic()
    with pytest.raises(SimConnectRefused, match="NAME_UNRECOGNIZED"):
        client.request_raw(definition, "INCONNU", timeout_s=20.0)

    assert time.monotonic() - started < 5.0


def test_refused_simvars_give_up_without_waiting():
    client = _refused_client(code=3)

    started = time.monotonic()
    with pytest.raises(SimConnectRefused):
        client.read_simvars((("PLANE LATITUDE", "Degrees"),), timeout_s=20.0)

    assert time.monotonic() - started < 5.0


def test_a_refusal_is_distinguishable_from_a_silence():
    """Un refus renseigne sur la donnée ; un silence ne prouve rien."""
    assert issubclass(SimConnectRefused, SimConnectError)


# --------------------------------------------------------------------------- #
# Définition hiérarchique
# --------------------------------------------------------------------------- #


def test_definition_balances_open_and_close():
    definition = FacilityDefinition()
    definition.open("AIRPORT", F.TYPE_AIRPORT, (F.f64("LATITUDE"),))
    definition.open("RUNWAY", F.TYPE_RUNWAY, (F.f32("LENGTH"),)).close()
    definition.close_all()
    assert definition.tokens == [
        "OPEN AIRPORT", "LATITUDE", "OPEN RUNWAY", "LENGTH",
        "CLOSE RUNWAY", "CLOSE AIRPORT",
    ]


def test_definition_records_a_layout_per_type():
    definition = FacilityDefinition()
    definition.open("AIRPORT", F.TYPE_AIRPORT, (F.f64("LATITUDE"),)).close_all()
    assert definition.layouts[F.TYPE_AIRPORT] == (F.f64("LATITUDE"),)


# --------------------------------------------------------------------------- #
# Reconstruction des procédures
# --------------------------------------------------------------------------- #


def _leg(fix: str | None) -> dict:
    return {"fix": fix, "altitude1_ft": None, "speed_limit_kt": None}


def test_a_sid_is_its_single_runway_transition():
    """MSFS ne publie aucun segment au niveau de la procédure elle-même."""
    procedure = {
        "legs": [],
        "runway_transitions": [
            {"ident": "20", "legs": [_leg("PO201"), _leg("AGOPA")]}
        ],
        "enroute_transitions": [],
    }
    trunk, branches = msfs_store._split_trunk(procedure, "SID")
    assert [leg["fix"] for leg in trunk] == ["PO201", "AGOPA"]
    assert branches == [("20", [])]


def test_a_star_keeps_its_diverging_branches():
    """Trois transitions de piste partagent un début et divergent en finale."""
    procedure = {
        "legs": [],
        "runway_transitions": [
            {"ident": "02", "legs": [_leg("AMB"), _leg("ODILO"), _leg("FI02")]},
            {"ident": "06", "legs": [_leg("AMB"), _leg("ODILO"), _leg("FI06")]},
            {"ident": "07", "legs": [_leg("AMB"), _leg("ODILO"), _leg("FI07")]},
        ],
        "enroute_transitions": [],
    }
    trunk, branches = msfs_store._split_trunk(procedure, "STAR")
    assert [leg["fix"] for leg in trunk] == ["AMB", "ODILO"]
    assert {ident for ident, _ in branches} == {"02", "06", "07"}
    assert [leg["fix"] for _ident, legs in branches for leg in legs] == [
        "FI02", "FI06", "FI07"
    ]


def test_common_prefix_stops_at_the_first_difference():
    sequences = [
        [_leg("A"), _leg("B"), _leg("C")],
        [_leg("A"), _leg("X")],
    ]
    assert [leg["fix"] for leg in msfs_store._common_prefix(sequences)] == ["A"]


# --------------------------------------------------------------------------- #
# Base NaviXav
# --------------------------------------------------------------------------- #


def test_store_creates_its_schema(tmp_path):
    connection = msfs_store.connect(tmp_path / "navixav.sqlite")
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    assert {"airport", "runway", "procedure", "leg", "transition",
            "navaid", "waypoint", "airway_segment"} <= tables
    connection.close()


def test_store_round_trip(tmp_path):
    connection = msfs_store.connect(tmp_path / "navixav.sqlite")
    msfs_store.store_airport(connection, _minimal_airport())
    row = connection.execute("SELECT * FROM airport WHERE icao = 'TEST'").fetchone()
    assert row["name"] == "Essai"
    assert row["transition_altitude_ft"] == 5000
    assert connection.execute("SELECT COUNT(*) FROM runway").fetchone()[0] == 2
    connection.close()


def test_navaid_and_waypoint_round_trip(tmp_path):
    connection = msfs_store.connect(tmp_path / "navixav.sqlite")
    msfs_store.store_navaid(connection, {
        "ident": "OLN", "region": "LF", "frequency_mhz": 110.3, "name": "ILS RWY 02",
        "has_glide_slope": True, "has_dme": True, "localizer_course": 18.4,
        "glide_slope": 3.0, "lat": 48.72, "lon": 2.38,
    })
    msfs_store.store_waypoint(connection, {
        "ident": "EPIKO", "region": "LF", "lat": 48.23144, "lon": 6.68692,
        "routes": [{"airway": "V27", "next": "LUL", "next_region": "LF",
                    "previous": None, "previous_region": None}],
    })
    assert connection.execute(
        "SELECT frequency_mhz FROM navaid WHERE ident = 'OLN'"
    ).fetchone()[0] == 110.3
    assert connection.execute(
        "SELECT COUNT(*) FROM airway_segment WHERE airway = 'V27'"
    ).fetchone()[0] == 1
    connection.close()


def _minimal_airport() -> dict:
    return {
        "icao": "TEST", "name": "Essai", "lat": 48.0, "lon": 7.0,
        "altitude_ft": 500.0, "transition_altitude_ft": 5000,
        "transition_level_ft": None,
        "runways": [{
            "primary": "05", "secondary": "23", "lat": 48.0, "lon": 7.0,
            "altitude_ft": 500.0, "heading_true": 48.6, "length_ft": 7900,
            "width_ft": 148, "surface": "asphalte",
            "primary_ils": "TST", "secondary_ils": None,
        }],
        "frequencies": [], "approaches": [], "departures": [], "arrivals": [],
        "taxi_points": [], "taxi_parkings": [], "taxi_paths": [],
    }


# --------------------------------------------------------------------------- #
# Réseau de roulage
#
# Les noms de voies, la nature des segments et les points d'attente sont ce qui
# distingue un tracé décoratif d'un réseau sur lequel on peut guider un avion.
# --------------------------------------------------------------------------- #


def _taxi_block(name: str, size: int) -> tuple[int, int, bytes]:
    """Bloc TAXI_NAME tel que le simulateur l'enverrait sur `size` octets."""
    payload = name.encode().ljust(size, b"\x00")
    return (F.TYPE_TAXI_NAME, 0, payload)


@pytest.mark.parametrize("size", [8, 32, 64])
def test_taxi_names_are_read_whatever_their_declared_length(size):
    """La longueur du champ varie d'une version à l'autre du simulateur.

    Le bloc ne portant qu'une chaîne, elle est lue sur toute la charge : aucune
    longueur ne peut désaligner le décodage.
    """
    blocks = [_taxi_block("A", size), _taxi_block("B3", size)]
    assert extract._taxi_names(blocks) == ["A", "B3"]


def test_taxi_names_ignore_the_other_blocks():
    blocks = [(F.TYPE_RUNWAY, 0, b"\x00" * 8), _taxi_block("C", 32)]
    assert extract._taxi_names(blocks) == ["C"]


def test_the_names_block_can_be_left_out_of_the_definition():
    """Repli lorsqu'une version du simulateur refuse ce bloc."""
    assert "OPEN TAXI_NAME" in extract.airport_definition().tokens
    assert "OPEN TAXI_NAME" not in extract.airport_definition(False).tokens


class _NameRefusingClient:
    """Simulateur qui refuse la définition dès qu'elle demande les noms.

    Un refus porte sur la définition entière : sans repli, c'est tout
    l'aéroport qui serait perdu, procédures comprises.
    """

    def __init__(self) -> None:
        self.attempts: list[bool] = []

    def request(self, definition, _icao):
        asked_names = "OPEN TAXI_NAME" in definition.tokens
        self.attempts.append(asked_names)
        if asked_names:
            raise SimConnectRefused("refus", [1])
        return []


def test_a_refused_names_block_does_not_cost_the_whole_airport():
    client = _NameRefusingClient()
    airport = extract.extract_airport(client, "lfst")
    assert client.attempts == [True, False]
    assert airport["icao"] == "LFST"
    assert airport["taxi_names"] == []


RUNWAY_PATH = F.TAXI_PATH_TYPE_RUNWAY


def test_a_runway_segment_names_its_runway():
    values = {"TYPE": RUNWAY_PATH, "RUNWAY_NUMBER": 32, "RUNWAY_DESIGNATOR": 2}
    assert extract._path_runway(values) == "32R"


def test_a_segment_serving_no_runway_has_none():
    """Les pistes vont de 1 à 36 : un numéro nul n'est pas la piste « 00 »."""
    values = {"TYPE": RUNWAY_PATH, "RUNWAY_NUMBER": 0, "RUNWAY_DESIGNATOR": 0}
    assert extract._path_runway(values) is None


@pytest.mark.parametrize("path_type", [1, 3, 4, 5, 6])
def test_only_a_runway_segment_is_believed_about_its_runway(path_type):
    """Ailleurs, ces deux champs ne sont pas remis à zéro par le simulateur.

    Sondés à LFST, LFBO et LFPO, ils y contiennent de la mémoire résiduelle :
    2 114 segments de circulation à Toulouse, aucune valeur exploitable. Le
    seul contrôle de plage ne protège pas, un reste tombant parfois entre 1 et
    36 — c'est ainsi qu'une piste « 01 » apparaissait à Strasbourg, qui n'a
    que la 05/23.
    """
    values = {"TYPE": path_type, "RUNWAY_NUMBER": 1, "RUNWAY_DESIGNATOR": 0}
    assert extract._path_runway(values) is None


def test_the_two_thresholds_of_a_runway_are_the_same_strip():
    assert base.reciprocal_runway("05") == "23"
    assert base.reciprocal_runway("23") == "05"
    assert base.reciprocal_runway("14L") == "32R"
    assert base.reciprocal_runway("32R") == "14L"
    assert base.reciprocal_runway("18C") == "36C"
    assert base.reciprocal_runway("36") == "18"


def test_a_reciprocal_is_always_reversible():
    for number in range(1, 37):
        for designator in ("", "L", "R", "C"):
            name = f"{number:02d}{designator}"
            assert base.reciprocal_runway(base.reciprocal_runway(name)) == name


def test_an_anonymous_segment_keeps_no_name():
    """L'indice 0 est l'entrée vide : lui inventer un nom tromperait le guidage."""
    names = ["", "A", "B3"]
    assert msfs_store._taxi_path_name(names, 0) is None
    assert msfs_store._taxi_path_name(names, 2) == "B3"
    assert msfs_store._taxi_path_name(names, 9) is None
    assert msfs_store._taxi_path_name(names, None) is None


def test_ground_round_trip_keeps_names_kinds_and_hold_points(tmp_path):
    connection = msfs_store.connect(tmp_path / "navixav.sqlite")
    airport = _minimal_airport()
    airport["taxi_names"] = ["", "A", "B3"]
    airport["taxi_points"] = [
        {"x": 0.0, "y": 0.0, "type": 1},
        {"x": 100.0, "y": 0.0, "type": 2},
        {"x": 100.0, "y": 200.0, "type": 1},
    ]
    airport["taxi_paths"] = [
        {"type": 1, "width_m": 23.0, "start": 0, "end": 1,
         "name_index": 1, "runway": None},
        {"type": 2, "width_m": 45.0, "start": 1, "end": 2,
         "name_index": 0, "runway": "05"},
    ]
    msfs_store.store_airport(connection, airport)

    rows = connection.execute(
        "SELECT * FROM taxi_path WHERE icao = 'TEST' ORDER BY start_idx"
    ).fetchall()
    assert [(row["kind"], row["name"], row["runway_name"]) for row in rows] == [
        ("taxi", "A", None),
        ("runway", None, "05"),
    ]
    kinds = [
        row["kind"] for row in connection.execute(
            "SELECT kind FROM taxi_point WHERE icao = 'TEST' ORDER BY idx"
        )
    ]
    assert kinds == ["normal", "hold_short", "normal"]
    connection.close()


def test_a_stored_airport_records_its_ground_version(tmp_path):
    connection = msfs_store.connect(tmp_path / "navixav.sqlite")
    msfs_store.store_airport(connection, _minimal_airport())
    version = connection.execute(
        "SELECT ground_version FROM airport WHERE icao = 'TEST'"
    ).fetchone()[0]
    assert version == msfs_store.GROUND_VERSION
    connection.close()


# --------------------------------------------------------------------------- #
# Migration
# --------------------------------------------------------------------------- #


_SCHEMA_V1 = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE airport (
    icao TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '',
    lat REAL NOT NULL, lon REAL NOT NULL, altitude_ft REAL,
    transition_altitude_ft INTEGER, transition_level_ft INTEGER,
    source TEXT NOT NULL DEFAULT 'MSFS', fetched_at TEXT NOT NULL
);
CREATE TABLE taxi_point (
    icao TEXT NOT NULL, idx INTEGER NOT NULL,
    x REAL NOT NULL, y REAL NOT NULL, PRIMARY KEY (icao, idx)
);
CREATE TABLE taxi_path (
    icao TEXT NOT NULL, start_idx INTEGER NOT NULL,
    end_idx INTEGER NOT NULL, width_m REAL NOT NULL
);
INSERT INTO meta VALUES ('schema_version', '1');
INSERT INTO airport (icao, lat, lon, fetched_at)
    VALUES ('LFST', 48.5, 7.6, '2026-01-01T00:00:00+00:00');
INSERT INTO taxi_point VALUES ('LFST', 0, 12.0, 34.0);
INSERT INTO taxi_path VALUES ('LFST', 0, 1, 23.0);
"""


def _store_at_v1(path):
    connection = sqlite3.connect(path)
    connection.executescript(_SCHEMA_V1)
    connection.commit()
    connection.close()
    return path


def test_migration_keeps_what_the_previous_version_had_cached(tmp_path):
    """Rien n'est effacé : une base ancienne reste lisible simulateur fermé."""
    path = _store_at_v1(tmp_path / "navixav.sqlite")
    connection = msfs_store.connect(path)

    assert connection.execute(
        "SELECT COUNT(*) FROM airport WHERE icao = 'LFST'"
    ).fetchone()[0] == 1
    point = connection.execute("SELECT * FROM taxi_point").fetchone()
    assert (point["x"], point["y"]) == (12.0, 34.0)
    assert point["kind"] is None
    path_row = connection.execute("SELECT * FROM taxi_path").fetchone()
    assert path_row["width_m"] == 23.0
    assert (path_row["kind"], path_row["name"], path_row["runway_name"]) == (
        None, None, None,
    )
    connection.close()


def test_migration_marks_the_ground_geometry_as_outdated(tmp_path):
    """C'est ce marqueur qui déclenchera la reprise au simulateur."""
    connection = msfs_store.connect(_store_at_v1(tmp_path / "navixav.sqlite"))
    assert connection.execute(
        "SELECT ground_version FROM airport WHERE icao = 'LFST'"
    ).fetchone()[0] == 0
    assert msfs_store.GROUND_VERSION > 0
    connection.close()


def test_migration_records_the_new_schema_version(tmp_path):
    connection = msfs_store.connect(_store_at_v1(tmp_path / "navixav.sqlite"))
    assert connection.execute(
        "SELECT value FROM meta WHERE key = 'schema_version'"
    ).fetchone()[0] == str(msfs_store.SCHEMA_VERSION)
    connection.close()


def test_migration_is_idempotent(tmp_path):
    path = _store_at_v1(tmp_path / "navixav.sqlite")
    msfs_store.connect(path).close()
    connection = msfs_store.connect(path)
    assert connection.execute("SELECT COUNT(*) FROM taxi_point").fetchone()[0] == 1
    connection.close()


def test_an_outdated_airport_is_not_lost_when_the_simulator_is_absent(tmp_path):
    """Sans simulateur, un terrain d'une version antérieure reste consultable."""
    from navixav.navdata.msfs import MsfsProvider

    provider = MsfsProvider(
        _store_at_v1(tmp_path / "navixav.sqlite"), allow_fetch=False
    )
    try:
        assert provider.ensure("LFST") is False
        assert provider.airport("LFST") is not None
    finally:
        provider.close()


# --------------------------------------------------------------------------- #
# Contre le simulateur (ignoré s'il ne tourne pas)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def sim_provider(tmp_path_factory):
    from navixav.navdata.msfs import MsfsProvider

    provider = MsfsProvider(tmp_path_factory.mktemp("msfs") / "navixav.sqlite")
    try:
        provider.ensure("LFPO")
    except Exception:  # noqa: BLE001 - simulateur absent
        provider.close()
        pytest.skip("Microsoft Flight Simulator ne répond pas")
    yield provider
    provider.close()


@pytest.mark.live_msfs
def test_live_airport_matches_published_values(sim_provider):
    airport = sim_provider.airport("LFPO")
    assert airport.name == "Orly"
    assert round(airport.lat, 3) == 48.723
    assert airport.transition_altitude_ft == 5000


@pytest.mark.live_msfs
def test_live_runways_are_complete(sim_provider):
    names = {runway.name for runway in sim_provider.runways("LFPO")}
    assert names == {"02", "20", "06", "24", "07", "25"}


@pytest.mark.live_msfs
def test_live_procedures_have_connection_points(sim_provider):
    """Sans point de raccord, le moteur ne peut pas chaîner la procédure."""
    sids = sim_provider.procedures("LFPO", ProcedureKind.SID)
    stars = sim_provider.procedures("LFPO", ProcedureKind.STAR)
    assert sids and stars
    assert all(procedure.exit_fix for procedure in sids)
    assert all(procedure.entry_fix for procedure in stars)


@pytest.mark.live_msfs
def test_live_transitions_are_fixes_not_runways(sim_provider):
    """Une transition de piste n'est pas une transition de route."""
    for procedure in sim_provider.procedures("LFPO", ProcedureKind.SID):
        for ident in procedure.transition_idents():
            assert not ident.strip().isdigit()


@pytest.mark.live_msfs
def test_live_ils_frequency(sim_provider):
    frequency = sim_provider.ils_frequency("LFPO", "02")
    assert frequency is not None
    assert 108.0 <= frequency <= 112.0


@pytest.mark.live_msfs
def test_live_fix_position(sim_provider):
    position = sim_provider.fix_position("EPIKO")
    assert position is not None
    assert round(position[0], 3) == 48.231
    assert round(position[1], 3) == 6.687


@pytest.mark.live_msfs
def test_unknown_fix_is_remembered_as_missing(sim_provider):
    assert sim_provider.fix_position("ZZZZZ") is None
    assert sim_provider._missed("ZZZZZ", "waypoint")
