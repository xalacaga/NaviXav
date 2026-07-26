"""Contraintes publiées : lecture des descripteurs ARINC 424."""

from __future__ import annotations

from navixav.constraints import (
    ConstraintRow,
    format_altitude,
    format_speed,
    rows_from_legs,
)
from navixav.navdata.base import ProcedureKind, ProcedureLeg
from navixav.planner.engine import CompletionEngine
from navixav.preferences import AirportPreferences


def _leg(
    descriptor: str | None = None,
    altitude1: float | None = None,
    altitude2: float | None = None,
    speed: int | None = None,
    speed_type: str | None = "-",
    fix: str | None = "TESTF",
    leg_type: str = "TF",
    missed: bool = False,
) -> ProcedureLeg:
    return ProcedureLeg(
        leg_type=leg_type,
        fix_ident=fix,
        fix_type="W",
        is_missed=missed,
        alt_descriptor=descriptor,
        altitude1_ft=altitude1,
        altitude2_ft=altitude2,
        speed_limit_kt=speed,
        speed_limit_type=speed_type,
        course_deg=None,
        distance_nm=None,
        lat=None,
        lon=None,
    )


# --------------------------------------------------------------------------- #
# Descripteurs d'altitude
# --------------------------------------------------------------------------- #


def test_at_or_above():
    assert format_altitude(_leg("+", 8000)) == "≥ 8000 ft"


def test_at_or_below():
    assert format_altitude(_leg("-", 4000)) == "≤ 4000 ft"


def test_at_altitude():
    assert format_altitude(_leg("A", 547)) == "547 ft"


def test_between_two_altitudes_is_ordered():
    assert format_altitude(_leg("B", 5000, 3000)) == "entre 3000 et 5000 ft"


def test_zero_altitude_means_no_constraint():
    """Le schéma code « aucune contrainte » par une altitude nulle."""
    assert format_altitude(_leg("A", 0)) is None
    assert format_altitude(_leg(None, 0, 0)) is None


def test_unknown_descriptor_is_shown_verbatim():
    assert format_altitude(_leg("X", 3000)) == "3000 ft (X)"


# --------------------------------------------------------------------------- #
# Vitesses
# --------------------------------------------------------------------------- #


def test_speed_limit_is_a_maximum():
    assert format_speed(_leg(speed=205)) == "max 205 kt"


def test_no_speed_limit():
    assert format_speed(_leg(speed=None)) is None


# --------------------------------------------------------------------------- #
# Assemblage
# --------------------------------------------------------------------------- #


def test_only_constrained_legs_are_kept():
    rows = rows_from_legs([_leg(fix="AAAAA"), _leg("+", 3000, fix="BBBBB")])
    assert [r.label for r in rows] == ["BBBBB"]


def test_missed_approach_legs_are_excluded():
    rows = rows_from_legs([_leg("+", 4000, fix="CCCCC", missed=True)])
    assert rows == []


def test_unnamed_leg_is_labelled_by_its_nature():
    rows = rows_from_legs([_leg(speed=205, fix=None, leg_type="CR")])
    assert rows[0].label == "cap jusqu'à radiale"
    assert rows[0].is_fix is False


def test_repeated_fix_is_merged():
    rows = rows_from_legs(
        [_leg("+", 3000, fix="DDDDD"), _leg(speed=210, fix="DDDDD")]
    )
    assert len(rows) == 1
    assert rows[0].altitude == "≥ 3000 ft"
    assert rows[0].speed == "max 210 kt"


def test_summary_joins_both_constraints():
    row = ConstraintRow("IO32R", "≥ 3000 ft", "max 210 kt")
    assert row.summary() == "≥ 3000 ft · max 210 kt"


# --------------------------------------------------------------------------- #
# Sur données réelles
# --------------------------------------------------------------------------- #


def test_real_star_constraint(provider, settings, ofp):
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(ofp)
    labels = {r.label: r for r in plan.arrival.star_constraints}
    assert labels["ADIMO"].altitude == "≥ 8000 ft"


def test_real_sid_speed_constraint(provider, settings, ofp):
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(ofp)
    speeds = [r.speed for r in plan.departure.sid_constraints if r.speed]
    assert "max 205 kt" in speeds


def test_approach_includes_its_via_legs(provider, settings, ofp):
    """La VIA est survolée avant l'approche : ses contraintes doivent y figurer."""
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(ofp)
    labels = [r.label for r in plan.arrival.approach_constraints]
    assert labels[0] == "ADIMO"
    assert "RW32R" in labels


def test_selected_procedures_expose_their_map_paths(provider, settings, ofp):
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(ofp)
    assert plan.departure.sid_path
    assert plan.arrival.star_path
    assert plan.arrival.approach_path
    for point in [
        *plan.departure.sid_path,
        *plan.arrival.star_path,
        *plan.arrival.approach_path,
    ]:
        assert {"ident", "lat", "lon"} <= point.keys()


def test_missed_approach_altitude_is_reported(provider, settings, ofp):
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(ofp)
    assert plan.arrival.missed_approach_altitude_ft == 5000


def test_missed_altitude_differs_between_variants(provider):
    """ILS Y remonte à 4000 ft, ILS Z à 5000 ft.

    Si la source ne renseigne pas le champ dédié, la valeur est reconstituée
    depuis les segments d'approche interrompue et doit redonner exactement
    celle publiée par les données MSFS.
    """
    approaches = {
        p.display_name: p
        for p in provider.procedures("LFBO", ProcedureKind.APPROACH)
    }
    assert approaches["ILS Y RWY 32R"].missed_approach_altitude_ft == 4000
    assert approaches["ILS Z RWY 32R"].missed_approach_altitude_ft == 5000
