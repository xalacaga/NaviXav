"""Un plan de vol préparé dans MSFS (.PLN) vaut un OFP SimBrief pour le moteur.

    LFST  RWY 05   EPIK8M / EPIKO
    LFBO  RWY 32R  AFRI8N / AFRIC  puis ILS Z RWY 32R / ADIMO

C'est la même route que l'OFP de référence, pour que le moteur produise le
même panneau quelle que soit la provenance du plan.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from navixav.config import Settings
from navixav.models import Confidence
from navixav.msfs.flightplan import (
    MsfsPlanError,
    current_flight_plan,
    load_pln,
    parse_pln,
)
from navixav.planner.engine import CompletionEngine
from navixav.preferences import AirportPreferences
from navixav.web.app import create_app

DATA_DIR = Path(__file__).parent / "data"
PLN = DATA_DIR / "msfs_lfst_lfbo.pln"

METAR_LFST = "LFST 260730Z 05008KT CAVOK 18/09 Q1020"
METAR_LFBO = "LFBO 260730Z 32010KT CAVOK 21/11 Q1018"


@pytest.fixture(scope="module")
def pln():
    return load_pln(PLN)


# --------------------------------------------------------------------------- #
# Lecture du fichier
# --------------------------------------------------------------------------- #


def test_airports_altitude_and_positions(pln):
    assert pln.plan_source == "msfs"
    assert pln.origin_icao == "LFST"
    assert pln.destination_icao == "LFBO"
    assert pln.cruise_altitude_ft == 34000
    assert pln.alternate_icao is None
    assert (pln.origin_lat, pln.origin_lon) == pytest.approx((48.538056, 7.634722))
    assert (pln.destination_lat, pln.destination_lon) == pytest.approx(
        (43.628889, 1.363889)
    )


def test_planned_runways_come_from_the_departure_position_and_the_approach(pln):
    assert pln.origin_planned_runway == "05"
    assert pln.destination_planned_runway == "32R"


def test_procedures_and_connection_hints(pln):
    """Les noms de SID/STAR et leurs points de raccord, comme avec SimBrief."""
    assert pln.simbrief_sid == "EPIK8M"
    assert pln.simbrief_star == "AFRI8N"
    assert pln.sid_exit_hint == "EPIKO"
    assert pln.star_entry_hint == "AFRIC"


def test_enroute_route_keeps_airways_and_excludes_procedures(pln):
    assert pln.enroute_fixes == ["LIRKO", "MOKIP", "GERVA"]
    assert [leg["via"] for leg in pln.enroute_route] == ["DCT", "UN854", "UN854"]
    assert all("lat" in leg and "lon" in leg for leg in pln.enroute_route)


def test_route_text_reads_like_an_icao_route(pln):
    assert pln.route == "LFST EPIK8M LIRKO UN854 MOKIP GERVA AFRI8N LFBO"


def test_what_a_pln_does_not_carry_stays_empty(pln):
    """Ni dispatch, ni météo, ni avion : rien n'est inventé."""
    assert pln.dispatch.block_fuel is None
    assert pln.origin_metar is None
    assert pln.destination_metar is None
    assert pln.aircraft_icao == ""
    assert pln.airac == ""
    assert pln.generated_at is not None


def test_plan_fingerprint_follows_the_content_not_the_file_date(pln):
    """MSFS réécrit CustomFlight.PLN à chaque chargement : le journal de vol
    et le TOC retrouvé au redémarrage se reconnaissent au contenu du plan."""
    from navixav.msfs.flightplan import parse_pln

    text = PLN.read_text(encoding="utf-8")
    assert pln.plan_fingerprint
    assert parse_pln(text).plan_fingerprint == pln.plan_fingerprint
    other = parse_pln(text.replace("<CruisingAlt>", "<CruisingAlt>1"))
    assert other.plan_fingerprint != pln.plan_fingerprint


def test_the_procedure_name_on_the_airport_never_becomes_a_connection_hint():
    text = PLN.read_text(encoding="utf-8")
    # Sans point de SID, le terrain reste le seul à nommer EPIK8M.
    for ident in ("D308M", "EPIKO"):
        start = text.index(f'<ATCWaypoint id="{ident}">')
        end = text.index("</ATCWaypoint>", start) + len("</ATCWaypoint>")
        text = text[:start] + text[end:]
    summary = parse_pln(text)
    assert summary.simbrief_sid == "EPIK8M"
    assert summary.sid_exit_hint is None
    assert summary.enroute_fixes == ["LIRKO", "MOKIP", "GERVA"]


def test_a_gate_as_departure_position_leaves_the_runway_to_the_sid():
    text = PLN.read_text(encoding="utf-8").replace(
        "<DeparturePosition>05</DeparturePosition>",
        "<DeparturePosition>GATE 12</DeparturePosition>",
    )
    assert parse_pln(text).origin_planned_runway == "05"


def test_a_plan_without_procedure_is_a_plain_direct_route():
    text = """<?xml version="1.0"?>
<SimBase.Document Type="AceXML" version="1,0">
  <FlightPlan.FlightPlan>
    <FPType>IFR</FPType>
    <CruisingAlt>9000</CruisingAlt>
    <DepartureID>LFPO</DepartureID>
    <DepartureLLA>N48° 43' 24.00",E2° 22' 46.00",+000291.00</DepartureLLA>
    <DestinationID>LFPG</DestinationID>
    <DestinationLLA>N49° 0' 35.00",E2° 32' 52.00",+000392.00</DestinationLLA>
    <ATCWaypoint id="LFPO"><ATCWaypointType>Airport</ATCWaypointType>
      <WorldPosition>N48° 43' 24.00",E2° 22' 46.00",+000291.00</WorldPosition></ATCWaypoint>
    <ATCWaypoint id="LFPG"><ATCWaypointType>Airport</ATCWaypointType>
      <WorldPosition>N49° 0' 35.00",E2° 32' 52.00",+000392.00</WorldPosition></ATCWaypoint>
  </FlightPlan.FlightPlan>
</SimBase.Document>"""
    summary = parse_pln(text)
    assert (summary.origin_icao, summary.destination_icao) == ("LFPO", "LFPG")
    assert summary.enroute_fixes == []
    assert summary.route == "LFPO LFPG"
    assert summary.simbrief_sid is None
    assert summary.origin_planned_runway is None


def test_southern_and_western_hemispheres_are_signed():
    text = """<SimBase.Document><FlightPlan.FlightPlan>
    <DepartureID>SCEL</DepartureID>
    <DepartureLLA>S33° 23' 34.00",W70° 47' 8.00",+001555.00</DepartureLLA>
    <DestinationID>SAEZ</DestinationID>
    <DestinationLLA>S34° 49' 20.00",W58° 32' 9.00",+000067.00</DestinationLLA>
    </FlightPlan.FlightPlan></SimBase.Document>"""
    summary = parse_pln(text)
    assert summary.origin_lat < 0 and summary.origin_lon < 0
    assert summary.destination_lat == pytest.approx(-34.822222)


def test_a_file_that_is_not_a_plan_is_refused_with_its_name(tmp_path):
    bogus = tmp_path / "notes.pln"
    bogus.write_text("<SimBase.Document></SimBase.Document>", encoding="utf-8")
    with pytest.raises(MsfsPlanError, match="notes.pln"):
        load_pln(bogus)
    broken = tmp_path / "broken.pln"
    broken.write_text("<not xml", encoding="utf-8")
    with pytest.raises(MsfsPlanError, match="broken.pln"):
        load_pln(broken)
    with pytest.raises(MsfsPlanError):
        load_pln(tmp_path / "missing.pln")


def test_a_plan_without_both_airports_is_refused():
    with pytest.raises(MsfsPlanError, match="départ et d'arrivée"):
        parse_pln(
            "<SimBase.Document><FlightPlan.FlightPlan>"
            "<DepartureID>LFPO</DepartureID>"
            "</FlightPlan.FlightPlan></SimBase.Document>"
        )


# --------------------------------------------------------------------------- #
# Le vol courant de MSFS
# --------------------------------------------------------------------------- #


def test_the_most_recent_current_flight_wins(tmp_path):
    store = tmp_path / "store" / "CustomFlight.PLN"
    steam = tmp_path / "steam" / "CustomFlight.PLN"
    for path in (store, steam):
        path.parent.mkdir()
        path.write_text("x", encoding="utf-8")
    import os

    os.utime(store, (1_000, 1_000))
    os.utime(steam, (2_000, 2_000))
    assert current_flight_plan([store, steam, tmp_path / "absent.PLN"]) == steam
    assert current_flight_plan([tmp_path / "absent.PLN"]) is None


# --------------------------------------------------------------------------- #
# Réglages
# --------------------------------------------------------------------------- #


def test_the_plan_source_setting_is_validated_and_persisted():
    base = Settings()
    assert base.plan_source == "simbrief"
    assert base.plan_configured is False

    msfs = base.with_user_values({"plan_source": "msfs"})
    assert msfs.plan_source == "msfs"
    assert msfs.plan_configured is True
    assert msfs.user_values()["plan_source"] == "msfs"

    # Un plan MSFS n'apporte pas de météo : la source en direct s'impose.
    assert msfs.effective_metar_source == "live"
    assert base.effective_metar_source == "simbrief"

    assert base.with_user_values({"plan_source": "navigraph"}).plan_source == "simbrief"


# --------------------------------------------------------------------------- #
# Moteur : le même panneau qu'avec l'OFP SimBrief
# --------------------------------------------------------------------------- #


@pytest.fixture
def offline_weather(monkeypatch):
    """Un plan MSFS n'a pas de METAR : le moteur va le chercher, pas les tests."""
    metars = {"LFST": METAR_LFST, "LFBO": METAR_LFBO}
    monkeypatch.setattr(
        "navixav.planner.engine.fetch_metar", lambda icao: metars.get(icao)
    )
    monkeypatch.setattr(
        "navixav.weather.briefing.fetch_metar", lambda icao: metars.get(icao)
    )
    monkeypatch.setattr("navixav.weather.briefing.fetch_taf", lambda icao: None)


def test_the_engine_completes_a_msfs_plan_like_a_simbrief_one(
    provider, pln, offline_weather
):
    settings = Settings(plan_source="msfs")
    engine = CompletionEngine(provider, settings, AirportPreferences.load())
    plan = engine.complete(pln)

    assert plan.source["plan_source"] == "msfs"
    assert plan.source["simbrief"] is False
    assert plan.departure.icao == "LFST"
    assert plan.departure.runway.choice.value == "05"
    assert plan.departure.sid.value == "EPIK8M"
    assert plan.departure.sid.confidence is Confidence.HIGH
    assert plan.arrival.icao == "LFBO"
    assert plan.arrival.star.value == "AFRI8N"
    assert plan.arrival.runway.choice.value == "32R"
    assert [leg["to"] for leg in plan.enroute.route_legs] == ["LIRKO", "MOKIP", "GERVA"]
    assert plan.enroute.route_path[0]["ident"] == "LFST"
    assert plan.enroute.route_path[-1]["ident"] == "LFBO"
    # La météo est venue du réseau, faute d'OFP pour la porter.
    assert plan.departure.wind.raw_metar == METAR_LFST


# --------------------------------------------------------------------------- #
# Service web
# --------------------------------------------------------------------------- #


def test_status_reports_the_plan_source_and_the_current_msfs_file(monkeypatch):
    monkeypatch.setattr("navixav.web.app.current_flight_plan", lambda: PLN)
    client = TestClient(create_app(Settings(plan_source="msfs")))
    status = client.get("/api/status").json()
    assert status["plan_source"] == "msfs"
    assert status["plan_configured"] is True
    assert status["simbrief_configured"] is False
    assert status["msfs_plan_file"] == PLN.name
    assert status["metar_source"] == "live"


def test_without_a_msfs_plan_the_service_says_what_to_do(monkeypatch):
    monkeypatch.setattr("navixav.web.app.current_flight_plan", lambda: None)
    client = TestClient(create_app(Settings(plan_source="msfs")))
    response = client.post("/api/plan", json={})
    assert response.status_code == 404
    assert ".PLN" in response.json()["detail"]


def test_the_file_picker_needs_the_desktop_window_and_a_confirmation():
    client = TestClient(create_app(Settings(plan_source="msfs")))
    assert client.post("/api/plan/select-file").status_code == 403
    response = client.post(
        "/api/plan/select-file", headers={"X-NaviXav-Plan": "browse"}
    )
    assert response.status_code == 409


def test_a_picked_file_is_kept_for_the_session(monkeypatch):
    monkeypatch.setattr("navixav.web.app.current_flight_plan", lambda: None)
    app = create_app(Settings(plan_source="msfs"))
    app.state.request_plan_file = lambda current: str(PLN)
    client = TestClient(app)

    response = client.post(
        "/api/plan/select-file", headers={"X-NaviXav-Plan": "browse"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "selected_file": PLN.name,
        "origin": "LFST",
        "destination": "LFBO",
    }
    assert client.get("/api/status").json()["msfs_plan_file"] == PLN.name


def test_a_cancelled_picker_changes_nothing():
    app = create_app(Settings(plan_source="msfs"))
    app.state.request_plan_file = lambda current: None
    client = TestClient(app)
    response = client.post(
        "/api/plan/select-file", headers={"X-NaviXav-Plan": "browse"}
    )
    assert response.json() == {"cancelled": True}


def test_a_picked_file_that_is_not_a_plan_is_refused(tmp_path):
    bogus = tmp_path / "bogus.pln"
    bogus.write_text("<SimBase.Document/>", encoding="utf-8")
    app = create_app(Settings(plan_source="msfs"))
    app.state.request_plan_file = lambda current: str(bogus)
    client = TestClient(app)
    response = client.post(
        "/api/plan/select-file", headers={"X-NaviXav-Plan": "browse"}
    )
    assert response.status_code == 422
    assert "bogus.pln" in response.json()["detail"]


# --------------------------------------------------------------------------- #
# Interface
# --------------------------------------------------------------------------- #


def test_the_interface_offers_the_plan_source_in_every_language():
    """Le choix existe aux réglages et au premier lancement, dans les huit langues."""
    static = Path(__file__).parent.parent / "navixav" / "web" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    translations = (static / "i18n.js").read_text(encoding="utf-8")

    assert html.count('<option value="msfs">') == 2, "réglages et premier lancement"
    assert 'id="msfs-plan-open"' in html
    assert 'id="settings-msfs-plan-help"' in html
    for key in (
        "plan_source:", "plan_source_msfs:", "msfs_plan_open:", "no_msfs_plan:",
        "welcome_msfs_help:", "settings_msfs_plan_help:", "loading_plan_msfs:",
    ):
        assert translations.count(key) == 8, key

    # Le plan MSFS n'exige aucun identifiant SimBrief au premier lancement,
    # et un seul bouton d'entrée reste visible selon la source.
    assert 'return !window.I18N.hasLanguage() || !status.plan_configured;' in javascript
    assert 'show($("simbrief-create"), !msfsPlan && !status.remote_client);' in javascript
    assert 'show($("msfs-plan-open"), msfsPlan && !status.remote_client);' in javascript
    assert '"X-NaviXav-Plan": "browse"' in javascript
