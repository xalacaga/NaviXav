"""Cohérence du départ : la SID doit partir du seuil réellement utilisé.

Symétrique de `test_arrival_chain.py`. Une SID n'est publiée que pour certaines
pistes : caps initiaux, altitudes minimales et obstacles franchis dépendent du
seuil d'où l'on décolle. Celle qui ne dessert pas la piste retenue n'est pas un
départ dégradé, elle est involable.

    LFZZ RWY 11/29
      SID NORD2B : piste 11, sortie LAVRA
      SID NORD2C : piste 29, sortie LAVRA
"""

from __future__ import annotations

from string import ascii_uppercase

import pytest

from navixav.config import Settings
from navixav.models import Confidence
from navixav.navdata.base import (
    Airport,
    Procedure,
    ProcedureKind,
    ProcedureLeg,
    Runway,
)
from navixav.planner.engine import CompletionEngine, PlannerOverrides
from navixav.preferences import AirportPreferences
from navixav.simbrief.parser import NavlogFix, OfpSummary

AIRPORTS = {
    "LFZZ": Airport(
        ident="LFZZ", name="Terrain de départ", city=None, country="FR",
        lat=45.04, lon=1.48, altitude_ft=1016.0, mag_var=1.0,
        transition_altitude_ft=5000, transition_level_ft=6000,
    ),
    "LFYY": Airport(
        ident="LFYY", name="Terrain d'arrivée", city=None, country="FR",
        lat=46.20, lon=1.10, altitude_ft=900.0, mag_var=1.0,
        transition_altitude_ft=5000, transition_level_ft=6000,
    ),
}


def _leg(fix: str) -> ProcedureLeg:
    return ProcedureLeg(
        leg_type="TF", fix_ident=fix, fix_type=None, is_missed=False,
        alt_descriptor=None, altitude1_ft=None, altitude2_ft=None,
        speed_limit_kt=None, speed_limit_type=None, course_deg=None,
        distance_nm=None, lat=None, lon=None,
    )


def _runway(icao: str, name: str, heading: float) -> Runway:
    airport = AIRPORTS[icao]
    return Runway(
        name=name, heading_true_deg=heading, length_ft=6898.0, width_ft=148.0,
        surface="ASPHALT", ils_ident=None, is_landing=True, is_takeoff=True,
        lat=airport.lat, lon=airport.lon,
    )


def _sid(provider_id: int, ident: str, runway: str) -> Procedure:
    return Procedure(
        provider_id=provider_id, kind=ProcedureKind.SID, ident=ident,
        arinc_name=None, proc_type=None, suffix=None, runway_name=None,
        runways=(runway,), legs=(_leg(f"D{runway}"), _leg("LAVRA")),
    )


class _Provider:
    """Base minimale : les SID publiées sont paramétrables par test."""

    airac_cycle = "2608"
    source_name = "base d'essai"
    supports_rnp_flag = True

    POSITIONS = {
        "LAVRA": (45.60, 1.20), "D11": (44.95, 1.60), "D29": (45.10, 1.35),
    }

    def __init__(self, sid_runways=("11",)) -> None:
        self._sids = [
            _sid(index, f"NORD2{ascii_uppercase[index + 1]}", runway)
            for index, runway in enumerate(sid_runways)
        ]

    def airport(self, icao):
        return AIRPORTS.get(icao.strip().upper())

    def runways(self, icao):
        key = icao.strip().upper()
        if key not in AIRPORTS:
            return []
        return [_runway(key, "11", 114.6), _runway(key, "29", 294.6)]

    def procedures(self, icao, kind):
        if icao.strip().upper() == "LFZZ" and kind is ProcedureKind.SID:
            return list(self._sids)
        return []

    def ils_frequency(self, icao, runway_name):
        return None

    def is_airway(self, name):
        return False

    def fix_position(self, ident, icao=None, near=None):
        return self.POSITIONS.get(ident.strip().upper())

    def close(self):
        pass


def _ofp() -> OfpSummary:
    return OfpSummary(
        origin_icao="LFZZ", destination_icao="LFYY",
        origin_planned_runway="29",
        origin_metar="LFZZ 061700Z 30012KT CAVOK 25/10 Q1020 NOSIG",
        navlog=[
            NavlogFix("LFZZ", fix_type="apt"),
            NavlogFix("LAVRA", fix_type="wpt"),
            NavlogFix("LFYY", fix_type="apt"),
        ],
    )


def _departure(sid_runways=("11",), overrides=None):
    engine = CompletionEngine(
        _Provider(sid_runways), Settings(metar_source="simbrief"),
        AirportPreferences.load(),
    )
    return engine.complete(_ofp(), overrides)


# --------------------------------------------------------------------------- #
# Une SID d'une autre piste n'est pas un départ dégradé
# --------------------------------------------------------------------------- #


def test_a_sid_serving_another_runway_is_never_selected():
    plan = _departure(sid_runways=("11",))
    assert plan.departure.runway.choice.value == "29"
    assert plan.departure.sid.value is None
    assert plan.departure.sid.confidence is Confidence.NONE
    assert "piste 29" in plan.departure.sid.reason
    assert plan.departure.sid_transition.value is None


def test_the_discarded_sid_stays_available_as_an_alternative():
    alternatives = _departure(sid_runways=("11",)).departure.sid.alternatives
    assert [a["value"] for a in alternatives] == ["NORD2B"]
    assert alternatives[0]["runways"] == ["11"]


def test_every_published_sid_for_the_runway_stays_choosable():
    """Le moteur propose, le pilote dispose : la liste n'est plus tronquée.

    Un choix sûr reste un choix : cinq SID publiées pour la 29 doivent toutes
    rester atteignables après coup, pas seulement les trois premières.
    """
    plan = _departure(sid_runways=("29",) * 5)
    assert plan.departure.sid.value == "NORD2B"
    assert [a["value"] for a in plan.departure.sid.alternatives] == [
        "NORD2C", "NORD2D", "NORD2E", "NORD2F",
    ]


def test_the_missing_sid_announces_radar_vectors():
    warnings = _departure(sid_runways=("11",)).warnings
    assert any("Aucune SID n'est publiée pour la piste 29" in w for w in warnings)
    assert not any("recherche élargie" in w for w in warnings)


def test_forcing_the_sid_still_works_and_says_why_it_is_odd():
    plan = _departure(sid_runways=("11",), overrides=PlannerOverrides(sid="NORD2B"))
    assert plan.departure.sid.value == "NORD2B"
    assert plan.departure.sid.confidence is Confidence.HIGH
    assert any("n'est pas publiée pour la piste 29" in w for w in plan.warnings)


def test_no_path_is_drawn_for_a_departure_without_a_sid():
    """Rien à tracer tant qu'aucune procédure n'est retenue."""
    assert _departure(sid_runways=("11",)).departure.sid_path == []


# --------------------------------------------------------------------------- #
# Le cas normal reste intact
# --------------------------------------------------------------------------- #


def test_the_sid_published_for_the_runway_is_still_chosen():
    plan = _departure(sid_runways=("11", "29"))
    assert plan.departure.sid.value == "NORD2C"
    assert plan.departure.sid.confidence is Confidence.HIGH
    assert plan.departure.sid_transition.value == "LAVRA"
    assert not any("Aucune SID" in w for w in plan.warnings)


@pytest.mark.parametrize("runway, expected", [("11", "NORD2B"), ("29", "NORD2C")])
def test_each_threshold_gets_its_own_sid(runway, expected):
    plan = _departure(
        sid_runways=("11", "29"), overrides=PlannerOverrides(departure_runway=runway)
    )
    assert plan.departure.sid.value == expected
