"""Guidage au sol : où en est l'avion, et que lui dit-on.

Les règles se vérifient sur l'aérodrome synthétique de `test_ground`, dont la
géométrie rend chaque conséquence mesurable, puis contre les trois terrains
réels pour ce qui ne se simule pas — la finesse du découpage des courbes, la
densité du réseau.
"""

from __future__ import annotations

import math

import pytest

from navixav.ground import (
    ARRIVAL,
    OFF_ROUTE_M,
    TaxiGraph,
    TaxiNode,
    build_graph,
    forget_graphs,
    guide,
    plan_taxi,
    project_on_route,
    replan,
    replan_needed,
)
from navixav.ground import route as route_module
from navixav.ground.plan import JOIN_KIND, MIN_JOIN_M, STAND_KIND
from navixav.navdata import msfs_store
from navixav.navdata.msfs import MsfsProvider
from tests.test_ground import _airport

EARTH_RADIUS_M = 6378137.0
ORIGIN_LAT, ORIGIN_LON = 48.0, 7.0


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    path = tmp_path_factory.mktemp("guidance") / "navixav.sqlite"
    connection = msfs_store.connect(path)
    msfs_store.store_airport(connection, _airport())
    connection.close()
    return path


@pytest.fixture(scope="module")
def graph(store):
    provider = MsfsProvider(store, allow_fetch=False)
    yield build_graph(provider, "TEST", cache=False)
    provider.close()


@pytest.fixture(scope="module")
def departure(graph):
    return plan_taxi(graph, parking="porte A 1", runway="09")


def to_latlon(x: float, y: float) -> tuple[float, float]:
    """Inverse de la projection locale, pour parler au service en degrés."""
    return (
        ORIGIN_LAT + math.degrees(y / EARTH_RADIUS_M),
        ORIGIN_LON + math.degrees(
            x / (EARTH_RADIUS_M * math.cos(math.radians(ORIGIN_LAT)))
        ),
    )


# --------------------------------------------------------------------------- #
# Projection sur le tracé
# --------------------------------------------------------------------------- #


def test_a_position_on_the_route_has_no_lateral_error():
    points = ((0.0, 0.0), (100.0, 0.0))
    fix = project_on_route(points, 40.0, 0.0)
    assert fix.travelled_m == pytest.approx(40.0)
    assert fix.lateral_m == pytest.approx(0.0)


def test_a_position_beside_the_route_keeps_its_distance():
    points = ((0.0, 0.0), (100.0, 0.0))
    fix = project_on_route(points, 40.0, 30.0)
    assert fix.travelled_m == pytest.approx(40.0)
    assert fix.lateral_m == pytest.approx(30.0)


def test_a_position_past_the_end_stops_at_the_end():
    points = ((0.0, 0.0), (100.0, 0.0))
    fix = project_on_route(points, 250.0, 0.0)
    assert fix.travelled_m == pytest.approx(100.0)
    assert fix.lateral_m == pytest.approx(150.0)


def test_projection_follows_the_segment_not_the_nearest_point():
    """Un aller-retour met deux portions du tracé côte à côte.

    Rabattu sur le point le plus proche, l'avion sauterait du brin aller au brin
    retour, annonçant un virage déjà passé ou une distance qui augmente. Rabattu
    sur le segment, la progression reste celle du brin qu'il parcourt.
    """
    # Aller vers l'est en y = 0, demi-tour, retour vers l'ouest en y = 10.
    points = ((0.0, 0.0), (200.0, 0.0), (200.0, 10.0), (0.0, 10.0))
    fix = project_on_route(points, 100.0, 4.0)
    assert fix.travelled_m == pytest.approx(100.0)
    assert fix.lateral_m == pytest.approx(4.0)

    # Un mètre plus loin de l'aller : c'est le brin retour qui est le plus proche.
    late = project_on_route(points, 100.0, 6.0)
    assert late.travelled_m == pytest.approx(310.0)


def test_a_route_reduced_to_one_point_still_answers():
    fix = project_on_route(((0.0, 0.0),), 30.0, 40.0)
    assert fix.travelled_m == 0.0
    assert fix.lateral_m == pytest.approx(50.0)


# --------------------------------------------------------------------------- #
# Virage mesuré sur une fenêtre
# --------------------------------------------------------------------------- #


def _line_graph(points):
    """Graphe réduit à une suite de points : de quoi mesurer un angle."""
    nodes = {
        index: TaxiNode(index=index, x=x, y=y, kind=None)
        for index, (x, y) in enumerate(points)
    }
    return TaxiGraph(
        icao="TEST", origin_lat=0.0, origin_lon=0.0,
        nodes=nodes, edges=(), parkings=(),
    )


def _quarter_turn(radius: float = 50.0, steps: int = 9):
    """Virage à droite adouci, tel que le simulateur les découpe.

    Une ligne droite, un quart de tour en `steps` segments, puis une autre
    ligne droite.
    """
    points = [(0.0, -80.0), (0.0, 0.0)]
    for step in range(1, steps + 1):
        angle = math.radians(90.0 * step / steps)
        points.append((radius * (1 - math.cos(angle)), radius * math.sin(angle)))
    points.append((points[-1][0] + 80.0, points[-1][1]))
    return points


def test_a_smoothed_turn_is_invisible_between_two_segments():
    """Contrôle : c'est bien la mesure d'origine qui laissait passer le virage."""
    points = _quarter_turn()
    graph = _line_graph(points)
    nodes = list(range(len(points)))
    middle = len(points) // 2

    incoming = route_module._bearing(graph, nodes[middle - 1], nodes[middle])
    outgoing = route_module._bearing(graph, nodes[middle], nodes[middle + 1])
    single = (outgoing - incoming + 180.0) % 360.0 - 180.0
    assert abs(single) < 30.0
    assert route_module._turn_label(single) is None


def test_a_smoothed_turn_is_seen_over_a_window():
    """Sans cette fenêtre, aucun quart de tour réel n'était annoncé."""
    points = _quarter_turn()
    graph = _line_graph(points)
    nodes = list(range(len(points)))
    middle = len(points) // 2

    degrees = route_module._turn_at(graph, nodes, middle)
    assert degrees >= 30.0
    assert route_module._turn_label(degrees) == "right"


def test_a_smoothed_turn_the_other_way_reads_left():
    points = [(-x, y) for x, y in _quarter_turn()]
    graph = _line_graph(points)
    nodes = list(range(len(points)))
    degrees = route_module._turn_at(graph, nodes, len(points) // 2)
    assert route_module._turn_label(degrees) == "left"


def test_a_straight_line_is_not_a_turn():
    graph = _line_graph([(0.0, 0.0), (50.0, 0.0), (100.0, 0.0), (150.0, 0.0)])
    assert route_module._turn_at(graph, [0, 1, 2, 3], 1) == pytest.approx(0.0)


def test_the_window_stops_at_the_ends_of_the_route():
    """Au premier ou au dernier nœud, il n'y a rien avant ni après à comparer."""
    graph = _line_graph([(0.0, 0.0), (50.0, 0.0), (50.0, 50.0)])
    assert route_module._turn_at(graph, [0, 1, 2], 0) == 0.0
    assert route_module._turn_at(graph, [0, 1, 2], 2) == 0.0


# --------------------------------------------------------------------------- #
# Situation et consigne
# --------------------------------------------------------------------------- #


def test_the_route_is_measured_from_the_stand(departure):
    """Poste (-50, -25) -> 7 (0, -20) -> 0 (0, 0) -> 1 (300, 0) -> 3 (300, 300)."""
    assert departure.distance_m == pytest.approx(
        math.hypot(50.0, 5.0) + 20.0 + 300.0 + 300.0, abs=0.2
    )


def test_at_the_stand_the_first_taxiway_is_already_announced(departure):
    """La ligne de guidage ne fait que 70 m : la voie A est déjà en vue."""
    guidance = guide(departure, -50.0, -25.0)
    assert guidance.on_route
    assert not guidance.arrived
    assert guidance.remaining_m == pytest.approx(departure.distance_m, abs=0.2)
    assert guidance.next_name == "A"
    assert guidance.announce() == "Tournez à droite sur A."


def test_a_manoeuvre_still_far_off_is_not_announced(departure):
    """Une instruction affichée trop tôt se confond avec celle qui précède."""
    guidance = guide(departure, 0.0, 0.0)
    assert guidance.current == "A"
    assert guidance.next_name == "B"
    assert guidance.distance_to_next_m == pytest.approx(300.0, abs=0.5)
    assert guidance.announce() is None


def test_the_next_taxiway_is_announced_once_close_enough(departure):
    guidance = guide(departure, 150.0, 0.0)
    assert guidance.current == "A"
    assert guidance.next_name == "B"
    assert guidance.next_turn == "left"
    assert guidance.distance_to_next_m == pytest.approx(150.0, abs=0.5)
    assert guidance.announce() == "Tournez à gauche sur B."


def test_the_hold_takes_precedence_over_the_next_taxiway(departure):
    guidance = guide(departure, 300.0, 150.0)
    assert guidance.current == "B"
    assert guidance.hold_short == "09"
    assert guidance.distance_to_hold_m == pytest.approx(150.0, abs=0.5)
    assert guidance.announce() == "Arrêt avant la piste 09."


def test_the_end_of_the_route_ends_the_taxi(departure):
    guidance = guide(departure, 300.0, 300.0)
    assert guidance.arrived
    assert guidance.remaining_m == pytest.approx(0.0, abs=0.5)
    assert guidance.announce() == "Roulage terminé."


def test_leaving_the_route_is_seen_and_said(departure):
    guidance = guide(departure, 100.0, 150.0)
    assert not guidance.on_route
    assert guidance.fix.lateral_m == pytest.approx(150.0, abs=0.5)
    assert guidance.announce() == "Hors itinéraire."


def test_staying_within_the_tolerance_is_not_leaving_the_route(departure):
    """Contourner un poste occupé écarte de plusieurs dizaines de mètres."""
    guidance = guide(departure, 150.0, OFF_ROUTE_M - 5.0)
    assert guidance.on_route
    assert replan_needed(guidance) is False


def test_an_unnamed_link_announces_the_named_taxiway_that_follows(departure):
    """Le pilote suit la ligne jaune : une liaison n'a rien à annoncer."""
    guidance = guide(departure, 0.0, -10.0)
    assert guidance.current is None
    assert guidance.next_name == "A"


# --------------------------------------------------------------------------- #
# Reprise de l'itinéraire
# --------------------------------------------------------------------------- #


def test_a_route_is_taken_up_again_only_when_it_has_been_left(departure):
    assert replan_needed(guide(departure, 150.0, 0.0)) is False
    assert replan_needed(guide(departure, 100.0, 150.0)) is True


def test_an_arrived_aircraft_is_never_sent_a_new_route(departure):
    """La fin d'un roulage éloigne du dernier point : le guidage boucherait."""
    guidance = guide(departure, 320.0, 300.0)
    assert guidance.arrived
    assert replan_needed(guidance) is False


def test_a_new_route_starts_at_the_aircraft_not_at_the_nearest_node(departure):
    """Sans raccordement, l'avion restait hors de son propre nouveau tracé.

    L'itinéraire repris part du nœud le plus proche, à 180 m ici. Le guidage
    l'aurait déclaré égaré et en aurait redemandé un autre chaque seconde,
    indéfiniment.
    """
    taken_up = replan(departure, 100.0, 150.0)
    assert taken_up.from_position
    first = taken_up.legs()[0]
    assert first["kind"] == JOIN_KIND
    assert first["points"][0] == {"x": 100.0, "y": 150.0}
    assert first["distance_m"] == pytest.approx(math.hypot(100.0, 150.0), abs=0.2)

    after = guide(taken_up, 100.0, 150.0)
    assert after.on_route
    assert after.fix.lateral_m == pytest.approx(0.0, abs=0.1)
    assert replan_needed(after) is False


def test_a_resumed_departure_does_not_send_the_pilot_back_to_the_stand(departure):
    taken_up = replan(departure, 100.0, 150.0)
    assert taken_up.summary()[0] != "porte A 1"
    assert taken_up.summary() == ("A", "B", "attente 09")
    assert all(leg["kind"] != STAND_KIND for leg in taken_up.legs())


def test_a_resumed_arrival_still_ends_at_the_stand(graph):
    arrival = plan_taxi(graph, parking="porte A 1", runway="09", direction=ARRIVAL)
    taken_up = replan(arrival, 100.0, 150.0)
    assert taken_up.legs()[0]["kind"] == JOIN_KIND
    assert taken_up.legs()[-1]["kind"] == STAND_KIND
    assert taken_up.summary()[-1] == "porte A 1"


def test_an_aircraft_already_on_the_network_gets_no_join_segment(graph):
    """Le raccordement ne sert qu'à revenir sur le réseau, pas à le longer."""
    taken_up = plan_taxi(
        graph, parking="porte A 1", runway="09", position=(300.0, 0.0)
    )
    assert all(leg["kind"] != JOIN_KIND for leg in taken_up.legs())


# --------------------------------------------------------------------------- #
# Cache des réseaux
# --------------------------------------------------------------------------- #


def test_a_network_is_assembled_once(store):
    """Reconstruire LFPO demande 130 ms : intenable une fois par seconde."""
    forget_graphs()
    provider = MsfsProvider(store, allow_fetch=False)
    try:
        assert build_graph(provider, "TEST") is build_graph(provider, "TEST")
    finally:
        provider.close()
        forget_graphs()


def test_a_reimported_airport_is_assembled_again(store):
    """La date d'import change à chaque reprise au simulateur."""
    forget_graphs()
    provider = MsfsProvider(store, allow_fetch=False)
    try:
        first = build_graph(provider, "TEST")
        provider._conn.execute(
            "UPDATE airport SET fetched_at = '2030-01-01T00:00:00+00:00'"
        )
        provider._conn.commit()
        assert build_graph(provider, "TEST") is not first
    finally:
        provider.close()
        forget_graphs()


def test_the_cache_can_be_bypassed(store):
    forget_graphs()
    provider = MsfsProvider(store, allow_fetch=False)
    try:
        assert build_graph(provider, "TEST", cache=False) is not build_graph(
            provider, "TEST", cache=False
        )
    finally:
        provider.close()
        forget_graphs()


# --------------------------------------------------------------------------- #
# Service web
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def guided_app(store):
    from navixav.config import Settings
    from navixav.web.app import create_app

    forget_graphs()
    app = create_app(Settings(navdata_store=store, metar_source="simbrief"))
    yield app
    for close in app.router.on_shutdown:
        close()
    forget_graphs()


def _guidance(app, x, y, direction="departure"):
    endpoint = next(
        route.endpoint for route in app.routes
        if route.path == "/api/ground/{icao}/guidance"
    )
    latitude, longitude = to_latlon(x, y)
    return endpoint("TEST", "porte A 1", "09", latitude, longitude, direction)


def test_the_service_situates_an_aircraft_on_its_route(guided_app):
    payload = _guidance(guided_app, 150.0, 0.0)
    assert payload["recomputed"] is False
    guidance = payload["guidance"]
    assert guidance["on_route"] is True
    assert guidance["current"] == "A"
    assert guidance["announce"] == "Tournez à gauche sur B."
    assert guidance["remaining_m"] > 0


def test_the_service_takes_the_route_up_again_by_itself(guided_app):
    payload = _guidance(guided_app, 100.0, 150.0)
    assert payload["recomputed"] is True
    assert payload["plan"]["legs"][0]["kind"] == JOIN_KIND
    # Le nouveau tracé part de l'avion : il est de nouveau sur sa route.
    assert payload["guidance"]["on_route"] is True
    assert payload["guidance"]["announce"] != "Hors itinéraire."


def test_the_service_reports_a_parking_it_does_not_know(guided_app):
    from fastapi import HTTPException

    endpoint = next(
        route.endpoint for route in guided_app.routes
        if route.path == "/api/ground/{icao}/guidance"
    )
    with pytest.raises(HTTPException) as refused:
        endpoint("TEST", "porte Z 9", "09", ORIGIN_LAT, ORIGIN_LON, "departure")
    assert refused.value.status_code == 404


# --------------------------------------------------------------------------- #
# Contre les terrains réels
# --------------------------------------------------------------------------- #


def _routable(provider, icao):
    network = build_graph(provider, icao, cache=False)
    if not network.has_kinds:
        pytest.skip("base de test antérieure aux natures de segment")
    return network


@pytest.mark.parametrize(
    ("icao", "stand", "runway"),
    [("LFST", "porte B 3", "05"), ("LFBO", "500", "32R")],
)
def test_a_real_route_announces_its_manoeuvres_from_end_to_end(
    ground_provider, icao, stand, runway
):
    """Chaque position du tracé doit donner une consigne tenable."""
    network = _routable(ground_provider, icao)
    plan = plan_taxi(network, parking=stand, runway=runway)
    points = plan.polyline()

    announcements = []
    for index in range(0, len(points), max(1, len(points) // 12)):
        guidance = guide(plan, *points[index])
        assert guidance.on_route, f"le tracé s'écarte de lui-même en {index}"
        announcements.append(guidance.announce())

    assert guide(plan, *points[-1]).announce() == "Roulage terminé."
    assert any(a and a.startswith("Tournez") for a in announcements)
    assert any(a and a.startswith("Arrêt avant la piste") for a in announcements)


@pytest.mark.parametrize("icao", ["LFST", "LFBO", "LFPO"])
@pytest.mark.parametrize("direction", ["departure", ARRIVAL])
def test_a_real_deviation_is_recovered(ground_provider, icao, direction):
    """Sur un réseau dense, la reprise doit refermer la boucle du premier coup."""
    network = _routable(ground_provider, icao)
    stand = network.parkings[len(network.parkings) // 2]
    runway = network.runway_names()[0]
    plan = plan_taxi(
        network, parking=stand.label, runway=runway, direction=direction
    )
    points = plan.polyline()
    middle = points[len(points) // 2]

    astray = None
    for distance in (100, 200, 300, 500):
        for bearing in range(0, 360, 30):
            candidate = (
                middle[0] + distance * math.cos(math.radians(bearing)),
                middle[1] + distance * math.sin(math.radians(bearing)),
            )
            if project_on_route(points, *candidate).lateral_m > OFF_ROUTE_M + 15:
                astray = candidate
                break
        if astray:
            break
    assert astray, "aucune position franchement hors itinéraire n'a été trouvée"

    assert replan_needed(guide(plan, *astray))
    recovered = guide(replan(plan, *astray), *astray)
    assert recovered.on_route
    assert replan_needed(recovered) is False
    # Le raccordement ramène l'avion sur son tracé ; à défaut, c'est qu'il était
    # déjà sur le réseau, à moins d'un pas du premier nœud.
    assert recovered.fix.lateral_m <= MIN_JOIN_M
