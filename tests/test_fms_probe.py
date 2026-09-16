"""La sonde FMS relève les deux canaux sans rien écrire dans l'avion."""

from __future__ import annotations

import json

import pytest

from navixav import fms_probe
from navixav.cli import build_parser


def test_gateway_absent_gives_an_empty_but_valid_report(monkeypatch):
    monkeypatch.setattr(fms_probe, "gateway_listening", lambda *_a, **_k: False)

    report = fms_probe.probe_fenix_gateway()

    assert report["listening"] is False
    assert report["values"] == {}
    assert report["error"] is None


def test_gateway_values_are_read_through_readonly_queries(monkeypatch):
    monkeypatch.setattr(fms_probe, "gateway_listening", lambda *_a, **_k: True)
    queries: list[str] = []

    def fake_graphql(query, variables=None, timeout_s=10.0):
        queries.append(query)
        if "list" in query:
            return {"dataRef": {"list": [
                {"name": "aircraft.fms.origin", "canRead": True, "canWrite": False},
                {"name": "aircraft.fms.flightPlanXml", "canRead": True, "canWrite": False},
                {"name": "aircraft.fms.init.zfw", "canRead": False, "canWrite": True},
            ]}}
        assert "aircraft.fms.init.zfw" not in variables["names"]
        return {"dataRef": {"dataRefs": [
            {"name": "aircraft.fms.origin", "value": "LFST"},
            {"name": "aircraft.fms.flightPlanXml", "value": "<fms><leg/></fms>"},
        ]}}

    monkeypatch.setattr(fms_probe, "_graphql", fake_graphql)

    report = fms_probe.probe_fenix_gateway()

    assert report["values"]["aircraft.fms.origin"] == "LFST"
    assert len(report["datarefs"]) == 3
    # Aucune mutation : la sonde ne fait que des requêtes de lecture.
    assert all("mutation" not in query for query in queries)


def test_gateway_error_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(fms_probe, "gateway_listening", lambda *_a, **_k: True)

    def failing(*_a, **_k):
        raise RuntimeError("Introspection is not allowed")

    monkeypatch.setattr(fms_probe, "_graphql", failing)

    report = fms_probe.probe_fenix_gateway()

    assert "Introspection" in report["error"]


def test_report_is_written_as_json_in_the_diagnostics_folder(tmp_path):
    report = {"probed_at": "now", "fenix_gateway": {"listening": False}, "simconnect_gps": {}}

    path = fms_probe.write_report(report, tmp_path / "diagnostics")

    assert path.parent == tmp_path / "diagnostics"
    assert path.name.startswith("fms_probe_") and path.suffix == ".json"
    assert json.loads(path.read_text(encoding="utf-8"))["probed_at"] == "now"


def test_summary_stays_short_and_never_prints_the_route():
    route = "<fms>" + "<leg><displayString>SONAK</displayString></leg>" * 3 + "</fms>"
    report = {
        "fenix_gateway": {
            "listening": True,
            "error": None,
            "datarefs": [{"canRead": True}, {"canRead": False}],
            "values": {
                "aircraft.fms.origin": "LFPO",
                "aircraft.fms.destination": "DTTA",
                "aircraft.fms.alternate": "DTTJ",
                "aircraft.fms.flightPhase": "Descent",
                "aircraft.fms.flightPlanXml": route,
                "aircraft.fms.perf.takeOff.v1": 137,
                "aircraft.fms.perf.takeOff.vr": 138,
                "aircraft.fms.perf.takeOff.v2": 142,
                "aircraft.mcdu1.display": "<root><line>a</line><line>b</line></root>",
            },
        },
        "simconnect_gps": {
            "connected": True,
            "refused": [],
            "values": {
                "GPS IS ACTIVE FLIGHT PLAN": 0.0,
                "GPS FLIGHT PLAN WP COUNT": 0.0,
                "GPS FLIGHT PLAN WP INDEX": 0.0,
                "GPS WP NEXT ID": "",
                "GPS WP DISTANCE": 0.0,
            },
        },
    }

    lines = fms_probe.summarize(report)
    text = "\n".join(lines)

    assert "LFPO -> DTTA" in text
    assert "3 segment(s)" in text
    assert "SONAK" not in text
    assert "2 ligne(s)" in text
    assert "0 point(s)" in text


def test_cli_knows_the_probe_command():
    args = build_parser().parse_args(["probe-fms", "--out", "somewhere"])

    assert args.command == "probe-fms"
    assert args.out == "somewhere"


@pytest.mark.live_msfs
def test_live_probe_runs_against_the_simulator():
    report = fms_probe.run_probe()

    assert report["simconnect_gps"]["connected"]
