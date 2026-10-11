import pytest
import requests

from navixav.traffic.opensky import CACHE_TTL_S, OpenSkyClient, OpenSkyError
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
    def __init__(self, payload, status_code=200, headers=None):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"{self.status_code} Client Error")
            error.response = self
            raise error

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
            "39abcd", " AFR123 ", "France", 1788083970, 1788083999, 2.2, 48.5,
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
    assert aircraft.position_timestamp == 1788083970
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


def test_anonymous_refresh_interval_fits_the_daily_credit_allowance():
    assert CACHE_TTL_S >= 86400 / 400


def test_rate_limit_header_stops_requests_until_opensky_allows_retry(tmp_path, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("navixav.traffic.opensky.time.monotonic", lambda: clock[0])

    class Session:
        calls = 0
        def get(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return _Response({}, 429, {
                    "X-Rate-Limit-Retry-After-Seconds": "120",
                })
            return _Response({"time": 1234, "states": []})

    session = Session()
    client = OpenSkyClient(
        lambda: (48.0, 2.0), session=session, ttl_s=0,
        registry=_OfflineRegistry(tmp_path / "rate-limit.sqlite"),
    )

    with pytest.raises(OpenSkyError, match="Quota public OpenSky") as first:
        client.traffic()
    assert first.value.code == "opensky_daily_quota"
    assert first.value.retry_after_s == 120
    clock[0] += 119
    with pytest.raises(OpenSkyError, match="Quota public OpenSky") as waiting:
        client.traffic()
    assert waiting.value.code == "opensky_daily_quota"
    assert waiting.value.retry_after_s == 1
    assert session.calls == 1

    clock[0] += 1
    assert client.traffic() == []
    assert session.calls == 2


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


def test_remaining_credits_pace_the_refresh_over_a_flight(tmp_path, monkeypatch):
    """Le quota journalier se dépense au rythme d'un vol, sans s'épuiser."""
    clock = [1000.0]
    monkeypatch.setattr("navixav.traffic.opensky.time.monotonic", lambda: clock[0])

    class Session:
        calls = 0
        remaining = 400

        def get(self, *_args, **_kwargs):
            self.calls += 1
            self.remaining -= 1
            return _Response({"time": 1234, "states": []}, headers={
                "X-Rate-Limit-Remaining": str(self.remaining),
            })

    session = Session()
    client = OpenSkyClient(
        lambda: (48.0, 2.0), session=session,
        registry=_OfflineRegistry(tmp_path / "budget.sqlite"),
    )
    client.traffic()
    # 399 crédits sur trois heures : un relevé toutes les 27 s environ.
    clock[0] += 20
    client.traffic()
    assert session.calls == 1
    clock[0] += 10
    client.traffic()
    assert session.calls == 2

    # Presque épuisé, le quota ramène la cadence au plafond anonyme.
    session.remaining = 5
    clock[0] += 30
    client.traffic()
    assert session.calls == 3
    clock[0] += CACHE_TTL_S - 1
    client.traffic()
    assert session.calls == 3
    clock[0] += 1
    client.traffic()
    assert session.calls == 4


def test_missing_credit_header_keeps_the_anonymous_interval(tmp_path, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("navixav.traffic.opensky.time.monotonic", lambda: clock[0])
    session = _Session({"time": 1234, "states": []})
    client = OpenSkyClient(
        lambda: (48.0, 2.0), session=session,
        registry=_OfflineRegistry(tmp_path / "no-header.sqlite"),
    )
    client.traffic()
    clock[0] += CACHE_TTL_S - 1
    client.traffic()
    assert session.calls == 1


def test_opensky_extends_the_injection_extrapolation_window(tmp_path):
    client = OpenSkyClient(
        lambda: (48.0, 2.0), session=_Session({"states": []}),
        registry=_OfflineRegistry(tmp_path / "window.sqlite"),
    )
    assert client.max_extrapolation_s > CACHE_TTL_S


def _state(track, time_position, on_ground=False):
    return ["39abcd", "AFR123", "France", time_position, time_position, 2.2, 48.5,
            3048.0, on_ground, 154.33, track, 0.0, None, None, None, False, 0]


def _sequence_client(tmp_path, reports):
    class Session:
        calls = 0

        def get(self, *_args, **_kwargs):
            payload = {"time": 1, "states": reports[self.calls]}
            self.calls += 1
            return _Response(payload)

    return OpenSkyClient(
        lambda: (48.0, 2.0), session=Session(), ttl_s=0,
        registry=_OfflineRegistry(tmp_path / "turn.sqlite"),
    )


def test_turn_rate_is_measured_between_two_reports(tmp_path):
    client = _sequence_client(tmp_path, [
        [_state(350.0, 1000)], [_state(20.0, 1030)], [_state(20.0, 1030)],
    ])
    assert client.traffic()[0].turn_rate_dps is None
    # 350° → 020° en 30 s : 1 °/s à droite, à travers le nord.
    assert client.traffic()[0].turn_rate_dps == pytest.approx(1.0)
    # Sans nouvelle position, la mesure précédente reste valable.
    assert client.traffic()[0].turn_rate_dps == pytest.approx(1.0)


def test_straight_ground_and_implausible_turns_are_not_anticipated(tmp_path):
    straight = _sequence_client(tmp_path, [[_state(90.0, 1000)], [_state(91.0, 1030)]])
    straight.traffic()
    assert straight.traffic()[0].turn_rate_dps is None

    ground = _sequence_client(tmp_path, [
        [_state(90.0, 1000, True)], [_state(180.0, 1030, True)],
    ])
    ground.traffic()
    assert ground.traffic()[0].turn_rate_dps is None

    noisy = _sequence_client(tmp_path, [[_state(90.0, 1000)], [_state(180.0, 1010)]])
    noisy.traffic()
    assert noisy.traffic()[0].turn_rate_dps == 3.0
