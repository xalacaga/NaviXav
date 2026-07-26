"""Couche MSFS : décodage des facilities et base NaviXav.

Les tests qui touchent le simulateur sont ignorés s'il ne tourne pas. Ceux qui
portent sur le décodage et la reconstruction s'exécutent toujours.
"""

from __future__ import annotations

import struct

import pytest

from navixav.msfs import fields as F
from navixav.msfs.client import FacilityDefinition, SimConnectError, decode
from navixav.navdata import msfs_store
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


def test_live_airport_matches_published_values(sim_provider):
    airport = sim_provider.airport("LFPO")
    assert airport.name == "Orly"
    assert round(airport.lat, 3) == 48.723
    assert airport.transition_altitude_ft == 5000


def test_live_runways_are_complete(sim_provider):
    names = {runway.name for runway in sim_provider.runways("LFPO")}
    assert names == {"02", "20", "06", "24", "07", "25"}


def test_live_procedures_have_connection_points(sim_provider):
    """Sans point de raccord, le moteur ne peut pas chaîner la procédure."""
    sids = sim_provider.procedures("LFPO", ProcedureKind.SID)
    stars = sim_provider.procedures("LFPO", ProcedureKind.STAR)
    assert sids and stars
    assert all(procedure.exit_fix for procedure in sids)
    assert all(procedure.entry_fix for procedure in stars)


def test_live_transitions_are_fixes_not_runways(sim_provider):
    """Une transition de piste n'est pas une transition de route."""
    for procedure in sim_provider.procedures("LFPO", ProcedureKind.SID):
        for ident in procedure.transition_idents():
            assert not ident.strip().isdigit()


def test_live_ils_frequency(sim_provider):
    frequency = sim_provider.ils_frequency("LFPO", "02")
    assert frequency is not None
    assert 108.0 <= frequency <= 112.0


def test_live_fix_position(sim_provider):
    position = sim_provider.fix_position("EPIKO")
    assert position is not None
    assert round(position[0], 3) == 48.231
    assert round(position[1], 3) == 6.687


def test_unknown_fix_is_remembered_as_missing(sim_provider):
    assert sim_provider.fix_position("ZZZZZ") is None
    assert sim_provider._missed("ZZZZZ", "waypoint")
