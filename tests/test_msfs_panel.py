"""Panneau MSFS : proposé, jamais imposé, et retiré sans dégât collatéral."""

import json
from pathlib import Path

import pytest

from navixav import msfs_panel


def _bundled(tmp_path: Path, *, compiled: bool = True) -> Path:
    package = tmp_path / "bundled" / msfs_panel.PACKAGE_NAME
    (package / "html_ui" / "InGamePanels" / "NaviXavPanel").mkdir(parents=True)
    (package / "manifest.json").write_text(
        '{"title":"NaviXav Toolbar","package_version":"1.0.0"}', encoding="utf-8"
    )
    (package / "html_ui" / "InGamePanels" / "NaviXavPanel" / "NaviXavPanel.js").write_text(
        "// panneau", encoding="utf-8"
    )
    if compiled:
        (package / "InGamePanels").mkdir()
        (package / msfs_panel.PANEL_FILE).write_bytes(b"spb")
    return package


def _community(tmp_path: Path) -> Path:
    community = tmp_path / "Community"
    community.mkdir()
    return community


def test_the_panel_is_not_offered_while_its_declaration_is_missing(tmp_path, monkeypatch):
    """Sans le `.spb`, le paquet se copierait sans jamais apparaître."""
    package = _bundled(tmp_path, compiled=False)
    monkeypatch.setattr(msfs_panel, "bundled_package", lambda: package)
    community = _community(tmp_path)

    status = msfs_panel.status([community])
    assert status.available is True
    assert status.complete is False

    with pytest.raises(FileNotFoundError):
        msfs_panel.install([community])
    assert list(community.iterdir()) == []


def test_installing_copies_the_package_and_describes_it_to_the_simulator(
    tmp_path, monkeypatch
):
    package = _bundled(tmp_path)
    monkeypatch.setattr(msfs_panel, "bundled_package", lambda: package)
    community = _community(tmp_path)

    assert msfs_panel.status([community]).installed is False
    target = msfs_panel.install([community])
    assert target == community / msfs_panel.PACKAGE_NAME

    layout = json.loads((target / "layout.json").read_text(encoding="utf-8"))
    paths = {entry["path"] for entry in layout["content"]}
    assert "InGamePanels/navixav-toolbar.spb" in paths
    assert "html_ui/InGamePanels/NaviXavPanel/NaviXavPanel.js" in paths
    # Le simulateur n'attend ni le manifeste ni le layout dans le layout.
    assert "manifest.json" not in paths and "layout.json" not in paths
    assert all(entry["size"] > 0 and entry["date"] > 0 for entry in layout["content"])

    status = msfs_panel.status([community])
    assert status.installed is True
    assert status.installed_version == "1.0.0"
    assert status.path == str(target)


def test_installing_again_replaces_our_package_without_piling_up(tmp_path, monkeypatch):
    package = _bundled(tmp_path)
    monkeypatch.setattr(msfs_panel, "bundled_package", lambda: package)
    community = _community(tmp_path)

    target = msfs_panel.install([community])
    (target / "stale.txt").write_text("ancienne version", encoding="utf-8")
    msfs_panel.install([community])
    assert not (target / "stale.txt").exists()


def test_removing_takes_our_package_and_nothing_else(tmp_path, monkeypatch):
    package = _bundled(tmp_path)
    monkeypatch.setattr(msfs_panel, "bundled_package", lambda: package)
    community = _community(tmp_path)
    neighbour = community / "fsltl-traffic-base"
    neighbour.mkdir()
    (neighbour / "manifest.json").write_text("{}", encoding="utf-8")

    msfs_panel.install([community])
    assert msfs_panel.uninstall([community]) is True
    assert not (community / msfs_panel.PACKAGE_NAME).exists()
    assert neighbour.is_dir(), "un paquet voisin a disparu"
    # Retirer ce qui n'est plus là n'est pas une erreur.
    assert msfs_panel.uninstall([community]) is False


def test_a_foreign_folder_wearing_our_name_is_never_touched(tmp_path, monkeypatch):
    """Le nom ne suffit pas : sans notre manifeste, on ne supprime rien."""
    package = _bundled(tmp_path)
    monkeypatch.setattr(msfs_panel, "bundled_package", lambda: package)
    community = _community(tmp_path)
    intruder = community / msfs_panel.PACKAGE_NAME
    intruder.mkdir()
    (intruder / "important.txt").write_text("données d'un tiers", encoding="utf-8")

    with pytest.raises(FileExistsError):
        msfs_panel.install([community])
    with pytest.raises(FileExistsError):
        msfs_panel.uninstall([community])
    assert (intruder / "important.txt").is_file()


def test_no_community_folder_is_a_refusal_not_a_crash(tmp_path, monkeypatch):
    package = _bundled(tmp_path)
    monkeypatch.setattr(msfs_panel, "bundled_package", lambda: package)
    with pytest.raises(FileNotFoundError):
        msfs_panel.install([tmp_path / "absent"])


# --------------------------------------------------------------------------- #
# Le paquet livré et son service
# --------------------------------------------------------------------------- #


def test_the_shipped_package_carries_everything_but_its_compiled_declaration():
    package = msfs_panel.bundled_package()
    for relative in (
        "manifest.json",
        "html_ui/InGamePanels/NaviXavPanel/NaviXavPanel.html",
        "html_ui/InGamePanels/NaviXavPanel/NaviXavPanel.js",
        "html_ui/InGamePanels/NaviXavPanel/NaviXavPanel.css",
        "html_ui/Textures/Menu/toolbar/NAVIXAV_ICON_TOOLBAR.svg",
        "html_ui/icons/toolbar/NAVIXAV_ICON_TOOLBAR.svg",
    ):
        assert (package / relative).is_file(), relative

    javascript = (
        package / "html_ui/InGamePanels/NaviXavPanel/NaviXavPanel.js"
    ).read_text(encoding="utf-8")
    # Deux paquets qui déclarent le même élément s'excluent dans la barre.
    assert 'customElements.define("ingamepanel-navixav"' in javascript
    assert "ingamepanel-custom" not in javascript
    assert "/api/panel/state" in javascript
    # `localhost` peut se résoudre en ::1, où le service n'écoute jamais.
    assert '"http://127.0.0.1:"' in javascript
    assert 'http://localhost' not in javascript


def test_the_panel_probes_exactly_the_ports_the_service_can_take():
    """Le panneau cherchait 8775-8779 quand le service prend 8765-8775."""
    from navixav import desktop

    javascript = (
        msfs_panel.bundled_package()
        / "html_ui/InGamePanels/NaviXavPanel/NaviXavPanel.js"
    ).read_text(encoding="utf-8")
    first = int(
        javascript.split("NAVIXAV_FIRST_PORT = ")[1].split(";")[0].strip()
    )
    last = int(javascript.split("NAVIXAV_LAST_PORT = ")[1].split(";")[0].strip())
    assert (first, last) == (desktop.DEFAULT_PORT, desktop.LAST_PORT)


def _app(settings=None):
    from navixav.config import Settings
    from navixav.web.app import create_app

    return create_app(settings or Settings(metar_source="simbrief"))


def _endpoint(app, path):
    return next(route.endpoint for route in app.routes if route.path == path)


def test_the_panel_reads_the_state_the_map_already_shows():
    state = _endpoint(_app(), "/api/panel/state")()
    assert state["running"] is True
    assert {"traffic_enabled", "traffic_source", "injection_active", "conflict"} <= set(state)
    # Rien d'identifiant ne sort par cette porte ouverte au simulateur.
    assert not {"simbrief_pilot_id", "simbrief_username"} & set(state)


def test_a_panel_traffic_command_preserves_every_other_setting(monkeypatch):
    """Une commande partielle ne doit surtout pas vider le compte SimBrief."""
    from navixav.config import Settings
    from navixav.web import app as web_app

    saved = []
    monkeypatch.setattr(web_app, "save_user_settings", saved.append)
    configured = Settings(
        simbrief_pilot_id="123456",
        simbrief_username="xavier",
        metar_source="live",
        map_basemap="opentopo",
    )
    app = _app(configured)

    state = _endpoint(app, "/api/panel/traffic/{state}")("on")

    assert state["traffic_enabled"] is True
    assert saved[-1].simbrief_pilot_id == "123456"
    assert saved[-1].simbrief_username == "xavier"
    assert saved[-1].metar_source == "live"
    assert saved[-1].map_basemap == "opentopo"


def test_the_panel_offers_every_traffic_source_the_settings_offer(monkeypatch):
    """Un bouton du panneau sans source derrière ne ferait rien du tout."""
    from navixav.config import TRAFFIC_SOURCES
    from navixav.web import app as web_app

    monkeypatch.setattr(web_app, "save_user_settings", lambda settings: None)
    endpoint = _endpoint(_app(), "/api/panel/source/{name}")
    for source in TRAFFIC_SOURCES:
        assert endpoint(source)["traffic_source"] == source

    javascript = (
        msfs_panel.bundled_package()
        / "html_ui/InGamePanels/NaviXavPanel/NaviXavPanel.js"
    ).read_text(encoding="utf-8")
    html = (
        msfs_panel.bundled_package()
        / "html_ui/InGamePanels/NaviXavPanel/NaviXavPanel.html"
    ).read_text(encoding="utf-8")
    for source in TRAFFIC_SOURCES:
        assert f'"/api/panel/source/" + source.id' in javascript
        assert f'id: "{source}"' in javascript
    # Un bouton par source, et aucun de plus.
    assert html.count("sourceButton") == len(TRAFFIC_SOURCES)


def test_an_unknown_traffic_source_is_refused():
    from fastapi import HTTPException

    endpoint = _endpoint(_app(), "/api/panel/source/{name}")
    with pytest.raises(HTTPException):
        endpoint("flightradar")


def test_an_unknown_traffic_command_is_refused():
    from fastapi import HTTPException

    endpoint = _endpoint(_app(), "/api/panel/traffic/{state}")
    with pytest.raises(HTTPException):
        endpoint("maybe")


def test_installing_from_the_interface_requires_the_confirmation_header():
    from types import SimpleNamespace

    from fastapi import HTTPException

    app = _app()
    for path in ("/api/msfs-panel/install", "/api/msfs-panel/uninstall"):
        endpoint = _endpoint(app, path)
        with pytest.raises(HTTPException) as refused:
            endpoint(SimpleNamespace(headers={}))
        assert refused.value.status_code == 403
