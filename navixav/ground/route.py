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
from typing import Any, Iterable, Mapping, Sequence

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
    # Faux pour la portion ajoutée par NaviXav au-delà de la clairance saisie.
    # L'affichage doit pouvoir la distinguer : ce n'est pas le contrôleur qui
    # l'a dite.
    from_clearance: bool = True

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

    @property
    def is_completed(self) -> bool:
        """Le tracé continue-t-il au-delà de la clairance saisie ?

        Seule la fin compte. Le début aussi peut sortir de la clairance — celle
        qui nomme la voie sortant du poste est rare — mais rejoindre la première
        voie dictée n'est pas la dépasser, et l'annoncer comme tel ferait
        passer toute clairance pour incomplète.
        """
        origins = [leg.from_clearance for leg in self.legs]
        return bool(origins) and True in origins and not origins[-1]

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
    initial_heading: float | None = None,
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
            code="ground_no_kinds", icao=graph.icao,
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
    # La valeur porte l'état précédent et l'origine du tronçon. Ici tout vient
    # de NaviXav, donc tout est « de la clairance » : la distinction ne sert
    # qu'au roulage dicté, qui partage cette reconstruction.
    came_from: dict[
        tuple[int, TaxiEdge | None], tuple[tuple[int, TaxiEdge | None], bool]
    ] = {}
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
            # Après l'atterrissage, le premier tronçon de piste ne peut pas
            # repartir vers le seuil déjà franchi. Une sortie latérale reste
            # permise ; seul un départ à plus de 90° du cap piste est écarté.
            if arrived_by is None and initial_heading is not None and edge.is_runway:
                bearing = _bearing(graph, node, following)
                difference = (bearing - initial_heading + 180.0) % 360.0 - 180.0
                if abs(difference) > 90.0:
                    continue
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
            came_from[next_state] = (state, True)
            counter += 1
            heapq.heappush(
                queue,
                (candidate + heuristic(following), counter, candidate, next_state),
            )

    raise GroundError(
        f"Aucun itinéraire de roulage praticable sur {graph.icao} "
        "entre ces deux points.",
        code="ground_no_route", icao=graph.icao,
    )


# --------------------------------------------------------------------------- #
# Itinéraire dicté : la clairance du contrôleur
# --------------------------------------------------------------------------- #

# Longueur au-delà de laquelle un segment sans nom n'est plus une liaison.
#
# Le simulateur sème entre deux voies nommées de courts segments anonymes : les
# refuser ferait échouer presque toute clairance à la première jonction. Les
# accepter sans limite en ferait des raccourcis, et l'itinéraire s'écarterait
# des voies dictées par un chemin que personne n'a annoncé.
MAX_LINK_M = 80.0


def taxiway_names(graph: TaxiGraph) -> tuple[str, ...]:
    """Voies de circulation nommées du terrain, triées."""
    return tuple(sorted({
        edge.name.strip().upper()
        for edge in graph.edges
        if edge.name and not edge.is_runway
    }))


def parse_taxiways(text: str) -> tuple[str, ...]:
    """Suite de voies telle que le pilote la saisit.

    On accepte ce qu'une clairance donne à l'oreille — « N D B », « n, d, b »,
    « N-D-B » — parce que le pilote la recopie en écoutant et non en relisant.
    """
    separators = str.maketrans(",;/-\t\n", "      ")
    return tuple(
        word for word in text.translate(separators).upper().split() if word
    )


def _is_link(edge: TaxiEdge, arrived_by: TaxiEdge | None) -> bool:
    """Le segment peut-il servir de raccord entre deux voies dictées ?

    Une traversée de piste en fait partie — l'interdire rendrait inaccessibles
    les terrains où la clairance franchit une piste — mais une seule à la fois :
    deux segments de piste enchaînés, ce n'est plus une traversée, c'est un
    roulage sur la piste. Sans cette limite, une clairance impossible finissait
    par se satisfaire en remontant la piste jusqu'à la voie manquante, au lieu
    d'être signalée comme fausse.
    """
    if edge.is_runway:
        return not (arrived_by is not None and arrived_by.is_runway)
    return not edge.name and edge.length_m <= MAX_LINK_M


def follow_route(
    graph: TaxiGraph,
    start: int | Iterable[int],
    goal: int | Iterable[int],
    names: Sequence[str],
    costs: TaxiCosts = DEFAULT_COSTS,
    *,
    require_kinds: bool = True,
) -> TaxiRoute:
    """Itinéraire suivant les voies dictées, prolongé jusqu'à la piste.

    La recherche est celle de `find_route`, avec une dimension de plus dans
    l'état : le rang atteint dans la suite des voies. On ne peut, tant que la
    clairance n'est pas épuisée, que rester sur la voie en cours, entrer dans la
    suivante, ou emprunter une liaison. Le rang ne recule jamais : une clairance
    se parcourt dans l'ordre où elle a été donnée.

    La recherche est libre aux deux bouts : avant d'être entré dans la première
    voie dictée — une clairance nomme rarement celle qui sort du poste — et
    après la dernière, ce qui complète une clairance donnée en deux fois. Les
    tronçons ainsi ajoutés sont les seuls dont `from_clearance` est faux, et
    l'affichage les distingue de ce que le contrôleur a réellement dit.
    """
    if require_kinds and not graph.has_kinds:
        raise GroundError(
            f"Le tracé au sol de {graph.icao} ne distingue pas les pistes des "
            "voies de service : reprends le terrain avec le simulateur ouvert.",
            code="ground_no_kinds", icao=graph.icao,
        )
    if not names:
        raise GroundError(
            "Aucune voie de circulation n'a été saisie.",
            code="clearance_empty",
        )

    known = set(taxiway_names(graph))
    unknown = [name for name in names if name not in known]
    if unknown:
        catalogue = ", ".join(taxiway_names(graph)) or "aucune"
        raise GroundError(
            f"{graph.icao} n'a pas de voie « {unknown[0]} » "
            f"(voies du terrain : {catalogue}).",
            code="clearance_unknown_taxiway",
            icao=graph.icao, taxiway=unknown[0], taxiways=catalogue,
        )

    starts = frozenset([start] if isinstance(start, int) else start)
    goals = frozenset([goal] if isinstance(goal, int) else goal)
    if not starts or not goals:
        raise GroundError(
            "Le roulage dicté n'a pas ses deux extrémités.",
            code="ground_no_endpoints",
        )

    total = len(names)
    targets = [(graph.nodes[index].x, graph.nodes[index].y) for index in goals]

    def heuristic(node: int) -> float:
        position = graph.nodes[node]
        return min(math.hypot(position.x - x, position.y - y) for x, y in targets)

    State = tuple[int, TaxiEdge | None, int]
    best: dict[State, float] = {}
    came_from: dict[State, tuple[State, bool]] = {}
    counter = 0
    queue: list[tuple[float, int, float, State]] = []
    for index in sorted(starts):
        state: State = (index, None, 0)
        best[state] = 0.0
        counter += 1
        heapq.heappush(queue, (heuristic(index), counter, 0.0, state))

    # Rang le plus avancé jamais atteint : c'est lui qui désigne la voie sur
    # laquelle la clairance s'est rompue, et donc le message à afficher.
    furthest = 0

    while queue:
        _estimate, _tie, cost, state = heapq.heappop(queue)
        node, arrived_by, rank = state
        if cost > best.get(state, math.inf):
            continue
        furthest = max(furthest, rank)
        if rank == total and node in goals:
            return _build_route(graph, came_from, state)

        for edge in graph.neighbours(node):
            if not costs.allows(edge):
                continue
            following = edge.other(node)
            if arrived_by is not None and following == _origin(arrived_by, node):
                continue

            name = edge.name.strip().upper() if edge.name else None
            if rank < total and name == names[rank]:
                next_rank, cleared = rank + 1, True
            elif rank >= 1 and name is not None and name == names[rank - 1]:
                next_rank, cleared = rank, True
            elif rank >= 1 and rank < total and _is_link(edge, arrived_by):
                next_rank, cleared = rank, True
            elif rank in (0, total):
                # Avant la première voie dictée comme après la dernière, la
                # recherche est libre : une clairance omet presque toujours la
                # voie qui sort du poste, et s'y arrêter rendrait la saisie
                # inutilisable. Ces tronçons ne sont pas dits par le contrôleur
                # et le disent — `cleared` est faux, l'affichage les distingue.
                next_rank, cleared = rank, False
            else:
                continue

            step = edge.length_m * costs.multiplier(edge.kind)
            step += _manoeuvre_penalty(graph, node, arrived_by, edge, costs)
            candidate = cost + step
            next_state: State = (following, edge, next_rank)
            if candidate >= best.get(next_state, math.inf):
                continue
            best[next_state] = candidate
            came_from[next_state] = (state, cleared)
            counter += 1
            heapq.heappush(
                queue,
                (candidate + heuristic(following), counter, candidate, next_state),
            )

    raise _clearance_error(graph, names, furthest)


def _clearance_error(
    graph: TaxiGraph, names: Sequence[str], furthest: int
) -> GroundError:
    """Motif exact de l'échec, à l'endroit où la clairance s'est rompue.

    C'est l'information utile : savoir *quelle* voie ne se raccorde pas à la
    précédente, c'est savoir qu'on a mal entendu ce mot-là de la clairance.
    """
    if furthest >= len(names):
        return GroundError(
            f"Les voies saisies ne rejoignent pas la piste sur {graph.icao}.",
            code="clearance_no_runway", icao=graph.icao,
        )
    blocked = names[furthest]
    if furthest == 0:
        return GroundError(
            f"La voie « {blocked} » ne se rejoint pas depuis ce point "
            f"sur {graph.icao}.",
            code="clearance_unreachable", icao=graph.icao, taxiway=blocked,
        )
    return GroundError(
        f"La voie « {blocked} » ne prolonge pas « {names[furthest - 1]} » "
        f"sur {graph.icao}.",
        code="clearance_not_connected",
        icao=graph.icao, taxiway=blocked, previous=names[furthest - 1],
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
    came_from: dict[Any, tuple[Any, bool]],
    final: Any,
) -> TaxiRoute:
    """Remonte la chaîne des états jusqu'au départ et en fait un itinéraire.

    Les états de la recherche libre et ceux du roulage dicté n'ont pas la même
    forme — le second porte en plus le rang atteint dans la clairance — mais
    tous commencent par le nœud et le segment d'arrivée, les deux seuls dont la
    reconstruction a besoin.
    """
    states = [final]
    cleared: list[bool] = []
    while states[-1] in came_from:
        previous, from_clearance = came_from[states[-1]]
        cleared.append(from_clearance)
        states.append(previous)
    states.reverse()
    cleared.reverse()

    nodes = tuple(state[0] for state in states)
    edges = tuple(state[1] for state in states[1:] if state[1] is not None)
    legs = _split_into_legs(graph, nodes, edges, tuple(cleared))
    _validate_runway_crossings(graph, nodes, edges, legs)
    return TaxiRoute(
        icao=graph.icao,
        nodes=nodes,
        legs=legs,
        distance_m=round(sum(edge.length_m for edge in edges), 1),
    )


def _split_into_legs(
    graph: TaxiGraph,
    nodes: tuple[int, ...],
    edges: tuple[TaxiEdge, ...],
    cleared: tuple[bool, ...] = (),
) -> tuple[RouteLeg, ...]:
    """Regroupe les segments consécutifs parcourus sur une même voie.

    Une liaison sans nom prolonge la portion nommée en cours plutôt que d'en
    ouvrir une : le simulateur en sème entre les voies, et les annoncer une à
    une noierait les instructions utiles. Seules celles rencontrées avant toute
    voie nommée forment une portion à part, faute de quoi les rattacher.

    Le passage de la clairance à sa complétion ouvre une portion, lui aussi :
    une même portion ne peut pas être à la fois dite par le contrôleur et
    ajoutée par NaviXav, puisque l'affichage doit les distinguer.
    """
    if not edges:
        return ()
    origins = cleared or (True,) * len(edges)

    legs: list[RouteLeg] = []
    current: list[TaxiEdge] = []
    current_nodes: list[int] = [nodes[0]]
    current_name: str | None = None
    current_origin: bool = origins[0]
    turn: str | None = None
    pending_turn: str | None = None

    for position, edge in enumerate(edges):
        changes_origin = bool(current) and origins[position] != current_origin
        enters_runway = bool(current) and edge.is_runway and not current[-1].is_runway
        crosses_runway = bool(current) and bool(_crossing_runways_at_node(
            graph, nodes[position], current[-1], edge
        ))
        opens_leg = changes_origin or enters_runway or crosses_runway or (
            bool(edge.name) and current and edge.name != current_name
        )
        if opens_leg:
            legs.append(_leg(
                graph, current, current_nodes, current_name, turn,
                next_edge=edge, from_clearance=current_origin,
            ))
            turn = pending_turn
            current = []
            current_nodes = [nodes[position]]
            current_name = None
            current_origin = origins[position]

        current.append(edge)
        current_nodes.append(nodes[position + 1])
        current_name = current_name or edge.name

        if position + 1 < len(edges):
            pending_turn = _turn_label(_turn_at(graph, nodes, position + 1))

    legs.append(_leg(
        graph, current, current_nodes, current_name, turn, None,
        from_clearance=current_origin,
    ))
    return tuple(legs)


def _crossing_runways_at_node(
    graph: TaxiGraph,
    node: int,
    incoming: TaxiEdge,
    outgoing: TaxiEdge,
) -> tuple[str, ...]:
    """Pistes réellement traversées par deux segments de taxiway.

    Toucher un nœud de piste ne suffit pas : deux raccordements peuvent rester
    du même côté de la ligne médiane. Les extrémités doivent se trouver de part
    et d'autre de l'axe publié par MSFS. Cette distinction évite de créer une
    fausse attente lors d'un virage effectué entièrement avant la piste.
    """
    if incoming.is_runway or outgoing.is_runway:
        return ()
    centre = graph.nodes[node]
    before = graph.nodes[incoming.other(node)]
    after = graph.nodes[outgoing.other(node)]
    crossed: set[str] = set()
    for runway_edge in graph.neighbours(node):
        if not runway_edge.is_runway or not runway_edge.runway:
            continue
        runway_point = graph.nodes[runway_edge.other(node)]
        axis_x = runway_point.x - centre.x
        axis_y = runway_point.y - centre.y
        before_side = axis_x * (before.y - centre.y) - axis_y * (before.x - centre.x)
        after_side = axis_x * (after.y - centre.y) - axis_y * (after.x - centre.x)
        if before_side * after_side < -1e-6:
            crossed.add(runway_edge.runway)
    return tuple(sorted(crossed))


def _validate_runway_crossings(
    graph: TaxiGraph,
    nodes: tuple[int, ...],
    edges: tuple[TaxiEdge, ...],
    legs: tuple[RouteLeg, ...],
) -> None:
    """Refuse toute traversée de piste qui ne porte pas une attente explicite.

    Le découpage normal sait annoncer les entrées par un segment de piste et
    les croisements topologiques. Le contrôle final reste volontairement
    indépendant : une future modification du regroupement des portions ne doit
    jamais pouvoir rendre une traversée silencieuse.
    """
    if not edges:
        return

    announced = {
        (leg.points[-1], leg.hold_short)
        for leg in legs
        if leg.points and leg.hold_short
    }
    required: set[tuple[tuple[float, float], str]] = set()

    for position in range(1, len(nodes) - 1):
        for runway in _crossing_runways_at_node(
            graph, nodes[position], edges[position - 1], edges[position]
        ):
            point = graph.nodes[nodes[position]]
            required.add(((point.x, point.y), runway))

    for position, edge in enumerate(edges):
        if not edge.is_runway or position == 0 or edges[position - 1].is_runway:
            continue
        point = graph.nodes[nodes[position]]
        if edge.runway:
            required.add(((point.x, point.y), edge.runway))

    # Un départ s'arrête au raccordement avec sa piste sans parcourir le
    # segment de piste lui-même : cette limite doit elle aussi être annoncée.
    if not edges[-1].is_runway:
        final = graph.nodes[nodes[-1]]
        for edge in graph.neighbours(nodes[-1]):
            if edge.is_runway and edge.runway:
                required.add(((final.x, final.y), edge.runway))

    missing = sorted(required - announced, key=lambda item: item[1])
    if missing:
        runway = missing[0][1]
        raise GroundError(
            f"Le tracé calculé à {graph.icao} traverse la piste {runway} "
            "sans point d'attente exploitable ; route refusée.",
            code="ground_unsafe_runway_crossing",
            icao=graph.icao,
            runway=runway,
        )



def _leg(
    graph: TaxiGraph,
    edges: list[TaxiEdge],
    nodes: list[int],
    name: str | None,
    turn: str | None,
    next_edge: TaxiEdge | None,
    from_clearance: bool = True,
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
        from_clearance=from_clearance,
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
