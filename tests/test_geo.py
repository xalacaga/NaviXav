"""Couloir de plausibilité d'un point en route.

Un identifiant de repère n'est unique que dans sa région du monde. Quand la
base en connaît plusieurs, le tracé ne doit jamais retenir celui qui fait
traverser un continent puis revenir.
"""

from __future__ import annotations

from navixav.geo import distance_nm, near_direct_route

ANDRAVIDA = (37.920, 21.293)   # LGZV
ORLY = (48.723, 2.379)         # LFPO
TOULOUSE = (43.635, 1.368)     # LFBO
MILAN = (45.630, 8.723)        # sur la route Grèce -> Paris
AUCKLAND = (-37.008, 174.792)  # homonyme à l'autre bout du monde


def test_distance_nm_is_symmetric():
    forward = distance_nm(*ANDRAVIDA, *ORLY)
    backward = distance_nm(*ORLY, *ANDRAVIDA)
    assert forward == backward
    assert 1000 < forward < 1300


def test_a_point_on_the_way_is_accepted():
    assert near_direct_route(ANDRAVIDA, ORLY, MILAN)


def test_a_detour_of_a_few_hundred_miles_is_accepted():
    """Une route réelle s'écarte du direct : Toulouse reste plausible."""
    assert near_direct_route(ANDRAVIDA, ORLY, TOULOUSE)


def test_an_homonym_on_another_continent_is_refused():
    assert not near_direct_route(ANDRAVIDA, ORLY, AUCKLAND)


def test_a_short_flight_keeps_a_generous_margin():
    """Sur 200 NM, le couloir vaut au moins 300 NM d'allongement."""
    assert near_direct_route(ORLY, TOULOUSE, (46.5, 4.5))
    assert not near_direct_route(ORLY, TOULOUSE, AUCKLAND)


# --------------------------------------------------------------------------- #
# Vols dont les deux extrémités se confondent
#
# Sur un aller-retour, la route directe ne mesure plus rien : c'est la distance
# annoncée par le plan qui dit jusqu'où le vol s'éloigne. Sans elle, le couloir
# ne juge pas — mieux vaut tracer que retirer à tort.
# --------------------------------------------------------------------------- #

FAR_FROM_ORLY = (44.0, 2.0)  # environ 300 NM au sud d'Orly


def test_a_round_trip_keeps_its_turning_point():
    assert near_direct_route(ORLY, ORLY, FAR_FROM_ORLY, planned_nm=650)


def test_a_round_trip_without_a_planned_distance_judges_nothing():
    assert near_direct_route(ORLY, ORLY, FAR_FROM_ORLY)


def test_a_round_trip_still_refuses_the_other_side_of_the_world():
    assert not near_direct_route(ORLY, ORLY, AUCKLAND, planned_nm=650)


def test_the_planned_distance_never_narrows_the_corridor():
    """Une distance annoncée courte ne doit pas rétrécir un couloir déjà large."""
    assert near_direct_route(ANDRAVIDA, ORLY, TOULOUSE, planned_nm=10)
