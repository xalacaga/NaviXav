"""Guidage au sol : où l'avion en est de son itinéraire, et quoi lui dire.

Tout se rapporte au tracé par projection. La position est rabattue sur le
segment le plus proche, et non sur le point le plus proche : un itinéraire qui
revient sur lui-même — un aller-retour sur la même voie, une boucle autour d'un
terminal — met deux portions du tracé à quelques mètres l'une de l'autre, et un
plus-proche-point ferait sauter la progression de l'une à l'autre, annonçant un
virage déjà passé ou une distance qui augmente.

L'écart latéral sert à deux choses : dire que l'avion a quitté l'itinéraire, et
seulement alors en demander un nouveau. Le seuil est large — la précision n'est
pas en cause, c'est la largeur des aires de manœuvre qui l'impose : un avion qui
contourne un poste occupé s'écarte de plusieurs dizaines de mètres sans pour
autant s'être trompé.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

from navixav.ground.plan import TaxiPlan

# Au-delà, l'avion n'est plus sur l'itinéraire prévu.
OFF_ROUTE_M = 45.0

# En deçà de cette distance de la fin, le roulage est terminé.
ARRIVED_M = 30.0

# Distance à partir de laquelle on annonce la manœuvre suivante.
ANNOUNCE_M = 250.0


@dataclass(frozen=True)
class RouteFix:
    """Position de l'avion rapportée au tracé."""

    travelled_m: float
    lateral_m: float
    x: float
    y: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "travelled_m": round(self.travelled_m, 1),
            "lateral_m": round(self.lateral_m, 1),
            "position": {"x": round(self.x, 1), "y": round(self.y, 1)},
        }


@dataclass(frozen=True)
class Guidance:
    """Ce qu'il y a à annoncer au pilote, à cet instant."""

    on_route: bool
    arrived: bool
    fix: RouteFix
    remaining_m: float
    current: str | None
    next_name: str | None
    next_turn: str | None
    distance_to_next_m: float | None
    hold_short: str | None
    distance_to_hold_m: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "on_route": self.on_route,
            "arrived": self.arrived,
            "fix": self.fix.to_dict(),
            "remaining_m": round(self.remaining_m),
            "current": self.current,
            "next_name": self.next_name,
            "next_turn": self.next_turn,
            "distance_to_next_m": (
                None if self.distance_to_next_m is None
                else round(self.distance_to_next_m)
            ),
            "hold_short": self.hold_short,
            "distance_to_hold_m": (
                None if self.distance_to_hold_m is None
                else round(self.distance_to_hold_m)
            ),
            "announce": self.announce(),
        }

    def announce(self) -> str | None:
        """Consigne courte, telle qu'on la lirait à voix haute.

        Rien n'est annoncé tant que la manœuvre est loin : une instruction
        affichée trop tôt se confond avec celle qui la précède.
        """
        if self.arrived:
            return "Roulage terminé."
        if not self.on_route:
            return "Hors itinéraire."
        if (
            self.hold_short
            and self.distance_to_hold_m is not None
            and self.distance_to_hold_m <= ANNOUNCE_M
        ):
            return f"Arrêt avant la piste {self.hold_short}."
        if not self.next_name or self.distance_to_next_m is None:
            return None
        if self.distance_to_next_m > ANNOUNCE_M:
            return None
        turns = {"left": "à gauche", "right": "à droite"}
        side = turns.get(self.next_turn or "")
        if side:
            return f"Tournez {side} sur {self.next_name}."
        return f"Continuez sur {self.next_name}."


def guide(
    plan: TaxiPlan,
    x: float,
    y: float,
    *,
    tolerance_m: float = OFF_ROUTE_M,
) -> Guidance:
    """Situe l'avion sur son itinéraire et en tire la consigne du moment."""
    points = plan.polyline()
    legs = plan.legs()
    fix = project_on_route(points, x, y)
    total = _length(points)
    remaining = max(0.0, total - fix.travelled_m)

    bounds = _leg_bounds(legs)
    current_index = _leg_at(bounds, fix.travelled_m)
    current = legs[current_index] if current_index is not None else None

    following = _next_named(legs, current_index)
    hold_index = _next_hold(legs, current_index)

    return Guidance(
        on_route=fix.lateral_m <= tolerance_m,
        arrived=remaining <= ARRIVED_M,
        fix=fix,
        remaining_m=remaining,
        current=_leg_name(current),
        next_name=_leg_name(legs[following]) if following is not None else None,
        next_turn=legs[following]["turn"] if following is not None else None,
        distance_to_next_m=(
            None if following is None
            else max(0.0, bounds[following][0] - fix.travelled_m)
        ),
        hold_short=legs[hold_index]["hold_short"] if hold_index is not None else None,
        distance_to_hold_m=(
            None if hold_index is None
            else max(0.0, bounds[hold_index][1] - fix.travelled_m)
        ),
    )


def project_on_route(
    points: Sequence[tuple[float, float]], x: float, y: float
) -> RouteFix:
    """Rabat une position sur le tracé, segment par segment."""
    if len(points) < 2:
        origin = points[0] if points else (x, y)
        return RouteFix(
            travelled_m=0.0,
            lateral_m=math.hypot(x - origin[0], y - origin[1]),
            x=origin[0],
            y=origin[1],
        )

    travelled = 0.0
    best = RouteFix(0.0, math.inf, x, y)
    for index in range(1, len(points)):
        (x1, y1), (x2, y2) = points[index - 1], points[index]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length > 0:
            ratio = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / length**2))
            near_x, near_y = x1 + dx * ratio, y1 + dy * ratio
            lateral = math.hypot(x - near_x, y - near_y)
            if lateral < best.lateral_m:
                best = RouteFix(travelled + length * ratio, lateral, near_x, near_y)
        travelled += length
    return best


def replan_needed(guidance: Guidance) -> bool:
    """Faut-il reprendre l'itinéraire ?

    Arrivé, on ne recalcule rien : la fin d'un roulage éloigne forcément l'avion
    du dernier point du tracé, et le guidage repartirait en boucle.
    """
    return not guidance.on_route and not guidance.arrived


def replan(plan: TaxiPlan, x: float, y: float, **kwargs: Any) -> TaxiPlan:
    """Reprend l'itinéraire depuis la position de l'avion."""
    from navixav.ground.plan import plan_taxi

    return plan_taxi(
        plan.graph,
        parking=plan.parking.label,
        runway=plan.runway,
        direction=plan.direction,
        position=(x, y),
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# Découpage du tracé
# --------------------------------------------------------------------------- #


def _length(points: Sequence[tuple[float, float]]) -> float:
    return sum(
        math.hypot(
            points[index][0] - points[index - 1][0],
            points[index][1] - points[index - 1][1],
        )
        for index in range(1, len(points))
    )


def _leg_bounds(legs: Sequence[dict[str, Any]]) -> list[tuple[float, float]]:
    """Distance de début et de fin de chaque tronçon le long du tracé."""
    bounds = []
    offset = 0.0
    for leg in legs:
        length = _length([(p["x"], p["y"]) for p in leg["points"]])
        bounds.append((offset, offset + length))
        offset += length
    return bounds


def _leg_at(bounds: Sequence[tuple[float, float]], travelled: float) -> int | None:
    """Tronçon en cours de parcours.

    Pile sur une limite, c'est le tronçon qui commence qui l'emporte : sinon
    l'avion resterait annoncé sur celui qu'il vient de quitter, et la voie
    suivante lui serait indiquée à zéro mètre.
    """
    for index, (start, end) in enumerate(bounds):
        if start <= travelled < end:
            return index
    return len(bounds) - 1 if bounds else None


def _next_named(legs: Sequence[dict[str, Any]], current: int | None) -> int | None:
    """Premier tronçon nommé après celui en cours.

    Un tronçon anonyme ne s'annonce pas : le pilote suit la ligne jaune jusqu'à
    la voie suivante, qui, elle, porte un nom.
    """
    if current is None:
        return None
    for index in range(current + 1, len(legs)):
        if legs[index]["name"]:
            return index
    return None


def _next_hold(legs: Sequence[dict[str, Any]], current: int | None) -> int | None:
    if current is None:
        return None
    for index in range(current, len(legs)):
        if legs[index]["hold_short"]:
            return index
    return None


def _leg_name(leg: dict[str, Any] | None) -> str | None:
    return leg["name"] if leg else None
