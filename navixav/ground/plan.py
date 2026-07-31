"""Itinéraire de roulage complet, du poste de stationnement à la piste.

Le calcul d'itinéraire s'arrête aux nœuds du réseau. Or un poste n'en est pas
un : il se trouve à quelques dizaines de mètres du premier point de
circulation, au bout de sa ligne de guidage. Cette portion est ajoutée ici,
comme premier ou dernier tronçon selon le sens, pour que le tracé affiché parte
bien de l'avion et non du milieu de l'aire de trafic.

Le sens est celui du vol, pas celui du graphe : au départ on va du poste vers
le point d'attente, à l'arrivée on part des sorties de piste — toutes à la fois,
c'est la recherche qui désigne la meilleure — vers le poste attribué.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from navixav.ground.graph import GroundError, Parking, TaxiGraph
from navixav.ground.route import DEFAULT_COSTS, TaxiCosts, TaxiRoute, find_route
from navixav.navdata.base import normalise_runway, reciprocal_runway

DEPARTURE = "departure"
ARRIVAL = "arrival"
DIRECTIONS = (DEPARTURE, ARRIVAL)

# Nature donnée au tronçon de ligne de guidage, distincte des segments du
# réseau : il ne se parcourt pas comme une voie de circulation.
STAND_KIND = "stand"

# Raccordement entre la position de l'avion et le réseau, lors d'une reprise en
# cours de roulage.
JOIN_KIND = "join"

# En deçà, l'avion est déjà sur le réseau et le raccordement n'a pas lieu d'être.
MIN_JOIN_M = 5.0

# En deçà, la ligne de guidage est trop courte pour valoir un tronçon : le poste
# touche pratiquement le réseau.
MIN_LEAD_IN_M = 5.0


@dataclass(frozen=True)
class TaxiPlan:
    """Itinéraire prêt à afficher, avec ses deux extrémités nommées."""

    graph: TaxiGraph
    direction: str
    parking: Parking
    runway: str
    route: TaxiRoute
    entries: tuple[int, ...]
    # Position de l'avion quand l'itinéraire a été repris en cours de roulage,
    # en mètres locaux. Absente pour un itinéraire calculé depuis le poste.
    origin: tuple[float, float] | None = None

    @property
    def from_position(self) -> bool:
        return self.origin is not None

    @property
    def icao(self) -> str:
        return self.graph.icao

    @property
    def has_lead_in(self) -> bool:
        """La ligne de guidage du poste fait-elle partie du tracé ?

        Repris en cours de roulage, un départ ne repasse pas par le poste : la
        rattacher ferait revenir le tracé en arrière jusqu'à l'aire de trafic.
        """
        if self.parking.lead_in_m < MIN_LEAD_IN_M:
            return False
        return not (self.from_position and self.direction == DEPARTURE)

    @property
    def distance_m(self) -> float:
        """Distance totale, raccordements aux extrémités compris."""
        return round(sum(leg["distance_m"] for leg in self.legs()), 1)

    def _hold_short(self, runway: str | None) -> str | None:
        """Consigne d'attente, dite dans le sens que le pilote emploie.

        La géométrie ne nomme qu'un seuil par bande : au départ de la 05 à
        Strasbourg, elle annoncerait « attente 23 ». C'est la même limite, mais
        se voir arrêter devant la piste opposée à celle qu'on va prendre est
        déroutant au point de faire douter de l'itinéraire.
        """
        if not runway:
            return None
        wanted = normalise_runway(self.runway)
        if normalise_runway(runway) in (wanted, reciprocal_runway(wanted)):
            return wanted
        return runway

    def legs(self) -> list[dict[str, Any]]:
        """Tronçons du tracé, dans l'ordre où le pilote les parcourt."""
        network = [
            {
                "name": leg.name,
                "kind": leg.kind,
                "distance_m": leg.distance_m,
                "turn": leg.turn,
                "hold_short": self._hold_short(leg.hold_short),
                "points": [{"x": x, "y": y} for x, y in leg.points],
            }
            for leg in self.route.legs
        ]
        if self.has_lead_in:
            if self.direction == ARRIVAL:
                network = [*network, self._stand_leg()]
            else:
                network = [self._stand_leg(), *network]

        join = self._join_leg()
        return [join, *network] if join else network

    def _join_leg(self) -> dict[str, Any] | None:
        """Rejoint le réseau depuis la position de l'avion.

        L'itinéraire repris en cours de roulage part du nœud le plus proche, qui
        peut être à des dizaines de mètres. Sans ce raccordement, l'avion resterait
        hors de son propre tracé, le guidage le déclarerait égaré et en
        demanderait un nouveau à chaque seconde — indéfiniment.
        """
        if self.origin is None or not self.route.nodes:
            return None
        node = self.graph.nodes[self.route.nodes[0]]
        distance = math.hypot(self.origin[0] - node.x, self.origin[1] - node.y)
        if distance < MIN_JOIN_M:
            return None
        return {
            "name": None,
            "kind": JOIN_KIND,
            "distance_m": round(distance, 1),
            "turn": None,
            "hold_short": None,
            "points": [
                {"x": self.origin[0], "y": self.origin[1]},
                {"x": node.x, "y": node.y},
            ],
        }

    def _stand_leg(self) -> dict[str, Any]:
        """Ligne de guidage entre le poste et le réseau de circulation."""
        node = self.graph.nodes[self.parking.node]
        points = [
            {"x": self.parking.x, "y": self.parking.y},
            {"x": node.x, "y": node.y},
        ]
        if self.direction == ARRIVAL:
            points.reverse()
        return {
            "name": self.parking.label,
            "kind": STAND_KIND,
            "distance_m": round(self.parking.lead_in_m, 1),
            "turn": None,
            "hold_short": None,
            "points": points,
        }

    def summary(self) -> tuple[str, ...]:
        """Enchaînement annoncé au pilote, poste compris.

        Il se construit sur les tronçons du plan et non sur ceux de la
        recherche, pour que consigne affichée et consigne tracée ne puissent
        pas diverger.
        """
        steps: list[str] = []
        for leg in self.legs():
            if leg["kind"] in (STAND_KIND, JOIN_KIND):
                continue
            if leg["name"]:
                steps.append(leg["name"])
            if leg["hold_short"]:
                steps.append(f"attente {leg['hold_short']}")
        if self.direction == ARRIVAL:
            return (*steps, self.parking.label)
        # Repris en cours de roulage, un départ ne repasse pas par le poste :
        # l'annoncer en tête ferait croire à un retour en arrière.
        if self.from_position:
            return tuple(steps)
        return (self.parking.label, *steps)

    def polyline(self) -> tuple[tuple[float, float], ...]:
        """Tracé complet en une seule ligne, sans point répété.

        Les tronçons se touchent par leurs extrémités : les garder en double
        introduirait des segments de longueur nulle, sur lesquels aucune
        direction ne se calcule.
        """
        points: list[tuple[float, float]] = []
        for leg in self.legs():
            for point in leg["points"]:
                current = (point["x"], point["y"])
                if points and points[-1] == current:
                    continue
                points.append(current)
        return tuple(points)

    def to_dict(self) -> dict[str, Any]:
        return {
            "icao": self.icao,
            "direction": self.direction,
            "runway": self.runway,
            "from_position": self.from_position,
            "parking": {
                "label": self.parking.label,
                "kind": self.parking.kind,
                "heading": self.parking.heading,
                "radius_m": self.parking.radius_m,
                "position": {"x": self.parking.x, "y": self.parking.y},
            },
            "distance_m": self.distance_m,
            "legs": self.legs(),
            "summary": list(self.summary()),
        }


def plan_taxi(
    graph: TaxiGraph,
    *,
    parking: str,
    runway: str,
    direction: str = DEPARTURE,
    costs: TaxiCosts = DEFAULT_COSTS,
    position: tuple[float, float] | None = None,
) -> TaxiPlan:
    """Itinéraire entre un poste et une piste, dans le sens demandé.

    `position`, en mètres locaux, remplace le point de départ par le nœud le
    plus proche de l'avion. C'est ce qui permet de reprendre l'itinéraire au
    milieu du roulage, sans renvoyer le pilote à son point de départ.
    """
    if direction not in DIRECTIONS:
        raise GroundError(
            f"Sens de roulage inconnu : « {direction} ». "
            f"Attendu {' ou '.join(DIRECTIONS)}.",
        )

    stand = graph.parking(parking)
    if stand is None:
        raise GroundError(f"{graph.icao} n'a pas de poste nommé « {parking} ».")

    # Au départ, on vise le seuil demandé ; à l'arrivée, toute sortie de la
    # bande convient et c'est la recherche qui retient la plus proche du poste.
    entries = (
        graph.takeoff_entry(runway)
        if direction == DEPARTURE
        else graph.runway_entries(runway)
    )
    if not entries:
        known = ", ".join(graph.runway_names()) or "aucune"
        raise GroundError(
            f"Le réseau de {graph.icao} ne rejoint pas la piste {runway} "
            f"(pistes desservies : {known}).",
        )

    # Reprise en cours de roulage : on repart d'où l'avion est, pas de l'autre
    # extrémité du trajet.
    if position is not None:
        start: int | tuple[int, ...] = graph.nearest_node(*position)
    elif direction == DEPARTURE:
        start = stand.node
    else:
        start = entries

    if direction == DEPARTURE:
        route = find_route(graph, start, entries, costs)
    else:
        route = find_route(graph, start, stand.node, costs)

    return TaxiPlan(
        graph=graph,
        direction=direction,
        parking=stand,
        runway=runway.strip().upper(),
        route=route,
        entries=entries,
        origin=position,
    )
