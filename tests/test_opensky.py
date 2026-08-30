import pytest
import requests

from navixav.traffic.opensky import OpenSkyClient, OpenSkyError
from navixav.traffic.registry import AircraftIdentity, AircraftRegistry


class _OfflineRegistry(AircraftRegistry):
    """Registre qui ne sort jamais : les tests ne joignent aucun service."""

    def __init__(self, path, known=None):
        super().__init__(path=path, session=_RefusingSession())
        self.requested = []
        self._known = dict(known or {})

    def lookup(self, icao24):
        return self._known.get(icao24.strip().lower())

    def request(self, icao24):
        self.requested.append(icao24)


class _RefusingSession:
    def get(self, *_args, **_kwargs):
        raise AssertionError("le registre ne doit pas être interrogé ici")

    def close(self):
        return None


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Session:
    def __init__(self, payload):
        self.payload = payload
        self.params = None
        self.calls = 0

    def get(self, _url, *, params, timeout, headers):
        self.calls += 1
        self.params = params
        if isinstance(self.payload, Exception):
            raise self.payload
        return _Response(self.payload)


def test_real_traffic_is_bounded_normalized_and_cached(tmp_path):
    session = _Session({
        "time": 1788084000,
        "states": [[
            "39abcd", " AFR123 ", "France", 0, 0, 2.2, 48.5,
            3048.0, False, 154.33, 270.0, -2.54, None, None, None, False, 0,
        ]],
    })
    client = OpenSkyClient(
        lambda: (48.0, 2.0), session=session,
        registry=_OfflineRegistry(tmp_path / "registry.sqlite"),
    )

    aircraft = client.traffic()[0]
    client.updated_at()

    assert aircraft.uid == "opensky:39abcd"
    assert aircraft.callsign == "AFR123"
    assert aircraft.aircraft_type is None
    assert aircraft.altitude_ft == pytest.approx(10000, rel=0.001)
    assert aircraft.ground_speed_kt == pytest.approx(300, rel=0.001)
    assert aircraft.vertical_speed_fpm == pytest.approx(-500, rel=0.01)
    assert session.params["lamin"] < 48.0 < session.params["lamax"]
    assert session.calls == 1


def test_real_traffic_needs_msfs_position_and_a_valid_feed(tmp_path):
    client = OpenSkyClient(
        lambda: (_ for _ in ()).throw(RuntimeError("offline")), session=_Session({}),
        registry=_OfflineRegistry(tmp_path / "a.sqlite"),
    )
    with pytest.raises(OpenSkyError, match="Position MSFS"):
        client.traffic()

    broken = OpenSkyClient(
        lambda: (48.0, 2.0), session=_Session(requests.ConnectionError("offline")),
        registry=_OfflineRegistry(tmp_path / "b.sqlite"),
    )
    with pytest.raises(OpenSkyError, match="OpenSky"):
        broken.traffic()


def test_resolved_identity_makes_real_traffic_injectable(tmp_path):
    """Sans type, aucun modèle FSLTL : le registre est ce qui rend l'ADS-B injectable."""
    session = _Session({
        "time": 1788084000,
        "states": [[
            "39abcd", "AFR123", "France", 0, 0, 2.2, 48.5,
            3048.0, False, 154.33, 270.0, -2.54, None, None, None, False, 0,
        ]],
    })
    registry = _OfflineRegistry(
        tmp_path / "registry.sqlite",
        known={"39abcd": AircraftIdentity("39abcd", "A320", "AFR")},
    )
    client = OpenSkyClient(lambda: (48.0, 2.0), session=session, registry=registry)

    aircraft = client.traffic()[0]

    assert aircraft.aircraft_type == "A320"
    assert aircraft.airline_icao == "AFR"
    # Déjà connue, l'adresse ne repart pas en résolution.
    assert registry.requested == []


def test_identity_resolved_during_the_opensky_cache_is_used_immediately(tmp_path):
    session = _Session({
        "time": 1788084000,
        "states": [[
            "39abcd", "AFR123", "France", 0, 0, 2.2, 48.5,
            3048.0, False, 154.33, 270.0, -2.54, None, None, None, False, 0,
        ]],
    })
    registry = _OfflineRegistry(tmp_path / "registry.sqlite")
    client = OpenSkyClient(lambda: (48.0, 2.0), session=session, registry=registry)

    assert client.traffic()[0].aircraft_type is None
    registry._known["39abcd"] = AircraftIdentity("39abcd", "A320", "AFR")
    resolved = client.traffic()[0]

    assert resolved.aircraft_type == "A320"
    assert resolved.airline_icao == "AFR"
    assert session.calls == 1


def test_unknown_address_is_queued_and_flown_without_a_type(tmp_path):
    session = _Session({
        "time": 1788084000,
        "states": [[
            "abcdef", "BAW99", "UK", 0, 0, 2.2, 48.5,
            3048.0, False, 154.33, 270.0, -2.54, None, None, None, False, 0,
        ]],
    })
    registry = _OfflineRegistry(tmp_path / "registry.sqlite")
    client = OpenSkyClient(lambda: (48.0, 2.0), session=session, registry=registry)

    aircraft = client.traffic()[0]

    assert aircraft.aircraft_type is None
    assert registry.requested == ["abcdef"]


def test_missing_callsign_receives_a_stable_generic_one(tmp_path):
    """Un champ vide vaudrait immatriculation manquante dans le simulateur."""
    session = _Session({
        "time": 1788084000,
        "states": [[
            "39abcd", "   ", "France", 0, 0, 2.2, 48.5,
            3048.0, False, 154.33, 270.0, -2.54, None, None, None, False, 0,
        ]],
    })
    client = OpenSkyClient(
        lambda: (48.0, 2.0), session=session,
        registry=_OfflineRegistry(tmp_path / "registry.sqlite"),
    )

    aircraft = client.traffic()[0]

    assert aircraft.callsign == "TFCABCD"
    assert aircraft.callsign.isalnum()


def test_parked_aircraft_with_sparse_adsb_motion_remains_spawnable(tmp_path):
    session = _Session({
        "time": 1788084000,
        "states": [[
            "39abcd", "AFR123", "France", 0, 0, 2.2, 48.5,
            None, True, None, None, None, None, None, None, False, 0,
        ]],
    })
    client = OpenSkyClient(
        lambda: (48.0, 2.0), session=session,
        registry=_OfflineRegistry(tmp_path / "registry.sqlite"),
    )

    aircraft = client.traffic()[0]

    assert aircraft.on_ground is True
    assert aircraft.altitude_ft == 0.0
    assert aircraft.ground_speed_kt == 0.0
    assert aircraft.heading_deg == 0.0
