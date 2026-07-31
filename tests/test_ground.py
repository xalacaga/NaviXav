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

import pytest

from navixav.ground import (
    ARRIVAL,
    DEPARTURE,
    GroundError,
    TaxiCosts,
    build_graph,
    find_route,
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
    assert len(graph.edges) == len(_PATHS)
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
    assert graph.runway_entries("09") == (3,)


def test_runway_entries_accept_an_unpadded_number(graph):
    assert graph.runway_entries("9") == graph.runway_entries("09")


def test_the_network_knows_which_runways_it_serves(graph):
    assert graph.runway_names() == ("09",)


def test_a_parking_is_attached_to_the_stand_that_serves_it(graph):
    """Le nœud 8 est plus proche, mais il ne dessert aucun poste."""
    parking = graph.parking("porte A 1")
    assert parking is not None
    assert parking.node == 7
    assert parking.lead_in_m == pytest.approx(math.hypot(50.0, 5.0), abs=0.1)


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
    assert first["kind"] == "stand"
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


def test_the_lead_in_line_counts_in_the_total_distance(graph):
    plan = plan_taxi(graph, parking="porte A 1", runway="09")
    assert plan.has_lead_in
    assert plan.distance_m == pytest.approx(
        plan.route.distance_m + plan.parking.lead_in_m, abs=0.2
    )


def test_the_summary_names_both_ends(graph):
    plan = plan_taxi(graph, parking="porte A 1", runway="09")
    assert plan.summary() == ("porte A 1", "A", "B", "attente 09")
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
            "name", "kind", "distance_m", "turn", "hold_short", "points"
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
    assert plan.route.nodes == (7, 0, 1, 3)


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
    for close in app.router.on_shutdown:
        close()


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
    assert payload["summary"] == ["porte A 1", "A", "B", "attente 09"]
    assert payload["legs"][0]["kind"] == "stand"
    assert payload["distance_m"] > 600
    assert all(leg["points"] for leg in payload["legs"])


def test_the_service_reports_an_impossible_route(routable_app):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as refused:
        _endpoint(routable_app, "/api/ground/{icao}/route")(
            "TEST", "porte Z 9", "09", DEPARTURE
        )
    assert refused.value.status_code == 404
    assert "poste nommé" in refused.value.detail
