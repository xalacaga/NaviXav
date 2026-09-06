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


# Seuil d'écriture en niveau de vol sur la carte. C'est une convention
# d'affichage, pas l'altitude de transition du terrain : celle-ci varie d'un
# aérodrome à l'autre et la base ne la publie pas. 10 000 ft la place au-dessus
# de la quasi-totalité des transitions rencontrées, si bien qu'une contrainte
# écrite en niveau en est bien un.
_FLIGHT_LEVEL_FLOOR_FT = 10000


def _level(feet: int) -> str:
    """Une altitude en pieds, ou en niveau de vol au-dessus du seuil."""
    if feet < _FLIGHT_LEVEL_FLOOR_FT:
        return str(feet)
    return f"FL{round(feet / 100):03d}"


def compact_altitude(leg: ProcedureLeg) -> str | None:
    """Contrainte d'altitude en notation de carte, pour une étiquette de carte.

    Le tableau des contraintes peut s'offrir une phrase ; une étiquette posée
    sur la route, non — elle doit tenir en quelques caractères sans masquer le
    tracé. On reprend donc la notation des cartes d'approche : le signe porte
    le sens, la valeur s'écrit en pieds ou en niveau selon `_level`.

    Les deux bornes d'une fenêtre sont converties chacune pour son compte : une
    fenêtre à cheval sur le seuil s'écrit donc « FL110/9000 », ce qui est le
    plus fidèle aux deux valeurs publiées.
    """
    first = int(leg.altitude1_ft or 0)
    second = int(leg.altitude2_ft or 0)
    if not first and not second:
        return None

    descriptor = (leg.alt_descriptor or "").strip().upper()
    if descriptor == "B" and first and second:
        low, high = sorted((first, second))
        return f"{_level(high)}/{_level(low)}"
    if descriptor == "+":
        return f"+{_level(first)}"
    if descriptor == "-":
        return f"-{_level(first)}"
    return _level(first or second)


def compact_speed(leg: ProcedureLeg) -> str | None:
    """Contrainte de vitesse en notation de carte, ou None s'il n'y en a pas.

    Une vitesse publiée est un maximum sauf mention contraire : seul le
    plancher mérite son signe, comme sur les cartes.
    """
    speed = leg.speed_limit_kt
    if not speed:
        return None
    if (leg.speed_limit_type or "-").strip() == "+":
        return f"+{speed}Kt"
    return f"{speed}Kt"


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
    runway_ident: str | None = None,
) -> list[ConstraintRow]:
    """Contraintes d'une procédure, transition publiée incluse.

    `transition_first` place les segments de la transition avant ceux de la
    procédure : c'est l'ordre de survol d'une STAR ou d'une approche, alors
    qu'une transition de SID se parcourt après.

    `runway_ident` ajoute la branche propre à la piste retenue, du côté où la
    procédure diverge : au début pour une SID, en finale pour une STAR.
    """
    legs = _ordered_legs(procedure, transition_ident, transition_first, runway_ident)
    return rows_from_legs(legs)


def _ordered_legs(
    procedure: Procedure,
    transition_ident: str | None,
    transition_first: bool,
    runway_ident: str | None,
) -> list[ProcedureLeg]:
    """Segments d'une procédure dans l'ordre de survol."""
    transition: Transition | None = (
        procedure.find_transition(transition_ident) if transition_ident else None
    )
    transition_legs: Sequence[ProcedureLeg] = transition.legs if transition else ()
    runway_legs: Sequence[ProcedureLeg] = procedure.effective_runway_legs(runway_ident)

    if transition_first:
        return [*transition_legs, *procedure.legs, *runway_legs]
    return [*runway_legs, *procedure.legs, *transition_legs]


def procedure_path(
    procedure: Procedure,
    transition_ident: str | None = None,
    transition_first: bool = False,
    position_lookup: Callable[[str], tuple[float, float] | None] | None = None,
    runway_ident: str | None = None,
) -> list[dict[str, object]]:
    """Points géographiques ordonnés d'une procédure et de sa transition."""
    legs = _ordered_legs(procedure, transition_ident, transition_first, runway_ident)

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
        point: dict[str, object] = {
            "ident": leg.fix_ident or leg.leg_type or "segment",
            "lat": position[0],
            "lon": position[1],
        }
        altitude = compact_altitude(leg)
        speed = compact_speed(leg)
        if altitude:
            point["altitude"] = altitude
        if speed:
            point["speed"] = speed

        # Un même repère porté par deux segments consécutifs ne fait qu'un point
        # sur la carte. La comparaison ne peut donc porter que sur l'identité et
        # la position : si le second segment est celui qui publie la contrainte,
        # comparer les points entiers la ferait passer pour un repère distinct,
        # et deux étiquettes se superposeraient au même endroit.
        previous = path[-1] if path else None
        if previous and all(previous[key] == point[key] for key in ("ident", "lat", "lon")):
            for key in ("altitude", "speed"):
                if key in point and key not in previous:
                    previous[key] = point[key]
            continue
        path.append(point)
    return path
