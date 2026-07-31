"""Calcul d'itinéraire de roulage sur le réseau d'un aérodrome.

La recherche est un A\\* dont l'état est le couple (nœud, segment d'arrivée) et
non le seul nœud : sans le segment parcouru, on ne saurait ni mesurer l'angle
d'un virage ni voir un changement de voie, et l'itinéraire enchaînerait des
zigzags aussi courts que raisonnables sur le papier, impraticables en vrai.

Les pénalités sont exprimées en mètres, dans la même unité que les distances.
Toutes les pondérations valent au moins 1 : la distance à vol d'oiseau reste
donc une minoration du coût réel, ce qui garantit que le premier itinéraire
trouvé est bien le meilleur.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from navixav.ground.graph import (
    FORBIDDEN_KINDS,
    GroundError,
    TaxiEdge,
    TaxiGraph,
)


@dataclass(frozen=True)
class TaxiCosts:
    """Ce qui rend un itinéraire préférable à un autre."""

    # Multiplicateur de distance par nature de segment. Rouler sur une piste
    # est possible — c'est ainsi qu'on la dégage — mais doit rester un dernier
    # recours tant qu'une voie de circulation existe.
    kind_multipliers: Mapping[str | None, float] = field(
        default_factory=lambda: {
            "taxi": 1.0,
            "path": 1.0,
            "parking": 1.0,
            "runway": 8.0,
            None: 1.0,
        }
    )
    forbidden_kinds: frozenset[str] = FORBIDDEN_KINDS
    # Un virage marqué coûte du temps et une instruction de plus.
    turn_penalty_m: float = 25.0
    turn_threshold_deg: float = 30.0
    # Rester sur la même voie vaut mieux que multiplier les changements.
    change_penalty_m: float = 40.0
    # Largeur minimale exigée par l'avion, en mètres.
    min_width_m: float | None = None

    def multiplier(self, kind: str | None) -> float:
        return max(1.0, self.kind_multipliers.get(kind, 1.0))

    def allows(self, edge: TaxiEdge) -> bool:
        if edge.kind in self.forbidden_kinds:
            return False
        if self.min_width_m and edge.width_m and edge.width_m < self.min_width_m:
            return False
        return True


DEFAULT_COSTS = TaxiCosts()


@dataclass(frozen=True)
class RouteLeg:
    """Portion d'itinéraire parcourue sur une même voie."""

    name: str | None
    kind: str | None
    distance_m: float
    turn: str | None
    points: tuple[tuple[float, float], ...]
    hold_short: str | None

    @property
    def label(self) -> str:
        return self.name or "liaison"


@dataclass(frozen=True)
class TaxiRoute:
    """Itinéraire complet, du premier au dernier nœud."""

    icao: str
    nodes: tuple[int, ...]
    legs: tuple[RouteLeg, ...]
    distance_m: float

    @property
    def is_empty(self) -> bool:
        return len(self.nodes) < 2

    def summary(self) -> tuple[str, ...]:
        """Enchaînement des voies, tel qu'on l'annoncerait au pilote.

        Les liaisons sans nom sont tues : elles n'ont rien à annoncer, le
        pilote suit la ligne jaune jusqu'à la voie suivante. Leurs points
        d'attente, eux, sont conservés — c'est une consigne, pas un repère.
        """
        steps = []
        for leg in self.legs:
            if leg.name:
                steps.append(leg.name)
            if leg.hold_short:
                steps.append(f"attente {leg.hold_short}")
        return tuple(steps)


def find_route(
    graph: TaxiGraph,
    start: int | Iterable[int],
    goal: int | Iterable[int],
    costs: TaxiCosts = DEFAULT_COSTS,
    *,
    require_kinds: bool = True,
) -> TaxiRoute:
    """Meilleur itinéraire de `start` vers `goal`, chacun pouvant être multiple.

    Plusieurs départs servent à l'arrivée : l'avion dégage la piste par l'une
    quelconque de ses sorties, et c'est la recherche qui doit désigner la
    meilleure plutôt qu'un choix arbitraire fait d'avance.

    `require_kinds` protège contre un réseau importé avant que NaviXav ne
    demande la nature des segments : faute de la connaître, rien ne
    distinguerait une piste d'une route de service, et l'itinéraire serait faux
    sans le dire. Ne le lever que pour analyser une base ancienne.
    """
    if require_kinds and not graph.has_kinds:
        raise GroundError(
            f"Le tracé au sol de {graph.icao} ne distingue pas les pistes des "
            "voies de service : reprends le terrain avec le simulateur ouvert.",
        )

    starts = frozenset([start] if isinstance(start, int) else start)
    goals = frozenset([goal] if isinstance(goal, int) else goal)
    if not starts:
        raise GroundError("Aucun point de départ de roulage n'a été désigné.")
    if not goals:
        raise GroundError("Aucune destination de roulage n'a été désignée.")
    for index in (*starts, *goals):
        if index not in graph.nodes:
            raise GroundError(f"Le point {index} n'appartient pas à {graph.icao}.")
    reached = starts & goals
    if reached:
        return TaxiRoute(graph.icao, (min(reached),), (), 0.0)

    targets = [(graph.nodes[index].x, graph.nodes[index].y) for index in goals]

    def heuristic(node: int) -> float:
        position = graph.nodes[node]
        return min(
            math.hypot(position.x - x, position.y - y) for x, y in targets
        )

    best: dict[tuple[int, TaxiEdge | None], float] = {}
    came_from: dict[tuple[int, TaxiEdge | None], tuple[int, TaxiEdge | None]] = {}
    # Le compteur départage les états de même coût : sans lui, le tas
    # comparerait des segments entre eux, ce qu'ils ne savent pas faire.
    counter = 0
    queue: list[tuple[float, int, float, tuple[int, TaxiEdge | None]]] = []
    for index in sorted(starts):
        state: tuple[int, TaxiEdge | None] = (index, None)
        best[state] = 0.0
        counter += 1
        heapq.heappush(queue, (heuristic(index), counter, 0.0, state))

    while queue:
        _estimate, _tie, cost, state = heapq.heappop(queue)
        node, arrived_by = state
        if cost > best.get(state, math.inf):
            continue
        if node in goals:
            return _build_route(graph, came_from, state)

        for edge in graph.neighbours(node):
            if not costs.allows(edge):
                continue
            following = edge.other(node)
            # Un demi-tour sur place n'est pas manœuvrable par un aéronef.
            if arrived_by is not None and following == _origin(arrived_by, node):
                continue
            step = edge.length_m * costs.multiplier(edge.kind)
            step += _manoeuvre_penalty(graph, node, arrived_by, edge, costs)
            candidate = cost + step
            next_state = (following, edge)
            if candidate >= best.get(next_state, math.inf):
                continue
            best[next_state] = candidate
            came_from[next_state] = state
            counter += 1
            heapq.heappush(
                queue,
                (candidate + heuristic(following), counter, candidate, next_state),
            )

    raise GroundError(
        f"Aucun itinéraire de roulage praticable sur {graph.icao} "
        "entre ces deux points.",
    )


# --------------------------------------------------------------------------- #
# Coût d'une manœuvre
# --------------------------------------------------------------------------- #


def _origin(edge: TaxiEdge, node: int) -> int:
    """Nœud d'où l'on vient en arrivant sur `node` par ce segment."""
    return edge.other(node)


def _manoeuvre_penalty(
    graph: TaxiGraph,
    node: int,
    arrived_by: TaxiEdge | None,
    leaving_by: TaxiEdge,
    costs: TaxiCosts,
) -> float:
    """Surcoût d'un virage et d'un changement de voie au passage d'un nœud."""
    if arrived_by is None:
        return 0.0
    penalty = 0.0
    turn = _turn_degrees(graph, node, arrived_by, leaving_by)
    if abs(turn) >= costs.turn_threshold_deg:
        penalty += costs.turn_penalty_m
    if (
        arrived_by.name
        and leaving_by.name
        and arrived_by.name != leaving_by.name
    ):
        penalty += costs.change_penalty_m
    return penalty


def _turn_degrees(
    graph: TaxiGraph, node: int, arrived_by: TaxiEdge, leaving_by: TaxiEdge
) -> float:
    """Angle du virage au nœud, négatif à gauche et positif à droite."""
    incoming = _bearing(graph, arrived_by.other(node), node)
    outgoing = _bearing(graph, node, leaving_by.other(node))
    return (outgoing - incoming + 180.0) % 360.0 - 180.0


def _bearing(graph: TaxiGraph, origin: int, target: int) -> float:
    """Cap de `origin` vers `target`, en degrés depuis le nord local."""
    first, second = graph.nodes[origin], graph.nodes[target]
    return math.degrees(math.atan2(second.x - first.x, second.y - first.y)) % 360.0


# --------------------------------------------------------------------------- #
# Reconstruction
# --------------------------------------------------------------------------- #


def _build_route(
    graph: TaxiGraph,
    came_from: dict[tuple[int, TaxiEdge | None], tuple[int, TaxiEdge | None]],
    final: tuple[int, TaxiEdge | None],
) -> TaxiRoute:
    states = [final]
    while states[-1] in came_from:
        states.append(came_from[states[-1]])
    states.reverse()

    nodes = tuple(node for node, _edge in states)
    edges = tuple(edge for _node, edge in states[1:] if edge is not None)
    legs = _split_into_legs(graph, nodes, edges)
    return TaxiRoute(
        icao=graph.icao,
        nodes=nodes,
        legs=legs,
        distance_m=round(sum(edge.length_m for edge in edges), 1),
    )


def _split_into_legs(
    graph: TaxiGraph, nodes: tuple[int, ...], edges: tuple[TaxiEdge, ...]
) -> tuple[RouteLeg, ...]:
    """Regroupe les segments consécutifs parcourus sur une même voie.

    Une liaison sans nom prolonge la portion nommée en cours plutôt que d'en
    ouvrir une : le simulateur en sème entre les voies, et les annoncer une à
    une noierait les instructions utiles. Seules celles rencontrées avant toute
    voie nommée forment une portion à part, faute de quoi les rattacher.
    """
    if not edges:
        return ()

    legs: list[RouteLeg] = []
    current: list[TaxiEdge] = []
    current_nodes: list[int] = [nodes[0]]
    current_name: str | None = None
    turn: str | None = None
    pending_turn: str | None = None

    for position, edge in enumerate(edges):
        opens_leg = bool(edge.name) and current and edge.name != current_name
        if opens_leg:
            legs.append(_leg(
                graph, current, current_nodes, current_name, turn,
                next_edge=edge,
            ))
            turn = pending_turn
            current = []
            current_nodes = [nodes[position]]
            current_name = None

        current.append(edge)
        current_nodes.append(nodes[position + 1])
        current_name = current_name or edge.name

        if position + 1 < len(edges):
            pending_turn = _turn_label(_turn_at(graph, nodes, position + 1))

    legs.append(_leg(graph, current, current_nodes, current_name, turn, None))
    return tuple(legs)


def _leg(
    graph: TaxiGraph,
    edges: list[TaxiEdge],
    nodes: list[int],
    name: str | None,
    turn: str | None,
    next_edge: TaxiEdge | None,
) -> RouteLeg:
    return RouteLeg(
        name=name,
        kind=edges[0].kind,
        distance_m=round(sum(edge.length_m for edge in edges), 1),
        turn=turn,
        points=tuple(
            (graph.nodes[index].x, graph.nodes[index].y) for index in nodes
        ),
        hold_short=_hold_short_runway(graph, nodes[-1], next_edge),
    )


# Portion prise de part et d'autre d'un nœud pour mesurer un virage.
TURN_SPAN_M = 45.0


def _turn_at(
    graph: TaxiGraph, nodes: Sequence[int], index: int, span_m: float = TURN_SPAN_M
) -> float:
    """Angle du virage au nœud, mesuré à quelques dizaines de mètres de part et
    d'autre.

    Les jonctions sont adoucies par des raccordements que le simulateur découpe
    en segments courts. L'angle entre deux segments consécutifs y est presque
    nul là où le virage, lui, est franc : mesuré ainsi, un quart de tour à
    Toulouse ne se voyait pas du tout, et aucune manœuvre n'était annoncée. On
    compare donc le cap d'avant l'entrée en courbe à celui d'après la sortie.
    """
    before = _walk(graph, nodes, index, -1, span_m)
    after = _walk(graph, nodes, index, 1, span_m)
    if before is None or after is None:
        return 0.0
    incoming = _bearing(graph, before, nodes[index])
    outgoing = _bearing(graph, nodes[index], after)
    return (outgoing - incoming + 180.0) % 360.0 - 180.0


def _walk(
    graph: TaxiGraph, nodes: Sequence[int], index: int, step: int, span_m: float
) -> int | None:
    """Nœud atteint en s'éloignant de `index` sur au plus `span_m`.

    À défaut d'aller assez loin — l'itinéraire commence ou finit avant —, le
    dernier nœud disponible fait foi.
    """
    travelled = 0.0
    current = index
    while 0 <= current + step < len(nodes):
        travelled += graph.distance(nodes[current], nodes[current + step])
        current += step
        if travelled >= span_m:
            break
    return nodes[current] if current != index else None


def _turn_label(degrees: float) -> str | None:
    if abs(degrees) < 30.0:
        return None
    return "right" if degrees > 0 else "left"


def _hold_short_runway(
    graph: TaxiGraph, node: int, next_edge: TaxiEdge | None
) -> str | None:
    """Piste devant laquelle il faut s'arrêter en quittant cette portion.

    La consigne ne peut pas dépendre des seuls points d'attente publiés : les
    entrées en piste de LFST, LFBO et LFPO sont toutes marquées « normal », les
    points publiés se trouvant en retrait sur la voie. S'y fier n'annoncerait
    jamais aucune attente. Un nœud qui touche un segment de piste est la limite
    elle-même, qu'il porte ou non un marquage.
    """
    if next_edge is not None and next_edge.is_runway:
        return next_edge.runway
    for edge in graph.neighbours(node):
        if edge.is_runway and edge.runway:
            return edge.runway
    return None
