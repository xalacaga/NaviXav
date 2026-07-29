"""Fenêtre native et cycle de vie du service local."""

import sys
import time
import logging
import shutil
from pathlib import Path
from types import SimpleNamespace

from navixav import desktop
from navixav.config import Settings
from navixav.logging_setup import (
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES,
    configure_logging,
)
from navixav.web.app import PlanRequest, create_app


class _Event:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


class _Window:
    def __init__(self):
        self.events = SimpleNamespace(closed=_Event())
        self.destroyed = False

    def destroy(self):
        self.destroyed = True


class _Server:
    def __init__(self):
        self.should_exit = False
        self.force_exit = False
        self.config = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace())
        )

    def run(self):
        while not self.should_exit and not self.force_exit:
            time.sleep(0.001)


def test_desktop_window_is_resizable_and_stops_with_the_interface(monkeypatch):
    server = _Server()
    window = _Window()
    captured = {}

    def create_window(_title, _url, **options):
        captured.update(options)
        return window

    def start(**options):
        captured["start"] = options
        server.config.app.state.request_shutdown()

    fake_webview = SimpleNamespace(create_window=create_window, start=start)
    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(desktop, "_wait_until_ready", lambda _url: None)
    monkeypatch.setattr(desktop, "_webview2_version", lambda: "150.0")
    monkeypatch.setattr(desktop.sys, "platform", "win32")

    desktop._run_desktop_window("http://127.0.0.1:8765", server)

    assert captured["min_size"] == (720, 560)
    assert captured["start"]["gui"] == "edgechromium"
    assert captured["start"]["icon"].endswith("assets\\navixav.ico")
    assert window.destroyed is True
    assert server.should_exit is True


def test_responsive_styles_cover_compact_windows():
    css = (Path(desktop.__file__).parent / "web" / "static" / "app.css").read_text(
        encoding="utf-8"
    )
    assert "@media (max-width: 760px)" in css
    assert "@media (max-width: 520px)" in css
    assert "100dvh" in css


def test_interface_offers_persistent_european_languages():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert 'id="settings-language"' in html
    for language in ("fr", "en", "de", "es", "it", "pt", "nl", "pl"):
        assert f'value="{language}"' in html
        assert f"{language}:" in translations
    assert '"navixav-language"' in translations
    assert "localStorage.setItem" in translations
    assert "navixav:languagechange" in translations


def test_windows_distribution_uses_the_navixav_aircraft_icon():
    project = Path(desktop.__file__).parent.parent
    icon = project / "assets" / "navixav.ico"
    spec = (project / "NaviXav.spec").read_text(encoding="utf-8")
    html = (
        Path(desktop.__file__).parent / "web" / "static" / "index.html"
    ).read_text(encoding="utf-8")

    header = icon.read_bytes()[:6]
    assert header[:4] == b"\x00\x00\x01\x00"
    assert int.from_bytes(header[4:6], "little") == 7
    assert 'icon=str(project_root / "assets" / "navixav.ico")' in spec
    assert '(str(project_root / "assets" / "navixav.ico"), "assets")' in spec
    assert 'href="/static/navixav-icon.svg?v=__NAVIXAV_VERSION__"' in html


def test_windows_process_uses_stable_navixav_identity(monkeypatch):
    captured = []
    shell32 = SimpleNamespace(
        SetCurrentProcessExplicitAppUserModelID=captured.append
    )
    monkeypatch.setattr(
        desktop.ctypes,
        "windll",
        SimpleNamespace(shell32=shell32),
        raising=False,
    )
    monkeypatch.setattr(desktop.sys, "platform", "win32")

    desktop._configure_windows_app_identity()

    assert captured == ["Galvo.NaviXav"]


def test_logging_is_rotating_and_cache_wait_is_explained(tmp_path):
    log_file = configure_logging(tmp_path / "navixav.log")
    handler = next(
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_navixav_rotating_file", False)
        and Path(handler.baseFilename) == log_file
    )
    logging.getLogger("navixav.test").info("diagnostic sans identifiant")
    handler.flush()

    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")
    assert handler.maxBytes == LOG_MAX_BYTES
    assert handler.backupCount == LOG_BACKUP_COUNT
    assert "diagnostic sans identifiant" in log_file.read_text(encoding="utf-8")
    assert 'showBanner("info", t("cache_title"), [t("cache_body")])' in javascript
    assert "plusieurs dizaines de secondes" in translations

    logging.getLogger().removeHandler(handler)
    handler.close()


def test_interface_checks_and_installs_verified_github_updates():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    assert 'id="update-install"' in html
    assert 'fetch("/api/update/check"' in javascript
    assert '"X-NaviXav-Update": "install"' in javascript
    assert "checkForUpdates(true)" in javascript
    assert 'class="icon-btn update-btn"' in html


def test_silent_update_restarts_navixav():
    project = Path(desktop.__file__).parent.parent
    installer = (project / "installer" / "NaviXav.iss").read_text(encoding="utf-8")
    run_entry = next(
        line
        for line in installer.splitlines()
        if line.startswith('Filename: "{app}\\{#MyAppExeName}"')
    )

    assert "postinstall" in run_entry
    assert "runasoriginaluser" in run_entry
    assert "skipifsilent" not in run_entry


def test_mobile_lan_interface_is_protected_and_responsive():
    project = Path(desktop.__file__).parent.parent
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    server = (Path(desktop.__file__).parent / "web" / "app.py").read_text(
        encoding="utf-8"
    )

    assert 'id="settings-lan-enabled"' in html
    assert 'id="settings-lan-url"' in html
    assert 'name="mobile-web-app-capable"' in html
    assert "env(safe-area-inset-bottom)" in css
    assert "body.remote-client" in css
    assert 'document.body.classList.toggle("remote-client"' in javascript
    # L'accès depuis un téléphone ne demande aucun jeton : seules les commandes
    # qui modifient ou arrêtent l'application restent réservées au PC hôte.
    assert "navixav_lan" not in server
    assert "compare_digest" not in server
    assert '"/api/settings",' in server
    assert '"/api/shutdown",' in server
    assert '"0.0.0.0" if settings.lan_enabled' in (
        project / "navixav" / "desktop.py"
    ).read_text(encoding="utf-8")


def test_vertical_profile_waits_for_descent_before_reporting_too_low():
    javascript = (
        Path(desktop.__file__).parent / "web" / "static" / "app.js"
    ).read_text(encoding="utf-8")
    assert 'phase === "Descente"' in javascript
    assert 'phase === "Approche"' in javascript
    assert "En attente du TOD" in javascript
    assert "Math.abs(delta) <= 500" in javascript


def test_global_alarm_opens_its_details_and_armed_spoilers_take_priority():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert 'id="global-flight-alert"' in html
    assert 'aria-controls="panel-flight"' in html
    assert ".global-flight-alert" in css
    assert "updateGlobalFlightAlert(active);" in javascript
    assert 'selectTab("flight");' in javascript
    assert '#flight-alerts .flight-alert' in javascript

    spoilers = javascript[
        javascript.index("function describeSpoilers"):
        javascript.index("function describeParkingBrake")
    ]
    assert spoilers.index("configuration.spoilers_armed === true") < spoilers.index(
        "capabilities && !capabilities.spoilers"
    )


def test_local_flight_journal_lists_previous_flights_and_replay_speeds():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")

    assert 'FLIGHT_LOG_INDEX_KEY = "navixav-flight-log-index"' in javascript
    assert 'key.startsWith("navixav-flight-log:")' in javascript
    assert "function renderFlightArchive()" in javascript
    assert 'archiveList.id = "flight-archive-list"' in javascript
    assert "for (const value of [0.5, 1, 2, 4])" in javascript
    assert "FLIGHT_REPLAY_BASE_MS / replaySpeed" in javascript
    assert ".flight-archive-row" in css


def test_ifr_debrief_analyses_track_and_replays_each_event():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")

    assert "function flightDebrief(points, routeSegments" in javascript
    assert "function projectAircraftOnDebriefPath(aircraft, routeSegments)" in javascript
    assert "route_segments: flightStagePaths(plan)" in javascript
    assert "entry.route_segments || (sameRoute" in javascript
    assert "maxDeviationNm" in javascript
    assert "offRouteSeconds" in javascript
    assert '"Train non confirmé sous 1 000 ft"' in javascript
    assert '"Taux de descente élevé sous 1 000 ft"' in javascript
    assert '"Survitesse détectée"' in javascript
    assert "debrief.samples.slice(start, end)" in javascript
    assert 'debrief.id = "flight-debrief"' in javascript
    assert '"Débrief IFR intelligent"' in javascript
    assert ".flight-debrief-event" in css


def test_mcdu_takeoff_page_keeps_unavailable_performance_values_manual():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert "function takeoffPerformanceStorageKey(plan)" in javascript
    assert '"navixav-takeoff-performance"' in javascript
    assert "function takeoffPerformanceEditor(plan, performance)" in javascript
    assert "NaviXav ne calcule pas les vitesses de décollage." in javascript
    assert 'mcduPage(`PERF TO · RWY ${dep.runway?.value || "□□"}`' in javascript
    for field in (
        '"V1"',
        '"VR"',
        '"V2"',
        '"FLAPS/THS"',
        '"F RETR"',
        '"S RETR"',
        '"CLEAN"',
        '"TRANS ALT"',
        '"TO SHIFT"',
        '"FLEX TEMP"',
        '"THR RED/ACC"',
        '"ENG OUT ACC"',
    ):
        assert field in javascript


def test_map_breaks_teleports_and_never_invents_a_direct_route():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    map_javascript = (static / "map.js").read_text(encoding="utf-8")

    assert "const cruise = route.slice(1, -1);" in javascript
    assert "const enroute = cruise.length" in javascript
    assert "function flightTrailPoints(points)" in javascript
    assert "trail.push(null);" in javascript
    assert 'previous.source === "Démonstration"' in javascript
    assert "haversineNm(previous, point) > plausibleDistanceNm" in javascript
    assert "if (!point)" in map_javascript
    assert "...trail.filter(Boolean).map" in map_javascript


def test_demo_plan_chart_and_live_flow_does_not_crash(tmp_path):
    project = Path(desktop.__file__).parent.parent
    store = tmp_path / "navdata.sqlite"
    shutil.copyfile(project / "tests" / "data" / "navdata_test.sqlite", store)
    app = create_app(Settings(navdata_store=store, metar_source="simbrief"))

    def endpoint(path):
        return next(route.endpoint for route in app.routes if route.path == path)

    try:
        plan = endpoint("/api/plan")(PlanRequest(demo=True))
        departure = plan["departure"]
        runway = departure["runway"]["value"]
        chart = endpoint("/api/chart/{icao}")(departure["icao"], runway)
        live = endpoint("/api/live")(True, departure["icao"], runway)

        assert chart["parkings"]
        assert live["connected"] is True
        assert live["aircraft"]["source"] == "Démonstration"
    finally:
        for close in app.router.on_shutdown:
            close()


def test_route_progress_uses_sid_star_and_approach_geometry():
    javascript = (
        Path(desktop.__file__).parent / "web" / "static" / "app.js"
    ).read_text(encoding="utf-8")
    assert "flightGeometry = buildFlightGeometry(plan);" in javascript
    assert "const route = flightGeometry;" in javascript
    assert 'routeStage = null' in javascript
    assert 'null, "star"' in javascript
    assert 'null, "approach"' in javascript
    assert "activeRoutePointIndex + 1" in javascript
    assert "appendProcedureFixes(" in javascript
    assert "arr.star_path" in javascript
    assert "arr.approach_path" in javascript
