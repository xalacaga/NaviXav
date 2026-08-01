"""Fenêtre native et cycle de vie du service local."""

import sys
import time
import logging
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

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


def test_flight_tracking_and_local_logbook_follow_the_selected_language():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    panel = javascript[javascript.index("function renderFlightPanel(plan)"):]
    panel = panel[: panel.index("\n}\n")]
    summaries = javascript[javascript.index("function renderFlightSummaries()") :]
    summaries = summaries[: summaries.index("\n}\n")]
    for french in (
        "Suivi du vol en temps réel", "Journal local", "Résumé des vols effectués",
        "Purger l’historique des vols", "Prochain point", "Écart latéral",
    ):
        assert french not in panel
    assert "Aucun vol terminé pour le moment" not in summaries
    for key in (
        "flight_tracking_title", "local_journal", "flight_summaries",
        "purge_history", "flight_next_fix", "flight_lateral_deviation",
        "simbrief_create", "simbrief_create_title",
    ):
        assert f'{key}:' in translations


def test_flight_rules_do_not_depend_on_french_phase_names():
    javascript = (
        Path(desktop.__file__).parent / "web" / "static" / "app.js"
    ).read_text(encoding="utf-8")
    rules = javascript[javascript.index("const ALERT_RULES ="):]
    rules = rules[: rules.index("function resetAlertStates")]
    for phase in ("Approche", "Atterrissage", "Montée", "Décollage", "Descente", "Croisière"):
        assert f'c.phase === "{phase}"' not in rules


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


def test_simbrief_creation_button_opens_the_official_new_plan_page():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    desktop_source = Path(desktop.__file__).read_text(encoding="utf-8")

    assert 'id="simbrief-create"' in html
    assert 'fetch("/api/simbrief/new"' in javascript
    assert '"X-NaviXav-External": "simbrief"' in javascript
    assert "https://dispatch.simbrief.com/options/new" in desktop_source


def test_support_button_opens_buy_me_a_coffee_only_after_an_explicit_click():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    desktop_source = Path(desktop.__file__).read_text(encoding="utf-8")
    server_source = (
        Path(desktop.__file__).parent / "web" / "app.py"
    ).read_text(encoding="utf-8")

    assert 'id="support-open"' in html
    assert 'id="support-open-toolbar"' in html
    assert 'class="toolbar-exit-actions"' in html
    assert 'fetch("/api/support/open"' in javascript
    assert '$("support-open-toolbar").addEventListener("click", openSupportPage)' in javascript
    assert '"X-NaviXav-External": "support"' in javascript
    assert "https://buymeacoffee.com/xalacaga" in desktop_source
    assert 'request.headers.get("X-NaviXav-External") != "support"' in server_source
    assert '"/api/support/open",' in server_source


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
    assert 'phase === t("phase_descent")' in javascript
    assert 'phase === t("phase_approach")' in javascript
    assert 'tf("profile_waiting"' in javascript
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


def test_corrected_alert_is_acknowledged_and_rearmed_automatically():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert "const ALERT_CORRECTION_MS = 750;" in javascript
    assert "if (!state.correctedAt) state.correctedAt = now;" in javascript
    assert "now - state.correctedAt >= ALERT_CORRECTION_MS" in javascript
    assert "state.acknowledged = false;" in javascript


def test_flap_detents_adapt_to_known_aircraft_families():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert "function flapDetentLabels(aircraft, plan, positions)" in javascript
    assert 'return ["UP", "1", "1", "2", "3", "FULL"]' in javascript
    assert 'extended >= 98' in javascript
    assert 'return ["UP", "1", "2", "5", "10", "15", "25", "30", "40"]' in javascript
    assert 'return ["UP", "1", "5", "10", "20", "25", "30"]' in javascript
    assert 'return ["UP", "1", "5", "15", "20", "25", "30"]' in javascript
    assert "`${Math.round(extended)} %`" in javascript
    assert "describeFlaps(configuration, capabilities, aircraft, currentPlan)" in javascript


def test_local_flight_journal_keeps_only_completed_flight_summaries():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")

    assert 'FLIGHT_SUMMARY_KEY = "navixav-flight-summaries"' in javascript
    assert 'key.startsWith("navixav-flight-log:")' in javascript
    assert "function updateFlightSummary(aircraft)" in javascript
    assert 'summaryList.id = "flight-summary-list"' in javascript
    assert 't("flight_summaries")' in javascript
    assert 't("purge_history")' in javascript
    assert "localStorage.removeItem(FLIGHT_SUMMARY_KEY)" in javascript
    assert ".flight-summary-row" in css


def test_flight_summary_stores_no_detailed_track_or_replay_controls():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    panel = javascript[
        javascript.index("function renderFlightPanel(plan)"):
        javascript.index("function choiceRow")
    ]
    assert '"Enregistrement et rejeu"' not in panel
    assert '"Rejouer"' not in panel
    assert '"Débrief IFR intelligent"' not in panel
    assert "recordFlightPoint(aircraft)" not in javascript[
        javascript.index("function applyAircraftState"):
        javascript.index("async function pollLive")
    ]


def test_terminal_choices_and_planner_warnings_are_localized():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    terminal = javascript[javascript.index("function terminalCard"):]
    terminal = terminal[: terminal.index("/* ----------------------------------------------------------- constraints */")]
    assert 'choiceRow(t("runway")' in terminal
    assert 'terminalCard(plan.departure, t("departure_title")' in terminal
    assert 'terminalCard(plan.arrival, t("arrival_title")' in terminal
    assert '[t("approach"), plan.arrival.approach' in terminal
    assert 'plannerText(choice.reason)' in javascript
    assert 'plan.warnings.map(warningText)' in javascript
    for key in (
        "warnings", "source_computed", "departure_title", "route_title",
        "arrival_title", "approach", "reason_runway_simbrief",
        "reason_transition_nearest_star", "reason_fix_distance",
    ):
        assert f"{key}:" in translations


def test_current_flight_trace_is_memory_only_and_still_drawn_on_the_map():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    recorder = javascript[
        javascript.index("function recordCurrentFlightTrail"):
        javascript.index("function recordFlightPoint")
    ]
    aircraft_update = javascript[
        javascript.index("function applyAircraftState"):
        javascript.index("async function pollLive")
    ]

    assert "currentFlightTrail.push" in recorder
    assert "localStorage" not in recorder
    assert "MAP.setTrail(flightTrailPoints(currentFlightTrail))" in javascript
    assert "recordCurrentFlightTrail(aircraft)" in aircraft_update


def test_mcdu_omits_non_automatable_takeoff_performance_editor():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert "function takeoffPerformanceStorageKey(plan)" not in javascript
    assert '"navixav-takeoff-performance"' not in javascript
    assert "function takeoffPerformanceEditor(plan, performance)" not in javascript
    assert '"Performances à saisir dans le MCDU"' not in javascript
    assert "mcduPage(`PERF TO · RWY" not in javascript


def test_mcdu_card_adapts_terminology_to_aircraft_type():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert "function aircraftFmsProfile(plan)" in javascript
    assert 'label: "MCDU"' in javascript
    assert 'label: "CDU"' in javascript
    assert 'label: "FMS"' in javascript
    assert "mcduPage(profile.init" in javascript
    assert "mcduPage(profile.departure" in javascript
    assert "mcduPage(profile.arrival" in javascript
    assert "mcduLine(profile.approachTransition" in javascript


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


def test_map_shares_one_web_mercator_frame_with_its_tiles():
    """Une seule projection, sinon le fond de carte dérive de la route.

    Le plan de terrain arrive en mètres locaux tangents à l'aérodrome. Tant
    qu'il était dessiné tel quel sous des tuiles Web Mercator, l'écart
    atteignait 14 NM au bout d'une route de 385 NM.
    """
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    map_javascript = (static / "map.js").read_text(encoding="utf-8")

    # Le repère monde est celui des tuiles, au rayon des tuiles.
    assert "const EARTH_RADIUS_M = 6378137;" in map_javascript
    assert "const MERCATOR_WORLD_M = 2 * Math.PI * EARTH_RADIUS_M;" in map_javascript
    assert "function project(latitude, longitude)" in map_javascript
    assert "Math.log(Math.tan(Math.PI / 4 + phi / 2))" in map_javascript

    # Le plan de terrain est reconverti à la réception, pas dessiné en local.
    assert "function localToLatLon(origin, point)" in map_javascript
    assert "chart = prepareChart(data);" in map_javascript

    # L'indice de tuile se lit dans le repère monde, sans facteur d'échelle
    # figé à la latitude de l'aérodrome.
    assert "const tileWorldM = MERCATOR_WORLD_M / tileCount;" in map_javascript
    assert "(view.centerX + halfWorld) / tileWorldM" in map_javascript

    # Les longueurs au sol tiennent compte de la dilatation de Mercator.
    assert "function groundRatio(worldY)" in map_javascript
    assert "1 / Math.cosh(worldY / EARTH_RADIUS_M)" in map_javascript
    assert "m * pixelsPerMetre >= target" in map_javascript
    assert "runway.width_m * pixelsPerMetre" in map_javascript

    # Une seule définition : l'interface délègue à la carte.
    assert "return MAP.project(latitude, longitude);" in javascript
    assert "webMercatorPixel" not in map_javascript
    assert "6371000" not in map_javascript


def test_the_map_stays_free_of_the_ground_layout():
    """La carte sert à suivre un vol, pas à rouler.

    Voies, postes et itinéraire de roulage y avaient été ajoutés : sur un grand
    terrain, les milliers de segments et leurs étiquettes couvraient les
    tuiles, la route SID/STAR et l'avion. Tout cela vit désormais dans le plan
    de roulage, qui n'affiche que l'aérodrome.
    """
    static = Path(desktop.__file__).parent / "web" / "static"
    map_javascript = (static / "map.js").read_text(encoding="utf-8")

    for absent in (
        "drawTaxiways", "drawParkings", "drawTaxiwayLabels",
        "drawTaxiRoute", "drawHoldShortMarks", "setTaxiPlan", "parkingAt",
    ):
        assert absent not in map_javascript, f"{absent} n'a rien à faire sur la carte"


def test_the_ground_view_owns_the_airport_layout():
    static = Path(desktop.__file__).parent / "web" / "static"
    ground = (static / "ground.js").read_text(encoding="utf-8")

    assert "function drawTaxiways()" in ground
    assert "function drawParkings()" in ground
    assert "function drawRunways()" in ground
    # Les voies passent sous les pistes : à leur croisement, c'est la piste qui
    # est continue au sol.
    assert ground.index("drawTaxiways();") < ground.index("drawRunways();")


def test_the_ground_view_carries_no_basemap_and_no_flight_route():
    """C'est tout l'objet du module : le fond de carte noyait les voies sous
    les rues de la ville, et la route de vol traversait le terrain sans rien
    apprendre au pilote qui cherche sa piste."""
    static = Path(desktop.__file__).parent / "web" / "static"
    ground = (static / "ground.js").read_text(encoding="utf-8")

    for absent in ("tile.openstreetmap.org", "basemap", "MERCATOR", "routeSegments"):
        assert absent not in ground


def test_only_the_taxiways_of_the_route_are_named():
    """Toutes les nommer couvrait le terrain de pastilles — plus de mille à
    Toulouse — et masquait ce qu'on venait y chercher."""
    static = Path(desktop.__file__).parent / "web" / "static"
    ground = (static / "ground.js").read_text(encoding="utf-8")

    labels = ground[ground.index("function drawRouteLabels()"):]
    labels = labels[: labels.index("\n  }\n")]
    # Les noms sont pris sur les tronçons de l'itinéraire, jamais sur le plan.
    assert "for (const leg of plan.legs)" in labels
    assert "chart.taxiways" not in labels
    assert "placed.has(leg.name)" in labels


def test_the_taxi_route_is_split_at_the_aircraft():
    """Vert derrière, bleu devant : la bascule suit l'avion, pas le nœud suivant."""
    static = Path(desktop.__file__).parent / "web" / "static"
    ground = (static / "ground.js").read_text(encoding="utf-8")

    assert "const ratio = (travelled - walked) / length;" in ground
    assert 'css(done ? "--taxi-done" : "--taxi-ahead")' in ground
    assert "function drawHoldBars()" in ground


def test_the_ground_progress_comes_from_the_service():
    """Un calcul local en doublon situerait la manœuvre ailleurs que le tracé."""
    static = Path(desktop.__file__).parent / "web" / "static"
    ground = (static / "ground.js").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert "setProgress(metres)" in ground
    assert "GROUND.setProgress(data.guidance?.fix?.travelled_m ?? 0)" in javascript


def test_the_ground_view_reads_the_local_metres_the_service_sends():
    """Pas de tuiles avec lesquelles s'aligner : aucune reprojection n'est due."""
    static = Path(desktop.__file__).parent / "web" / "static"
    ground = (static / "ground.js").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert "function toLocal(latitude, longitude)" in ground
    assert "GROUND.setChart(currentChart);" in javascript


def test_a_taxi_plan_never_survives_a_change_of_airport():
    """Sinon l'itinéraire d'un terrain se dessinerait sur le sol d'un autre."""
    static = Path(desktop.__file__).parent / "web" / "static"
    ground = (static / "ground.js").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    setter = ground[ground.index("setChart(data) {"):]
    setter = setter[: setter.index("},")]
    assert "plan = null;" in setter
    assert "travelled = 0;" in setter
    assert "currentTaxiPlan = null;" in javascript


def test_the_ground_view_has_its_own_tab_and_panel():
    static = Path(desktop.__file__).parent / "web" / "static"
    markup = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert '<button data-tab="ground">' in markup
    assert 'id="panel-ground"' in markup
    assert 'id="ground-canvas"' in markup
    assert "/static/ground.js" in markup
    assert '"ground", "flight"' in javascript
    # Le canvas doit être mesuré une fois visible, sinon il reste à zéro.
    assert 'if (name === "ground") window.requestAnimationFrame(() => GROUND.resize());' in javascript


def test_the_ground_canvas_fills_its_stage_and_stays_decluttered():
    static = Path(desktop.__file__).parent / "web" / "static"
    stylesheet = (static / "app.css").read_text(encoding="utf-8")
    ground = (static / "ground.js").read_text(encoding="utf-8")

    canvas_rule = stylesheet[stylesheet.index("#ground-canvas {"):]
    canvas_rule = canvas_rule[: canvas_rule.index("}")]
    assert "width: 100%;" in canvas_rule
    assert "height: 100%;" in canvas_rule
    assert "touch-action: none;" in canvas_rule
    # Secondary links only appear once they are useful to the pilot.
    assert 'taxiway.kind === "parking" || taxiway.kind === "path"' in ground
    assert "secondary && !showSecondaryTaxiways" in ground
    # Screen-space widths stay bounded on large airports.
    assert "Math.min(4.5, (taxiway.width_m || 15) * view.scale * 0.48)" in ground


def test_ground_secondary_taxiways_are_an_opt_in_control():
    static = Path(desktop.__file__).parent / "web" / "static"
    markup = (static / "index.html").read_text(encoding="utf-8")
    ground = (static / "ground.js").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert 'id="ground-secondary"' in markup
    assert 'aria-pressed="false"' in markup
    assert "let showSecondaryTaxiways = false;" in ground
    assert "toggleSecondaryTaxiways()" in ground
    assert 'GROUND.toggleSecondaryTaxiways()' in javascript


def test_ground_uses_an_oriented_metric_background():
    static = Path(desktop.__file__).parent / "web" / "static"
    ground = (static / "ground.js").read_text(encoding="utf-8")

    assert "function drawGroundGrid()" in ground
    assert "function drawNorthArrow()" in ground
    assert ground.index("drawGroundGrid();") < ground.index("drawTaxiways();")


def test_departure_taxi_route_is_proposed_from_the_aircraft_position():
    static = Path(desktop.__file__).parent / "web" / "static"
    ground = (static / "ground.js").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert "nearestParking(state)" in ground
    assert "function maybeRequestAutomaticTaxiRoute(aircraft)" in javascript
    automatic = javascript[javascript.index("function maybeRequestAutomaticTaxiRoute"):]
    automatic = automatic[: automatic.index("\n}")]
    assert 'currentMapRole !== "departure"' in automatic
    assert "nearest.distance_m > 180" in automatic
    assert "requestTaxiRoute(nearest.label)" in automatic


def test_the_taxi_guidance_follows_the_live_positions():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert "async function pollTaxiGuidance(aircraft)" in javascript
    assert "pollTaxiGuidance(aircraft);" in javascript
    assert "/api/ground/${currentIcao}/guidance?" in javascript
    # En vol, il n'y a plus rien à guider au sol.
    assert "if (!aircraft?.on_ground)" in javascript


def test_taxi_ui_uses_the_selected_language_not_backend_french():
    """The service returns semantics; the browser owns display language."""
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    ground_hud = javascript[javascript.index("function updateGroundHud"):]
    ground_hud = ground_hud[: ground_hud.index("\n}\n")]
    assert "guidance.announce" not in ground_hud
    assert 't("taxi_turn_left")' not in ground_hud  # selected dynamically
    assert '"taxi_turn_left"' in ground_hud
    assert 't("runway_selected")' in ground_hud
    assert 'tf("metres_remaining"' in ground_hud

    # French + English + the six additional supported languages.
    for key in ("tab_ground", "ground_secondary_title", "taxi_turn_left"):
        assert translations.count(f"{key}:") == 8


def test_the_taxi_route_is_only_redrawn_when_it_changed():
    """Le redéposer chaque seconde ramènerait la progression à zéro."""
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    guard = javascript[javascript.index("async function pollTaxiGuidance"):]
    guard = guard[: guard.index("\n}\n")]
    assert "if (data.recomputed) {" in guard
    assert guard.count("GROUND.setPlan(") == 1


def test_the_last_selected_parking_always_wins():
    """Une ancienne réponse ne doit pas restaurer le premier itinéraire."""
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    request = javascript[javascript.index("async function requestTaxiRoute"):]
    request = request[: request.index("\n}\n")]
    assert "taxiRouteRequestController?.abort();" in request
    assert "const revision = ++taxiRouteRevision;" in request
    assert "signal: controller.signal" in request
    assert "if (revision !== taxiRouteRevision) return;" in request
    assert 'error?.name === "AbortError"' in request

    guidance = javascript[javascript.index("async function pollTaxiGuidance"):]
    guidance = guidance[: guidance.index("\n}\n")]
    assert "const requestedPlan = currentTaxiPlan;" in guidance
    assert "revision !== taxiRouteRevision || currentTaxiPlan !== requestedPlan" in guidance
    assert "|| taxiRouteRequestController" in guidance


def test_a_guidance_failure_stays_silent():
    """Le signaler chaque seconde couvrirait la carte de bandeaux."""
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    guard = javascript[javascript.index("async function pollTaxiGuidance"):]
    guard = guard[: guard.index("\n}\n")]
    assert "showBanner" not in guard


def test_dragging_the_ground_view_does_not_select_a_parking():
    static = Path(desktop.__file__).parent / "web" / "static"
    ground = (static / "ground.js").read_text(encoding="utf-8")

    assert "function parkingAt(px, py)" in ground
    assert "moved <= 4 && parkingListener" in ground
    # Dézoomé, un poste ne fait que quelques pixels.
    assert "Math.max(11, (parking.radius_m || 15) * view.scale)" in ground


def test_hidden_map_waits_for_a_real_canvas_size_before_loading_tiles():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    map_javascript = (static / "map.js").read_text(encoding="utf-8")

    assert "window.requestAnimationFrame(() => MAP.resize())" in javascript
    assert "canvas.clientWidth <= 0 || canvas.clientHeight <= 0" in map_javascript
    assert "fitPending = true;" in map_javascript
    assert "!Number.isFinite(screenPixelsPerTile)" in map_javascript
    assert "MAX_TILE_RADIUS" in map_javascript


def test_basemap_is_composited_once_so_tiles_show_no_seams():
    """La transparence du fond s'applique au calque, pas à chaque tuile.

    Appliquée tuile par tuile avec un débord d'un pixel, elle se cumulait dans
    le recouvrement — 0,95 au lieu de 0,78 — et dessinait la grille des tuiles.
    """
    static = Path(desktop.__file__).parent / "web" / "static"
    map_javascript = (static / "map.js").read_text(encoding="utf-8")

    assert "const basemapLayer = document.createElement(\"canvas\");" in map_javascript
    assert "basemapContext.drawImage(" in map_javascript
    assert "context.drawImage(basemapLayer, 0, 0" in map_javascript
    # Les tuiles se touchent sans se chevaucher.
    assert "Math.floor(screenX + screenPixelsPerTile) - left" in map_javascript
    assert "Math.ceil(screenPixelsPerTile) + 1" not in map_javascript


def test_demo_plan_chart_and_live_flow_does_not_crash(tmp_path):
    project = Path(desktop.__file__).parent.parent
    store = tmp_path / "navdata.sqlite"
    shutil.copyfile(project / "tests" / "data" / "navdata_test.sqlite", store)
    app = create_app(Settings(navdata_store=store, metar_source="simbrief"))

    def endpoint(path):
        return next(route.endpoint for route in app.routes if route.path == path)

    try:
        current_plan = endpoint("/api/plan/current")
        with pytest.raises(HTTPException) as missing:
            current_plan()
        assert missing.value.status_code == 404

        plan = endpoint("/api/plan")(PlanRequest(demo=True))
        assert current_plan() == plan
        departure = plan["departure"]
        runway = departure["runway"]["value"]
        chart = endpoint("/api/chart/{icao}")(departure["icao"], runway)
        live = endpoint("/api/live")(True, departure["icao"], runway)

        assert chart["parkings"]
        assert live["connected"] is True
        assert live["aircraft"]["source"] == "Démonstration"
        # La démonstration doit rejouer le vol complet du plan, pas un roulage.
        assert live["aircraft"]["title"] == "Démonstration NaviXav"

        # Changer d'aéroport sur la carte ne doit pas relancer le vol au départ.
        arrival = plan["arrival"]["icao"]
        again = endpoint("/api/live")(True, arrival, None)
        assert again["aircraft"]["title"] == "Démonstration NaviXav"

        # Les postes servent à demander un itinéraire de roulage.
        parkings = endpoint("/api/ground/{icao}/parkings")(departure["icao"])
        assert parkings["parkings"]
        assert parkings["icao"] == departure["icao"]

        # La base de référence est antérieure aux natures de segment : le
        # roulage doit le dire plutôt que de tracer une route fausse.
        if not parkings["routable"]:
            with pytest.raises(HTTPException) as refused:
                endpoint("/api/ground/{icao}/route")(
                    departure["icao"], parkings["parkings"][0]["label"], runway,
                )
            assert refused.value.status_code == 404
    finally:
        for close in app.router.on_shutdown:
            close()


def test_mobile_reads_the_pc_current_flight_without_rebuilding_it():
    app_source = (
        Path(desktop.__file__).parent / "web" / "app.py"
    ).read_text(encoding="utf-8")
    javascript = (
        Path(desktop.__file__).parent / "web" / "static" / "app.js"
    ).read_text(encoding="utf-8")

    assert '@app.get("/api/plan/current")' in app_source
    assert (
        'request.url.path == "/api/plan" and request.method == "POST"'
        in app_source
    )
    assert 'fetch("/api/plan/current")' in javascript
    assert "if (status.remote_client)" in javascript
    assert "await loadCurrentPlan();" in javascript


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
