from dataclasses import replace
import threading

import pytest

from navixav.traffic.base import MatchKind, ResolvedAircraftModel, TrafficAircraft
from navixav.traffic.injector import SimConnectTrafficInjector
from navixav.traffic.manager import TrafficManager
from navixav.msfs.client import SimConnectError


class FakeClient:
    def __init__(self, live=None):
        self.created = []
        self.updated = []
        self.removed = []
        self.closed = False
        self.enumerated = []
        self.live = [{"object_id": 42}] if live is None else live
        self._next_object_id = 42

    def create_ai_aircraft(self, title, callsign, **position):
        self.created.append((title, callsign, position))
        return (17, self._next_object_id)

    def read_objects(self, variables, radius_m, text_variable=None):
        self.enumerated.append((tuple(variables), radius_m))
        return list(self.live)

    def update_ai_aircraft(self, object_id, **position):
        self.updated.append((object_id, position))

    def remove_ai_object(self, object_id):
        self.removed.append(object_id)

    def close(self):
        self.closed = True


def _aircraft() -> TrafficAircraft:
    return TrafficAircraft(
        "AFR1", "AFR1", "A320", "AFR", 48.0, 2.0,
        altitude_ft=3000, heading_deg=90, ground_speed_kt=180, on_ground=False,
    )


def _model(title="FSLTL_A320_AFR") -> ResolvedAircraftModel:
    return ResolvedAircraftModel(title, "FSLTL", MatchKind.EXACT, 0, "exact")


def test_injector_tracks_only_ids_returned_by_its_own_creation():
    client = FakeClient()
    injector = SimConnectTrafficInjector(lambda: client)
    owned = injector.upsert(_aircraft(), _model())
    assert (owned.request_id, owned.object_id) == (17, 42)
    injector.upsert(replace(_aircraft(), longitude=2.001), _model())
    assert client.updated[0][0] == 42
    assert injector.owned["AFR1"].object_id == 42


def test_a_stationary_aircraft_is_not_repositioned_every_cycle():
    client = FakeClient()
    injector = SimConnectTrafficInjector(lambda: client)
    injector.upsert(_aircraft(), _model())

    injector.upsert(_aircraft(), _model())

    assert client.updated == []


def test_model_change_recreates_and_close_removes_owned_objects():
    client = FakeClient()
    injector = SimConnectTrafficInjector(lambda: client)
    injector.upsert(_aircraft(), _model())
    injector.upsert(_aircraft(), _model("FSLTL_A320_ZZZZ"))
    assert client.removed == [42]
    injector.close()
    assert client.removed == [42, 42]
    assert client.closed


def test_incomplete_position_is_never_invented():
    client = FakeClient()
    injector = SimConnectTrafficInjector(lambda: client)
    aircraft = TrafficAircraft("X", "X", "A320", None, 48.0, 2.0)
    try:
        injector.upsert(aircraft, _model())
    except ValueError:
        pass
    else:
        raise AssertionError("une position incomplète a été injectée")
    assert client.created == []


def test_reconcile_forgets_objects_the_simulator_dropped():
    """L'ObjectID absent du relevé est oublié, donc recréé au cycle suivant."""
    client = FakeClient(live=[{"object_id": 7}])
    injector = SimConnectTrafficInjector(lambda: client)
    injector.upsert(_aircraft(), _model())

    assert injector.reconcile(185200) == ["AFR1"]
    assert injector.owned == {}
    # Le retrait est tenté avant l'oubli : un relevé tronqué par son délai
    # rendrait un objet vivant pour disparu, et le recréer sans supprimer le
    # premier laisserait un orphelin que plus personne ne posséderait.
    assert client.removed == [42]

    injector.upsert(_aircraft(), _model())
    assert len(client.created) == 2


def test_reconcile_keeps_everything_when_the_enumeration_comes_back_empty():
    """Un relevé vide est un relevé manqué : il ne fait rien disparaître."""
    client = FakeClient(live=[])
    injector = SimConnectTrafficInjector(lambda: client)
    injector.upsert(_aircraft(), _model())

    assert injector.reconcile(185200) == []
    assert injector.owned["AFR1"].object_id == 42


def test_reconcile_leaves_living_objects_alone():
    client = FakeClient(live=[{"object_id": 42}, {"object_id": 99}])
    injector = SimConnectTrafficInjector(lambda: client)
    injector.upsert(_aircraft(), _model())

    assert injector.reconcile(185200) == []
    assert injector.owned["AFR1"].object_id == 42
    assert client.enumerated[0][1] == 185200


@pytest.mark.parametrize('operation', ['position', 'reconcile', 'creation'])
def test_motion_continues_during_blocking_simulator_operations(operation):
    entered, release = threading.Event(), threading.Event()
    blocked = [False]

    def wait_for_simulator():
        entered.set()
        assert release.wait(3)

    class ControlClient(FakeClient):
        def create_ai_aircraft(self, *args, **kwargs):
            if blocked[0] and operation == 'creation':
                wait_for_simulator()
            result = super().create_ai_aircraft(*args, **kwargs)
            self._next_object_id += 1
            return result

        def read_objects(self, *args, **kwargs):
            if blocked[0] and operation == 'reconcile':
                wait_for_simulator()
            return super().read_objects(*args, **kwargs)

    def position():
        if blocked[0] and operation == 'position':
            wait_for_simulator()
        return 47.9, 2.0

    class Provider:
        name = 'TEST'
        aircraft = [_aircraft()]

        def traffic(self):
            return list(self.aircraft)

    class Models:
        def match(self, aircraft):
            return _model()

    control, motion = ControlClient(), FakeClient()
    clients = iter([control, motion])
    injector = SimConnectTrafficInjector(lambda: next(clients))
    provider = Provider()
    now = [100.0]
    manager = TrafficManager(provider, Models(), injector, position, clock=lambda: now[0])
    manager.sync_once()
    manager.render_once()
    initial_longitude = motion.updated[-1][1]['longitude']
    blocked[0] = True
    if operation == 'creation':
        provider.aircraft.append(replace(_aircraft(), uid='SECOND'))
    if operation == 'reconcile':
        manager._last_reconcile_at = None
    sync = threading.Thread(target=manager.sync_once, daemon=True)
    render = None
    sync.start()
    try:
        assert entered.wait(1)
        now[0] += 1 / 30
        render = threading.Thread(target=manager.render_once, daemon=True)
        render.start()
        render.join(1)
        assert not render.is_alive(), 'animation waited for SimConnect lifecycle'
        assert motion.updated[-1][1]['longitude'] > initial_longitude
        assert motion.created == []
    finally:
        release.set()
        sync.join(3)
        if render:
            render.join(3)
        manager.close()
    assert control.closed and motion.closed
    count = len(motion.updated)
    manager.render_once()
    injector.animate(_aircraft())
    assert len(motion.updated) == count


def test_slow_lifecycle_update_cannot_overwrite_newer_animated_position():
    control, motion = FakeClient(), FakeClient()
    clients = iter([control, motion])
    injector = SimConnectTrafficInjector(lambda: next(clients))
    injector.upsert(_aircraft(), _model())
    injector.animate(replace(_aircraft(), longitude=2.002))
    injector.upsert(replace(_aircraft(), longitude=2.001), _model())
    assert control.updated == []
    assert motion.updated[-1][1]['longitude'] == 2.002
    injector.remove('AFR1')
    injector.animate(_aircraft())
    assert len(motion.updated) == 1
    injector.close()


def test_failed_motion_connection_is_reopened_without_recreating_aircraft():
    class FailedMotion(FakeClient):
        def update_ai_aircraft(self, *args, **kwargs):
            raise SimConnectError('connection lost')

    control, failed, recovered = FakeClient(), FailedMotion(), FakeClient()
    clients = iter([control, failed, recovered])
    injector = SimConnectTrafficInjector(lambda: next(clients))
    injector.upsert(_aircraft(), _model())
    with pytest.raises(SimConnectError):
        injector.animate(_aircraft())
    assert failed.closed
    injector.animate(_aircraft())
    assert recovered.updated[-1][0] == 42
    assert len(control.created) == 1
    injector.close()
    assert recovered.closed
