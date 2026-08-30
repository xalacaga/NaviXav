"""Panneau de procédures par appareil dans les réglages locaux."""

from pathlib import Path
from types import SimpleNamespace

from navixav.aircraft.community import InstalledAircraft, Survey
from navixav.config import Settings
from navixav.web import app as web_app
from navixav.web.app import AircraftScaffoldRequest, create_app


def _endpoint(app, path: str):
    return next(route.endpoint for route in app.routes if route.path == path)


def _missing() -> InstalledAircraft:
    return InstalledAircraft(
        package="vendor-widget",
        directory=Path("Community/vendor-widget/SimObjects/Airplanes/widget"),
        titles=("Widget 500",),
        manufacturer="Widget",
        model="500",
        icao="W500",
        engine_count=2,
        engine_type="turboprop",
    )


def test_aircraft_survey_route_serializes_detected_folders(monkeypatch, tmp_path):
    community = tmp_path / "Community"
    community.mkdir()
    report = Survey(folders=[community], missing=[_missing()])
    monkeypatch.setattr(web_app, "community_folders", lambda explicit=None: [community])
    monkeypatch.setattr(web_app, "AircraftMatcher", lambda: object())
    monkeypatch.setattr(web_app, "survey", lambda matcher, folders: report)
    app = create_app(Settings())

    payload = _endpoint(app, "/api/aircraft/survey")()

    assert payload["folders"] == [str(community)]
    assert payload["missing"][0]["label"] == "Widget 500"
    app.state.close_resources()


def test_aircraft_photo_route_only_serves_a_scanned_community_thumbnail(
    monkeypatch, tmp_path
):
    community = tmp_path / "Community"
    community.mkdir()
    directory = community / "vendor" / "SimObjects" / "Airplanes" / "widget"
    directory.mkdir(parents=True)
    thumbnail = directory / "thumbnail.jpg"
    thumbnail.write_bytes(b"jpeg")
    aircraft = InstalledAircraft(
        package="vendor", directory=directory, titles=("Fenix A321 CFM",),
        manufacturer="Fenix", model="A321", icao="A21N",
    )
    monkeypatch.setattr(web_app, "community_folders", lambda explicit=None: [community])
    monkeypatch.setattr(web_app, "scan", lambda folders: [aircraft])
    app = create_app(Settings())

    response = _endpoint(app, "/api/aircraft/photo")(
        icao="A21N", name="Fenix A321", community=str(community)
    )

    assert Path(response.path) == thumbnail
    app.state.close_resources()


def test_folder_selector_returns_the_inventory_without_saving(monkeypatch, tmp_path):
    community = tmp_path / "Community"
    community.mkdir()
    report = Survey(folders=[community], missing=[_missing()])
    monkeypatch.setattr(web_app, "AircraftMatcher", lambda: object())
    monkeypatch.setattr(web_app, "survey", lambda matcher, folders: report)
    app = create_app(Settings())
    app.state.request_aircraft_folder = lambda current: str(community)
    request = SimpleNamespace(headers={"X-NaviXav-Aircraft": "browse"})

    payload = _endpoint(app, "/api/aircraft/select-folder")(request)

    assert payload["selected_path"] == str(community)
    assert payload["total"] == 1
    app.state.close_resources()


def test_each_missing_aircraft_can_create_its_own_draft(monkeypatch, tmp_path):
    community = tmp_path / "Community"
    community.mkdir()
    aircraft = _missing()
    before = Survey(folders=[community], missing=[aircraft])
    after = Survey(
        folders=[community],
        covered=[(aircraft, "widget/500", "draft")],
    )
    reports = iter((before, after))
    written = tmp_path / "aircraft_db" / "aircraft" / "widget" / "500"
    monkeypatch.setattr(web_app, "community_folders", lambda explicit=None: [community])
    monkeypatch.setattr(web_app, "AircraftMatcher", lambda: object())
    monkeypatch.setattr(web_app, "survey", lambda matcher, folders: next(reports))
    monkeypatch.setattr(web_app, "write_entry", lambda selected: written)
    app = create_app(Settings())
    request = SimpleNamespace(headers={"X-NaviXav-Aircraft": "scaffold"})

    payload = _endpoint(app, "/api/aircraft/scaffold")(
        AircraftScaffoldRequest(
            label=aircraft.label,
            package=aircraft.package,
            community_path=str(community),
        ),
        request,
    )

    assert payload["missing"] == []
    assert payload["covered"][0]["maturity"] == "draft"
    assert payload["created"]["directory"] == str(written)
    app.state.close_resources()


def test_settings_contain_the_complete_aircraft_panel():
    static = Path(web_app.__file__).parent / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")

    assert 'id="settings-aircraft-community"' in html
    assert 'id="aircraft-folder-browse"' in html
    assert 'id="aircraft-covered-list"' in html
    assert 'id="aircraft-missing-list"' in html
    assert 'fetch("/api/aircraft/scaffold"' in javascript
    assert 'visual.classList.add("aircraft-survey-photo")' in javascript
    assert "aircraft-survey-columns" in css
    assert ".aircraft-survey-photo" in css


def test_aircraft_panel_uses_bundled_photos_then_community_thumbnails():
    static = Path(web_app.__file__).parent / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    css = (static / "app.css").read_text(encoding="utf-8")
    photos = static / "aircraft"

    assert 'asset: "airbus-a321"' in javascript
    assert javascript.index('asset: "airbus-a321"') < javascript.index('asset: "airbus-a320"')
    assert 'encodeURIComponent(loadedTitle ? "" : plan.aircraft || "")' in javascript
    assert 'encodeURIComponent(loadedTitle || plan.aircraft_name || "")' in javascript
    assert '}, null, community, photoRevision)' in javascript
    assert '`&community=${encodeURIComponent(communityPath)}`' in javascript
    assert '`&v=${encodeURIComponent(photoRevision)}`' in javascript
    assert 'photo.classList.remove("hidden")' in javascript
    assert 'mark.classList.add("hidden")' in javascript
    assert "photo.hidden" not in javascript
    assert "mark.hidden" not in javascript
    assert "aircraft-photo" in css
    assert 'id="aircraft-photo-dialog"' in html
    assert 'id="aircraft-photo-large"' in html
    assert 'id="aircraft-photo-close"' in html
    assert "function openAircraftPhoto(" in javascript
    assert 'visual.setAttribute("role", "button")' in javascript
    assert 'event.key !== "Enter" && event.key !== " "' in javascript
    assert ".aircraft-photo-dialog::backdrop" in css
    assert len(list(photos.glob("*.jpg"))) == 31
    assert all(path.stat().st_size > 20_000 for path in photos.glob("*.jpg"))
