"""Analyse d'atterrissage : piste, note, rebonds et garde-fous."""

from __future__ import annotations

import math

import pytest

from navixav.live.base import (
    AircraftCapabilities,
    AircraftConfiguration,
    AircraftState,
    TouchdownSample,
)
from navixav.live.landing import (
    LandingMonitor,
    grade_for_rate,
    locate_on_runway,
    score_landing,
    stability_checks,
    wind_components,
)
from navixav.navdata.base import Runway

EARTH_RADIUS_M = 6_371_000.0
THRESHOLD = (45.0, 5.0)


def runway(name="09", heading=90.0, lat=THRESHOLD[0], lon=THRESHOLD[1]):
    return Runway(
        name=name,
        heading_true_deg=heading,
        length_ft=9843.0,  # 3 000 m
        width_ft=148.0,  # 45 m
        surface="ASPHALT",
        ils_ident=None,
        is_landing=True,
        is_takeoff=True,
        lat=lat,
        lon=lon,
    )


def offset(east_m: float, north_m: float) -> tuple[float, float]:
    lat = THRESHOLD[0] + math.degrees(north_m / EARTH_RADIUS_M)
    lon = THRESHOLD[1] + math.degrees(
        east_m / (EARTH_RADIUS_M * math.cos(math.radians(THRESHOLD[0])))
    )
    return lat, lon


def configuration(**overrides):
    values = dict(
        gear_extended_pct=100.0,
        flaps_handle_index=3,
        wind_direction_deg=60.0,
        wind_speed_kt=10.0,
        capabilities=AircraftCapabilities(
            retractable_gear=True, flaps=True, spoilers=True, flap_positions=5
        ),
    )
    values.update(overrides)
    return AircraftConfiguration(**values)


def airborne(height, *, east=-3000.0, vs=-700.0, ias=140.0, cfg=None):
    lat, lon = offset(east, 0.0)
    return AircraftState(
        latitude=lat,
        longitude=lon,
        height_above_ground_ft=height,
        heading_true_deg=90.0,
        ground_speed_kt=135.0,
        indicated_airspeed_kt=ias,
        vertical_speed_fpm=vs,
        on_ground=False,
        configuration=cfg or configuration(),
    )


def on_ground(*, east=420.0, north=0.0, touchdown=None):
    lat, lon = offset(east, north)
    return AircraftState(
        latitude=lat,
        longitude=lon,
        height_above_ground_ft=0.0,
        heading_true_deg=90.0,
        ground_speed_kt=130.0,
        on_ground=True,
        title="Test Airliner",
        configuration=configuration(),
        touchdown=touchdown,
    )


def touchdown_at(east, north, rate=180.0):
    lat, lon = offset(east, north)
    return TouchdownSample(
        normal_velocity_fpm=rate,
        latitude=lat,
        longitude=lon,
        heading_true_deg=90.0,
        pitch_deg=4.5,
        bank_deg=-1.0,
    )


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def fly_approach(monitor, clock, heights=(1200, 1000, 800, 600, 450, 300, 200, 100, 50, 20)):
    for height in heights:
        clock.now += 1
        monitor.observe(airborne(height))


def test_locate_on_runway_measures_threshold_distance_and_centerline():
    lat, lon = offset(400.0, -5.0)
    contact = locate_on_runway(lat, lon, 90.0, [("LFXX", runway())])
    assert contact is not None
    assert contact.runway == "09"
    assert contact.distance_from_threshold_m == pytest.approx(400.0, abs=1.0)
    # Au sud d'une piste orientée à l'est : à droite de l'axe.
    assert contact.centerline_offset_m == pytest.approx(5.0, abs=0.5)


def test_locate_on_runway_ignores_the_opposite_end_and_far_runways():
    lat, lon = offset(400.0, 0.0)
    opposite = runway(name="27", heading=270.0)
    assert locate_on_runway(lat, lon, 90.0, [("LFXX", opposite)]) is None
    far_lat, far_lon = offset(400.0, 500.0)
    assert locate_on_runway(far_lat, far_lon, 90.0, [("LFXX", runway())]) is None


def test_wind_components_from_the_right():
    headwind, crosswind = wind_components(120.0, 20.0, 90.0)
    assert headwind == pytest.approx(17.3, abs=0.1)
    assert crosswind == pytest.approx(10.0, abs=0.1)


@pytest.mark.parametrize(
    ("rate", "grade"),
    [(80, "soft"), (200, "smooth"), (350, "firm"), (550, "hard"), (800, "very_hard")],
)
def test_grade_for_rate(rate, grade):
    assert grade_for_rate(rate) == grade


def test_unknown_components_leave_the_score_instead_of_lowering_it():
    score, parts = score_landing(150.0, None, {"sink_rate": None}, 0)
    assert score == 100
    assert set(parts) == {"rate"}


def test_stability_flags_late_gear_and_unstable_speed():
    approach = [
        airborne(1000, cfg=configuration(gear_extended_pct=0.0)),
        airborne(700, vs=-1400),
        airborne(400, ias=150),
        airborne(200, ias=132),
    ]
    assert stability_checks(approach) == {
        "configured_1000": False,
        "sink_rate": False,
        "speed_stable": False,
    }


def test_monitor_reports_a_landing_from_the_simulator_touchdown_values():
    clock = Clock()
    monitor = LandingMonitor(lambda: [("LFXX", runway())], clock=clock)
    fly_approach(monitor, clock)
    clock.now += 1
    report = monitor.observe(on_ground(touchdown=touchdown_at(400.0, 2.0)))

    assert report is not None
    assert report["rate_fpm"] == 180
    assert report["rate_source"] == "simulator"
    assert report["grade"] == "smooth"
    assert report["airport"] == "LFXX"
    assert report["runway"] == "09"
    assert report["distance_from_threshold_m"] == pytest.approx(400, abs=2)
    assert report["centerline_offset_m"] == pytest.approx(-2.0, abs=0.5)
    assert report["in_touchdown_zone"] is True
    assert report["pitch_deg"] == 4.5
    assert report["headwind_kt"] == pytest.approx(9, abs=1)
    assert report["stability"] == {
        "configured_1000": True, "sink_rate": True, "speed_stable": True,
    }
    assert report["score"] >= 90
    assert report["final"] is False


def test_monitor_counts_bounces_then_finalises():
    clock = Clock()
    monitor = LandingMonitor(lambda: [("LFXX", runway())], clock=clock)
    fly_approach(monitor, clock)
    clock.now += 1
    first = monitor.observe(on_ground(touchdown=touchdown_at(400.0, 0.0)))
    clock.now += 1
    monitor.observe(airborne(4, east=480.0))
    clock.now += 1
    bounced = monitor.observe(on_ground(east=560.0))
    assert bounced["bounces"] == 1
    assert bounced["score"] == first["score"] - 10
    assert bounced["id"] == first["id"]

    clock.now += 20
    final = monitor.observe(on_ground(east=900.0))
    assert final["final"] is True
    assert final["bounces"] == 1


def test_stale_touchdown_values_fall_back_to_the_sampled_vertical_speed():
    clock = Clock()
    monitor = LandingMonitor(lambda: [], clock=clock)
    fly_approach(monitor, clock)
    clock.now += 1
    stale = touchdown_at(400.0, 50_000.0, rate=900.0)
    report = monitor.observe(on_ground(touchdown=stale))
    assert report["rate_source"] == "sampled"
    assert report["rate_fpm"] == 700
    assert report["runway"] is None


def test_teleport_to_the_ground_is_not_a_landing():
    clock = Clock()
    monitor = LandingMonitor(lambda: [("LFXX", runway())], clock=clock)
    monitor.observe(airborne(30_000))
    clock.now += 1
    monitor.observe(airborne(500))
    clock.now += 1
    assert monitor.observe(on_ground(touchdown=touchdown_at(400.0, 0.0))) is None


def test_the_same_snapshot_is_only_counted_once():
    clock = Clock()
    monitor = LandingMonitor(lambda: [("LFXX", runway())], clock=clock)
    fly_approach(monitor, clock)
    state = on_ground(touchdown=touchdown_at(400.0, 0.0))
    first = monitor.observe(state)
    assert monitor.observe(state) == first
    assert monitor.latest() == first


# --------------------------------------------------------------------------- #
# Image de partage


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _landing_app():
    from navixav.config import Settings
    from navixav.web.app import create_app

    return create_app(Settings(metar_source="simbrief", lan_enabled=True))


def test_the_card_needs_the_desktop_window_and_a_confirmation():
    from fastapi.testclient import TestClient

    client = TestClient(_landing_app(), client=("127.0.0.1", 50000))
    assert client.post("/api/landing/card", content=PNG).status_code == 403
    response = client.post(
        "/api/landing/card", content=PNG, headers={"X-NaviXav-Landing": "save"}
    )
    assert response.status_code == 409


def test_the_card_is_written_where_the_pilot_chose(tmp_path):
    from fastapi.testclient import TestClient

    app = _landing_app()
    target = tmp_path / "touchdown"
    app.state.request_landing_card_path = lambda name: str(target)
    client = TestClient(app, client=("127.0.0.1", 50000))

    rejected = client.post(
        "/api/landing/card", content=b"<svg/>", headers={"X-NaviXav-Landing": "save"}
    )
    assert rejected.status_code == 400

    response = client.post(
        "/api/landing/card?name=../../evil.exe",
        content=PNG,
        headers={"X-NaviXav-Landing": "save"},
    )
    assert response.json() == {"saved": True, "file": "touchdown.png"}
    assert (tmp_path / "touchdown.png").read_bytes() == PNG


def test_a_tablet_cannot_open_a_save_dialog_on_the_pc():
    from fastapi.testclient import TestClient

    app = _landing_app()
    app.state.request_landing_card_path = lambda name: pytest.fail("dialog opened")
    client = TestClient(app, client=("192.168.1.20", 50000))
    response = client.post(
        "/api/landing/card", content=PNG, headers={"X-NaviXav-Landing": "save"}
    )
    assert response.status_code == 403
    assert client.get("/api/landing").json() == {"landing": None}
