"""Sources de position : unités demandées et dégradation propre."""

from __future__ import annotations

import pytest

from navixav.live.base import AircraftState, PositionUnavailable
from navixav.live.demo import DemoSource, _bearing
from navixav.live.registry import LiveTracker
from navixav.live.simconnect import SimConnectSource, _VARIABLES


# --------------------------------------------------------------------------- #
# Unités
#
# NaviXav ne convertit plus rien : il demande l'unité au simulateur, qui la
# fournit. C'est ce qui protège du piège de « PLANE HEADING DEGREES TRUE »,
# dont le nom annonce des degrés alors que l'unité native est le radian.
# --------------------------------------------------------------------------- #


def test_every_variable_declares_its_unit():
    assert _VARIABLES
    for name, unit in _VARIABLES:
        assert name and unit, f"unité manquante pour {name}"


def test_headings_are_requested_in_degrees():
    """Le nom de la variable ment sur son unité : on impose la nôtre."""
    units = dict(_VARIABLES)
    assert units["PLANE HEADING DEGREES TRUE"] == "Degrees"
    assert units["PLANE HEADING DEGREES MAGNETIC"] == "Degrees"


def test_position_and_speed_units():
    units = dict(_VARIABLES)
    assert units["PLANE LATITUDE"] == "Degrees"
    assert units["PLANE LONGITUDE"] == "Degrees"
    assert units["PLANE ALTITUDE"] == "Feet"
    assert units["GROUND VELOCITY"] == "Knots"
    assert units["VERTICAL SPEED"] == "Feet per minute"


# --------------------------------------------------------------------------- #
# Client SimConnect unique
# --------------------------------------------------------------------------- #


def test_simconnect_source_maps_direct_values(monkeypatch):
    """La source temps réel passe par le client ctypes commun, sans conversion."""

    class FakeClient:
        def read_simvars(self, variables):
            assert variables == _VARIABLES
            return {
                "PLANE LATITUDE": 48.723,
                "PLANE LONGITUDE": 2.379,
                "PLANE ALTITUDE": 5100.0,
                "PLANE ALT ABOVE GROUND": 4300.0,
                "PLANE HEADING DEGREES TRUE": 371.5,
                "PLANE HEADING DEGREES MAGNETIC": -2.0,
                "GROUND VELOCITY": 185.0,
                "VERTICAL SPEED": -700.0,
                "SIM ON GROUND": 0.0,
            }

        def close(self):
            pass

    source = SimConnectSource()
    fake = FakeClient()
    monkeypatch.setattr(source, "_connect", lambda: fake)

    state = source.read()

    assert state.latitude == 48.723
    assert state.longitude == 2.379
    assert state.altitude_ft == 5100.0
    assert state.height_above_ground_ft == 4300.0
    assert state.heading_true_deg == 11.5
    assert state.heading_magnetic_deg == 358.0
    assert state.ground_speed_kt == 185.0
    assert state.vertical_speed_fpm == -700.0
    assert not state.on_ground
    assert state.source == "SimConnect"


# --------------------------------------------------------------------------- #
# Source de démonstration
# --------------------------------------------------------------------------- #


def test_demo_starts_at_its_origin():
    source = DemoSource(start=(48.545, 7.632), end=(48.535, 7.615))
    state = source.read()
    assert state.latitude == pytest.approx(48.545, abs=1e-3)
    assert state.on_ground
    assert state.source == "Démonstration"


def test_demo_points_along_its_travel():
    """Le cap doit suivre le roulage, pas l'axe de la piste rejointe."""
    source = DemoSource(start=(48.545, 7.632), end=(48.535, 7.615))
    heading = source.read().heading_true_deg
    expected = _bearing((48.545, 7.632), (48.535, 7.615))
    assert heading == pytest.approx(expected, abs=0.5)
    assert 180 < heading < 270  # trajet vers le sud-ouest


def test_bearing_cardinal_directions():
    assert _bearing((48.0, 7.0), (49.0, 7.0)) == pytest.approx(0, abs=0.5)
    assert _bearing((48.0, 7.0), (48.0, 8.0)) == pytest.approx(90, abs=0.5)
    assert _bearing((48.0, 7.0), (47.0, 7.0)) == pytest.approx(180, abs=0.5)


def test_demo_rejects_a_degenerate_path():
    source = DemoSource(start=(48.545, 7.632), end=(48.545, 7.632))
    with pytest.raises(PositionUnavailable):
        source.read()


# --------------------------------------------------------------------------- #
# Dégradation propre
# --------------------------------------------------------------------------- #


def test_tracker_prefers_its_demo_source():
    tracker = LiveTracker()
    tracker.set_demo(DemoSource(start=(48.545, 7.632), end=(48.535, 7.615)))
    state = tracker.read(allow_demo=True)
    assert state.source == "Démonstration"
    tracker.close()


def test_tracker_ignores_demo_when_not_requested():
    """Sans autorisation explicite, la démo ne doit jamais se substituer au réel."""
    tracker = LiveTracker()
    tracker.set_demo(DemoSource(start=(48.545, 7.632), end=(48.535, 7.615)))
    tracker._sources = []  # aucune source réelle disponible
    with pytest.raises(PositionUnavailable):
        tracker.read(allow_demo=False)
    tracker.close()


def test_state_serialises():
    state = AircraftState(latitude=48.72, longitude=2.36, source="Test")
    payload = state.to_dict()
    assert payload["latitude"] == 48.72
    assert payload["source"] == "Test"
    assert "on_ground" in payload
