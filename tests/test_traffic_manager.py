from dataclasses import replace
import threading

import pytest

from navixav.traffic.base import MatchKind, ResolvedAircraftModel, TrafficAircraft, distance_nm
from navixav.traffic.manager import TrafficManager
from navixav.live.base import AircraftState


def _aircraft(
    uid: str,
    latitude: float,
    *,
    speed: float | None = 180,
    on_ground: bool | None = False,
) -> TrafficAircraft:
    return TrafficAircraft(
        uid=uid,
        callsign=uid,
        aircraft_type="A320",
        airline_icao="AFR",
        latitude=latitude,
        longitude=2.0,
        altitude_ft=5000,
        ground_speed_kt=speed,
        heading_deg=90,
        on_ground=on_ground,
    )


class _Provider:
    name = "test"

    def __init__(self, aircraft):
        self.aircraft = aircraft

    def traffic(self, limit=None):
        return list(self.aircraft)

    def close(self):
        raise AssertionError("TrafficManager ne possède pas la source partagée")


class _Models:
    def match(self, aircraft):
        if aircraft.uid == "NO_MODEL":
            return None
        return ResolvedAircraftModel(
            "FSLTL A320 AFR", "FSLTL", MatchKind.EXACT, 0, "test"
        )


class _Injector:
    def __init__(self, lost=()):
        self.owned = {}
        self.updated = []
        self.removed = []
        self.closed = False
        self.reconciled = []
        self._lost = list(lost)

    def reconcile(self, radius_m):
        self.reconciled.append(radius_m)
        lost = [uid for uid in self._lost if uid in self.owned]
        for uid in lost:
            self.owned.pop(uid, None)
        self._lost = []
        return lost

    def upsert(self, aircraft, model):
        self.updated.append((aircraft, model))
        self.owned[aircraft.uid] = object()

    def remove(self, uid):
        self.removed.append(uid)
        self.owned.pop(uid, None)

    def close(self):
        self.closed = True
        self.owned.clear()


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def test_player_position_and_altitude_come_from_one_snapshot():
    calls = []

    def state():
        calls.append(True)
        return AircraftState(latitude=48.0, longitude=2.0, altitude_ft=5000)

    def separate_read():
        raise AssertionError('a second simulator read would mix snapshots')

    injector = _Injector()
    manager = TrafficManager(
        _Provider([_aircraft('OWN', 48.0), _aircraft('NEAR', 48.01)]),
        _Models(), injector, separate_read, altitude=separate_read, state=state,
    )
    manager.sync_once()
    assert len(calls) == 1
    assert set(injector.owned) == {'NEAR'}
    manager.close()


def test_animation_continues_while_a_source_request_waits():
    entered, release = threading.Event(), threading.Event()

    class Provider(_Provider):
        waiting = False

        def traffic(self, limit=None):
            if self.waiting:
                entered.set()
                assert release.wait(2)
            return super().traffic(limit)

    provider = Provider([_aircraft('TAXI', 48.01, speed=15, on_ground=True)])
    injector, clock = _Injector(), _Clock()
    manager = TrafficManager(provider, _Models(), injector, lambda: (48, 2), clock=clock)
    manager.sync_once()
    longitude = injector.updated[-1][0].longitude
    provider.waiting = True
    worker = threading.Thread(target=manager.sync_once)
    worker.start()
    try:
        assert entered.wait(1)
        clock.advance(1 / 30)
        manager.render_once()
        assert injector.updated[-1][0].longitude > longitude
    finally:
        release.set()
        worker.join(2)
        manager.close()


def test_confirmation_count_requires_successful_object_creation():
    class Injector(_Injector):
        def upsert(self, aircraft, model):
            if aircraft.uid == 'FAIL':
                raise RuntimeError('creation refused')
            super().upsert(aircraft, model)

    injector = Injector()
    manager = TrafficManager(_Provider([_aircraft('OK', 48.01), _aircraft('FAIL', 48.02)]),
                             _Models(), injector, lambda: (48, 2))
    states = []
    manager.progress = states.append
    manager.sync_once()
    assert states[-1]['state'] == 'error'
    assert states[-1]['confirmed'] == 1
    assert states[-1]['failed'] == 1
    manager.close()


def test_large_fleet_is_created_in_batches_with_visible_progress():
    injector = _Injector()
    provider = _Provider([_aircraft(str(i), 48.01 + i * .001) for i in range(9)])
    manager = TrafficManager(provider, _Models(), injector, lambda: (48, 2))
    states = []
    manager.progress = states.append
    manager.sync_once()
    assert len(injector.owned) == 4
    assert states[-1]['state'] == 'loading'
    manager.sync_once()
    manager.sync_once()
    assert len(injector.owned) == 9
    assert states[-1]['state'] == 'active'
    manager.close()


def test_manager_bounds_radius_count_and_infers_evidence_based_ground_state():
    provider = _Provider([
        _aircraft("NEAR", 48.01),
        _aircraft("INFERRED_FLIGHT", 48.02, on_ground=None, speed=120),
        _aircraft("INFERRED_GROUND", 48.03, on_ground=None, speed=20),
        _aircraft("AMBIGUOUS", 48.04, on_ground=None, speed=65),
        _aircraft("FAR", 52.0),
    ])
    injector = _Injector()
    manager = TrafficManager(
        provider, _Models(), injector, lambda: (48.0, 2.0),
        radius_nm=100, max_aircraft=4,
    )

    result = manager.sync_once()

    assert result == {
        "created_or_updated": 3, "removed": 0, "recreated": 0, "skipped": 1,
    }
    assert [item.uid for item, _model in injector.updated] == [
        "NEAR", "INFERRED_FLIGHT", "INFERRED_GROUND",
    ]
    assert injector.updated[1][0].on_ground is False
    assert injector.updated[2][0].on_ground is True


def test_manager_preserves_ambiguous_owned_aircraft_and_removes_absent_ones():
    provider = _Provider([_aircraft("KEPT", 48.01, on_ground=None, speed=65)])
    injector = _Injector()
    injector.owned = {"KEPT": object(), "GONE": object()}
    manager = TrafficManager(provider, _Models(), injector, lambda: (48.0, 2.0))

    result = manager.sync_once()

    assert result == {
        "created_or_updated": 0, "removed": 1, "recreated": 0, "skipped": 1,
    }
    assert injector.removed == ["GONE"]
    assert "KEPT" in injector.owned


def test_manager_close_only_closes_its_injector():
    provider = _Provider([])
    injector = _Injector()
    manager = TrafficManager(provider, _Models(), injector, lambda: (48.0, 2.0))

    manager.close()

    assert injector.closed is True


def test_manager_recreates_aircraft_the_simulator_no_longer_carries():
    """Un objet AI disparu du simulateur doit repartir, pas rester fantôme."""
    provider = _Provider([_aircraft("LOST", 48.01)])
    injector = _Injector(lost=["LOST"])
    injector.owned = {"LOST": object()}
    manager = TrafficManager(provider, _Models(), injector, lambda: (48.0, 2.0))

    result = manager.sync_once()

    assert injector.reconciled == [int(40.0 * 1852)]
    assert result["recreated"] == 1
    assert result["removed"] == 0
    assert [item.uid for item, _model in injector.updated] == ["LOST"]


def test_manager_survives_an_impossible_reconciliation():
    """Un relevé refusé écarte la remise à niveau, jamais le cycle entier."""
    class _Refusing(_Injector):
        def reconcile(self, radius_m):
            raise RuntimeError("SimConnect indisponible")

    provider = _Provider([_aircraft("NEAR", 48.01)])
    injector = _Refusing()
    manager = TrafficManager(provider, _Models(), injector, lambda: (48.0, 2.0))

    result = manager.sync_once()

    assert result["recreated"] == 0
    assert [item.uid for item, _model in injector.updated] == ["NEAR"]


def test_the_player_is_never_injected_into_his_own_cockpit():
    """Le réseau rend aussi l'appareil du joueur quand il y est connecté."""
    provider = _Provider([
        _aircraft("SELF", 48.0, on_ground=True, speed=0),
        _aircraft("OTHER", 48.05),
    ])
    injector = _Injector()
    manager = TrafficManager(
        provider, _Models(), injector, lambda: (48.0, 2.0),
        altitude=lambda: 5000.0,
    )

    result = manager.sync_once()

    assert [item.uid for item, _model in injector.updated] == ["OTHER"]
    assert result["created_or_updated"] == 1


def test_an_aircraft_flying_over_the_player_is_still_injected():
    """Superposition n'est pas survol : seul le même niveau désigne le joueur."""
    provider = _Provider([_aircraft("ABOVE", 48.0, on_ground=False)])
    injector = _Injector()
    manager = TrafficManager(
        provider, _Models(), injector, lambda: (48.0, 2.0),
        altitude=lambda: 200.0,
    )

    manager.sync_once()

    assert [item.uid for item, _model in injector.updated] == ["ABOVE"]


def test_an_unreadable_own_altitude_never_stops_the_cycle():
    def refuse():
        raise RuntimeError("position indisponible")

    provider = _Provider([_aircraft("NEAR", 48.05)])
    injector = _Injector()
    manager = TrafficManager(
        provider, _Models(), injector, lambda: (48.0, 2.0), altitude=refuse,
    )

    assert manager.sync_once()["created_or_updated"] == 1


def test_a_cached_network_position_moves_smoothly_between_readings():
    clock = _Clock()
    provider = _Provider([
        _aircraft("TAXI", 48.0, speed=20, on_ground=True),
    ])
    injector = _Injector()
    manager = TrafficManager(
        provider, _Models(), injector, lambda: (47.9, 2.0), clock=clock,
    )

    manager.sync_once()
    first = injector.updated[-1][0]
    clock.advance(1.0)
    manager.sync_once()
    second = injector.updated[-1][0]

    assert second.latitude == pytest.approx(first.latitude, abs=1e-7)
    assert second.longitude > first.longitude
    assert second.on_ground is True
    # Le relevé SimConnect coûteux reste cadencé indépendamment du lissage.
    assert injector.reconciled == [int(40.0 * 1852)]


def test_a_new_taxi_observation_is_joined_without_teleporting():
    clock = _Clock()
    provider = _Provider([_aircraft("TAXI", 48.0, speed=20, on_ground=True)])
    injector = _Injector()
    manager = TrafficManager(
        provider, _Models(), injector, lambda: (47.9, 2.0), clock=clock,
    )
    manager.sync_once()

    clock.advance(1.0)
    provider.aircraft = [
        replace(provider.aircraft[0], longitude=2.01, heading_deg=110.0)
    ]
    manager.sync_once()
    joined = injector.updated[-1][0]

    assert 2.0 < joined.longitude < 2.01
    assert 90.0 < joined.heading_deg < 110.0


def test_small_adsb_position_noise_does_not_move_a_parked_aircraft():
    clock = _Clock()
    parked = _aircraft("PARKED", 48.0, speed=0, on_ground=True)
    provider = _Provider([parked])
    injector = _Injector()
    manager = TrafficManager(
        provider, _Models(), injector, lambda: (47.9, 2.0), clock=clock,
    )
    manager.sync_once()
    first = injector.updated[-1][0]

    clock.advance(60.0)
    provider.aircraft = [
        replace(
            parked,
            latitude=48.0001,
            longitude=2.0001,
            altitude_ft=parked.altitude_ft + 30.0,
            heading_deg=95.0,
        )
    ]
    manager.sync_once()
    held = injector.updated[-1][0]

    assert held.latitude == first.latitude
    assert held.longitude == first.longitude
    assert held.altitude_ft == first.altitude_ft
    assert held.heading_deg == first.heading_deg


def test_a_missing_network_aircraft_is_held_then_removed_without_blinking():
    clock = _Clock()
    provider = _Provider([_aircraft("HELD", 48.01)])
    injector = _Injector()
    manager = TrafficManager(
        provider, _Models(), injector, lambda: (48.0, 2.0), clock=clock,
    )

    manager.sync_once()
    provider.aircraft = []
    clock.advance(60.0)
    held = manager.sync_once()

    assert held["created_or_updated"] == 1
    assert held["removed"] == 0
    assert "HELD" in injector.owned

    clock.advance(31.0)
    expired = manager.sync_once()

    assert expired["removed"] == 1
    assert "HELD" not in injector.owned


def test_opensky_unknown_type_uses_the_fsltl_generic_fallback():
    class _OpenSkyProvider(_Provider):
        name = "OpenSky"

    class _FallbackModels(_Models):
        def __init__(self):
            self.fallbacks = []

        def match(self, aircraft):
            return None

        def generic_fallback(self, aircraft):
            self.fallbacks.append(aircraft.uid)
            return ResolvedAircraftModel(
                "FSLTL_A320_ZZZZ", "FSLTL", MatchKind.FAMILY, 2, "test"
            )

    provider = _OpenSkyProvider([
        _aircraft("REAL", 48.01, speed=210, on_ground=False),
    ])
    provider.aircraft[0] = replace(provider.aircraft[0], aircraft_type=None)
    models = _FallbackModels()
    injector = _Injector()
    manager = TrafficManager(provider, models, injector, lambda: (48.0, 2.0))

    result = manager.sync_once()

    assert result["created_or_updated"] == 1
    assert models.fallbacks == ["REAL"]
    assert injector.updated[0][1].title == "FSLTL_A320_ZZZZ"


@pytest.mark.parametrize("on_ground", [True, None])
def test_parking_report_removes_momentum_and_returns_to_reported_stand(on_ground):
    clock = _Clock()
    taxi = _aircraft("PARK", 48.01, speed=20, on_ground=on_ground)
    provider = _Provider([taxi])
    injector = _Injector()
    manager = TrafficManager(provider, _Models(), injector, lambda: (48.0, 2.0), clock=clock)
    manager.sync_once()
    for _ in range(30):
        clock.advance(1 / 30)
        manager.render_once()
    previous = injector.updated[-1][0].longitude
    assert previous > taxi.longitude
    # The parking report is within the jitter deadband, but follows motion.
    provider.aircraft = [replace(taxi, ground_speed_kt=0)]
    manager.sync_once()
    for frame in range(900):
        clock.advance(1 / 30)
        if frame % 30 == 0:
            manager.sync_once()
        manager.render_once()
        parked = injector.updated[-1][0]
        assert taxi.longitude <= parked.longitude <= previous
        assert parked.ground_speed_kt == 0
        previous = parked.longitude
    assert parked.longitude == taxi.longitude
    assert parked.latitude == taxi.latitude
    provider.aircraft = [replace(taxi, longitude=2.0002)]
    manager.sync_once()
    clock.advance(1 / 30)
    manager.render_once()
    assert injector.updated[-1][0].longitude > parked.longitude


@pytest.mark.parametrize("missing", [False, True])
@pytest.mark.parametrize("on_ground", [True, None])
def test_old_ground_report_cannot_extend_prediction_on_every_frame(missing, on_ground):
    clock = _Clock()
    taxi = _aircraft("STALE", 48.01, speed=20, on_ground=on_ground)
    provider = _Provider([taxi])
    injector = _Injector()
    manager = TrafficManager(provider, _Models(), injector, lambda: (48.0, 2.0), clock=clock)
    manager.sync_once()
    if missing:
        provider.aircraft = []
    for frame in range(1800):
        clock.advance(1 / 30)
        if frame % 30 == 0:
            manager.sync_once()
        manager.render_once()
        rendered = injector.updated[-1][0]
        # Two seconds at reported speed, then three seconds of deceleration.
        assert distance_nm((taxi.latitude, taxi.longitude),
                           (rendered.latitude, rendered.longitude)) <= 20 * 3.5 / 3600 + 1e-9
    held = injector.updated[-1][0]
    clock.advance(10)
    manager.sync_once()
    manager.render_once()
    assert injector.updated[-1][0] == held
    assert held.ground_speed_kt == 0
    if missing:
        clock.advance(21)
        assert manager.sync_once()["removed"] == 1


def test_position_timestamp_keeps_cached_report_old_but_accepts_fresh_identical_position():
    clock = _Clock()
    epoch = 1_800_000_000.0
    raw = replace(_aircraft("AGE", 48.01, speed=20, on_ground=True),
                  position_timestamp=epoch - 20)
    provider, injector = _Provider([raw]), _Injector()
    manager = TrafficManager(provider, _Models(), injector, lambda: (48.0, 2.0),
                             clock=clock, wall_clock=lambda: epoch + clock() - 1000)
    manager.sync_once()
    assert manager._tracks["AGE"].observed_at == 980
    assert injector.updated[-1][0].ground_speed_kt == 0
    clock.advance(1)
    manager.sync_once()
    manager.render_once()
    assert manager._tracks["AGE"].observed_at == 980
    assert injector.updated[-1][0].ground_speed_kt == 0
    # Same position, but this time the source explicitly confirms a new observation.
    provider.aircraft = [replace(raw, position_timestamp=epoch + 1)]
    manager.sync_once()
    manager.render_once()
    assert manager._tracks["AGE"].observed_at == 1001
    assert manager._render_tracks["AGE"].observed_at == 1001
    assert injector.updated[-1][0].ground_speed_kt == 20
    # An older report cannot replace the accepted position, even when it changes.
    provider.aircraft = [replace(raw, longitude=2.1)]
    clock.advance(1)
    manager.sync_once()
    assert manager._tracks["AGE"].aircraft.longitude == raw.longitude
    assert manager._tracks["AGE"].observed_at == 1001


@pytest.mark.parametrize("timestamp", [None, -1, float("nan"), float("inf"), 1_800_000_100])
def test_invalid_position_time_uses_local_observation_age(timestamp):
    clock = _Clock()
    raw = replace(_aircraft("AGE", 48.01, speed=20, on_ground=True),
                  position_timestamp=timestamp)
    manager = TrafficManager(_Provider([raw]), _Models(), _Injector(),
                             lambda: (48.0, 2.0), clock=clock,
                             wall_clock=lambda: 1_800_000_000)
    manager.sync_once()
    assert manager._tracks["AGE"].observed_at == clock()
    clock.advance(10)
    manager.sync_once()
    assert manager._tracks["AGE"].observed_at == 1000


def test_render_prioritizes_nearby_aircraft_and_leaves_settled_parking_alone():
    clock = _Clock()
    provider = _Provider([_aircraft("NEAR", 48.01), _aircraft("FAR", 48.8),
                          _aircraft("PARKED", 48.02, speed=0, on_ground=True)])
    injector = _Injector()
    manager = TrafficManager(
        provider, _Models(), injector, lambda: (48, 2), clock=clock,
        radius_nm=100,
    )
    manager.sync_once()
    manager.render_once()
    injector.updated.clear()
    for _ in range(30):
        clock.advance(1 / 30)
        manager.render_once()
    ids = [item.uid for item, _ in injector.updated]
    assert ids.count("NEAR") == 30
    assert ids.count("FAR") == 5
    assert ids.count("PARKED") == 0
    provider.aircraft[2] = replace(provider.aircraft[2], ground_speed_kt=15)
    manager.sync_once()
    clock.advance(1 / 30)
    manager.render_once()
    assert injector.updated[-1][0].uid in {"NEAR", "PARKED", "FAR"}
    assert manager._render_tracks["PARKED"].parked is None


def test_taxi_acceleration_and_heading_are_smoothed_but_stop_is_immediate():
    clock = _Clock()
    first = replace(_aircraft("TURN", 48.01, speed=10, on_ground=True), heading_deg=359)
    manager = TrafficManager(_Provider([]), _Models(), _Injector(), lambda: (48, 2), clock=clock)
    manager._tracked(first, clock())
    clock.advance(1 / 30)
    moving = manager._tracked(replace(first, heading_deg=1, ground_speed_kt=20), clock())
    assert 10 < moving.ground_speed_kt < 20
    assert moving.heading_deg > 359 or moving.heading_deg < 1
    clock.advance(1 / 30)
    stopped = manager._tracked(replace(first, ground_speed_kt=0), clock())
    assert stopped.ground_speed_kt == 0
