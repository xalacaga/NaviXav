"""Vol de démonstration complet : profil, configuration et arrivée au parking."""

from __future__ import annotations

import pytest

from navixav.live.demo_flight import DemoFlightSource
from navixav.web.app import _demo_flight_path

# LFST → LFBO, simplifié à quelques points de route.
PATH = [
    (48.5383, 7.6282),
    (48.30, 7.30),
    (47.60, 6.20),
    (46.50, 4.80),
    (45.20, 3.50),
    (44.10, 2.20),
    (43.70, 1.55),
    (43.6294, 1.3675),
]


class FakeClock:
    """Horloge pilotée par le test, en secondes."""

    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


def build_source(**kwargs) -> tuple[DemoFlightSource, FakeClock]:
    clock = FakeClock()
    source = DemoFlightSource(
        PATH,
        cruise_altitude_ft=kwargs.pop("cruise_altitude_ft", 34000),
        departure_elevation_ft=kwargs.pop("departure_elevation_ft", 505.0),
        arrival_elevation_ft=kwargs.pop("arrival_elevation_ft", 499.0),
        clock=clock,
        **kwargs,
    )
    return source, clock


def fly(source: DemoFlightSource, clock: FakeClock, step_s: float = 2.0):
    """Déroule le vol jusqu'à l'arrêt et renvoie tous les états lus."""
    states = []
    elapsed = 0.0
    while elapsed < 7200:
        clock.value = elapsed
        states.append(source.read())
        if source.finished:
            break
        elapsed += step_s
    return states


def test_demo_flight_starts_parked_at_the_departure_point():
    source, clock = build_source()
    state = source.read()

    assert state.on_ground is True
    assert state.ground_speed_kt == 0
    assert state.latitude == pytest.approx(PATH[0][0], abs=1e-3)
    assert state.longitude == pytest.approx(PATH[0][1], abs=1e-3)
    assert state.configuration is not None
    assert state.configuration.parking_brake is True
    # Les alarmes doivent rester évaluables : la démo n'accélère pas la session.
    assert state.configuration.simulation_rate == 1.0


def test_demo_flight_runs_every_phase_and_parks_at_destination():
    source, clock = build_source()
    states = fly(source, clock)

    assert source.finished
    altitudes = [s.altitude_ft or 0.0 for s in states]
    assert max(altitudes) == pytest.approx(34000, abs=50)
    assert max(s.ground_speed_kt or 0.0 for s in states) == pytest.approx(450, abs=5)
    assert max(s.vertical_speed_fpm or 0.0 for s in states) > 1000  # montée
    assert min(s.vertical_speed_fpm or 0.0 for s in states) < -600  # descente
    assert any(s.on_ground is False for s in states)

    final = states[-1]
    assert final.on_ground is True
    assert final.ground_speed_kt == 0
    assert final.latitude == pytest.approx(PATH[-1][0], abs=1e-3)
    assert final.longitude == pytest.approx(PATH[-1][1], abs=1e-3)
    assert final.configuration is not None
    assert final.configuration.parking_brake is True


def test_demo_flight_configures_the_aircraft_like_a_real_flight():
    source, clock = build_source()
    states = fly(source, clock)
    airborne = [s for s in states if not s.on_ground and s.configuration]

    cruise = [s for s in airborne if (s.altitude_ft or 0) > 30000]
    assert cruise, "la croisière doit être atteinte"
    assert all(s.configuration.gear_handle_down is False for s in cruise)
    assert all(s.configuration.flaps_handle_index == 0 for s in cruise)
    assert all(s.configuration.autopilot_master is True for s in cruise)

    # Train et volets sortis avant le toucher des roues. Le filtre part du
    # sommet du vol : en début de montée l'avion est aussi bas, volets 1.
    top = max(range(len(airborne)), key=lambda i: airborne[i].altitude_ft or 0)
    short_final = [
        s for s in airborne[top:] if 0 < (s.height_above_ground_ft or 0) < 800
    ]
    assert short_final
    assert all(s.configuration.gear_handle_down is True for s in short_final)
    assert all(s.configuration.flaps_handle_index >= 2 for s in short_final)


def test_demo_flight_never_moves_backwards():
    source, clock = build_source()
    states = fly(source, clock, step_s=3.0)
    for previous, current in zip(states, states[1:]):
        assert (current.ground_speed_kt or 0) >= 0
        assert (current.altitude_ft or 0) >= 0
    assert len(states) > 20


def test_demo_flight_rejects_an_unusable_route():
    with pytest.raises(ValueError):
        DemoFlightSource([(48.0, 7.0)])
    with pytest.raises(ValueError):
        DemoFlightSource([(48.0, 7.0), (48.0, 7.0)])


def test_demo_flight_path_follows_the_planned_route():
    payload = {
        "departure": {"icao": "LFST", "sid_path": [{"ident": "STR", "lat": 48.5, "lon": 7.6}]},
        "enroute": {
            "route_path": [
                {"ident": "LFST", "lat": 48.53, "lon": 7.62},
                {"ident": "EPINAL", "lat": 48.1, "lon": 6.5},
                {"ident": "LFBO", "lat": 43.62, "lon": 1.36},
            ]
        },
        "arrival": {
            "icao": "LFBO",
            "star_path": [{"ident": "TOU", "lat": 43.8, "lon": 1.5}],
            "approach_path": [{"ident": "FI14L", "lat": 43.7, "lon": 1.4}],
        },
    }
    path = _demo_flight_path(payload)

    assert path[0] == (48.53, 7.62)
    assert path[-1] == (43.62, 1.36)
    assert (48.5, 7.6) in path  # SID
    assert (48.1, 6.5) in path  # route
    assert (43.8, 1.5) in path  # STAR
    assert (43.7, 1.4) in path  # approche


def test_demo_flight_path_is_empty_without_a_route():
    assert _demo_flight_path({}) == []
