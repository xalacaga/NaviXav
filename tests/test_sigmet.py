"""SIGMET : lecture des deux flux d'aviationweather.gov et rapport à la route."""

from __future__ import annotations

import requests

from navixav.config import Settings
from navixav.web.app import create_app
from navixav.weather.sigmet import (
    SigmetFeed,
    contains,
    densify,
    parse_international,
    parse_us,
    relate_to_route,
)

NOW = 1_794_140_000


def _square(lat: float, lon: float, size: float = 2.0) -> list[dict]:
    return [
        {"lat": lat, "lon": lon},
        {"lat": lat + size, "lon": lon},
        {"lat": lat + size, "lon": lon + size},
        {"lat": lat, "lon": lon + size},
        {"lat": lat, "lon": lon},
    ]


def _international(**overrides) -> dict:
    item = {
        "firId": "LFFF",
        "seriesId": "W01",
        "hazard": "TS",
        "qualifier": "EMBD",
        "base": None,
        "top": 38000,
        "validTimeFrom": NOW - 600,
        "validTimeTo": NOW + 3600,
        "geom": "AREA",
        "coords": _square(46.0, 1.0),
        "rawSigmet": "LFFF SIGMET W01 VALID ...",
    }
    item.update(overrides)
    return item


def test_international_sigmets_keep_hazard_levels_and_every_area():
    [single, multiple] = parse_international([
        _international(),
        _international(
            seriesId="U15", hazard="TURB", qualifier="SEV", base=10000, top=34000,
            geom="AREAS", coords=[_square(-45.0, 157.0), _square(-36.0, 151.0)],
        ),
    ])

    assert (single.hazard, single.qualifier, single.base_ft, single.top_ft) == ("TS", "EMBD", None, 38000)
    assert single.polygons[0][0] == (46.0, 1.0)
    assert len(multiple.polygons) == 2
    assert multiple.to_dict()["polygons"][1][0] == [-36.0, 151.0]


def test_us_feed_keeps_sigmets_and_normalises_their_hazards():
    sigmets = parse_us([
        {
            "seriesId": "XRAY 2", "icaoId": "KKCI", "airSigmetType": "SIGMET",
            "hazard": "CONVECTIVE", "severity": 5,
            "altitudeLow1": None, "altitudeLow2": None,
            "altitudeHi1": None, "altitudeHi2": 14000,
            "validTimeFrom": NOW - 60, "validTimeTo": NOW + 600,
            "coords": _square(40.0, -100.0), "rawAirSigmet": "SIGMET XRAY 2",
        },
        {
            "seriesId": "O1", "airSigmetType": "OUTLOOK", "hazard": "CONVECTIVE",
            "validTimeFrom": NOW, "validTimeTo": NOW + 600, "coords": _square(30.0, -90.0),
        },
    ])

    assert len(sigmets) == 1
    assert (sigmets[0].hazard, sigmets[0].qualifier, sigmets[0].base_ft, sigmets[0].top_ft) == (
        "TS", "SEV", None, 14000,
    )


def test_incomplete_sigmets_are_dropped_rather_than_guessed():
    assert parse_international([
        _international(coords=[{"lat": 1, "lon": 1}, {"lat": 2, "lon": 2}]),
        _international(validTimeTo=None),
        _international(coords="garbage"),
    ]) == []


def test_containment_survives_the_antimeridian_and_the_far_side_of_the_globe():
    pacific = [(10.0, 179.0), (12.0, 179.0), (12.0, -179.0), (10.0, -179.0)]
    atlantic = [(-32.0, -40.0), (-19.0, -40.0), (-19.0, -16.0), (-32.0, -16.0)]

    assert contains(pacific, (11.0, 179.9))
    assert contains(pacific, (11.0, -179.9))
    assert not contains(pacific, (11.0, 170.0))
    # A polygon on the other side of the world must not stretch around it.
    assert not contains(atlantic, (-35.0, 148.0))
    assert contains(atlantic, (-25.0, -30.0))


def test_the_route_is_sampled_finely_enough_to_meet_small_areas():
    samples = densify([(45.0, 0.0), (45.0, 10.0)], step_nm=10)

    assert samples[0] == (45.0, 0.0)
    assert samples[-1] == (45.0, 10.0)
    assert len(samples) > 40


def test_route_relation_flags_crossed_areas_and_drops_distant_ones():
    crossed, nearby, distant, above = parse_international([
        _international(seriesId="A", coords=_square(46.0, 1.0)),
        _international(seriesId="B", coords=_square(46.0, 4.5)),
        _international(seriesId="C", coords=_square(10.0, 100.0)),
        _international(seriesId="D", base=41000, top=45000, coords=_square(46.0, 1.0)),
    ])
    route = [(47.0, -1.0), (47.0, 3.0)]

    related = {s.id.split("-")[2]: s for s in relate_to_route([crossed, nearby, distant, above], route, 37000)}

    assert set(related) == {"A", "B", "D"}
    assert related["A"].on_route is True
    assert related["B"].on_route is False
    # Above the cruise level: shown, but not on the route.
    assert related["D"].on_route is False
    assert list(related)[0] == "A"


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _Session:
    def __init__(self):
        self.calls = 0
        self.fail = False

    def get(self, url, **_kwargs):
        self.calls += 1
        if self.fail:
            raise requests.ConnectionError("offline")
        return _Response([_international()] if "isigmet" in url else [])

    def close(self):
        pass


def test_the_feed_is_cached_and_survives_an_outage():
    session = _Session()
    feed = SigmetFeed(session=session, cache_seconds=600)

    sigmets, fetched_at = feed.current(now=NOW)
    assert len(sigmets) == 1 and fetched_at > 0
    feed.current(now=NOW)
    assert session.calls == 2  # one request per feed, then the cache

    session.fail = True
    feed._fetched_at -= 601
    assert len(feed.current(now=NOW)[0]) == 1
    calls = session.calls
    feed.current(now=NOW)
    assert session.calls == calls  # no retry storm right after a failure


def test_expired_sigmets_are_not_returned():
    session = _Session()
    feed = SigmetFeed(session=session)

    assert feed.current(now=NOW + 7200)[0] == []


def test_the_endpoint_returns_every_sigmet_without_a_flight(monkeypatch, tmp_path):
    app = create_app(Settings(navdata_store=tmp_path / "missing.sqlite"))
    endpoint = next(route.endpoint for route in app.routes if route.path == "/api/weather/sigmets")
    monkeypatch.setattr(SigmetFeed, "current", lambda _self: (parse_international([_international()]), NOW))
    try:
        result = endpoint()
    finally:
        app.state.close_resources()

    assert result["route_filtered"] is False
    assert result["sigmets"][0]["hazard"] == "TS"
    assert result["source"] == "aviationweather.gov"
