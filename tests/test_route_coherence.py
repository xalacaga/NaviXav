"""Connections use flown endpoints, independently of airport names."""
from dataclasses import replace

import pytest

from navixav.models import Confidence
from navixav.navdata.base import Procedure, ProcedureKind, ProcedureLeg, Transition
from navixav.planner.engine import CompletionEngine
from navixav.preferences import AirportPreferences
from navixav.simbrief.parser import NavlogFix, OfpSummary


def leg(fix):
    return ProcedureLeg("TF", fix, None, False, None, None, None,
                        None, None, None, None, None, None)


def procedure(kind, transitions=()):
    return Procedure(1, kind, "TEST1", None, "ILS", None, "07", ("07",),
                     (leg("COMMON"), leg("END")), transitions)


@pytest.fixture
def engine(provider, settings):
    return CompletionEngine(provider, settings, AirportPreferences.load())


@pytest.mark.parametrize("endpoint,name", [("ODILO", "ODI1E"), ("FIXAA", "LINK2B")])
def test_approach_uses_actual_entry_not_transition_label(engine, endpoint, name):
    proc = procedure(ProcedureKind.APPROACH, (
        Transition(endpoint, "APPROACH", (leg("WRONG"), leg("COMMON"))),
        Transition(name, "APPROACH", (leg(endpoint), leg("COMMON"))),
    ))
    chosen = engine._approach_transition(proc, endpoint, True, None)
    assert chosen.value == name
    assert chosen.confidence is Confidence.HIGH


def test_interior_fix_is_not_an_entry(engine):
    proc = procedure(ProcedureKind.APPROACH, (
        Transition("LINK1", "APPROACH", (leg("OTHER"), leg("TARGET"), leg("COMMON"))),
    ))
    choice = engine._approach_transition(proc, "TARGET", True, None)
    assert choice.value == "VECTORS"
    assert choice.confidence is Confidence.LOW


def test_direct_common_entry_needs_no_transition(engine):
    choice = engine._approach_transition(procedure(ProcedureKind.APPROACH), "COMMON", True, None)
    assert choice.value is None
    assert choice.confidence is Confidence.HIGH


@pytest.mark.parametrize("kind", [ProcedureKind.SID, ProcedureKind.STAR])
def test_route_transition_uses_correct_endpoint(engine, kind):
    fixes = ("COMMON", "TARGET") if kind is ProcedureKind.SID else ("TARGET", "COMMON")
    proc = procedure(kind, (Transition("LINK2", "ENROUTE", tuple(map(leg, fixes))),))
    if kind is ProcedureKind.SID:
        _, choice = engine._departure_choice_from(proc, "TARGET", None, "test", Confidence.HIGH, "test")
    else:
        choice = engine._star_transition(proc, "TARGET", None)
    assert choice.value == "LINK2"
    assert choice.confidence is Confidence.HIGH


@pytest.mark.parametrize("kind", [ProcedureKind.SID, ProcedureKind.STAR])
def test_unconnected_transition_is_not_selected_by_default(engine, kind):
    proc = procedure(kind, (Transition("LINK2", "ENROUTE", (leg("OTHER"),)),))
    if kind is ProcedureKind.SID:
        _, choice = engine._departure_choice_from(proc, "TARGET", None, "test", Confidence.HIGH, "test")
    else:
        choice = engine._star_transition(proc, "TARGET", None)
    assert choice.value is None
    assert choice.confidence is Confidence.LOW
    assert choice.alternatives


def test_invalid_user_transition_is_preserved_but_not_validated(engine):
    choice = engine._approach_transition(procedure(ProcedureKind.APPROACH), "COMMON", True, "MISSING")
    assert choice.value == "MISSING"
    assert choice.confidence is Confidence.LOW
    assert engine._warnings


def test_published_but_disconnected_user_transition_is_not_validated(engine):
    proc = procedure(ProcedureKind.APPROACH, (
        Transition("LINK1", "APPROACH", (leg("OTHER"), leg("COMMON"))),
    ))
    choice = engine._approach_transition(proc, "TARGET", True, "LINK1")
    assert choice.value == "LINK1"
    assert choice.confidence is Confidence.LOW


@pytest.mark.parametrize("kind", [ProcedureKind.SID, ProcedureKind.STAR])
def test_common_endpoint_can_connect_without_optional_transition(engine, kind):
    proc = procedure(kind, (Transition("OPTION", "ENROUTE", (leg("OTHER"),)),))
    if kind is ProcedureKind.SID:
        _, choice = engine._departure_choice_from(proc, "END", None, "test", Confidence.HIGH, "test")
    else:
        choice = engine._star_transition(proc, "COMMON", None)
    assert choice.value is None
    assert choice.confidence is Confidence.HIGH


def test_duplicate_star_prefix_is_not_appended_as_runway_tail():
    proc = procedure(ProcedureKind.STAR)
    proc = replace(proc, runway_transitions=(Transition("07", "RUNWAY", proc.legs[:1]),))
    assert proc.effective_runway_legs("07") == ()
    changed = replace(proc.legs[0], altitude1_ft=7000, alt_descriptor="+")
    proc = replace(proc, runway_transitions=(Transition("07", "RUNWAY", (changed,)),))
    assert proc.effective_runway_legs("07") == (changed,)


def test_real_runway_tail_is_preserved():
    tail = (leg("IAF"),)
    proc = replace(procedure(ProcedureKind.STAR), runway_transitions=(Transition("07", "RUNWAY", tail),))
    assert proc.effective_runway_legs("07") == tail


def test_complete_flight_corrects_boundary_hints_and_arrival_chain(engine, monkeypatch):
    sid = replace(procedure(ProcedureKind.SID), ident="START1", runways=("32L",),
                  legs=(leg("INNER"), leg("EXITF")))
    star = replace(procedure(ProcedureKind.STAR), ident="FINISH1",
                   legs=(leg("ENTRYF"), leg("MIDDLE"), leg("IAFIX")))
    star = replace(star, runway_transitions=(Transition("07", "RUNWAY", star.legs[:1]),))
    approach = procedure(ProcedureKind.APPROACH, (
        Transition("WRONG1", "APPROACH", (leg("OTHER"), leg("COMMON"))),
        Transition("RIGHT1", "APPROACH", (leg("IAFIX"), leg("COMMON"))),
    ))
    monkeypatch.setattr(engine.provider, "procedures", lambda icao, kind: {
        ("LFBO", ProcedureKind.SID): [sid],
        ("LFPO", ProcedureKind.STAR): [star],
        ("LFPO", ProcedureKind.APPROACH): [approach],
    }.get((icao, kind), []))
    ofp = OfpSummary(
        origin_icao="LFBO", destination_icao="LFPO", aircraft_icao="A320",
        origin_planned_runway="32L", destination_planned_runway="07",
        origin_metar="LFBO 060530Z VRB01KT CAVOK 21/11 Q1020",
        destination_metar="LFPO 060530Z VRB03KT CAVOK 14/09 Q1024",
        simbrief_sid="START1", simbrief_star="FINISH1",
        sid_exit_hint="INNER", star_entry_hint="MIDDLE",
        navlog=[NavlogFix("EXITF", via_airway="START1"),
                NavlogFix("ENRTE", via_airway="DCT"),
                NavlogFix("ENTRYF", via_airway="UT158")],
    )
    plan = engine.complete(ofp)
    assert plan.departure.sid_transition.value == "EXITF"
    assert plan.departure.sid_transition.confidence is Confidence.HIGH
    assert plan.arrival.star_transition.value == "ENTRYF"
    assert plan.arrival.star_transition.confidence is Confidence.HIGH
    assert plan.arrival.approach_transition.value == "RIGHT1"
    assert plan.atc_route() == "START1 EXITF DCT ENRTE UT158 ENTRYF FINISH1"
    assert not any("Raccord" in warning or "se termine sur" in warning for warning in plan.warnings)
