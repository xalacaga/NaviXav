"""Turbulence prévue (cisaillement de l'OFP) et signalée (PIREP, AIREP)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from navixav.simbrief.parser import NavlogFix, _turbulence_profile, cat_risk
from navixav.weather.pirep import bounding_box, intensity_rank, parse, relate_to_route


def test_clear_air_turbulence_risk_follows_the_shear_thresholds():
    assert cat_risk(None) is None
    assert cat_risk(2) is None
    assert cat_risk(4) == "LGT"
    assert cat_risk(6) == "MOD"
    assert cat_risk(9.5) == "SEV"


def test_the_profile_is_indexed_by_distance_to_destination():
    """Valeurs relevées sur un OFP réel : cisaillement 4 à 5 au FL340."""
    navlog = [
        NavlogFix("LFBO", lat=43.6, lon=1.4, leg_distance_nm=0, shear_kt_per_kft=0, altitude_ft=500),
        NavlogFix("TOC", lat=44.5, lon=1.7, leg_distance_nm=100, shear_kt_per_kft=4, altitude_ft=34000),
        NavlogFix("LTP", lat=46.0, lon=2.0, leg_distance_nm=150, shear_kt_per_kft=7, altitude_ft=34000),
        NavlogFix("LFPO", lat=48.7, lon=2.4, leg_distance_nm=140, shear_kt_per_kft=1, altitude_ft=300),
    ]
    profile = _turbulence_profile(navlog)
    assert [point["remaining_nm"] for point in profile] == [390.0, 290.0, 140.0, 0.0]
    assert [point["risk"] for point in profile] == [None, "LGT", "MOD", None]


def test_compound_intensities_count_as_the_stronger_one():
    assert intensity_rank("LGT-MOD") == ("LGT-MOD", 2)
    assert intensity_rank("NEG") == ("NEG", 0)
    assert intensity_rank("") is None


REPORTS = [
    {"pirepType": "PIREP", "lat": 41.0, "lon": -88.0, "obsTime": 1_800_000_000, "fltLvl": 350,
     "tbInt1": "MOD", "tbType1": "CHOP", "acType": "B738", "rawOb": "UA /OV ... /TB MOD"},
    {"pirepType": "AIREP", "lat": 41.2, "lon": -88.3, "obsTime": 1_800_000_100, "fltLvl": 120,
     "tbInt1": "SEV", "rawOb": "ARP ..."},
    {"pirepType": "PIREP", "lat": 60.0, "lon": -88.0, "obsTime": 1_800_000_200, "fltLvl": 350,
     "tbInt1": "MOD", "rawOb": "far away"},
    {"pirepType": "PIREP", "lat": 41.0, "lon": -88.0, "obsTime": 1_800_000_300, "fltLvl": 350,
     "tbInt1": "", "rawOb": "no turbulence information"},
]


def test_reports_without_turbulence_are_ignored():
    assert len(parse(REPORTS)) == 3


def test_only_reports_in_the_route_corridor_are_kept_level_first():
    route = [(40.64, -73.78), (41.0, -87.9), (39.86, -104.67)]
    related = relate_to_route(parse(REPORTS), route, 35000)
    assert [report.raw for report in related] == ["UA /OV ... /TB MOD", "ARP ..."]
    assert related[0].near_level is True
    assert related[1].near_level is False
    assert related[0].level_ft == 35000


def test_the_request_box_surrounds_the_route_with_its_corridor():
    south, west, north, east = bounding_box([(40.6, -73.8), (33.9, -118.4)])
    assert south < 33.9 and north > 40.6 and west < -118.4 and east > -73.8


def test_without_a_loaded_flight_no_reports_are_requested():
    import navixav.web.app as web

    client = TestClient(web.create_app())
    response = client.get("/api/weather/turbulence")
    assert response.status_code == 200
    assert response.json()["reports"] == []
