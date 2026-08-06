"""Cohérence de la chaîne d'arrivée : STAR -> transition -> approche.

Le cas modélisé ici est celui de Brive-Souillac, mais la règle vaut partout :
une STAR n'est publiée que pour certaines pistes, et celle qui ne dessert pas
la piste retenue dépose l'avion sur l'IAF du côté opposé du terrain. Le moteur
n'a alors rien à enchaîner — il doit annoncer une arrivée directe plutôt que
produire une suite que personne ne peut voler.

    LFZZ RWY 11/29
      STAR ARRI1R  : MAKOX -> ISL11, transition de piste 11 uniquement
      ILS RWY 29   : transition BSC, corps CF29 -> BSC -> RW29
      RNAV RWY 29  : transitions ARMAX/OSDAG/UVRAK
"""

from __future__ import annotations

import pytest

from navixav.config import Settings
from navixav.models import Confidence
from navixav.navdata.base import (
    Airport,
    Procedure,
    ProcedureKind,
    ProcedureLeg,
    Runway,
    Transition,
)
from navixav.planner.engine import CompletionEngine, PlannerOverrides
from navixav.preferences import AirportPreferences
from navixav.simbrief.parser import NavlogFix, OfpSummary

AIRPORT = Airport(
    ident="LFZZ", name="Terrain d'essai", city=None, country="FR",
    lat=45.04, lon=1.48, altitude_ft=1016.0, mag_var=1.0,
    transition_altitude_ft=5000, transition_level_ft=6000,
)


def _leg(fix: str, missed: bool = False) -> ProcedureLeg:
    return ProcedureLeg(
        leg_type="TF", fix_ident=fix, fix_type=None, is_missed=missed,
        alt_descriptor=None, altitude1_ft=None, altitude2_ft=None,
        speed_limit_kt=None, speed_limit_type=None, course_deg=None,
        distance_nm=None, lat=None, lon=None,
    )


def _runway(name: str, heading: float) -> Runway:
    return Runway(
        name=name, heading_true_deg=heading, length_ft=6898.0, width_ft=148.0,
        surface="ASPHALT", ils_ident="BVC" if name == "29" else None,
        is_landing=True, is_takeoff=True, lat=45.04, lon=1.48,
    )


class _Provider:
    """Base minimale : une STAR pour la 11, trois approches pour la 29."""

    airac_cycle = "2608"
    source_name = "base d'essai"
    supports_rnp_flag = True

    # Positions cohérentes avec la géographie du terrain, pour que le repli
    # géométrique du moteur ait de quoi travailler.
    POSITIONS = {
        "LAVRA": (45.60, 1.20), "BSC": (45.04, 1.48), "MAKOX": (45.55, 1.90),
        "ISL11": (44.95, 1.20), "ARMAX": (44.80, 1.90), "OSDAG": (45.30, 1.10),
        "UVRAK": (44.70, 1.30), "CF29": (44.99, 1.62), "RW29": (45.04, 1.48),
    }

    def airport(self, icao):
        return AIRPORT if icao.upper() == "LFZZ" else None

    def runways(self, icao):
        return [_runway("11", 114.6), _runway("29", 294.6)]

    def procedures(self, icao, kind):
        if kind is ProcedureKind.STAR:
            return [
                Procedure(
                    provider_id=1, kind=kind, ident="ARRI1R", arinc_name=None,
                    proc_type=None, suffix=None, runway_name=None,
                    runways=("11",), legs=(_leg("MAKOX"), _leg("ISL11")),
                )
            ]
        if kind is ProcedureKind.APPROACH:
            return [
                Procedure(
                    provider_id=2, kind=kind, ident="29", arinc_name="RW29",
                    proc_type="ILS", suffix=None, runway_name="29",
                    runways=("29",),
                    legs=(_leg("CF29"), _leg("BSC"), _leg("RW29")),
                    transitions=(Transition("BSC", "APPROACH", (_leg("BSC"),)),),
                    ils_ident="BVC",
                ),
                Procedure(
                    provider_id=3, kind=kind, ident="29", arinc_name="RW29",
                    proc_type="RNAV", suffix=None, runway_name="29",
                    runways=("29",),
                    legs=(_leg("ISL29"), _leg("RW29")),
                    transitions=tuple(
                        Transition(ident, "APPROACH", (_leg(ident), _leg("ISL29")))
                        for ident in ("ARMAX", "OSDAG", "UVRAK")
                    ),
                    requires_rnp=True,
                ),
            ]
        return []

    def ils_frequency(self, icao, runway_name):
        return 109.95 if runway_name == "29" else None

    def is_airway(self, name):
        return False

    def fix_position(self, ident, icao=None, near=None):
        return self.POSITIONS.get(ident.strip().upper())

    def close(self):
        pass


def _ofp(**changes) -> OfpSummary:
    base = dict(
        origin_icao="LFBO", destination_icao="LFZZ",
        destination_planned_runway="29",
        destination_metar="LFZZ 061700Z 34009KT CAVOK 29/08 Q1021 NOSIG",
        navlog=[
            NavlogFix("LAVRA", fix_type="wpt"),
            NavlogFix("CF29", fix_type="wpt"),
            NavlogFix("BSC", fix_type="vor"),
            NavlogFix("LFZZ", fix_type="apt"),
        ],
    )
    base.update(changes)
    return OfpSummary(**base)


@pytest.fixture
def plan_arrival():
    def build(overrides=None, ofp=None):
        engine = CompletionEngine(
            _Provider(), Settings(metar_source="simbrief"), AirportPreferences.load()
        )
        return engine.complete(ofp or _ofp(), overrides)

    return build


# --------------------------------------------------------------------------- #
# Le repère de raccord : ni un point d'approche, ni un point inventé
# --------------------------------------------------------------------------- #


def test_synthetic_approach_fixes_are_not_en_route_points():
    """« CF29 » est un repère d'interception, pas le dernier point de la route.

    SimBrief le laisse au navlog sans le marquer comme appartenant à une
    procédure ; s'il compte comme point en route, c'est lui qui sert de repère
    de raccord et plus aucune STAR ne peut s'y accrocher.
    """
    ofp = _ofp()
    assert ofp.enroute_fixes == ["LAVRA", "BSC"]
    assert ofp.last_enroute_fix == "BSC"
    assert all(leg["to"] != "CF29" for leg in ofp.enroute_route)


@pytest.mark.parametrize(
    "ident", ["RW29", "CF32R", "FF05", "MA11", "19DME"]
)
def test_every_arinc_synthetic_name_is_recognised(ident):
    assert NavlogFix(ident).is_procedure_fix


@pytest.mark.parametrize("ident", ["MAKOX", "BSC", "LAVRA", "ARMAX", "TOULO"])
def test_published_waypoints_are_never_mistaken_for_procedure_fixes(ident):
    assert not NavlogFix(ident).is_procedure_fix


# --------------------------------------------------------------------------- #
# Une STAR d'une autre piste n'est pas une arrivée dégradée
# --------------------------------------------------------------------------- #


def test_a_star_serving_another_runway_is_never_selected(plan_arrival):
    arrival = plan_arrival().arrival
    assert arrival.runway.choice.value == "29"
    assert arrival.star.value is None
    assert arrival.star.confidence is Confidence.NONE
    assert "piste 29" in arrival.star.reason
    assert arrival.star_transition.value is None


def test_the_discarded_star_stays_available_as_an_alternative(plan_arrival):
    """Le moteur ne l'enchaîne plus, mais le pilote garde la main."""
    alternatives = plan_arrival().arrival.star.alternatives
    assert [a["value"] for a in alternatives] == ["ARRI1R"]
    assert alternatives[0]["runways"] == ["11"]


def test_the_missing_star_is_announced_once(plan_arrival):
    warnings = plan_arrival().warnings
    assert any("Aucune STAR n'est publiée pour la piste 29" in w for w in warnings)
    assert not any("recherche élargie" in w for w in warnings)


def test_forcing_the_star_still_works_and_says_why_it_is_odd(plan_arrival):
    """Imposer reste possible : le moteur obéit, et explique le risque."""
    plan = plan_arrival(PlannerOverrides(star="ARRI1R"))
    assert plan.arrival.star.value == "ARRI1R"
    assert plan.arrival.star.confidence is Confidence.HIGH
    assert any("n'est pas publiée pour la piste 29" in w for w in plan.warnings)


# --------------------------------------------------------------------------- #
# Sans STAR, l'approche se raccroche à la route
# --------------------------------------------------------------------------- #


def test_the_approach_connects_to_the_last_en_route_fix(plan_arrival):
    """BSC termine la route et ouvre l'ILS : le maillon existe, il doit être vu."""
    arrival = plan_arrival().arrival
    assert arrival.approach.value == "ILS RWY 29"
    assert arrival.approach.confidence is Confidence.HIGH
    assert "transition publiée depuis BSC" in arrival.approach.reason
    assert arrival.approach_transition.value == "BSC"
    assert arrival.approach_transition.confidence is Confidence.HIGH


def test_the_reason_no_longer_blames_an_absent_star(plan_arrival):
    reason = plan_arrival().arrival.approach_transition.reason
    assert "STAR" not in reason
    assert reason == "transition partant du dernier point en route"


def test_a_published_link_outranks_the_type_preference(plan_arrival):
    """Un raccord publié prime : la RNAV a des transitions, mais pas depuis BSC."""
    ofp = _ofp(
        navlog=[
            NavlogFix("LAVRA", fix_type="wpt"),
            NavlogFix("ARMAX", fix_type="wpt"),
            NavlogFix("LFZZ", fix_type="apt"),
        ]
    )
    arrival = plan_arrival(ofp=ofp).arrival
    assert arrival.approach.value == "RNAV RWY 29"
    assert arrival.approach_transition.value == "ARMAX"
    assert arrival.approach_transition.confidence is Confidence.HIGH


def test_no_chain_warning_when_the_arrival_holds_together(plan_arrival):
    plan = plan_arrival()
    assert not any("prévoir un guidage radar" in w for w in plan.warnings)


def test_a_star_that_leads_nowhere_is_reported(plan_arrival):
    """STAR imposée pour la 11 alors qu'on atterrit en 29 : la rupture est dite."""
    plan = plan_arrival(PlannerOverrides(star="ARRI1R"))
    assert plan.arrival.star.value == "ARRI1R"
    assert any(
        "se termine sur ISL11" in w and "guidage radar" in w for w in plan.warnings
    )
