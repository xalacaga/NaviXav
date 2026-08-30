from dataclasses import replace

import pytest

from navixav.traffic.base import MatchKind, ResolvedAircraftModel, TrafficAircraft
from navixav.traffic.manager import TrafficManager


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

    assert injector.reconciled == [int(100.0 * 1852)]
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
    assert injector.reconciled == [int(100.0 * 1852)]


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
