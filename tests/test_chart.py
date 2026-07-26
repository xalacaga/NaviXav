"""Plan de terrain : géométrie et exactitude de la projection locale."""

from __future__ import annotations

import math

import pytest

from navixav.chart import EARTH_RADIUS_M, Projection, build_chart

FEET_PER_METRE = 3.280839895


@pytest.fixture(scope="module")
def lfst(ground_provider):
    return build_chart(ground_provider, "LFST", "05")


# --------------------------------------------------------------------------- #
# Projection
# --------------------------------------------------------------------------- #


def test_origin_projects_to_zero():
    projection = Projection(48.5383, 7.6282)
    x, y = projection.to_xy(48.5383, 7.6282)
    assert x == pytest.approx(0, abs=1e-6)
    assert y == pytest.approx(0, abs=1e-6)


def test_one_degree_of_latitude_is_about_111_km():
    projection = Projection(48.0, 7.0)
    _x, y = projection.to_xy(49.0, 7.0)
    assert y == pytest.approx(111_320, rel=0.001)


def test_longitude_shrinks_with_latitude():
    """Un degré de longitude vaut moins qu'un degré de latitude en Europe."""
    projection = Projection(48.0, 7.0)
    x, _y = projection.to_xy(48.0, 8.0)
    assert x == pytest.approx(111_320 * math.cos(math.radians(48.0)), rel=0.001)


def test_projection_is_invertible():
    projection = Projection(48.5383, 7.6282)
    x, y = projection.to_xy(48.5500, 7.6500)
    latitude = 48.5383 + math.degrees(y / EARTH_RADIUS_M)
    longitude = 7.6282 + math.degrees(
        x / (EARTH_RADIUS_M * math.cos(math.radians(48.5383)))
    )
    assert latitude == pytest.approx(48.5500, abs=1e-9)
    assert longitude == pytest.approx(7.6500, abs=1e-9)


# --------------------------------------------------------------------------- #
# Contenu du plan
# --------------------------------------------------------------------------- #


def test_chart_has_ground_geometry(lfst):
    assert lfst["icao"] == "LFST"
    assert len(lfst["runways"]) == 1
    assert len(lfst["taxiways"]) > 100
    assert len(lfst["parkings"]) > 10


def test_runway_length_matches_the_projected_distance(lfst):
    """La géométrie projetée doit redonner la longueur publiée."""
    runway = lfst["runways"][0]
    dx = runway["end"]["x"] - runway["start"]["x"]
    dy = runway["end"]["y"] - runway["start"]["y"]
    measured_ft = math.hypot(dx, dy) * FEET_PER_METRE
    assert measured_ft == pytest.approx(runway["length_ft"], rel=0.01)


def test_runway_ends_are_opposite(lfst):
    ends = lfst["runways"][0]["ends"]
    headings = sorted(end["heading"] for end in ends)
    assert abs((headings[1] - headings[0]) - 180) < 2


def test_both_thresholds_are_named(lfst):
    names = {end["name"] for end in lfst["runways"][0]["ends"]}
    assert names == {"05", "23"}


def test_highlight_is_carried_through(lfst):
    assert lfst["highlight_runway"] == "05"


def test_bounds_contain_every_element(lfst):
    bounds = lfst["bounds"]
    for taxiway in lfst["taxiways"]:
        for point in (taxiway["start"], taxiway["end"]):
            assert bounds["min_x"] <= point["x"] <= bounds["max_x"]
            assert bounds["min_y"] <= point["y"] <= bounds["max_y"]


def test_parkings_are_labelled(lfst):
    assert all(parking["label"] for parking in lfst["parkings"])
    assert all(parking["radius_m"] > 0 for parking in lfst["parkings"])


def test_unknown_airport_raises(ground_provider):
    with pytest.raises(LookupError):
        build_chart(ground_provider, "ZZZZ")


def test_large_airport_is_complete(ground_provider):
    chart = build_chart(ground_provider, "LFBO", "32R")
    assert len(chart["runways"]) == 2
    assert len(chart["taxiways"]) > 1000
    names = {end["name"] for r in chart["runways"] for end in r["ends"]}
    assert names == {"14L", "14R", "32L", "32R"}


def test_ground_provider_reports_its_capability(ground_provider):
    assert ground_provider.has_ground_geometry
