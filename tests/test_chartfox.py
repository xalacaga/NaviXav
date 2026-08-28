"""OAuth public et catalogue ChartFox, sans appel réseau réel."""

from __future__ import annotations

from pathlib import Path
import sys
import uuid
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

import navixav.chartfox as chartfox_module
from navixav.chartfox import (
    AUTHORIZE_URL,
    SCOPES,
    ChartFoxClient,
    ChartFoxError,
    MemoryTokenStore,
    OAuthTokens,
    WindowsTokenStore,
)
from navixav.config import Settings
from navixav.web.app import create_app


CHART_ID = "55813afc-8119-4887-a0a3-f7f8ebb66609"


class _Response:
    def __init__(self, payload=None, *, content=b"", content_type="application/json", status=200):
        self.payload = payload
        self.content = content
        self.status_code = status
        self.ok = 200 <= status < 300
        self.headers = {"Content-Type": content_type}
        self.closed = False

    def json(self):
        return self.payload

    def iter_content(self, chunk_size):
        for index in range(0, len(self.content), chunk_size):
            yield self.content[index:index + chunk_size]

    def close(self):
        self.closed = True


class _Session:
    def __init__(self):
        self.headers = {}
        self.posts = []
        self.gets = []
        self.responses = []

    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return self.responses.pop(0)

    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        return self.responses.pop(0)

    def close(self):
        pass


def _chart(**changes):
    payload = {
        "id": CHART_ID,
        "airport_icao": "EGLL",
        "name": "ILS RWY 27L",
        "code": "IAC 27L",
        "type": 6,
        "type_key": "Approach",
        "view_url": f"https://chartfox.org/EGLL#{CHART_ID}",
        "meta": [
            {"type_key": "Runways", "value": ["27L"]},
            {"type_key": "ProcedureIdent", "value": ["ILS27L"]},
        ],
        "has_georeferences": True,
    }
    payload.update(changes)
    return payload


def _endpoint(app, path):
    return next(route.endpoint for route in app.routes if route.path == path)


def test_public_oauth_uses_pkce_state_and_only_required_scopes():
    client = ChartFoxClient(session=_Session(), token_store=MemoryTokenStore())
    redirect_uri = "http://127.0.0.1:8765/oauth/chartfox/callback"

    url = client.begin_authorization(redirect_uri)
    query = parse_qs(urlsplit(url).query)

    assert url.startswith(f"{AUTHORIZE_URL}?")
    assert query["redirect_uri"] == [redirect_uri]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == [client.pending.state]
    assert query["scope"] == [" ".join(SCOPES)]
    assert "oauth:telemetry:view" not in query["scope"][0]


def test_oauth_callback_exchanges_code_and_records_user_name():
    session = _Session()
    session.responses = [
        _Response({"access_token": "access", "refresh_token": "refresh", "expires_in": 3600}),
        _Response({"full_name": "Pilot VATSIM"}),
    ]
    store = MemoryTokenStore()
    client = ChartFoxClient(session=session, token_store=store)
    client.begin_authorization("http://127.0.0.1:8765/oauth/chartfox/callback")

    tokens = client.complete_authorization("code", client.pending.state)

    assert tokens.user_name == "Pilot VATSIM"
    assert store.load().access_token == "access"
    assert session.posts[0][1]["data"]["code_verifier"]
    assert session.gets[0][1]["headers"]["Authorization"] == "Bearer access"


def test_catalogue_is_normalised_and_cached():
    session = _Session()
    session.responses = [_Response({"data": {"6": [_chart()]}})]
    client = ChartFoxClient(
        session=session,
        token_store=MemoryTokenStore(OAuthTokens("access")),
    )

    first = client.list_airport_charts("egll")
    second = client.list_airport_charts("EGLL")

    assert len(session.gets) == 1
    assert first == second
    assert first[0].category == "Approches IAC"
    assert first[0].procedure_ident == "ILS27L"
    assert first[0].to_dict()["chartfox_georeference_available"] is True
    assert first[0].to_dict()["georeferenced"] is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI")
def test_windows_token_store_encrypts_the_token():
    path = Path.cwd() / f".chartfox-test-{uuid.uuid4().hex}.oauth"
    store = WindowsTokenStore(path)
    try:
        store.save(OAuthTokens("private-access", "private-refresh"))

        assert b"private-access" not in path.read_bytes()
        assert store.load().refresh_token == "private-refresh"
    finally:
        store.clear()
    assert not path.exists()


def test_document_honours_iframe_restriction():
    session = _Session()
    session.responses = [
        _Response({"data": {"6": [_chart()]}}),
        _Response(_chart(allows_iframe=False)),
    ]
    client = ChartFoxClient(
        session=session,
        token_store=MemoryTokenStore(OAuthTokens("access")),
    )

    assert client.chart_access(CHART_ID, "EGLL") == {
        "requires_preauth": False,
        "allows_iframe": False,
        "can_embed": False,
    }
    with pytest.raises(ChartFoxError, match="interdit"):
        client.document(CHART_ID, "EGLL")


def test_document_is_streamed_without_writing_to_disk(monkeypatch):
    session = _Session()
    session.responses = [
        _Response({"data": {"6": [_chart()]}}),
        _Response(_chart(
            allows_iframe=True,
            files=[{"type": 0, "url": "https://files.chartfox.org/chart.pdf"}],
        )),
        _Response(content=b"%PDF-1.7\nchart", content_type="application/octet-stream"),
    ]
    monkeypatch.setattr(chartfox_module, "_public_http_url", lambda url: True)
    client = ChartFoxClient(
        session=session,
        token_store=MemoryTokenStore(OAuthTokens("access")),
    )

    content, media_type, filename = client.document(CHART_ID, "EGLL")

    assert content == b"%PDF-1.7\nchart"
    assert media_type == "application/pdf"
    assert filename.endswith(".pdf")
    assert session.gets[-1][1]["allow_redirects"] is False
    assert session.gets[-1][1]["stream"] is True


class _RouteClient:
    def __init__(self):
        self.connected = False
        self.opened = None

    def close(self):
        pass

    def status(self):
        return {"connected": self.connected}

    def begin_authorization(self, redirect_uri):
        self.opened = redirect_uri
        return f"{AUTHORIZE_URL}?state=test"

    def complete_authorization(self, code, state):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def list_airport_charts(self, icao):
        return []

    def chart_access(self, chart, icao):
        return {"requires_preauth": False, "allows_iframe": False, "can_embed": False}


def test_local_route_opens_registered_callback_and_disconnects():
    chartfox = _RouteClient()
    app = create_app(Settings(), chartfox_client=chartfox)
    opened = []
    app.state.request_open_chartfox_auth = opened.append
    request = SimpleNamespace(
        headers={"X-NaviXav-ChartFox": "connect"},
        url=SimpleNamespace(port=8775),
    )

    result = _endpoint(app, "/api/chartfox/connect")(request)

    assert result == {"opened": True}
    assert chartfox.opened == "http://127.0.0.1:8775/oauth/chartfox/callback"
    assert opened == [f"{AUTHORIZE_URL}?state=test"]

    assert _endpoint(app, "/api/charts/access")(
        provider="chartfox", icao="LFBO", chart=CHART_ID
    ) == {"requires_preauth": False, "allows_iframe": False, "can_embed": False}
    lfbo = _endpoint(app, "/api/charts/airport/{icao}")("LFBO", "chartfox")
    assert lfbo["official_available"] is True
    assert lfbo["official_provider"] == "sia"
    cyyz = _endpoint(app, "/api/charts/airport/{icao}")("CYYZ", "chartfox")
    assert cyyz["official_available"] is False
    assert cyyz["official_provider"] == ""

    disconnect = SimpleNamespace(headers={"X-NaviXav-ChartFox": "disconnect"})
    assert _endpoint(app, "/api/chartfox/disconnect")(disconnect) == {"connected": False}
    app.state.close_resources()


def test_chartfox_controls_are_present_in_settings_and_flight_charts():
    static = Path(__file__).parents[1] / "navixav" / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert 'id="chartfox-connect"' in html
    assert 'id="chartfox-disconnect"' in html
    assert 'id="chartfox-settings-simulation"' in html
    assert 'source = "auto"' in javascript
    assert 'chartfox_source_chartfox' in javascript
    assert 'chartfox_account_required' in javascript
    assert '"chartfox-settings-link", t("settings")' in javascript
    assert 'chartfoxSettingsLink.addEventListener("click", openSettings)' in javascript
    translations = (static / "i18n.js").read_text(encoding="utf-8")
    assert translations.count("chartfox_account_required:") == 8
    assert translations.count("chartfox_simulation_only:") == 8
    assert translations.count("chart_zoom_out:") == 8
    assert translations.count("chart_zoom_in:") == 8
    assert translations.count("chart_zoom_fit:") == 8
    assert translations.count("chart_zoom_fit_title:") == 8
    assert translations.count("chart_zoom_level:") == 8
    assert '"#chartfox-settings-simulation": "chartfox_simulation_only"' in translations
    assert "Un compte ChartFox/VATSIM est requis" in translations
    assert "A ChartFox/VATSIM account is required" in translations
    assert '/api/charts/access?' in javascript
    assert 'chartfox_iframe_blocked' in javascript
    assert 'chartfox_use_official_provider' in javascript
    assert 'officialAirportLibrary(icao, role, airport, plan, "official")' in javascript
    assert '"view=FitH"' in javascript
    assert '`zoom=${zoomPercent}`' in javascript
    assert 'zoomOut.addEventListener("click"' in javascript
    assert 'zoomIn.addEventListener("click"' in javascript
    assert 'zoomFit.addEventListener("click"' in javascript
    gitignore = (static.parents[2] / ".gitignore").read_text(encoding="utf-8")
    assert "data/credentials/" in gitignore
