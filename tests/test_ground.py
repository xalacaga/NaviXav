"""Réseau de roulage : construction du graphe et calcul d'itinéraire.

La base de référence a été extraite avant que NaviXav ne demande le nom et la
nature des segments : elle sert à éprouver l'échelle et la connexité, mais elle
ne peut rien prouver du guidage. Les règles de roulage se vérifient donc sur un
aérodrome synthétique, dont la géométrie est choisie pour que chaque règle ait
une conséquence mesurable.

                    5 (0,400) ══════ 4 (300,400) ══════ 6 (600,400)   piste 09
                                          ║                   │
                                          ║ piste             │ C
                                     3 (300,300) attente      │
                                          │                   │
                                          │ B                 │
        8 (-50,-40) ── 0 (0,0) ─────── 1 (300,0) ───────── 2 (700,0)
                       │        A                    A
                  7 (0,-20) desserte de poste
                       ·
                  poste (-50,-25)

    ═ piste    │ ─ voie de circulation
    Un raccourci fermé relie 0 à 3 : plus court, il ne doit jamais servir.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from navixav.ground import (
    ARRIVAL,
    DEPARTURE,
    GroundError,
    Parking,
    TaxiCosts,
    TaxiEdge,
    TaxiGraph,
    TaxiNode,
    build_graph,
    find_route,
    parse_taxiways,
    plan_taxi,
)
from navixav.navdata import msfs_store
from navixav.navdata.msfs import MsfsProvider

# Natures de segment, telles que le simulateur les code.
TAXI, RUNWAY, PARKING, PATH, CLOSED, VEHICLE = 1, 2, 3, 4, 5, 6
NORMAL, HOLD_SHORT = 1, 2

# Indices dans la table des noms : 0 est l'entrée vide.
NAMES = ["", "A", "B", "C"]
A, B, C, ANONYMOUS = 1, 2, 3, 0

_POINTS = [
    (0.0, 0.0, NORMAL),
    (300.0, 0.0, NORMAL),
    (700.0, 0.0, NORMAL),
    (300.0, 300.0, HOLD_SHORT),
    (300.0, 400.0, NORMAL),
    (0.0, 400.0, NORMAL),
    (600.0, 400.0, NORMAL),
    (0.0, -20.0, NORMAL),
    (-50.0, -40.0, NORMAL),
]

_PATHS = [
    (TAXI, 23.0, 0, 1, A, None),
    (TAXI, 23.0, 1, 2, A, None),
    (TAXI, 23.0, 1, 3, B, None),
    (TAXI, 23.0, 2, 6, C, None),
    (RUNWAY, 45.0, 3, 4, ANONYMOUS, "09"),
    (RUNWAY, 45.0, 5, 4, ANONYMOUS, "09"),
    (RUNWAY, 45.0, 4, 6, ANONYMOUS, "09"),
    (CLOSED, 23.0, 0, 3, ANONYMOUS, None),
    (PATH, 20.0, 7, 0, ANONYMOUS, None),
    (PARKING, 20.0, 7, 0, ANONYMOUS, None),
    (PATH, 23.0, 8, 0, ANONYMOUS, None),
]


def _airport() -> dict:
    return {
        "icao": "TEST", "name": "Aérodrome d'essai", "lat": 48.0, "lon": 7.0,
        "altitude_ft": 500.0, "transition_altitude_ft": 5000,
        "transition_level_ft": None,
        "runways": [{
            "primary": "09", "secondary": "27", "lat": 48.0, "lon": 7.0,
            "altitude_ft": 500.0, "heading_true": 90.0, "length_ft": 6000,
            "width_ft": 148, "surface": "asphalte",
            "primary_ils": None, "secondary_ils": None,
        }],
        "frequencies": [], "approaches": [], "departures": [], "arrivals": [],
        "taxi_names": NAMES,
        "taxi_points": [
            {"x": x, "y": y, "type": kind} for x, y, kind in _POINTS
        ],
        "taxi_paths": [
            {"type": kind, "width_m": width, "start": start, "end": end,
             "name_index": name, "runway": runway}
            for kind, width, start, end, name, runway in _PATHS
        ],
        "taxi_parkings": [{
            "name_index": 12, "number": 1, "suffix": 0, "type": 7,
            "heading": 90.0, "radius_m": 20.0, "x": -50.0, "y": -25.0,
        }],
    }


@pytest.fixture(scope="module")
def graph(tmp_path_factory):
    store = tmp_path_factory.mktemp("ground") / "navixav.sqlite"
    connection = msfs_store.connect(store)
    msfs_store.store_airport(connection, _airport())
    connection.close()

    provider = MsfsProvider(store, allow_fetch=False)
    yield build_graph(provider, "TEST")
    provider.close()


# --------------------------------------------------------------------------- #
# Construction du réseau
# --------------------------------------------------------------------------- #


def test_the_graph_carries_every_point_and_segment(graph):
    assert len(graph.nodes) == len(_POINTS)
    # Un chemin de parking relie un taxi_point à un index de parking : ce
    # n'est pas une arête du réseau de roulage.
    assert len(graph.edges) == len(_PATHS) - 1
    assert all(edge.kind != "parking" for edge in graph.edges)
    assert graph.has_kinds
    assert graph.has_names


def test_segment_lengths_come_from_the_geometry(graph):
    edge = next(e for e in graph.edges if {e.start, e.end} == {0, 1})
    assert edge.length_m == pytest.approx(300.0)


def test_a_hold_short_point_is_recognised(graph):
    assert graph.nodes[3].is_hold_short
    assert not graph.nodes[1].is_hold_short


def test_runway_entries_are_where_the_taxiways_meet_the_runway(graph):
    """Les autres points de la piste lui sont intérieurs et ne mènent nulle part."""
    assert graph.runway_entries("09") == (3, 6)


def test_runway_entries_accept_an_unpadded_number(graph):
    assert graph.runway_entries("9") == graph.runway_entries("09")


def test_takeoff_entry_does_not_discard_a_threshold_entry_for_a_remote_hold_marker():
    """Un marquage MSFS isolé ne doit pas imposer une intersection lointaine."""
    nodes = {
        0: TaxiNode(0, 0.0, 0.0, "normal"),
        1: TaxiNode(1, 0.0, -50.0, "normal"),
        2: TaxiNode(2, 1000.0, 0.0, "hold_short"),
        3: TaxiNode(3, 1000.0, -50.0, "normal"),
        4: TaxiNode(4, 100.0, 0.0, "normal"),
        5: TaxiNode(5, 1100.0, 0.0, "normal"),
    }
    edges = (
        TaxiEdge(0, 4, 100.0, 45.0, "runway", None, "09"),
        TaxiEdge(0, 1, 50.0, 23.0, "path", "Q", None),
        TaxiEdge(2, 5, 100.0, 45.0, "runway", None, "09"),
        TaxiEdge(2, 3, 50.0, 23.0, "path", "H3", None),
    )
    adjacency = {index: [] for index in nodes}
    for edge in edges:
        adjacency[edge.start].append(edge)
        adjacency[edge.end].append(edge)
    network = TaxiGraph(
        icao="TEST",
        origin_lat=0.0,
        origin_lon=0.0,
        nodes=nodes,
        edges=edges,
        parkings=(),
        adjacency={index: tuple(value) for index, value in adjacency.items()},
        thresholds={"09": (0.0, 0.0)},
    )

    assert network.runway_entries("09") == (0, 2)
    assert network.takeoff_entry("09") == (0,)


def test_a_taxiway_crossing_a_runway_is_split_at_an_explicit_hold():
    nodes = {
        0: TaxiNode(0, -100.0, 0.0, "normal"),
        1: TaxiNode(1, 0.0, 0.0, "normal"),
        2: TaxiNode(2, 100.0, 0.0, "normal"),
        3: TaxiNode(3, 0.0, -100.0, "normal"),
        4: TaxiNode(4, 0.0, 100.0, "normal"),
    }
    edges = (
        TaxiEdge(0, 1, 100.0, 23.0, "path", "A", None),
        TaxiEdge(1, 2, 100.0, 23.0, "path", "A", None),
        TaxiEdge(3, 1, 100.0, 45.0, "runway", None, "18"),
        TaxiEdge(1, 4, 100.0, 45.0, "runway", None, "18"),
    )
    adjacency = {index: [] for index in nodes}
    for edge in edges:
        adjacency[edge.start].append(edge)
        adjacency[edge.end].append(edge)
    network = TaxiGraph(
        icao="TEST",
        origin_lat=0.0,
        origin_lon=0.0,
        nodes=nodes,
        edges=edges,
        parkings=(),
        adjacency={index: tuple(value) for index, value in adjacency.items()},
    )

    route = find_route(network, 0, 2)

    assert route.summary() == ("A", "attente 18", "A")
    assert route.legs[0].points[-1] == (0.0, 0.0)
    assert route.legs[0].hold_short == "18"


def test_the_validator_rejects_a_certain_crossing_if_its_hold_disappears():
    from navixav.ground.route import RouteLeg, _validate_runway_crossings

    nodes = {
        0: TaxiNode(0, -100.0, 0.0, "normal"),
        1: TaxiNode(1, 0.0, 0.0, "normal"),
        2: TaxiNode(2, 100.0, 0.0, "normal"),
        3: TaxiNode(3, 0.0, -100.0, "normal"),
        4: TaxiNode(4, 0.0, 100.0, "normal"),
    }
    edges = (
        TaxiEdge(0, 1, 100.0, 23.0, "path", "A", None),
        TaxiEdge(1, 2, 100.0, 23.0, "path", "A", None),
        TaxiEdge(3, 1, 100.0, 45.0, "runway", None, "18"),
        TaxiEdge(1, 4, 100.0, 45.0, "runway", None, "18"),
    )
    adjacency = {index: [] for index in nodes}
    for edge in edges:
        adjacency[edge.start].append(edge)
        adjacency[edge.end].append(edge)
    network = TaxiGraph(
        icao="TEST",
        origin_lat=0.0,
        origin_lon=0.0,
        nodes=nodes,
        edges=edges,
        parkings=(),
        adjacency={index: tuple(value) for index, value in adjacency.items()},
    )
    silently_grouped = (
        RouteLeg(
            name="A",
            kind="path",
            distance_m=200.0,
            turn=None,
            points=((-100.0, 0.0), (0.0, 0.0), (100.0, 0.0)),
            hold_short=None,
        ),
    )

    with pytest.raises(GroundError) as error:
        _validate_runway_crossings(
            network, (0, 1, 2), edges[:2], silently_grouped
        )

    assert error.value.code == "ground_unsafe_runway_crossing"
    assert error.value.params == {"icao": "TEST", "runway": "18"}


def test_the_network_knows_which_runways_it_serves(graph):
    assert graph.runway_names() == ("09",)


def test_a_parking_is_attached_to_the_stand_that_serves_it(graph):
    """Le nœud 8 est plus proche, mais il ne dessert aucun poste."""
    parking = graph.parking("porte A 1")
    assert parking is not None
    assert parking.node == 7
    assert parking.lead_in_m == pytest.approx(math.hypot(50.0, 5.0), abs=0.1)


def test_a_parking_index_is_never_mistaken_for_a_taxi_point(graph):
    """END vaut ici 0, mais ne désigne surtout pas le taxi_point 0."""
    links = [edge for edge in graph.edges if {edge.start, edge.end} == {7, 0}]
    assert len(links) == 1
    assert links[0].kind == "path"


def test_a_parking_is_found_whatever_the_case(graph):
    assert graph.parking("PORTE A 1") is graph.parking("porte A 1")
    assert graph.parking("porte Z 9") is None


def test_nearest_node_reads_local_metres(graph):
    assert graph.nearest_node(295.0, 10.0) == 1


# --------------------------------------------------------------------------- #
# Itinéraire
# --------------------------------------------------------------------------- #


def test_a_route_follows_the_taxiways_it_is_named_after(graph):
    route = find_route(graph, 0, graph.runway_entries("09"))
    assert route.nodes == (0, 1, 3)
    assert [leg.name for leg in route.legs] == ["A", "B"]


def test_a_route_announces_the_runway_it_must_hold_short_of(graph):
    route = find_route(graph, 0, graph.runway_entries("09"))
    assert route.legs[-1].hold_short == "09"
    assert route.summary() == ("A", "B", "attente 09")


def test_a_route_names_the_direction_of_each_turn(graph):
    """Cap à l'est puis au nord : c'est un virage à gauche."""
    route = find_route(graph, 0, graph.runway_entries("09"))
    assert [leg.turn for leg in route.legs] == [None, "left"]


def test_route_distance_is_the_ground_distance_not_the_cost(graph):
    """Les pénalités orientent le choix ; elles ne s'ajoutent pas au trajet."""
    route = find_route(graph, 0, graph.runway_entries("09"))
    assert route.distance_m == pytest.approx(600.0)


def test_a_closed_segment_is_never_taken(graph):
    """Le raccourci fermé est plus court : seule son interdiction l'écarte."""
    shortcut = next(e for e in graph.edges if e.kind == "closed")
    assert shortcut.length_m < 600.0
    assert find_route(graph, 0, 3).nodes == (0, 1, 3)


def test_lifting_the_ban_would_take_the_shortcut(graph):
    """Contrôle du contraire : sans l'interdiction, le raccourci l'emporte."""
    costs = TaxiCosts(forbidden_kinds=frozenset())
    assert find_route(graph, 0, 3, costs).nodes == (0, 3)


def test_taxiing_along_a_runway_is_a_last_resort(graph):
    """Le détour par les voies est plus long, mais c'est celui qu'on veut."""
    route = find_route(graph, 0, 6)
    assert route.nodes == (0, 1, 2, 6)
    assert all(leg.kind != "runway" for leg in route.legs)


def test_without_that_penalty_the_runway_would_win(graph):
    costs = TaxiCosts(kind_multipliers={"runway": 1.0})
    assert find_route(graph, 0, 6, costs).nodes == (0, 1, 3, 4, 6)


def test_a_runway_can_still_be_vacated(graph):
    """Pénalisée n'est pas interdite : on quitte bien la piste par la piste."""
    route = find_route(graph, 5, 0)
    assert route.nodes == (5, 4, 3, 1, 0)


def test_an_aircraft_too_wide_for_a_taxiway_is_refused(graph):
    costs = TaxiCosts(min_width_m=30.0)
    with pytest.raises(GroundError, match="Aucun itinéraire"):
        find_route(graph, 0, 2, costs)


def test_a_route_to_oneself_is_empty(graph):
    route = find_route(graph, 3, 3)
    assert route.is_empty
    assert route.distance_m == 0.0
    assert route.legs == ()


def test_an_unknown_point_is_reported(graph):
    with pytest.raises(GroundError, match="n'appartient pas"):
        find_route(graph, 0, 9999)


def test_a_route_without_destination_is_reported(graph):
    with pytest.raises(GroundError, match="destination"):
        find_route(graph, 0, ())


# --------------------------------------------------------------------------- #
# Itinéraire complet, poste compris
# --------------------------------------------------------------------------- #


def test_a_departure_starts_at_the_stand_and_ends_short_of_the_runway(graph):
    plan = plan_taxi(graph, parking="porte A 1", runway="09")
    assert plan.direction == DEPARTURE
    first, last = plan.legs()[0], plan.legs()[-1]
    # Le poste d'essai est une porte : on le quitte tracté, et le tronçon le
    # dit. Voir les épreuves du repoussage plus bas.
    assert first["kind"] == "pushback"
    assert first["points"][0] == {"x": -50.0, "y": -25.0}
    assert last["hold_short"] == "09"


def test_an_arrival_runs_the_other_way(graph):
    plan = plan_taxi(graph, parking="porte A 1", runway="09", direction=ARRIVAL)
    legs = plan.legs()
    assert legs[-1]["kind"] == "stand"
    assert legs[-1]["points"][-1] == {"x": -50.0, "y": -25.0}
    assert plan.route.nodes[0] in plan.entries


def test_an_arrival_leaves_the_runway_by_its_nearest_exit(graph):
    """Les sorties sont toutes proposées : c'est la recherche qui choisit."""
    plan = plan_taxi(graph, parking="porte A 1", runway="09", direction=ARRIVAL)
    assert plan.route.nodes[0] == 3
    assert plan.route.nodes[-1] == graph.parking("porte A 1").node


def _directional_arrival_graph() -> TaxiGraph:
    """Deux sorties : la plus courte vers la porte est derrière l'avion."""
    nodes = {
        index: TaxiNode(index, x, y, NORMAL)
        for index, (x, y) in enumerate((
            (0.0, 0.0), (100.0, 0.0), (200.0, 0.0), (300.0, 0.0),
            (100.0, -100.0), (300.0, -100.0), (150.0, -200.0),
        ))
    }
    edges = (
        TaxiEdge(0, 1, 100.0, 45.0, "runway", None, "09"),
        TaxiEdge(1, 2, 100.0, 45.0, "runway", None, "09"),
        TaxiEdge(2, 3, 100.0, 45.0, "runway", None, "09"),
        TaxiEdge(1, 4, 100.0, 23.0, "taxi", "A", None),
        TaxiEdge(4, 6, 180.0, 23.0, "taxi", "A", None),
        TaxiEdge(3, 5, 100.0, 23.0, "taxi", "B", None),
        TaxiEdge(5, 6, 180.0, 23.0, "taxi", "B", None),
    )
    adjacency = {index: [] for index in nodes}
    for edge in edges:
        adjacency[edge.start].append(edge)
        adjacency[edge.end].append(edge)
    return TaxiGraph(
        icao="TEST",
        origin_lat=0.0,
        origin_lon=0.0,
        nodes=nodes,
        edges=edges,
        parkings=(Parking("porte 32", "porte grande", 150.0, -220.0,
                          20.0, 0.0, 6, 20.0),),
        adjacency={index: tuple(items) for index, items in adjacency.items()},
        runway_headings={"09": 90.0, "27": 270.0},
        routable_nodes=frozenset(nodes),
    )


def test_an_arrival_never_returns_to_an_exit_already_passed():
    network = _directional_arrival_graph()

    # Sans position, l'ancien calcul choisit bien A, plus proche de la porte.
    assert plan_taxi(
        network, parking="porte 32", runway="09", direction=ARRIVAL
    ).route.nodes[0] == 1

    plan = plan_taxi(
        network,
        parking="porte 32",
        runway="09",
        direction=ARRIVAL,
        position=(190.0, 0.0),
    )

    assert plan.route.nodes[:2] == (2, 3)
    assert 1 not in plan.route.nodes
    assert "B" in plan.summary()


def test_the_reciprocal_runway_reverses_the_allowed_arrival_direction():
    network = _directional_arrival_graph()
    plan = plan_taxi(
        network,
        parking="porte 32",
        runway="27",
        direction=ARRIVAL,
        position=(210.0, 0.0),
    )

    assert plan.route.nodes[:2] == (2, 1)
    assert 3 not in plan.route.nodes
    assert "A" in plan.summary()


def test_the_lead_in_line_counts_in_the_total_distance(graph):
    plan = plan_taxi(graph, parking="porte A 1", runway="09")
    assert plan.has_lead_in
    assert plan.distance_m == pytest.approx(
        plan.route.distance_m + plan.parking.lead_in_m, abs=0.2
    )


def test_the_summary_names_both_ends(graph):
    plan = plan_taxi(graph, parking="porte A 1", runway="09")
    assert plan.summary() == ("porte A 1", "repoussage", "A", "B", "attente 09")
    arrival = plan_taxi(graph, parking="porte A 1", runway="09", direction=ARRIVAL)
    assert arrival.summary()[-1] == "porte A 1"


def test_the_payload_carries_what_the_map_needs(graph):
    payload = plan_taxi(graph, parking="porte A 1", runway="09").to_dict()
    assert payload["icao"] == "TEST"
    assert payload["runway"] == "09"
    assert payload["parking"]["label"] == "porte A 1"
    assert payload["distance_m"] > 0
    for leg in payload["legs"]:
        assert set(leg) == {
            "name", "kind", "distance_m", "turn", "hold_short", "points",
            "from_clearance",
        }
        assert all(set(point) == {"x", "y"} for point in leg["points"])


def test_an_unknown_parking_is_reported(graph):
    with pytest.raises(GroundError, match="poste nommé"):
        plan_taxi(graph, parking="porte Z 9", runway="09")


def test_a_runway_the_network_does_not_reach_is_reported(graph):
    with pytest.raises(GroundError, match="ne rejoint pas la piste"):
        plan_taxi(graph, parking="porte A 1", runway="18")


def test_a_departure_from_the_other_threshold_finds_the_same_entries(graph):
    """Le simulateur ne nomme qu'un seuil : « 27 » doit trouver la piste « 09 »."""
    assert graph.runway_entries("27") == graph.runway_entries("09")
    plan = plan_taxi(graph, parking="porte A 1", runway="27")
    assert plan.route.nodes == (7, 0, 1, 2, 6)


def test_the_hold_instruction_names_the_runway_the_pilot_uses(graph):
    """La géométrie ne connaît que la « 09 » ; un départ en 27 attend en 27."""
    assert graph.runway_entries("27")[0] == 3
    assert plan_taxi(graph, parking="porte A 1", runway="09").summary()[-1] == (
        "attente 09"
    )
    assert plan_taxi(graph, parking="porte A 1", runway="27").summary()[-1] == (
        "attente 27"
    )


def test_an_unknown_direction_is_reported(graph):
    with pytest.raises(GroundError, match="Sens de roulage"):
        plan_taxi(graph, parking="porte A 1", runway="09", direction="pushback")


# --------------------------------------------------------------------------- #
# Refus de conclure sur une base incomplète
# --------------------------------------------------------------------------- #


def test_a_network_without_kinds_refuses_to_route(ground_provider):
    """Sans la nature des segments, une route de service passerait pour une voie."""
    network = build_graph(ground_provider, "LFST")
    if network.has_kinds:
        pytest.skip("la base de test distingue désormais les natures de segment")
    with pytest.raises(GroundError, match="ne distingue pas"):
        find_route(network, 0, 1)
    with pytest.raises(GroundError, match="ne distingue pas"):
        network.runway_entries("05")


# --------------------------------------------------------------------------- #
# Contre la base de référence : échelle et connexité
# --------------------------------------------------------------------------- #


def _routable(provider, icao):
    """Réseau réel, ignoré si la base précède les natures de segment."""
    network = build_graph(provider, icao)
    if not network.has_kinds:
        pytest.skip(
            "base de test antérieure aux natures de segment : refaire "
            "« navixav import LFST LFBO LFPO --store "
            "tests/data/navdata_test.sqlite » avec le simulateur ouvert"
        )
    return network


@pytest.mark.parametrize(
    ("icao", "first", "second"),
    [("LFST", "05", "23"), ("LFBO", "32R", "14L"), ("LFPO", "06", "24")],
)
def test_a_departure_uses_the_threshold_it_takes_off_from(
    ground_provider, icao, first, second
):
    """On ne décolle pas des deux seuils d'une bande au même endroit.

    Le simulateur ne nomme qu'un seuil par bande, si bien qu'accepter les deux
    indifféremment renvoyait le même point d'attente dans les deux sens — soit
    toute la longueur de piste à contresens.
    """
    network = _routable(ground_provider, icao)
    assert network.takeoff_entry(first) != network.takeoff_entry(second)


@pytest.mark.parametrize(
    ("icao", "runway"), [("LFST", "05"), ("LFBO", "32R"), ("LFPO", "06")]
)
def test_an_arrival_may_vacate_by_any_exit(ground_provider, icao, runway):
    """À l'atterrissage toute sortie convient : c'est la recherche qui trie."""
    network = _routable(ground_provider, icao)
    exits = network.runway_entries(runway)
    assert len(exits) > len(network.takeoff_entry(runway))
    assert set(network.takeoff_entry(runway)) <= set(exits)


@pytest.mark.parametrize(
    ("icao", "runway"), [("LFST", "05"), ("LFBO", "32R"), ("LFPO", "24")]
)
def test_a_real_route_names_real_taxiways(ground_provider, icao, runway):
    network = _routable(ground_provider, icao)
    stand = network.parkings[len(network.parkings) // 2]
    plan = plan_taxi(network, parking=stand.label, runway=runway)
    assert plan.distance_m > 100
    # Le poste, au moins une voie nommée, et la piste devant laquelle attendre.
    assert plan.summary()[0] == stand.label
    assert len(plan.summary()) >= 2
    assert all(leg["points"] for leg in plan.legs())
    assert plan.summary()[-1].startswith("attente ")


@pytest.mark.parametrize(
    ("icao", "runway"), [("LFST", "05"), ("LFBO", "32R"), ("LFPO", "24")]
)
def test_a_departure_always_ends_on_a_hold_instruction(ground_provider, icao, runway):
    """Les entrées en piste réelles ne portent aucun marquage publié.

    À LFST, LFBO et LFPO elles sont toutes de nature « normal », les points
    d'attente publiés se trouvant en retrait sur la voie. Fonder la consigne
    sur eux seuls n'aurait annoncé aucune attente nulle part.
    """
    network = _routable(ground_provider, icao)
    entry = network.takeoff_entry(runway)[0]
    assert not network.nodes[entry].is_hold_short

    stand = network.parkings[0]
    plan = plan_taxi(network, parking=stand.label, runway=runway)
    assert plan.route.legs[-1].hold_short


@pytest.mark.parametrize("icao", ["LFST", "LFBO", "LFPO"])
def test_a_real_route_never_uses_a_service_road(ground_provider, icao):
    """Les routes de véhicules sont exclues, sur le terrain comme en principe."""
    network = _routable(ground_provider, icao)
    stand = network.parkings[0]
    plan = plan_taxi(network, parking=stand.label, runway=network.runway_names()[0])
    assert all(leg["kind"] != "vehicle" for leg in plan.legs())


def test_lfbo_e42_does_not_cut_across_the_airport(ground_provider):
    """Le END du chemin de parking E42 est l'index 3 du parking, pas le point 3."""
    network = _routable(ground_provider, "LFBO")
    plan = plan_taxi(network, parking="porte E 42", runway="32R")

    assert plan.summary()[:4] == ("porte E 42", "repoussage", "T41", "T40")
    assert plan.summary()[-2:] == ("N1", "attente 32R")
    assert all(edge.kind != "parking" for edge in network.edges)
    # Aucun segment individuel de cet itinéraire local ne doit traverser tout
    # le terrain. La fausse liaison 927 -> 19 mesurait 1 215 m.
    t40 = next(leg for leg in plan.legs() if leg["name"] == "T40")
    assert t40["distance_m"] < 300
    assert len(t40["points"]) > 5


@pytest.mark.parametrize("icao", ["LFST", "LFBO", "LFPO"])
def test_a_real_airport_builds_a_usable_network(ground_provider, icao):
    network = build_graph(ground_provider, icao)
    assert len(network.nodes) > 300
    assert network.parkings
    assert all(parking.node in network.nodes for parking in network.parkings)


@pytest.mark.parametrize("icao", ["LFST", "LFBO", "LFPO"])
def test_every_parking_can_reach_every_other(ground_provider, icao):
    """Un réseau morcelé rendrait le guidage muet sur la moitié des postes."""
    network = build_graph(ground_provider, icao)
    first, last = network.parkings[0], network.parkings[-1]
    route = find_route(network, first.node, last.node, require_kinds=False)
    assert route.distance_m > 0
    assert route.nodes[0] == first.node
    assert route.nodes[-1] == last.node


def test_an_airport_without_ground_geometry_is_reported(ground_provider):
    with pytest.raises(GroundError, match="absent"):
        build_graph(ground_provider, "ZZZZ")


# --------------------------------------------------------------------------- #
# Service web
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def routable_app(tmp_path_factory):
    """Service monté sur un terrain dont le réseau est complet."""
    from navixav.config import Settings
    from navixav.web.app import create_app

    store = tmp_path_factory.mktemp("ground-api") / "navixav.sqlite"
    connection = msfs_store.connect(store)
    msfs_store.store_airport(connection, _airport())
    connection.close()

    app = create_app(Settings(navdata_store=store, metar_source="simbrief"))
    yield app
    app.state.close_resources()


def _endpoint(app, path):
    return next(route.endpoint for route in app.routes if route.path == path)


def test_the_service_lists_the_parkings_and_the_runways_served(routable_app):
    payload = _endpoint(routable_app, "/api/ground/{icao}/parkings")("TEST")
    assert payload["routable"] is True
    assert payload["named"] is True
    assert payload["runways"] == ["09"]
    assert [p["label"] for p in payload["parkings"]] == ["porte A 1"]


def test_the_service_returns_a_drawable_route(routable_app):
    payload = _endpoint(routable_app, "/api/ground/{icao}/route")(
        "TEST", "porte A 1", "09", DEPARTURE
    )
    assert payload["summary"] == ["porte A 1", "repoussage", "A", "B", "attente 09"]
    assert payload["legs"][0]["kind"] == "pushback"
    # Le bandeau lit la manœuvre du tracteur au niveau du plan, pas du tronçon :
    # tous les tronçons gardent la même forme.
    assert payload["pushback"] == {
        "distance_m": 50.2, "heading": 0, "target": {"x": 0.0, "y": -20.0},
    }
    assert payload["distance_m"] > 600
    assert all(leg["points"] for leg in payload["legs"])


def test_the_service_reports_an_impossible_route(routable_app):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as refused:
        _endpoint(routable_app, "/api/ground/{icao}/route")(
            "TEST", "porte Z 9", "09", DEPARTURE
        )
    assert refused.value.status_code == 404
    assert refused.value.detail["code"] == "ground_unknown_parking"
    assert refused.value.detail["params"]["parking"] == "porte Z 9"
    assert "poste nommé" in refused.value.detail["message"]


# --------------------------------------------------------------------------- #
# Roulage dicté par le contrôleur
# --------------------------------------------------------------------------- #


def test_a_clearance_is_read_the_way_it_is_heard():
    assert parse_taxiways("N D B") == ("N", "D", "B")
    assert parse_taxiways("n, d, b") == ("N", "D", "B")
    assert parse_taxiways("A-B/C") == ("A", "B", "C")
    assert parse_taxiways("   ") == ()


def test_the_dictated_route_follows_the_named_taxiways(graph):
    plan = plan_taxi(graph, parking="porte A 1", runway="09", via=("A", "B"))
    assert plan.is_dictated
    assert [leg["name"] for leg in plan.legs() if leg["name"]] == [
        "porte A 1", "A", "B"
    ]
    assert plan.summary() == ("porte A 1", "repoussage", "A", "B", "attente 09")


def test_the_dictated_route_matches_the_automatic_one_when_it_is_the_same(graph):
    dictated = plan_taxi(graph, parking="porte A 1", runway="09", via=("A", "B"))
    automatic = plan_taxi(graph, parking="porte A 1", runway="09")
    assert dictated.polyline() == automatic.polyline()
    assert not dictated.is_completed


def test_a_clearance_stopping_short_is_completed_and_says_so(graph):
    """Le contrôleur n'a dit que « A » : le reste est ajouté, et se distingue."""
    plan = plan_taxi(graph, parking="porte A 1", runway="09", via=("A",))
    assert plan.is_completed
    added = [leg["name"] for leg in plan.legs() if not leg["from_clearance"]]
    assert "B" in added


def test_the_leg_of_the_clearance_itself_is_not_marked_as_added(graph):
    plan = plan_taxi(graph, parking="porte A 1", runway="09", via=("A",))
    cleared = [
        leg["name"] for leg in plan.legs()
        if leg["from_clearance"] and leg["name"]
        and leg["kind"] not in ("stand", "pushback")
    ]
    assert cleared == ["A"]


def test_an_unknown_taxiway_is_reported_with_the_ones_that_exist(graph):
    with pytest.raises(GroundError) as refused:
        plan_taxi(graph, parking="porte A 1", runway="09", via=("Z",))
    assert "« Z »" in str(refused.value)
    assert "A, B, C" in str(refused.value)


def test_a_taxiway_that_does_not_extend_the_previous_one_is_reported(graph):
    """Le message doit nommer la voie fautive : c'est le mot mal entendu."""
    with pytest.raises(GroundError) as refused:
        plan_taxi(graph, parking="porte A 1", runway="09", via=("A", "B", "C"))
    assert "« C »" in str(refused.value)
    assert "« B »" in str(refused.value)


def test_a_clearance_omitting_the_stand_taxiway_still_works(graph):
    """« B » seul depuis le poste : A est ajoutée, marquée comme telle."""
    plan = plan_taxi(graph, parking="porte A 1", runway="09", via=("B",))
    named = {leg["name"]: leg["from_clearance"] for leg in plan.legs() if leg["name"]}
    assert named["B"] is True
    assert named["A"] is False


def test_the_dictated_route_never_takes_the_closed_shortcut(graph):
    """Le raccourci fermé 0→3 reste interdit, clairance ou pas."""
    plan = plan_taxi(graph, parking="porte A 1", runway="09", via=("A", "B"))
    assert plan.distance_m > 600


def test_the_arrival_can_be_dictated_too(graph):
    plan = plan_taxi(
        graph, parking="porte A 1", runway="09", direction=ARRIVAL, via=("B", "A")
    )
    assert plan.is_dictated
    assert plan.summary()[-1] == "porte A 1"


def test_the_payload_announces_the_clearance(graph):
    payload = plan_taxi(
        graph, parking="porte A 1", runway="09", via=("A", "B")
    ).to_dict()
    assert payload["via"] == ["A", "B"]
    assert payload["dictated"] is True
    assert payload["completed"] is False


def test_the_service_accepts_a_dictated_route(routable_app):
    payload = _endpoint(routable_app, "/api/ground/{icao}/route")(
        "TEST", "porte A 1", "09", DEPARTURE, "A B"
    )
    assert payload["via"] == ["A", "B"]
    assert payload["dictated"] is True


def test_the_service_reports_why_a_clearance_is_impossible(routable_app):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as refused:
        _endpoint(routable_app, "/api/ground/{icao}/route")(
            "TEST", "porte A 1", "09", DEPARTURE, "A B C"
        )
    assert refused.value.status_code == 404
    # Le détail part structuré : le client compose la phrase dans sa langue.
    assert refused.value.detail["code"] == "clearance_not_connected"
    assert refused.value.detail["params"] == {
        "icao": "TEST", "taxiway": "C", "previous": "B",
    }


def test_no_clearance_keeps_the_automatic_route(routable_app):
    payload = _endpoint(routable_app, "/api/ground/{icao}/route")(
        "TEST", "porte A 1", "09", DEPARTURE, ""
    )
    assert payload["dictated"] is False
    assert payload["summary"] == ["porte A 1", "repoussage", "A", "B", "attente 09"]


def test_every_ground_error_code_is_translated_in_every_language():
    """Un code sans traduction s'afficherait en français chez tout le monde.

    C'est exactement le défaut qui avait échappé : le service composait la
    phrase, et l'interface anglaise affichait du français. Le message français
    reste comme repli, mais le dépôt exige la traduction complète.
    """
    import re

    root = Path(__file__).resolve().parents[1]
    codes = set()
    for module in (root / "navixav" / "ground").glob("*.py"):
        codes |= set(re.findall(r'code="([a-z_]+)"', module.read_text("utf-8")))
    assert codes, "aucun code d'erreur trouvé dans le module au sol"

    catalogue = (root / "navixav" / "web" / "static" / "i18n.js").read_text("utf-8")
    missing = {
        code: catalogue.count(f"err_{code}:")
        for code in sorted(codes)
        if catalogue.count(f"err_{code}:") != 8
    }
    assert not missing, f"codes sans leurs huit traductions : {missing}"


# --------------------------------------------------------------------------- #
# Repoussage
# --------------------------------------------------------------------------- #


def _graph_with_stand(tmp_path: Path, *, name_index: int, kind: int):
    """Le même aérodrome, avec un poste d'une autre nature."""
    airport = _airport()
    airport["taxi_parkings"][0] |= {"name_index": name_index, "type": kind}
    store = tmp_path / "navixav.sqlite"
    connection = msfs_store.connect(store)
    msfs_store.store_airport(connection, airport)
    connection.close()

    provider = MsfsProvider(store, allow_fetch=False)
    try:
        return build_graph(provider, "TEST")
    finally:
        provider.close()


def test_a_gate_is_left_by_a_pushback_facing_the_taxiway(graph):
    """Un avion nez au terminal n'en sort pas par ses propres moyens.

    La ligne de guidage est la même, parcourue en marche arrière : le tracé et
    la distance ne changent pas, seule la nature du tronçon le dit.
    """
    plan = plan_taxi(graph, parking="porte A 1", runway="09")

    assert plan.needs_pushback
    assert plan.legs()[0]["kind"] == "pushback"
    pushback = plan.pushback()
    assert pushback["distance_m"] == pytest.approx(plan.parking.lead_in_m, abs=0.1)
    # Le poste regarde l'est, la desserte rejoint le réseau vers le nord : une
    # fois repoussé, l'avion présente le cap de la voie qu'il va suivre. C'est
    # l'orientation obtenue qui s'annonce, jamais le côté du mouvement — « nez
    # à gauche » est un calque, pas de la phraséologie française.
    assert plan.parking.heading == 90.0
    assert pushback["heading"] == 0
    assert "nose" not in pushback
    # Le guidage lit `turn` pour annoncer les virages du roulage : une consigne
    # de tracteur n'en est pas un.
    assert plan.legs()[0]["turn"] is None
    assert plan.summary()[:2] == ("porte A 1", "repoussage")


def test_a_general_aviation_ramp_is_left_under_its_own_power(tmp_path):
    """Annoncer un repoussage devant un hangar serait faux."""
    network = _graph_with_stand(tmp_path, name_index=1, kind=2)
    plan = plan_taxi(network, parking="parking 1", runway="09")

    assert plan.parking.kind == "rampe GA"
    assert not plan.needs_pushback
    assert plan.pushback() is None
    assert plan.legs()[0]["kind"] == "stand"
    assert "repoussage" not in plan.summary()


def test_a_taxi_taken_up_again_does_not_push_back_a_second_time(graph):
    """Repris en cours de roulage, le départ ne repasse pas par le poste."""
    plan = plan_taxi(graph, parking="porte A 1", runway="09", position=(150.0, 0.0))

    assert plan.from_position
    assert not plan.needs_pushback
    assert plan.pushback() is None
    assert all(leg["kind"] != "pushback" for leg in plan.legs())


def test_an_arrival_is_never_a_pushback(graph):
    """À l'arrivée, l'avion entre au poste : le tracteur n'y est pour rien."""
    plan = plan_taxi(graph, parking="porte A 1", runway="09", direction=ARRIVAL)

    assert not plan.needs_pushback
    assert plan.pushback() is None
    assert plan.legs()[-1]["kind"] == "stand"


def test_the_pushback_heading_follows_the_route_not_the_stand(tmp_path):
    """Le cap annoncé est celui de la voie, quel que soit le cap au poste.

    Le poste regarde ici le sud, la desserte rejoint toujours le réseau vers le
    nord : c'est elle qui commande, sans quoi le bandeau annoncerait un cap que
    le tracé dément.
    """
    airport = _airport()
    airport["taxi_parkings"][0]["heading"] = 180.0
    store = tmp_path / "navixav.sqlite"
    connection = msfs_store.connect(store)
    msfs_store.store_airport(connection, airport)
    connection.close()
    provider = MsfsProvider(store, allow_fetch=False)
    try:
        network = build_graph(provider, "TEST")
    finally:
        provider.close()

    plan = plan_taxi(network, parking="porte A 1", runway="09")

    assert plan.parking.heading == 180.0
    assert plan.pushback()["heading"] == 0
