"""Contraintes publiées : lecture des descripteurs ARINC 424."""

from __future__ import annotations

from navixav.constraints import (
    ConstraintRow,
    compact_altitude,
    compact_speed,
    format_altitude,
    format_speed,
    procedure_path,
    rows_from_legs,
)
from navixav.navdata.base import Procedure, ProcedureKind, ProcedureLeg
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
# Notation courte, pour les étiquettes de la carte
# --------------------------------------------------------------------------- #


def test_compact_altitude_keeps_the_chart_notation():
    assert compact_altitude(_leg("+", 8000)) == "+8000"
    assert compact_altitude(_leg("-", 4000)) == "-4000"
    assert compact_altitude(_leg("A", 547)) == "547"


def test_compact_altitude_shows_the_window_ceiling_first():
    """Comme sur une carte : le plafond au-dessus du plancher."""
    assert compact_altitude(_leg("B", 3000, 5000)) == "5000/3000"


def test_compact_altitude_without_constraint():
    assert compact_altitude(_leg("A", 0)) is None


def test_altitude_below_ten_thousand_stays_in_feet():
    assert compact_altitude(_leg("A", 7000)) == "7000"
    assert compact_altitude(_leg("+", 9900)) == "+9900"


def test_altitude_from_ten_thousand_is_written_as_a_flight_level():
    assert compact_altitude(_leg("A", 10000)) == "FL100"
    assert compact_altitude(_leg("+", 12000)) == "+FL120"
    assert compact_altitude(_leg("-", 35000)) == "-FL350"


def test_window_converts_each_bound_on_its_own():
    """Une fenêtre à cheval sur le seuil garde ses deux valeurs telles quelles."""
    assert compact_altitude(_leg("B", 9000, 11000)) == "FL110/9000"


def test_compact_speed_marks_only_the_floor():
    assert compact_speed(_leg(speed=205)) == "205Kt"
    assert compact_speed(_leg(speed=205, speed_type="+")) == "+205Kt"
    assert compact_speed(_leg(speed=None)) is None


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


def _procedure(*legs: ProcedureLeg) -> Procedure:
    return Procedure(
        provider_id=1,
        kind=ProcedureKind.SID,
        ident="TESTS",
        arinc_name=None,
        proc_type=None,
        suffix=None,
        runway_name=None,
        runways=(),
        legs=tuple(legs),
    )


def _path(*legs: ProcedureLeg) -> list[dict]:
    return procedure_path(
        _procedure(*legs), position_lookup=lambda ident: (43.6, 1.4)
    )


def test_path_points_carry_their_constraint():
    point = _path(_leg("+", 3000, speed=210, fix="EEEEE"))[0]
    assert point["altitude"] == "+3000"
    assert point["speed"] == "210Kt"


def test_path_point_without_constraint_stays_bare():
    point = _path(_leg(fix="FFFFF"))[0]
    assert "altitude" not in point and "speed" not in point


def test_repeated_fix_stays_one_point_and_keeps_its_constraint():
    """Deux segments au même repère : une seule étiquette, contrainte comprise.

    Le second segment peut être celui qui publie la contrainte ; le repère ne
    doit pas pour autant se dédoubler sur la carte.
    """
    path = _path(_leg(fix="GGGGG"), _leg("-", 6000, fix="GGGGG"))
    assert len(path) == 1
    assert path[0]["altitude"] == "-6000"


def test_repeated_fix_merges_altitude_and_speed():
    path = _path(_leg("+", 3000, fix="HHHHH"), _leg(speed=210, fix="HHHHH"))
    assert len(path) == 1
    assert path[0]["altitude"] == "+3000"
    assert path[0]["speed"] == "210Kt"


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


def test_real_star_path_carries_the_map_constraint(provider, settings, ofp):
    """La contrainte lue dans le tableau doit se retrouver sur le tracé."""
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(ofp)
    adimo = [p for p in plan.arrival.star_path if p["ident"] == "ADIMO"]
    assert adimo, "ADIMO absent du tracé de la STAR"
    assert adimo[0]["altitude"] == "+8000"


def test_real_approach_path_carries_the_threshold_altitude(provider, settings, ofp):
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(ofp)
    threshold = [p for p in plan.arrival.approach_path if p["ident"] == "RW32R"]
    assert threshold and threshold[0]["altitude"] == "+547"


def test_constraint_without_a_fix_stays_off_the_map(provider, settings, ofp):
    """Une contrainte portée par un segment sans repère n'a pas où s'afficher.

    Le SID de référence limite la vitesse à 205 kt sur une montée au cap, qui
    n'a ni nom ni coordonnées : le tableau des contraintes l'annonce, la carte
    ne peut pas l'y poser. Inventer un point pour l'accrocher serait pire que
    de ne pas l'afficher.
    """
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(ofp)
    assert any(row.speed and not row.is_fix for row in plan.departure.sid_constraints)
    assert not [p for p in plan.departure.sid_path if p.get("speed")]


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
