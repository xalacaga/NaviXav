"""Le plan actif du FMGC Fenix, lu par la passerelle locale de son EFB."""

from __future__ import annotations

from pathlib import Path

import pytest

from navixav.config import Settings
from navixav.live import fenix_fms
from navixav.live.fenix_fms import FenixFmsReader, parse_flight_plan_xml, parse_mcdu_display
from navixav.web.app import create_app

FIXTURE = Path(__file__).parent / "data" / "fenix_fms_lfpo_dtta.xml"


@pytest.fixture
def plan():
    return parse_flight_plan_xml(FIXTURE.read_text(encoding="utf-8"), phase="Cruise")


def test_the_active_route_stops_at_the_end_of_flight_plan(plan):
    assert plan.origin == "LFPO"
    assert plan.destination == "DTTA"
    assert plan.destination_runway == "29"
    assert plan.cruise_level_ft == 34000
    assert plan.flight_number == "ABF059"
    assert [leg.ident for leg in plan.legs] == [
        "(T/C)", "BALSI", "(T/D)", "SONAK", "(LIM)", "(DECEL)",
        "BAVRA", "FF29", "DTTA29", "3100", "MARSA",
    ]
    assert plan.legs[1].via == "UY156"
    assert plan.legs[1].distance_nm == 40


def test_the_alternate_plan_is_kept_apart_with_its_discontinuities(plan):
    assert [leg.ident for leg in plan.alternate_legs][:3] == ["DTTA", "GIBLI", "VAXAL"]
    assert plan.alternate_legs[-1].ident == "DTTJ"
    # Une discontinuité précède GIBLI et DTTJ dans le plan de dégagement.
    assert plan.alternate_legs[1].after_discontinuity
    assert plan.alternate_legs[-1].after_discontinuity
    assert not plan.alternate_legs[0].after_discontinuity


def test_pseudo_points_are_flagged_and_lines_without_position_carry_none(plan):
    assert [leg.ident for leg in plan.legs if leg.pseudo] == ["(T/C)", "(T/D)", "(LIM)", "(DECEL)"]
    assert all(leg.lat is not None for leg in plan.legs)


def test_the_turning_point_of_a_direct_to_is_not_a_published_fix():
    xml = FIXTURE.read_text(encoding="utf-8").replace(
        "<displayString>(T/C)</displayString>", "<displayString>T-P</displayString>"
    ).replace("<type>TopOfClimb</type>", "<type>TurningPoint</type>")

    plan = parse_flight_plan_xml(xml)

    assert plan.legs[0].ident == "T-P"
    assert plan.legs[0].pseudo


def test_toc_and_tod_carry_their_distance_along_the_legs(plan):
    data = plan.to_dict()

    assert data["available"] is True
    # Première ligne : le point FROM, déjà séquencé. Le point actif est BALSI.
    assert data["from"]["ident"] == "(T/C)"
    assert data["active"]["ident"] == "BALSI"
    # Un T/C déjà séquencé n'est plus devant l'avion.
    assert data["toc"] is None
    # BALSI est à 40 NM de l'avion selon le FMGC, le T/D 420 NM plus loin.
    assert data["tod"] == {
        "ident": "(T/D)", "lat": 37.1, "lon": 11.6, "to_distance_nm": 40.0,
        "distance_from_active_nm": 420.0, "index": 2,
    }


def test_a_plan_without_route_or_malformed_xml_is_unavailable():
    assert parse_flight_plan_xml("<fms><cruiseLevel>1</cruiseLevel></fms>") is None
    assert parse_flight_plan_xml("not xml") is None


def test_the_reader_tolerates_a_missing_gateway_and_retries_slowly():
    probes = []

    def listening():
        probes.append(True)
        return False

    reader = FenixFmsReader(reader=lambda: {}, listening=listening)

    first = reader.read()
    second = reader.read()

    assert first == {"available": False, "source": "fenix", "reason": "gateway_unavailable"}
    assert second == first
    assert len(probes) == 1


def test_the_reader_merges_gateway_values_and_serves_the_plan(monkeypatch):
    xml = FIXTURE.read_text(encoding="utf-8")
    values = {
        "aircraft.fms.flightPlanXml": xml,
        "aircraft.fms.flightPhase": "Cruise",
        "aircraft.fms.alternate": "DTTJ",
    }
    reader = FenixFmsReader(reader=lambda: values, listening=lambda: True)

    data = reader.read()

    assert data["available"] is True
    assert data["alternate"] == "DTTJ"
    assert data["phase"] == "Cruise"
    assert data["tod"]["ident"] == "(T/D)"


def test_a_gateway_error_makes_the_plan_unavailable_without_raising():
    def failing():
        raise RuntimeError("HC0046")

    reader = FenixFmsReader(reader=failing, listening=lambda: True)

    assert reader.read()["available"] is False


def test_the_reader_never_writes_to_the_gateway():
    source = Path(fenix_fms.__file__).read_text(encoding="utf-8")

    assert "mutation" not in source.lower().replace("aucune n'est jamais", "")
    assert "write" not in source.split("def read_datarefs")[1].split("class FenixFmsReader")[0]


def test_the_fms_endpoint_serves_the_reader():
    from navixav.live.fms_hub import FmsHub

    reader = FenixFmsReader(reader=lambda: {}, listening=lambda: False)
    app = create_app(Settings(), fms_reader=FmsHub([reader]))
    endpoint = next(route.endpoint for route in app.routes if route.path == "/api/fms")

    assert endpoint()["available"] is False
    app.state.close_resources()


def test_speed_limit_and_deceleration_points_are_served_with_their_distance(plan):
    data = plan.to_dict()

    assert data["speed_limit"]["ident"] == "(LIM)"
    assert data["speed_limit"]["to_distance_nm"] == 40.0
    # BALSI → T/D 420, T/D → SONAK 30, SONAK → (LIM) 29.3.
    assert data["speed_limit"]["distance_from_active_nm"] == 479.3
    assert data["decel"]["ident"] == "(DECEL)"
    assert data["destination_eta"] == "1000"


def test_the_mcdu_display_is_split_into_coloured_segments():
    display = parse_mcdu_display(
        "<root><title> sFROMl          sABF059l \u00a3\u00a2</title>"
        "<line>gSONAK  wg 0944w g s272ll/l FL185w</line>"
        "<line>s        gw          g11w    </line>"
        "<scratchpad>aENTER DEST DATAw        \u00a4</scratchpad></root>"
    )

    assert display["title"][0] == {"text": "FROM", "color": "white", "size": "small"}
    assert display["title"][-1]["text"] == " \u2191\u2193"
    sonak = display["lines"][0]
    assert sonak[0] == {"text": "SONAK  ", "color": "green", "size": "large"}
    assert any(segment["text"] == "272" and segment["size"] == "small" for segment in sonak)
    assert display["scratchpad"][0] == {"text": "ENTER DEST DATA", "color": "amber", "size": "large"}
    assert parse_mcdu_display("not xml") is None


def test_the_reader_carries_takeoff_perf_weights_and_mcdu_screens():
    xml = FIXTURE.read_text(encoding="utf-8")
    values = {
        "aircraft.fms.flightPlanXml": xml,
        "aircraft.fms.flightPhase": "Cruise",
        "aircraft.fms.perf.takeOff.v1": 137,
        "aircraft.fms.perf.takeOff.vr": 138,
        "aircraft.fms.perf.takeOff.v2": 142,
        "aircraft.fms.perf.takeOff.flaps": 3,
        "aircraft.fms.perf.takeOff.flexTemp": 0,
        "aircraft.weight.zfw": 62491.4,
        "aircraft.weight.gross": 66528.9,
        "aircraft.fuel.total.amount.kg": 4037.4,
        "fenix.cids.flightNumber": "ABF059",
        "aircraft.mcdu1.display": "<root><title>gTEST</title><line>a1</line></root>",
        "aircraft.mcdu2.display": None,
    }
    reader = FenixFmsReader(reader=lambda: values, listening=lambda: True)

    data = reader.read()

    assert data["perf_takeoff"] == {
        "v1": 137.0, "vr": 138.0, "v2": 142.0, "flaps": 3.0, "flexTemp": None, "ths": None,
    }
    assert data["weights"]["zfw_kg"] == 62491.4
    assert data["weights"]["fuel_kg"] == 4037.4
    assert data["flight_number"] == "ABF059"
    assert list(data["mcdu"]) == ["1"]
    assert data["mcdu"]["1"]["lines"][0][0]["color"] == "amber"


def test_the_origin_runway_is_read_when_the_fmgc_still_has_it():
    xml = FIXTURE.read_text(encoding="utf-8").replace(
        "<originRunway></originRunway>", "<originRunway>26</originRunway>"
    )

    plan = parse_flight_plan_xml(xml)

    assert plan.origin_runway == "26"
    assert plan.to_dict()["origin_runway"] == "26"
