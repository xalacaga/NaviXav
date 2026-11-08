"""Calque radar : validation, cache et repli sur le dernier relevé."""

import requests

from navixav.config import Settings
from navixav.weather.radar import RadarFeed, _latest_frame
from navixav.web.app import create_app


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class Session:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0
        self.closed = False

    def get(self, *_args, **_kwargs):
        self.calls += 1
        if isinstance(self.payload, Exception):
            raise self.payload
        return Response(self.payload)

    def close(self):
        self.closed = True


PAYLOAD = {
    "generated": 1_700_000_060,
    "host": "https://tilecache.rainviewer.com",
    "radar": {
        "past": [
            {"time": 1_700_000_000, "path": "/v2/radar/1700000000"},
            {"time": 1_700_000_600, "path": "/v2/radar/1700000600"},
        ]
    },
}


def test_latest_radar_frame_builds_the_documented_tile_template():
    frame = _latest_frame(PAYLOAD)

    assert frame is not None
    assert frame["time"] == 1_700_000_600
    assert frame["max_zoom"] == 7
    assert frame["tile_url"].endswith("/{z}/{x}/{y}/2/1_1.png")


def test_radar_rejects_an_untrusted_tile_host():
    payload = {**PAYLOAD, "host": "https://example.invalid"}

    assert _latest_frame(payload) is None


def test_radar_feed_caches_and_keeps_the_previous_frame_on_failure():
    session = Session(PAYLOAD)
    feed = RadarFeed(session=session, cache_seconds=600)

    assert feed.current(monotonic=10)["time"] == 1_700_000_600
    assert feed.current(monotonic=20)["time"] == 1_700_000_600
    assert session.calls == 1

    session.payload = requests.ConnectionError("offline")
    assert feed.current(monotonic=700)["time"] == 1_700_000_600
    feed.close()
    assert session.closed is True


def test_radar_feed_fails_when_no_frame_has_ever_loaded():
    feed = RadarFeed(session=Session(requests.ConnectionError("offline")))

    try:
        feed.current(monotonic=10)
    except requests.ConnectionError:
        pass
    else:  # pragma: no cover - contrat explicite du test
        raise AssertionError("une première panne doit être signalée")


def test_radar_endpoint_exposes_only_the_validated_frame(monkeypatch, tmp_path):
    frame = _latest_frame(PAYLOAD)
    monkeypatch.setattr(RadarFeed, "current", lambda _self: frame)
    app = create_app(Settings(navdata_store=tmp_path / "missing.sqlite"))
    endpoint = next(
        route.endpoint for route in app.routes if route.path == "/api/weather/radar"
    )
    try:
        result = endpoint()
    finally:
        app.state.close_resources()

    assert result["frame"]["source"] == "RainViewer"
    assert result["frame"]["max_zoom"] == 7
    assert result["refresh_interval_seconds"] == 600
