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
from typing import Any, Sequence

from navixav.ground.graph import GroundError, Parking, TaxiGraph
from navixav.ground.route import (
    DEFAULT_COSTS,
    TaxiCosts,
    TaxiRoute,
    find_route,
    follow_route,
)
from navixav.navdata.base import normalise_runway, reciprocal_runway

DEPARTURE = "departure"
ARRIVAL = "arrival"
DIRECTIONS = (DEPARTURE, ARRIVAL)

# Nature donnée au tronçon de ligne de guidage, distincte des segments du
# réseau : il ne se parcourt pas comme une voie de circulation.
STAND_KIND = "stand"

# Même ligne de guidage, quittée en marche arrière derrière un tracteur.
PUSHBACK_KIND = "pushback"

# Étape annoncée dans l'enchaînement, en français comme les consignes d'attente ;
# l'interface la traduit.
PUSHBACK_STEP = "repoussage"

# Postes qu'on ne quitte pas par ses propres moyens : l'avion y stationne nez
# au terminal et en sort tracté. Une rampe se quitte au moteur, et y annoncer
# un repoussage serait faux.
NOSE_IN_KINDS = ("porte petite", "porte moyenne", "porte grande", "dock")

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
    # Voies dictées par le contrôleur, dans l'ordre. Vide pour un itinéraire
    # calculé par NaviXav seul.
    via: tuple[str, ...] = ()

    @property
    def from_position(self) -> bool:
        return self.origin is not None

    @property
    def is_dictated(self) -> bool:
        """L'itinéraire suit-il une clairance saisie par le pilote ?"""
        return bool(self.via)

    @property
    def is_completed(self) -> bool:
        """La clairance saisie s'arrêtait-elle avant la piste ?"""
        return self.is_dictated and self.route.is_completed

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
    def needs_pushback(self) -> bool:
        """Le départ commence-t-il par un repoussage ?

        Repris en cours de roulage, il ne repasse pas par le poste : `has_lead_in`
        le dit déjà, et le repoussage est alors derrière l'avion.
        """
        if self.direction != DEPARTURE or not self.has_lead_in:
            return False
        return (self.parking.kind or "") in NOSE_IN_KINDS

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
                "from_clearance": leg.from_clearance,
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
            # Rejoindre le réseau ne relève d'aucune clairance : c'est le trajet
            # que l'avion fait de toute façon pour se remettre sur le tracé.
            "from_clearance": True,
        }

    def _stand_leg(self) -> dict[str, Any]:
        """Ligne de guidage entre le poste et le réseau de circulation.

        Au départ d'un poste nez-dedans, c'est le trajet du tracteur : même
        géométrie, parcourue en marche arrière. Le tronçon le dit, pour que le
        tracé et le bandeau ne l'annoncent pas comme un roulage.
        """
        node = self.graph.nodes[self.parking.node]
        points = [
            {"x": self.parking.x, "y": self.parking.y},
            {"x": node.x, "y": node.y},
        ]
        if self.direction == ARRIVAL:
            points.reverse()
        return {
            "name": self.parking.label,
            "kind": PUSHBACK_KIND if self.needs_pushback else STAND_KIND,
            "distance_m": round(self.parking.lead_in_m, 1),
            # `turn` reste vide : le guidage y lit les virages du roulage, et
            # une consigne de tracteur n'en est pas un. Le cap du repoussage
            # vit au niveau du plan, où le bandeau le lit.
            "turn": None,
            "hold_short": None,
            "points": points,
            "from_clearance": True,
        }

    def pushback(self) -> dict[str, Any] | None:
        """Manœuvre du tracteur, ou rien si le poste se quitte au moteur.

        Le cap dit tout : « nez à gauche » est le calque de *nose left*, quand
        la phraséologie française annonce l'orientation obtenue.
        """
        if not self.needs_pushback:
            return None
        heading = self._pushback_heading()
        node = self.graph.nodes[self.parking.node]
        return {
            "distance_m": round(self.parking.lead_in_m, 1),
            "heading": None if heading is None else round(heading),
            # Point où le repoussage s'achève : le bout de la ligne de guidage,
            # là où l'avion rejoint le réseau. C'est la cible que le tracteur
            # doit atteindre, et l'interface la propose d'un geste plutôt que
            # de la faire viser à la main.
            "target": {"x": round(node.x, 1), "y": round(node.y, 1)},
        }

    def _pushback_heading(self) -> float | None:
        """Cap présenté une fois l'avion repoussé, lu sur le tracé lui-même.

        C'est la direction du premier tronçon de circulation : le tracteur
        laisse l'avion face au chemin qu'il va suivre. Le déduire du tracé plutôt
        que du cap au poste évite d'annoncer un cap que l'itinéraire dément.
        """
        node = self.graph.nodes[self.parking.node]
        for leg in self.route.legs:
            for x, y in leg.points:
                if math.hypot(x - node.x, y - node.y) < MIN_LEAD_IN_M:
                    continue
                return math.degrees(math.atan2(x - node.x, y - node.y)) % 360.0
        return None

    def summary(self) -> tuple[str, ...]:
        """Enchaînement annoncé au pilote, poste compris.

        Il se construit sur les tronçons du plan et non sur ceux de la
        recherche, pour que consigne affichée et consigne tracée ne puissent
        pas diverger.
        """
        steps: list[str] = []
        for leg in self.legs():
            if leg["kind"] in (STAND_KIND, PUSHBACK_KIND, JOIN_KIND):
                continue
            if leg["name"]:
                steps.append(leg["name"])
            if leg["hold_short"]:
                steps.append(f"attente {leg['hold_short']}")
        if self.direction == ARRIVAL:
            return (*steps, self.parking.label)
        if self.needs_pushback:
            return (self.parking.label, PUSHBACK_STEP, *steps)
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
            "pushback": self.pushback(),
            "via": list(self.via),
            "dictated": self.is_dictated,
            "completed": self.is_completed,
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
    via: Sequence[str] = (),
) -> TaxiPlan:
    """Itinéraire entre un poste et une piste, dans le sens demandé.

    `position`, en mètres locaux, remplace le point de départ par le nœud le
    plus proche de l'avion. C'est ce qui permet de reprendre l'itinéraire au
    milieu du roulage, sans renvoyer le pilote à son point de départ.

    `via` est la suite de voies dictée par le contrôleur. Elle ne change ni les
    extrémités ni la sortie : seule la façon de les relier passe de la recherche
    libre à la recherche contrainte. Une clairance qui n'atteint pas la piste
    est prolongée, et les tronçons ajoutés se signalent par `from_clearance`.
    """
    if direction not in DIRECTIONS:
        raise GroundError(
            f"Sens de roulage inconnu : « {direction} ». "
            f"Attendu {' ou '.join(DIRECTIONS)}.",
            code="ground_unknown_direction", direction=direction,
        )

    stand = graph.parking(parking)
    if stand is None:
        raise GroundError(
            f"{graph.icao} n'a pas de poste nommé « {parking} ».",
            code="ground_unknown_parking", icao=graph.icao, parking=parking,
        )

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
            code="ground_runway_not_served",
            icao=graph.icao, runway=runway, runways=known,
        )

    # Reprise en cours de roulage : on repart d'où l'avion est, pas de l'autre
    # extrémité du trajet.
    arrival_heading: float | None = None
    if position is not None:
        arrival_start = (
            graph.arrival_start(runway, *position)
            if direction == ARRIVAL else None
        )
        if arrival_start is not None:
            start, arrival_heading = arrival_start
        else:
            start = graph.nearest_node(*position)
    elif direction == DEPARTURE:
        start = stand.node
    else:
        start = entries

    goal = entries if direction == DEPARTURE else stand.node
    clearance = tuple(via)
    if clearance:
        route = follow_route(graph, start, goal, clearance, costs)
    else:
        route = find_route(
            graph, start, goal, costs, initial_heading=arrival_heading
        )

    return TaxiPlan(
        graph=graph,
        direction=direction,
        parking=stand,
        runway=runway.strip().upper(),
        route=route,
        entries=entries,
        origin=position,
        via=clearance,
    )
