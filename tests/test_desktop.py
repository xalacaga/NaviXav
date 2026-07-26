"""Fenêtre native et cycle de vie du service local."""

import sys
import time
import logging
from pathlib import Path
from types import SimpleNamespace

from navixav import desktop
from navixav.logging_setup import (
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES,
    configure_logging,
)


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
    assert 'href="/static/navixav-icon.svg"' in html


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


def test_vertical_profile_waits_for_descent_before_reporting_too_low():
    javascript = (
        Path(desktop.__file__).parent / "web" / "static" / "app.js"
    ).read_text(encoding="utf-8")
    assert 'phase === "Descente"' in javascript
    assert 'phase === "Approche"' in javascript
    assert "En attente du TOD" in javascript
    assert "Math.abs(delta) <= 500" in javascript
