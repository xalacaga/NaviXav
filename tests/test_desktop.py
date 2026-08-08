"""Fenêtre native et cycle de vie du service local."""

import asyncio
import base64
import re
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
from navixav.models import AirportWeather, WeatherBriefing
from navixav.web.app import PlanRequest, SettingsRequest, create_app


class _Event:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


def test_fastapi_lifespan_closes_live_resources_once(monkeypatch):
    import navixav.web.app as web_app

    closed = []

    class _Tracker:
        def close(self):
            closed.append("tracker")

    monkeypatch.setattr(web_app, "LiveTracker", _Tracker)
    app = web_app.create_app(Settings(metar_source="simbrief"))

    async def run_lifespan():
        async with app.router.lifespan_context(app):
            pass

    asyncio.run(run_lifespan())
    app.state.close_resources()

    assert closed == ["tracker"]


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


def test_interface_offers_a_persistent_global_theme():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    javascript = (static / "theme.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert 'id="settings-theme"' in html
    assert 'src="/static/theme.js?v=__NAVIXAV_VERSION__"' in html
    assert html.index("/static/theme.js") < html.index("/static/app.css")
    for theme in ("auto", "light", "dark"):
        assert f'<option value="{theme}">' in html
    assert ':root[data-theme="light"]' in css
    assert "color-scheme: light" in css
    assert '"navixav-theme"' in javascript
    assert "localStorage.setItem(STORAGE_KEY, selected)" in javascript
    assert "navixav:themechange" in javascript
    for key in ("theme_auto", "theme_light", "theme_dark"):
        assert key in translations


def test_settings_prioritise_support_and_collapse_aircraft_procedures():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")

    assert '<details class="aircraft-settings">' in html
    assert '<details class="aircraft-settings" open' not in html
    assert '<summary class="aircraft-settings-summary">' in html
    assert html.index('class="support-card support-card-top"') < html.index('class="settings-grid"')
    assert html.index('class="support-card support-card-top"') < html.index('class="aircraft-settings"')


def test_procedure_header_status_and_phase_flow_are_compact():
    css = (
        Path(desktop.__file__).parent / "web" / "static" / "app.css"
    ).read_text(encoding="utf-8")

    badge = css[css.index(".procedure-badge {") : css.index(".procedure-badge::before")]
    phase = css[css.index(".procedure-phase {") : css.index(".procedure-phase:hover")]
    assert "0.48rem/1.1 var(--font)" in badge
    assert "padding: 2px 5px" in badge
    assert "min-height: 44px" in phase
    assert "flex: 1 0 82px" in phase
    assert "var(--sans)" not in css


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


def test_the_flight_timeline_records_keys_and_replays_in_the_selected_language():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    watchers = javascript[javascript.index("const FLIGHT_EVENT_WATCHERS = ["):]
    watchers = watchers[: watchers.index("\nfunction resetFlightEvents")]

    # Un événement conserve sa clé et ses valeurs brutes : un vol enregistré en
    # français doit se relire en anglais sans réécrire l'historique.
    assert re.search(r"(?<![A-Za-z_$])t\(", watchers) is None
    for key in (
        "events_title", "events_replay", "evt_phase", "evt_takeoff_runway",
        "evt_gear_up", "evt_flaps_set", "evt_light_on", "evt_light_landing",
        "evt_spoilers_armed", "evt_ap_off",
    ):
        assert f"{key}:" in translations

    # La chronologie suit l'anti-rebond des alarmes et date l'événement de sa
    # première observation, pas de sa confirmation.
    assert "now - state.since < FLIGHT_EVENT_CONFIRM_MS" in javascript
    assert "appendFlightEvent(watcher, previous, value, aircraft, observedAt)" in javascript

    # Elle est rattachée au vol terminé et rejouable depuis le journal local.
    assert "completed.events = storedFlightEvents()" in javascript
    assert "panel.append(buildFlightEventsSection())" in javascript
    assert 'toggle = el("button", "icon-btn", t("events_replay"))' in javascript


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
    assert 'class="icon-btn update-btn toolbar-icon"' in html


def test_topbar_prioritises_flight_actions_and_compacts_utilities():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    header = html[html.index('<header class="topbar">') : html.index("</header>")]
    assert 'class="nav-source"' not in header
    assert 'id="theme-toggle"' in header
    assert 'class="icon-btn toolbar-secondary"' in header
    for control in ("settings-open", "update-install", "support-open-toolbar", "shutdown"):
        assert f'id="{control}"' in header
    assert ".toolbar-icon .toolbar-label" in css
    assert "min-height: 36px" in css
    assert '$("theme-toggle").addEventListener("click"' in javascript
    assert "window.THEME.setPreference" in javascript


def test_route_strip_uses_a_compact_connected_rail():
    static = Path(desktop.__file__).parent / "web" / "static"
    css = (static / "app.css").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    strip = css[css.index(".strip {") : css.index("/* ----------------------------------------------------------------- cards */")]
    assert "scrollbar-width: none" in strip
    assert "border-radius: 7px" in strip
    assert ".strip-sep" in strip
    assert 'fragment.append(el("span", "strip-sep"))' in javascript


def test_overflowing_route_strip_supports_mouse_touch_and_keyboard_scrolling():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert 'id="strip" class="strip hidden" tabindex="0"' in html
    assert ".strip.can-scroll { cursor: grab; }" in css
    assert 'strip.addEventListener("wheel"' in javascript
    assert 'strip.addEventListener("pointerdown"' in javascript
    assert 'event.key === "ArrowLeft"' in javascript
    assert 'event.key === "ArrowRight"' in javascript
    assert "new ResizeObserver(updateStripOverflowState).observe(strip);" in javascript
    assert "initialiseStripScrolling();" in javascript


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


def test_update_waits_for_the_old_process_and_reuses_its_install_directory(tmp_path):
    installer = tmp_path / "NaviXav-Setup-1.4.12.exe"
    install_directory = Path(r"D:\MSFS2024\NaviXav")
    log_path = tmp_path / "NaviXav-Setup-1.4.12.install.log"

    command = desktop._update_helper_command(
        installer,
        parent_pid=4242,
        install_directory=install_directory,
        log_path=log_path,
    )
    encoded = command[command.index("-EncodedCommand") + 1]
    script = base64.b64decode(encoded).decode("utf-16-le")

    assert command[0].lower().endswith("powershell.exe")
    assert "Wait-Process -Id 4242" in script
    assert str(installer) in script
    assert f"/DIR={install_directory}" in script
    assert f"/LOG={log_path}" in script
    assert script.index("Wait-Process") < script.index("& $installer")


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
    assert "body.remote-client .toolbar .sim-status" in css
    assert "body.remote-client #sim-status-text" in css
    assert "clip-path: inset(50%)" in css
    assert 'document.body.classList.toggle("remote-client"' in javascript
    # L'accès depuis un téléphone ne demande aucun jeton : seules les commandes
    # qui modifient ou arrêtent l'application restent réservées au PC hôte.
    assert "navixav_lan" not in server
    assert "compare_digest" not in server
    assert '"/api/settings",' in server
    assert '"/api/demo/restart",' in server
    assert '"/api/shutdown",' in server
    assert '"0.0.0.0" if settings.lan_enabled' in (
        project / "navixav" / "desktop.py"
    ).read_text(encoding="utf-8")


def test_the_flight_level_comes_from_the_standard_atmosphere():
    """L'altitude vraie affichait FL342 pour un avion stabilisé au FL330."""
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    helper = javascript[javascript.index("function standardAltitude(aircraft)"):]
    helper = helper[: helper.index("\n}")]
    assert "configuration?.pressure_altitude_ft" in helper
    # Le bloc de configuration peut être refusé : l'altitude vraie sert de repli.
    assert "aircraft?.altitude_ft" in helper

    label = javascript[javascript.index("function progressAltitudeLabel"):]
    label = label[: label.index("\n}")]
    assert "standardAltitude(aircraft)" in label
    assert "aircraft?.altitude_ft" not in label

    phase = javascript[javascript.index("function detectFlightPhase"):]
    phase = phase[: phase.index("\n}")]
    # Le niveau de croisière du plan est un niveau de vol, lui aussi.
    assert "standardAltitude(aircraft)" in phase


def test_a_remote_client_can_still_choose_its_display_language():
    """Les paramètres lui sont fermés : sans ce sélecteur, la langue est figée."""
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert 'id="mobile-language"' in html
    for language in ("fr", "en", "de", "es", "it", "pt", "nl", "pl"):
        assert f'<option value="{language}">' in html
    # Caché sur le PC, où les paramètres portent déjà le choix de la langue.
    assert ".mobile-language," in css
    assert ".mobile-theme { display: none; }" in css
    assert "body.remote-client .mobile-language" in css
    assert 'body.remote-client #settings-open' in css

    listener = javascript[javascript.index('$("mobile-language").addEventListener'):]
    listener = listener[: listener.index("});")]
    # La langue ne vit que dans le navigateur : aucun écriture côté service.
    assert "window.I18N.setLanguage(event.target.value);" in listener
    assert "fetch(" not in listener
    assert '"#mobile-language"' in translations


def test_mobile_module_navigation_uses_an_accessible_side_drawer():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert 'id="module-menu-toggle"' in html
    assert 'aria-controls="tabs"' in html
    assert 'id="module-menu-backdrop"' in html
    assert '#simbrief-create { display: none; }' in css
    assert ".tabs.mobile-open" in css
    assert "transform: translateX(-105%);" in css
    assert 'const MOBILE_MODULE_MENU = window.matchMedia("(max-width: 760px)");' in javascript
    assert "setModuleMenuOpen(false, restoreMenuFocus);" in javascript
    assert 'event.key === "Escape"' in javascript
    assert 'event.key === "Tab" && menuOpen' in javascript


def test_wide_desktop_module_navigation_uses_a_left_side_rail_and_scrolls():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    wide_desktop = css[css.index("@media (min-width: 1101px)") :]
    wide_desktop = wide_desktop[: wide_desktop.index(".module-menu-toggle")]
    assert "position: fixed;" in wide_desktop
    assert "--module-rail-inset: clamp(" in wide_desktop
    assert "left: var(--module-rail-inset);" in wide_desktop
    assert "max-width: none;" in wide_desktop
    assert "padding-left: calc(var(--module-rail-inset) + var(--module-rail-width) + 18px);" in wide_desktop
    assert "flex-direction: column;" in wide_desktop
    assert "--module-rail-top: clamp(84px, 11vh, 112px);" in wide_desktop
    assert "body:has(.global-flight-alert:not(.hidden))" in wide_desktop
    assert "--module-rail-top: clamp(116px, 16vh, 150px);" in wide_desktop
    assert "top: var(--module-rail-top);" in wide_desktop
    assert "max-height: calc(100dvh - var(--module-rail-top) - 16px);" in wide_desktop
    assert ".tabs button.active::after" in wide_desktop
    assert '<button data-tab="terminal" class="active">Plan de vol</button>' in html
    assert '<button data-tab="map">Carte</button>' in html
    assert "selectTab(button.dataset.tab, true);" in javascript
    assert 'name === "terminal" ? $("terminal") : $(`panel-${name}`)' in javascript
    assert "target?.scrollIntoView({" in javascript
    assert "scroll-margin-top: 92px;" in css
    assert '\'[data-tab="terminal"]\': "tab_terminal"' in translations
    assert 'tab_terminal: "Flight plan"' in translations
    assert 'id="terminal-toggle"' not in html
    assert "TERMINAL_COLLAPSED_KEY" not in javascript
    assert 'show($("terminal"), name === "terminal");' in javascript


def test_an_open_official_pdf_uses_the_full_content_width():
    static = Path(desktop.__file__).parent / "web" / "static"
    css = (static / "app.css").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert ".sia-airport-library.pdf-open { grid-column: 1 / -1; }" in css
    display_pdf = javascript[javascript.index('display.addEventListener("click"'):]
    display_pdf = display_pdf[: display_pdf.index("});")]
    assert 'card.classList.add("pdf-open");' in display_pdf


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
    # Six positions déclarées : le cran 1 en occupe deux, 1 et 1+F.
    assert "isAirbus && positions >= 6" in javascript
    assert 'return ["0", "1", "1", "2", "3", "FULL"]' in javascript
    # Cinq positions : les crans se lisent sans décalage, manette sur 2 → « 2 ».
    assert "isAirbus && positions === 5" in javascript
    assert 'return ["0", "1", "2", "3", "FULL"]' in javascript
    # Le cran rentré suit le marquage Airbus, mais garde « UP » traduit ailleurs.
    assert 'retracted !== "UP" ? retracted : t("cfg_flaps_up")' in javascript
    describe = javascript[javascript.index("function describeFlaps("):]
    describe = describe[: describe.index("\n}")]
    # Une ancienne extension physique à 100 % ne doit jamais figer l'affichage
    # sur FULL après que la source a annoncé un autre cran.
    assert 'const detent = detents?.[Math.round(index)];' in describe
    assert 'extended >= 98' not in describe
    assert 'return ["UP", "1", "2", "5", "10", "15", "25", "30", "40"]' in javascript
    assert 'return ["UP", "1", "5", "10", "20", "25", "30"]' in javascript
    assert 'return ["UP", "1", "5", "15", "20", "25", "30"]' in javascript
    assert "`${Math.round(extended)} %`" in javascript
    assert "describeFlaps(configuration, capabilities, aircraft, currentPlan)" in javascript


def test_aircraft_controls_have_live_simvar_fallbacks_shared_with_events():
    static = Path(desktop.__file__).parent / "web" / "static"
    live = (Path(desktop.__file__).parent / "live" / "simconnect.py").read_text(
        encoding="utf-8"
    )
    javascript = (static / "app.js").read_text(encoding="utf-8")

    for simvar in (
        "FLAPS EFFECTIVE HANDLE INDEX",
        "TRAILING EDGE FLAPS LEFT INDEX",
        "FLAPS HANDLE PERCENT",
        "SPOILERS LEFT POSITION",
        "SPOILERS RIGHT POSITION",
        "BRAKE PARKING INDICATOR",
    ):
        assert f'("{simvar}",' in live
    assert "self._resolve_flaps_index(" in live
    assert "self._resolve_spoilers_pct(" in live
    assert "self._resolve_parking_brake(" in live
    # Le panneau et la chronologie lisent le même état résolu.
    assert "finiteOr(configuration.flaps_handle_index)" in javascript
    assert "finiteOr(configuration.spoilers_handle_pct)" in javascript
    assert "aircraft?.configuration?.parking_brake" in javascript
    assert 'aircraft: currentPlan?.aircraft_name || currentPlan?.aircraft || ""' in javascript

    for model in ("A319", "A320", "A321"):
        assert f'"{model}"' in live
    assert '("L:S_FC_FLAPS", "Number")' in live
    assert '("L:A_FC_SPEEDBRAKE", "Number")' in live
    assert '("L:S_MIP_PARKING_BRAKE", "Number")' in live


def test_an_unknown_aircraft_still_reads_its_flap_detents():
    """Aucune table ne couvrira tous les avions : le repli doit rester juste."""
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    live = (Path(desktop.__file__).parent / "live" / "simconnect.py").read_text(
        encoding="utf-8"
    )

    assert '("TRAILING EDGE FLAPS LEFT ANGLE", "Degrees")' in live
    assert 'flaps_angle_deg=values["TRAILING EDGE FLAPS LEFT ANGLE"]' in live

    describe = javascript[javascript.index("function describeFlaps("):]
    describe = describe[: describe.index("\n}")]
    # Le rang de manette reste lisible sur n'importe quelle aile.
    assert "const position = steps ? `${index} / ${steps}` : String(index);" in describe
    assert "finiteOr(configuration.flaps_angle_deg)" in describe
    assert "`${Math.round(angle)}°`" in describe
    # Le pourcentage ne sert plus que si l'angle manque.
    assert "(extended !== null ? `${Math.round(extended)} %` : null)" in describe


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
    assert (
        '["STAR donnée par SimBrief et validée en base", '
        't("reason_star_simbrief_validated")]'
        in javascript
    )
    assert (
        '["SID donnée par SimBrief et validée en base", '
        't("reason_sid_simbrief_validated")]'
        in javascript
    )
    assert 'plan.warnings.map(warningText)' in javascript
    for key in (
        "warnings", "source_computed", "departure_title", "route_title",
        "arrival_title", "approach", "reason_runway_simbrief",
        "reason_transition_nearest_star", "reason_fix_distance",
        "reason_sid_simbrief_validated", "reason_star_simbrief_validated",
    ):
        assert f"{key}:" in translations
    assert translations.count("reason_sid_simbrief_validated:") == 8
    assert translations.count("reason_star_simbrief_validated:") == 8


def test_an_absent_procedure_never_costs_more_room_than_a_real_one():
    """Dire qu'il n'y a pas de STAR ne doit pas prendre la place d'une STAR.

    Un tiret cadré, une seconde ligne d'explication, puis une ligne de
    transition qui répète l'absence : quatre lignes pour un vide.
    """
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")

    # L'explication tient lieu de valeur, sur une seule ligne.
    assert "const empty = !choice.value;" in javascript
    assert 'empty ? (parts || "—") : choice.value' in javascript
    assert 'if (parts && !empty) row.append(el("span", "row-reason", parts));' in javascript
    assert ".row-empty" in css

    # Sans SID pas de sortie de SID, sans STAR pas d'entrée de STAR.
    assert "function transitionRows(" in javascript
    assert "if (!procedure.value) return [];" in javascript
    terminal = javascript[javascript.index("function renderTerminal(plan)"):]
    terminal = terminal[: terminal.index("/* ------------")]
    assert "plan.departure.sid, plan.departure.sid_transition," in terminal
    assert "plan.arrival.star, plan.arrival.star_transition," in terminal
    assert "plan.arrival.approach, plan.arrival.approach_transition," in terminal


def test_terminal_choices_can_be_recalculated_from_safe_published_alternatives():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert '...plannerOverrides' in javascript
    assert 'alternative?.value && !alternative.disqualified' in javascript
    # Le sélecteur ne dépend plus de la confiance : une SID sûre reste
    # remplaçable, et les choix que le moteur laisse vides — une STAR publiée
    # pour une autre piste — restent imposables depuis les alternatives.
    assert (
        'if (overrideField && alternatives.length && !latestStatus?.remote_client)'
        in javascript
    )
    assert 'confidenceClass(choice)' in javascript
    assert 'await applyPlannerOverride(overrideField, next)' in javascript
    # Une surcharge doit pouvoir être rendue au moteur.
    assert 'auto.value = PLANNER_OVERRIDE_AUTO' in javascript
    assert 'delete plannerOverrides[field]' in javascript
    # La liste reste repliée derrière un crayon discret : un panneau de vol se
    # lit d'abord. Le bouton doit rester atteignable au clavier et annoncer
    # l'état de la liste qu'il commande.
    assert 'const toggle = el("button", `choice-edit' in javascript
    assert 'toggle.append(pencilMark())' in javascript
    assert 'toggle.setAttribute("aria-controls", select.id)' in javascript
    assert 'toggle.setAttribute("aria-expanded", String(opened))' in javascript
    assert 'toggle.setAttribute("aria-label", tf("change_choice", { label }))' in javascript
    assert 'el("select", "choice-select hidden")' in javascript
    assert ".choice-edit" in css
    assert ".row:hover .choice-edit" in css
    assert ".choice-edit:focus-visible" in css
    assert 'departure_runway: ["sid", "sid_transition"]' in javascript
    assert (
        'arrival_runway: ["star", "star_transition", "approach", "approach_transition"]'
        in javascript
    )
    assert 'dot.setAttribute("aria-label", confidenceDescription)' in javascript
    assert 'dot.title = confidenceDescription' in javascript
    assert ".choice-select" in css
    for key in (
        "confidence_high", "confidence_medium", "confidence_low",
        "confidence_none", "change_choice", "change_choice_action",
        "reset_choice_action",
    ):
        assert f"{key}:" in translations
    assert translations.count("reset_choice_action:") == 8


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


def test_the_simulator_indicator_distinguishes_pause_from_disconnect():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    styles = (static / "app.css").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert 'indicator.classList.toggle("paused", paused)' in javascript
    assert 'aircraft.paused ? t("sim_paused")' in javascript
    assert ".sim-status.paused" in styles
    assert ".live-pill.paused" in styles
    assert translations.count("sim_paused:") == 8
    assert translations.count("sim_paused_title:") == 8


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
    assert '"ground", "procedures", "flight"' in javascript
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
    # MSFS may classify published taxiways as generic paths (LCPH does this for
    # A, B, K, etc.). Named paths stay on the main plan; only anonymous links
    # and stand lead-ins remain behind the Secondary control.
    assert 'taxiway.kind === "parking" || (' in ground
    assert 'taxiway.kind === "path" && !String(taxiway.name || "").trim()' in ground
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


def test_the_ground_view_shows_the_live_ground_speed():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")

    assert 'id="ground-speed"' in html
    # Le bandeau de guidage est réécrit à chaque position : y loger la vitesse
    # relancerait le clignotement du dépassement à chaque seconde.
    assert html.index('id="ground-speed"') > html.index('id="ground-hud"')
    assert "renderTaxiSpeed(aircraft);" in javascript
    assert "renderTaxiSpeed(null);" in javascript
    assert ".ground-speed {" in css
    # Sans chasse fixe, le bandeau tressaute à chaque kt.
    assert "font-variant-numeric: tabular-nums;" in css


def test_the_taxi_speed_alarm_warns_before_it_shouts():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")

    state = javascript[javascript.index("function taxiSpeedState"):]
    state = state[: state.index("\n}\n")]
    assert 'level = "over"' in state
    assert 'level = "caution"' in state
    assert "TAXI_CAUTION_RATIO" in state
    assert "const TAXI_CAUTION_RATIO = 0.9;" in javascript

    assert ".ground-speed.is-caution" in css
    assert ".ground-speed.is-over" in css
    # Le clignotement n'est qu'un renfort : la couleur et le chiffre suffisent.
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_the_taxi_limit_tightens_for_turns_holds_and_the_stand():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")

    limit = javascript[javascript.index("function taxiSpeedLimitKt"):]
    limit = limit[: limit.index("\n}\n")]
    assert "guidance.arrived" in limit
    assert "guidance.hold_short" in limit
    assert 'guidance.next_turn === "left"' in limit
    assert "TAXI_TURN_ZONE_M" in limit
    # Une limite de virage plus haute que la ligne droite ne se déclencherait
    # jamais.
    assert "Math.min(taxiSpeedLimits.turn, straight)" in limit


def test_the_taxi_speed_alarm_stays_silent_on_the_runway():
    """Le décollage se fait à des vitesses qui n'ont rien à voir avec le roulage.

    La déduire de la vitesse ferait taire l'alarme précisément quand elle se
    justifie le plus : c'est la géométrie du terrain qui tranche.
    """
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    ground = (static / "ground.js").read_text(encoding="utf-8")

    assert "GROUND.onRunway(aircraft)" in javascript
    assert 'level: "runway"' in javascript
    assert "onRunway(state = aircraft)" in ground
    assert "distanceToSegment" in ground
    assert "runway.width_m || 45) / 2 + 10" in ground


def test_the_taxi_alarm_beep_is_synthesised_and_can_be_muted():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")

    assert 'id="ground-alarm"' in html
    assert '$("ground-alarm").addEventListener' in javascript
    assert "window.AudioContext || window.webkitAudioContext" in javascript
    assert "if (!taxiSpeedLimits.sound) return;" in javascript
    # Un dépassement doit tenir avant le premier bip : une bosse de piste ne
    # déclenche pas l'alarme.
    assert "const TAXI_ALARM_HOLD_MS = 1000;" in javascript
    assert "now - taxiAlarmSince < TAXI_ALARM_HOLD_MS" in javascript

    mute = javascript[javascript.index("async function toggleTaxiAlarmSound"):]
    mute = mute[: mute.index("\n}\n")]
    assert "latestStatus?.remote_client" in mute
    assert "taxi_speed_alarm_sound: taxiSpeedLimits.sound" in mute


def test_taxi_speed_limits_are_a_setting_in_every_language():
    static = Path(desktop.__file__).parent / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert 'id="settings-taxi-speed"' in html
    assert 'id="settings-taxi-turn-speed"' in html
    assert 'id="settings-taxi-alarm"' in html
    assert "taxi_speed_limit_kt: Number(" in javascript
    assert "applyTaxiSpeedPreferences(" in javascript
    # Un client distant ne lit pas /api/settings : le statut lui porte les
    # limites de l'hôte.
    assert "applyTaxiSpeedPreferences(status);" in javascript

    for key in (
        "ground_alarm",
        "taxi_speed_limit",
        "taxi_speed_over",
        "taxi_speed_runway",
        "taxi_speed_setting",
        "taxi_turn_speed_setting",
        "taxi_speed_alarm_setting",
    ):
        assert translations.count(f"{key}:") == 8


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


def test_demo_plan_chart_and_live_flow_does_not_crash(monkeypatch, tmp_path):
    project = Path(desktop.__file__).parent.parent
    import navixav.web.app as web_app

    # Cette vérification détaillée des cartes et du roulage utilise la base
    # historique LFST/LFBO, qui contient précisément ces deux aérodromes.
    monkeypatch.setattr(
        web_app, "DEMO_OFP", project / "tests" / "data" / "ofp_lfst_lfbo.json",
    )
    store = tmp_path / "navdata.sqlite"
    shutil.copyfile(project / "tests" / "data" / "navdata_test.sqlite", store)
    app = create_app(Settings(navdata_store=store, metar_source="simbrief"))

    def endpoint(path, method=None):
        return next(
            route.endpoint
            for route in app.routes
            if route.path == path and (method is None or method in route.methods)
        )

    try:
        current_plan = endpoint("/api/plan/current")
        restart_demo = endpoint("/api/demo/restart", "POST")
        with pytest.raises(HTTPException) as missing:
            current_plan()
        assert missing.value.status_code == 404
        with pytest.raises(HTTPException) as no_demo_route:
            restart_demo()
        assert no_demo_route.value.status_code == 409

        plan = endpoint("/api/plan")(PlanRequest(demo=True))
        assert current_plan() == plan
        weather = endpoint("/api/weather/current")()
        assert weather["enabled"] is False
        assert weather["live"] is False
        assert weather["weather"] == plan["weather"]
        assert weather["refresh_interval_seconds"] == 300
        departure = plan["departure"]
        runway = departure["runway"]["value"]
        chart = endpoint("/api/chart/{icao}")(departure["icao"], runway)
        live = endpoint("/api/live")(True, departure["icao"], runway)

        assert chart["parkings"]
        assert live["connected"] is True
        assert live["aircraft"]["source"] == "Démonstration"
        # La démonstration doit rejouer le vol complet du plan, pas un roulage.
        assert live["aircraft"]["title"] == "Démonstration NaviXav"

        restarted = restart_demo()
        assert restarted == {
            "started": True,
            "departure": plan["departure"]["icao"],
            "arrival": plan["arrival"]["icao"],
        }

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
        app.state.close_resources()


def test_bundled_demo_is_lcph_to_eham_and_keeps_an_offline_flight_path(
    monkeypatch, tmp_path,
):
    import navixav.navdata.msfs as msfs_module

    class _ForbiddenSimConnect:
        def __init__(self):
            raise AssertionError("la démo ne doit pas ouvrir SimConnect")

    monkeypatch.setattr(msfs_module, "SimConnectClient", _ForbiddenSimConnect)
    # Le fichier n'existe pas encore : cela représente une installation qui
    # n'a jamais lancé MSFS ni importé le moindre aérodrome.
    store = tmp_path / "empty-navdata.sqlite"
    app = create_app(Settings(navdata_store=store, metar_source="simbrief"))
    endpoint = next(route.endpoint for route in app.routes if route.path == "/api/plan")
    live_endpoint = next(route.endpoint for route in app.routes if route.path == "/api/live")

    try:
        plan = endpoint(PlanRequest(demo=True))
        assert plan["departure"]["icao"] == "LCPH"
        assert plan["arrival"]["icao"] == "EHAM"
        assert plan["enroute"]["route_path"][0]["ident"] == "LCPH"
        assert plan["enroute"]["route_path"][-1]["ident"] == "EHAM"
        assert not any(
            "absent de la base de navigation" in warning
            for warning in plan["warnings"]
        )
        live = live_endpoint(True, "LCPH", None, plan["aircraft"])
        assert live["connected"] is True
        assert live["aircraft"]["source"] == "Démonstration"
    finally:
        app.state.close_resources()


def test_mobile_reads_the_pc_current_flight_without_rebuilding_it():
    app_source = (
        Path(desktop.__file__).parent / "web" / "app.py"
    ).read_text(encoding="utf-8")
    javascript = (
        Path(desktop.__file__).parent / "web" / "static" / "app.js"
    ).read_text(encoding="utf-8")

    assert '@app.get("/api/plan/current")' in app_source
    assert '@app.get("/api/weather/current")' in app_source
    assert (
        'request.url.path == "/api/plan" and request.method == "POST"'
        in app_source
    )
    assert 'fetch("/api/plan/current")' in javascript
    assert 'fetch("/api/weather/current",' in javascript
    assert "if (status.remote_client)" in javascript
    assert "await loadCurrentPlan();" in javascript


def test_demo_toggle_restarts_the_current_plan_instead_of_loading_lfst_lfbo():
    app_source = (
        Path(desktop.__file__).parent / "web" / "app.py"
    ).read_text(encoding="utf-8")
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert '@app.post("/api/demo/restart")' in app_source
    assert 'fetch("/api/demo/restart", { method: "POST" })' in javascript
    assert 'if (currentPlan) await restartCurrentPlanDemo();' in javascript
    assert '$("refresh").addEventListener("click", refreshPlanOrDemo);' in javascript
    assert '$("demo-toggle").addEventListener("change", toggleDemoMode);' in javascript
    assert 'demo: useBundledDemo' in javascript
    assert 'demoOfp ?? (' in javascript
    assert 'demo_title: "Simuler le plan de vol actuellement chargé"' in translations
    assert 'demo_title: "Use the LFST → LFBO demonstration flight"' not in translations
    assert translations.count("demo_restart_failed:") == 8


def test_live_weather_refresh_updates_the_cached_plan(monkeypatch, tmp_path):
    project = Path(desktop.__file__).parent.parent
    store = tmp_path / "navdata.sqlite"
    shutil.copyfile(project / "tests" / "data" / "navdata_test.sqlite", store)
    app = create_app(Settings(navdata_store=store, metar_source="simbrief"))

    def endpoint(path, method=None):
        return next(
            route.endpoint
            for route in app.routes
            if route.path == path and (method is None or method in route.methods)
        )

    try:
        plan = endpoint("/api/plan")(PlanRequest(demo=True))
        monkeypatch.setattr(
            "navixav.web.app.save_user_settings",
            lambda _settings: None,
        )
        endpoint("/api/settings", "PUT")(SettingsRequest(metar_source="live"))
        fresh = AirportWeather(
            icao=plan["departure"]["icao"],
            role="departure",
            source="awc",
            raw_metar=f"{plan['departure']['icao']} 021300Z 09004KT CAVOK",
        )
        captured = {}

        def fake_briefing(_ofp, **options):
            captured.update(options)
            return WeatherBriefing(departure=fresh)

        monkeypatch.setattr("navixav.web.app.build_briefing", fake_briefing)
        result = endpoint("/api/weather/current")()

        assert captured == {"metar_source": "live", "force_live": True}
        assert result["enabled"] is True
        assert result["live"] is True
        assert result["partial"] is False
        assert result["refreshed_at"].endswith("+00:00")
        assert endpoint("/api/plan/current")()["weather"] == result["weather"]
    finally:
        app.state.close_resources()


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


def test_dispatch_panel_tracks_the_flight_in_real_time():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")
    styles = (static / "app.css").read_text(encoding="utf-8")

    # Le suivi s'alimente sur la boucle live et se repeint toutes les 2 s.
    assert "updateDispatchLive(aircraft);" in javascript
    assert "updateDispatchLive(null);" in javascript
    assert "const DISPATCH_LIVE_INTERVAL_MS = 2000;" in javascript

    # Les relevés viennent de SimConnect, jamais d'un service distant.
    engine = javascript[javascript.index("function ingestDispatchSample(aircraft)"):]
    engine = engine[: engine.index("\nfunction setDispatchLiveCell(")]
    assert "configuration?.fuel_total_kg" in engine
    assert "configuration?.total_weight_kg" in engine
    assert "fetch(" not in engine

    # Le temps est compté en secondes simulées : un vol accéléré ne doit pas
    # multiplier la consommation horaire affichée.
    assert "simulation_rate" in engine
    assert "state.sim_seconds += (elapsedMs / 1000) * rate;" in engine

    cells = javascript[javascript.index("function renderDispatchLiveCells(aircraft)"):]
    cells = cells[: cells.index("\nfunction updateDispatchLive(")]
    panel = javascript[javascript.index("function renderDispatch(plan)"):]
    panel = panel[: panel.index("function renderAircraft(plan)")]
    # Chaque cellule mise à jour doit exister dans le panneau construit.
    for identifier in (
        "dispatch-live-block", "dispatch-live-onboard", "dispatch-live-burn",
        "dispatch-live-flow", "dispatch-live-landing-fuel", "dispatch-live-tow",
        "dispatch-live-ldw", "dispatch-live-ete", "dispatch-live-block-time",
        "dispatch-live-distance",
    ):
        assert f'"{identifier}"' in cells
        assert f'"{identifier}"' in panel

    # Le carburant projeté sous la réserve finale est une alerte, pas une nuance.
    assert "landingFuelStatus = \"danger\"" in cells
    assert "landingWeightStatus = \"danger\"" in cells
    assert '.stat[data-live-status="danger"]' in styles

    for key in (
        "dispatch_live_title", "dispatch_live_hint", "dispatch_live_waiting",
        "dispatch_live_ground", "dispatch_live_airborne", "dispatch_live_arrived",
        "dispatch_actual", "dispatch_projected", "dispatch_loaded",
        "dispatch_burned", "dispatch_measured", "dispatch_remaining",
        "dispatch_elapsed", "dispatch_flown", "dispatch_as_planned",
        "dispatch_onboard_note",
    ):
        assert f"{key}:" in translations
        # Les états du bandeau passent par une variable : seul le libellé compte.
        assert f'"{key}"' in javascript


def test_dispatch_and_aircraft_panels_follow_the_selected_language():
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    dispatch = javascript[javascript.index("function renderDispatch(plan)"):]
    dispatch = dispatch[: dispatch.index("function renderAircraft(plan)")]
    aircraft = javascript[javascript.index("function renderAircraft(plan)"):]
    aircraft = aircraft[: aircraft.index("function mcduLine(")]

    for french in (
        "Aucune donnée de dispatch", "Charge marchande", "Réserve finale",
        "Restant à l", "Conso horaire", "Distances et temps", "Orthodromie",
        "Temps de vol", "Immatriculation", "Plan de vol OACI", "bagages",
        "de fret", "capacité ", "composante ",
    ):
        assert french not in dispatch
    for french in (
        "Appareil utilisé", "Type inconnu", "Équipement de bord",
        "Profil de montée", "Masse à vide", "Capacité carburant",
        "codes déclarés dans le plan de vol SimBrief",
    ):
        assert french not in aircraft

    # Les identifiants aéronautiques se lisent tels quels dans toutes les langues.
    for identifier in ("ZFW", "SELCAL", "Cost index"):
        assert f'"{identifier}"' in dispatch
    for identifier in ("MZFW", "MTOW", "MLW"):
        assert f'"{identifier}"' in aircraft

    for key in (
        "dsp_empty", "dsp_group_weights", "dsp_group_fuel", "dsp_payload",
        "dsp_reserve", "dsp_landing_fuel", "dsp_fuel_flow", "dsp_bags",
        "dsp_cargo_note", "dsp_max", "dsp_capacity_note", "dsp_wind_component",
        "dsp_atc_flightplan", "acf_kicker", "acf_flight", "acf_oew",
        "acf_equipment_note", "acf_planned_passengers",
    ):
        assert f"{key}:" in translations
        assert f'"{key}"' in javascript


def test_constraints_charts_and_mcdu_panels_follow_the_selected_language():
    """Ces trois modules affichaient encore leurs libellés en dur, en français."""
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    constraints = javascript[javascript.index("function constraintTable("):]
    constraints = constraints[: constraints.index("/* -------------------------------------------------------------- dispatch */")]
    charts = javascript[javascript.index("function siaApproachCard(plan)"):]
    charts = charts[: charts.index("function aircraftFmsProfile(plan)")]
    mcdu = javascript[javascript.index("function renderMcdu(plan)"):]
    mcdu = mcdu[: mcdu.index("/* ------------------------------------------------------------------ carte */")]

    for french in (
        "Aucune contrainte", "Repère", "Vitesse", "Ne pas descendre",
        "Profil vertical", "Axe LOC", "Interception", "remise de gaz",
        "minima officiels",
    ):
        assert french not in constraints
    for french in (
        "Source officielle", "Carte d", "Recherche", "Indisponible",
        "Cartes des aérodromes", "Afficher le PDF", "nouvel onglet",
        "Calque", "Catégorie", "Mémoriser",
    ):
        assert french not in charts
    for french in ("Fiche ", "sortie de la SID", "entrée de STAR", "À confirmer"):
        assert french not in mcdu

    # Les rubriques du catalogue AIS servent au classement : le service les
    # publie en français, l'interface ne traduit que l'affichage.
    assert 'chart.category === "Départs SID"' in javascript
    assert "chartCategory(chart.category)" in javascript
    assert 'role === "departure"' in javascript

    for key in (
        "cst_empty", "cst_fix", "cst_speed", "cst_not_below", "cst_maintain",
        "cst_sid", "cst_approach", "vprof_kicker", "vprof_loc", "vprof_intercept",
        "vprof_intercept_note", "vprof_empty", "vprof_missed", "vprof_caution",
        "chart_kicker", "chart_title", "chart_intro", "chart_document",
        "chart_show_pdf", "chart_open_tab", "chart_overlay",
        "chart_overlay_available", "chart_overlay_missing", "sia_kicker",
        "sia_title", "sia_use_values", "sia_extraction_caution", "min_kicker",
        "min_title", "min_field", "min_dh", "min_altitude", "min_rvr",
        "min_save", "mcdu_kicker", "mcdu_profile_note", "mcdu_sid_exit",
        "mcdu_star_entry", "mcdu_confirm",
    ):
        assert f"{key}:" in translations
        assert f'"{key}"' in javascript

    # Les libellés que le service compose sont traduits dans i18n.js même.
    for key in (
        "cst_between", "chart_cat_iac", "chart_cat_sid", "chart_cat_star",
        "chart_cat_airport", "chart_cat_visual", "chart_cat_other",
    ):
        assert f"{key}:" in translations
        assert f'"{key}"' in translations


def test_the_taxi_labels_of_the_service_are_translated_for_display():
    """« porte V 6 » et « attente 24 » viennent du service, en français."""
    static = Path(desktop.__file__).parent / "web" / "static"
    javascript = (static / "app.js").read_text(encoding="utf-8")
    ground = (static / "ground.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert "groundLabel," in translations
    assert "window.I18N.groundLabel(parking.label)" in ground
    # La sélection et la requête d'itinéraire gardent l'étiquette d'origine.
    assert "parking.label === selected" in ground
    assert "parking: requestedPlan.parking.label," in javascript

    hud = javascript[javascript.index("function updateGroundHud"):]
    hud = hud[: hud.index("\n}\n")]
    assert "groundLabel(currentTaxiPlan.parking?.label)" in hud
    assert "currentTaxiPlan.summary.map(groundLabel)" in hud

    for key in (
        "gnd_hold_short", "gnd_gate", "gnd_gate_small", "gnd_parking",
        "gnd_ramp_ga", "gnd_deicing",
    ):
        assert f"{key}:" in translations
