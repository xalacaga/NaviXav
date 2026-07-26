from __future__ import annotations

import pytest

from navixav.planner.runway import wind_components
from navixav.weather.metar import parse_wind


def test_parse_wind_standard():
    wind = parse_wind("LFBO 260730Z 33008KT CAVOK 21/11 Q1018 NOSIG")
    assert wind.direction_deg == 330
    assert wind.speed_kt == 8
    assert wind.gust_kt is None
    assert not wind.variable
    assert wind.qnh_hpa == 1018
    assert wind.altimeter_inhg == pytest.approx(30.06, abs=0.01)


def test_parse_wind_with_gust():
    wind = parse_wind("LFST 260730Z 04012G22KT 9999 FEW035 18/12 Q1019")
    assert (wind.direction_deg, wind.speed_kt, wind.gust_kt) == (40, 12, 22)


def test_parse_wind_variable():
    wind = parse_wind("LFPG 260730Z VRB03KT CAVOK 15/09 Q1020")
    assert wind.variable
    assert wind.direction_deg is None
    assert wind.speed_kt == 3


def test_parse_wind_calm():
    wind = parse_wind("LFPO 260730Z 00000KT CAVOK 15/09 Q1020")
    assert wind.speed_kt == 0
    assert wind.direction_deg is None


def test_parse_wind_metres_per_second():
    wind = parse_wind("UUEE 260730Z 09005MPS 9999 OVC020 05/03 Q1005")
    assert wind.direction_deg == 90
    assert wind.speed_kt == 10  # 5 m/s ≈ 9.7 kt


def test_parse_wind_absent():
    assert parse_wind(None).direction_deg is None
    assert parse_wind("").raw_metar is None


def test_us_altimeter_is_converted_to_qnh():
    wind = parse_wind("KJFK 261051Z 22008KT 10SM FEW040 24/16 A2992")
    assert wind.qnh_hpa == 1013
    assert wind.altimeter_inhg == 29.92


def test_qnh_is_kept_when_wind_is_missing():
    wind = parse_wind("LFBO 261100Z AUTO /////KT CAVOK 22/12 Q1017")
    assert wind.direction_deg is None
    assert wind.qnh_hpa == 1017


@pytest.mark.parametrize(
    ("wind_dir", "speed", "heading", "expected_head"),
    [
        (50, 10, 50, 10.0),   # pile dans l'axe
        (230, 10, 50, -10.0),  # plein vent arrière
        (140, 10, 50, 0.0),    # plein travers
    ],
)
def test_wind_components(wind_dir, speed, heading, expected_head):
    head, _cross = wind_components(wind_dir, speed, heading)
    assert head == pytest.approx(expected_head, abs=1e-6)


def test_crosswind_is_absolute():
    _head, cross = wind_components(140, 10, 50)
    assert cross == pytest.approx(10.0)
