from navixav.traffic.base import MatchKind, ResolvedAircraftModel, TrafficAircraft
from navixav.traffic.injector import SimConnectTrafficInjector


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
    injector.upsert(_aircraft(), _model())
    assert client.updated[0][0] == 42
    assert injector.owned["AFR1"].object_id == 42


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
