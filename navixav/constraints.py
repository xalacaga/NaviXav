"""Contraintes d'altitude et de vitesse publiées le long d'une procédure.

Les descripteurs suivent l'ARINC 424, tels que conservés dans la base MSFS :

    '+'  au niveau ou au-dessus de altitude1
    '-'  au niveau ou en dessous de altitude1
    'A'  au niveau de altitude1
    'B'  entre altitude1 et altitude2

Une altitude à 0 signifie « aucune contrainte » dans ce schéma, quel que soit
le descripteur. Les vitesses publiées sont toujours des maximums.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from navixav.navdata.base import Procedure, ProcedureLeg, Transition

# Segments sans repère nommé : le libellé décrit la nature du segment.
_LEG_LABELS = {
    "CA": "montée au cap",
    "CD": "cap jusqu'à distance",
    "CI": "cap vers interception",
    "CR": "cap jusqu'à radiale",
    "FA": "jusqu'à altitude",
    "FM": "jusqu'à manœuvre",
    "VA": "montée au cap (vecteur)",
    "VI": "vecteur vers interception",
    "VM": "vecteur à vue",
    "VR": "vecteur jusqu'à radiale",
}


@dataclass
class ConstraintRow:
    """Une contrainte publiée, rattachée à un repère ou à un segment."""

    label: str
    altitude: str | None = None
    speed: str | None = None
    is_fix: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "altitude": self.altitude,
            "speed": self.speed,
            "is_fix": self.is_fix,
        }

    def summary(self) -> str:
        parts = [p for p in (self.altitude, self.speed) if p]
        return " · ".join(parts)


def format_altitude(leg: ProcedureLeg) -> str | None:
    """Contrainte d'altitude d'un segment, ou None s'il n'y en a pas."""
    first = int(leg.altitude1_ft or 0)
    second = int(leg.altitude2_ft or 0)
    if not first and not second:
        return None

    descriptor = (leg.alt_descriptor or "").strip().upper()
    if descriptor == "B" and first and second:
        low, high = sorted((first, second))
        return f"entre {low} et {high} ft"
    if descriptor == "+":
        return f"≥ {first} ft"
    if descriptor == "-":
        return f"≤ {first} ft"
    if descriptor == "A" or not descriptor:
        return f"{first} ft"
    # Descripteur inconnu : afficher la valeur sans l'interpréter.
    return f"{first} ft ({descriptor})"


def format_speed(leg: ProcedureLeg) -> str | None:
    """Contrainte de vitesse d'un segment, ou None s'il n'y en a pas."""
    speed = leg.speed_limit_kt
    if not speed:
        return None
    limit_type = (leg.speed_limit_type or "-").strip()
    if limit_type == "+":
        return f"≥ {speed} kt"
    if limit_type == "-":
        return f"max {speed} kt"
    return f"{speed} kt"


def rows_from_legs(legs: Iterable[ProcedureLeg]) -> list[ConstraintRow]:
    """Ne retient que les segments porteurs d'une contrainte."""
    rows: list[ConstraintRow] = []
    for leg in legs:
        if leg.is_missed:
            continue
        altitude = format_altitude(leg)
        speed = format_speed(leg)
        if not altitude and not speed:
            continue

        if leg.fix_ident:
            label, is_fix = leg.fix_ident, True
        else:
            label = _LEG_LABELS.get(leg.leg_type, leg.leg_type or "segment")
            is_fix = False

        # Un même repère peut porter plusieurs segments : on fusionne.
        if rows and rows[-1].label == label:
            rows[-1].altitude = rows[-1].altitude or altitude
            rows[-1].speed = rows[-1].speed or speed
            continue
        rows.append(
            ConstraintRow(label=label, altitude=altitude, speed=speed, is_fix=is_fix)
        )
    return rows


def procedure_constraints(
    procedure: Procedure,
    transition_ident: str | None = None,
    transition_first: bool = False,
) -> list[ConstraintRow]:
    """Contraintes d'une procédure, transition publiée incluse.

    `transition_first` place les segments de la transition avant ceux de la
    procédure : c'est l'ordre de survol d'une STAR ou d'une approche, alors
    qu'une transition de SID se parcourt après.
    """
    transition: Transition | None = (
        procedure.find_transition(transition_ident) if transition_ident else None
    )
    transition_legs: Sequence[ProcedureLeg] = transition.legs if transition else ()

    if transition_first:
        legs = [*transition_legs, *procedure.legs]
    else:
        legs = [*procedure.legs, *transition_legs]
    return rows_from_legs(legs)


def procedure_path(
    procedure: Procedure,
    transition_ident: str | None = None,
    transition_first: bool = False,
    position_lookup: Callable[[str], tuple[float, float] | None] | None = None,
) -> list[dict[str, object]]:
    """Points géographiques ordonnés d'une procédure et de sa transition."""
    transition: Transition | None = (
        procedure.find_transition(transition_ident) if transition_ident else None
    )
    transition_legs: Sequence[ProcedureLeg] = transition.legs if transition else ()
    if transition_first:
        legs = [*transition_legs, *procedure.legs]
    else:
        legs = [*procedure.legs, *transition_legs]

    path: list[dict[str, object]] = []
    for leg in legs:
        if leg.is_missed:
            continue
        position = (
            (leg.lat, leg.lon)
            if leg.lat is not None and leg.lon is not None
            else position_lookup(leg.fix_ident)
            if position_lookup and leg.fix_ident
            else None
        )
        if position is None:
            continue
        point = {
            "ident": leg.fix_ident or leg.leg_type or "segment",
            "lat": position[0],
            "lon": position[1],
        }
        if path and path[-1] == point:
            continue
        path.append(point)
    return path
