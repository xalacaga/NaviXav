import requests
from unittest.mock import patch

from navixav.config import Settings
from navixav.live.base import AircraftState
from navixav.traffic.ivao import IvaoClient, IvaoError
from navixav.web.app import create_app


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
        self.calls = 0
        self.closed = False

    def get(self, *_args, **_kwargs):
        self.calls += 1
        if isinstance(self.payload, Exception):
            raise self.payload
        return _Response(self.payload)

    def close(self):
        self.closed = True


def _feed():
    return {
        "updatedAt": "2026-08-30T10:16:52.000Z",
        "clients": {"pilots": [{
            "id": 42,
            "callsign": "AFR123",
            "lastTrack": {
                "latitude": 48.5,
                "longitude": 2.2,
                "altitude": 12000,
                "groundSpeed": 310,
                "heading": 270,
                "onGround": False,
            },
            "flightPlan": {
                "departureId": "LFPG",
                "arrivalId": "LFBO",
                "aircraft": {"icaoCode": "A320"},
            },
        }]},
    }


def test_ivao_public_feed_is_normalized_and_cached():
    session = _Session(_feed())
    client = IvaoClient(session=session)

    aircraft = client.traffic()[0]
    detail = client.detail("afr123")

    assert aircraft.uid == "ivao:42"
    assert aircraft.aircraft_type == "A320"
    assert aircraft.airline_icao == "AFR"
    assert (aircraft.departure, aircraft.arrival) == ("LFPG", "LFBO")
    assert aircraft.on_ground is False
    assert detail.aircraft == "A320"
    assert client.updated_at() == "2026-08-30T10:16:52.000Z"
    assert session.calls == 1


def test_ivao_rejects_an_invalid_or_unreachable_feed():
    invalid = IvaoClient(session=_Session({"clients": {}}))
    try:
        invalid.traffic()
    except IvaoError:
        pass
    else:
        raise AssertionError("Un flux IVAO invalide doit être refusé")

    unavailable = IvaoClient(session=_Session(requests.ConnectionError("offline")))
    try:
        unavailable.traffic()
    except IvaoError:
        pass
    else:
        raise AssertionError("Une panne IVAO doit être explicitée")


def test_generic_traffic_endpoint_uses_the_selected_network():
    client = IvaoClient(session=_Session(_feed()))
    app = create_app(
        Settings(traffic_enabled=True, traffic_source="ivao"),
        ivao_client=client,
    )
    endpoint = next(
        route.endpoint for route in app.routes
        if getattr(route, "path", "") == "/api/traffic"
    )

    payload = endpoint()

    assert payload["source"] == "IVAO"
    assert payload["traffic"][0]["aircraft"] == "A320"
    app.state.close_resources()


def test_generic_traffic_endpoint_caps_the_displayed_aircraft_count():
    feed = _feed()
    template = feed["clients"]["pilots"][0]
    feed["clients"]["pilots"] = [
        {**template, "id": index, "callsign": f"TST{index}"}
        for index in range(15)
    ]
    app = create_app(
        Settings(
            traffic_enabled=True, traffic_source="ivao",
            traffic_max_aircraft=10, traffic_radius_nm=40,
        ),
        ivao_client=IvaoClient(session=_Session(feed)),
    )
    endpoint = next(route.endpoint for route in app.routes
                    if getattr(route, "path", "") == "/api/traffic")
    try:
        assert len(endpoint()["traffic"]) == 10
    finally:
        app.state.close_resources()


def test_generic_traffic_endpoint_keeps_nearest_aircraft_inside_radius():
    feed = _feed()
    template = feed["clients"]["pilots"][0]
    feed["clients"]["pilots"] = [
        {**template, "id": 1, "callsign": "NEAR", "lastTrack": {
            **template["lastTrack"], "latitude": 48.1, "longitude": 2.0,
        }},
        {**template, "id": 2, "callsign": "FAR", "lastTrack": {
            **template["lastTrack"], "latitude": 49.0, "longitude": 2.0,
        }},
    ]

    class Tracker:
        def read(self):
            return AircraftState(latitude=48.0, longitude=2.0, altitude_ft=10000)
        def close(self): pass
        def set_aircraft_hint(self, _hint): pass

    with patch("navixav.web.app.LiveTracker", return_value=Tracker()):
        app = create_app(
            Settings(traffic_enabled=True, traffic_source="ivao",
                     traffic_max_aircraft=10, traffic_radius_nm=40),
            ivao_client=IvaoClient(session=_Session(feed)),
        )
    endpoint = next(route.endpoint for route in app.routes
                    if getattr(route, "path", "") == "/api/traffic")
    try:
        assert [item["callsign"] for item in endpoint()["traffic"]] == ["NEAR"]
    finally:
        app.state.close_resources()
