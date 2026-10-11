"""Carnet de vol tenu par le service : stockage, reprise, statistiques, export."""

from __future__ import annotations

import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from navixav.config import Settings
from navixav.logbook import LogbookStore, logbook_csv, logbook_stats
from navixav.web.app import create_app


def flight(identifier, ended_at, *, dep="LFPO", arr="EGLL", aircraft="Fenix A320",
           duration=3600, distance=200.0, landing=None):
    entry = {
        "id": identifier,
        "departure": dep,
        "arrival": arr,
        "callsign": "AFR1",
        "aircraft": aircraft,
        "started_at": "2026-10-11T08:00:00Z",
        "ended_at": ended_at,
        "duration_seconds": duration,
        "distance_nm": distance,
        "max_altitude_ft": 35000,
    }
    if landing is not None:
        entry["landing"] = landing
    return entry


def landing(rate, score, runway="27L"):
    return {"rate_fpm": rate, "score": score, "grade": "smooth", "airport": "EGLL",
            "runway": runway, "touched_down_at": "2026-10-11T09:00:00Z",
            "distance_from_threshold_m": 400, "centerline_offset_m": -1.5, "bounces": 0}


def test_entries_survive_a_new_store_and_stay_sorted(tmp_path):
    path = tmp_path / "logbook.json"
    LogbookStore(path).replace([
        flight("a", "2026-10-01T10:00:00Z"),
        flight("b", "2026-10-03T10:00:00Z"),
        flight("a", "2026-10-02T10:00:00Z"),  # doublon ignoré
        {"no": "id"},
    ])
    reopened = LogbookStore(path).entries()
    assert [entry["id"] for entry in reopened] == ["b", "a"]
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1
    assert not (tmp_path / "logbook.tmp").exists()


def test_merge_keeps_known_entries_and_adds_new_ones(tmp_path):
    store = LogbookStore(tmp_path / "logbook.json")
    store.replace([flight("a", "2026-10-01T10:00:00Z", landing=landing(150, 90))])
    store.merge([flight("a", "2026-10-01T10:00:00Z"), flight("c", "2026-10-05T10:00:00Z")])
    entries = store.entries()
    assert [entry["id"] for entry in entries] == ["c", "a"]
    assert entries[1]["landing"]["score"] == 90


def test_an_unreadable_file_is_set_aside_not_overwritten(tmp_path):
    path = tmp_path / "logbook.json"
    path.write_text("{ broken", encoding="utf-8")
    store = LogbookStore(path)
    assert store.entries() == []
    assert (tmp_path / "logbook.corrupt.json").read_text(encoding="utf-8") == "{ broken"


def test_stats_total_landings_aircraft_and_airports():
    stats = logbook_stats([
        flight("a", "1", landing=landing(220, 80)),
        flight("b", "2", dep="EGLL", arr="LFPO", landing=landing(140, 95, runway="06")),
        flight("c", "3", aircraft="PMDG 737", dep="LFPO", arr="LFMN", duration=5400, distance=370),
    ])
    assert stats["flights"] == 3
    assert stats["total_duration_seconds"] == 12600
    assert stats["total_distance_nm"] == 770
    assert stats["landings"]["count"] == 2
    assert stats["landings"]["average_rate_fpm"] == 180
    assert stats["landings"]["average_score"] == 88  # 87,5 arrondi au pair
    assert stats["landings"]["best"]["runway"] == "06"
    assert stats["aircraft"][0] == {"name": "Fenix A320", "flights": 2, "duration_seconds": 7200}
    assert stats["airports"][0] == {"icao": "LFPO", "visits": 3}


def test_aircraft_falls_back_to_the_landing_report_for_older_flights():
    entry = flight("a", "1", aircraft="", landing={**landing(200, 80), "aircraft": "TBM 930"})
    assert logbook_stats([entry])["aircraft"][0]["name"] == "TBM 930"


def test_csv_has_one_row_per_flight_and_a_bom_for_excel():
    text = logbook_csv([flight("a", "2026-10-01T10:00:00Z", landing=landing(150, 90))])
    assert text.startswith("﻿")
    rows = list(csv.DictReader(io.StringIO(text[1:])))
    assert rows[0]["arrival"] == "EGLL"
    assert rows[0]["duration_minutes"] == "60"
    assert rows[0]["touchdown_rate_fpm"] == "150"
    assert rows[0]["centerline_offset_m"] == "-1.5"


# --------------------------------------------------------------------------- #
# Service


@pytest.fixture
def store(tmp_path):
    return LogbookStore(tmp_path / "logbook.json")


def _client(store, host="127.0.0.1"):
    app = create_app(Settings(metar_source="simbrief", lan_enabled=True), logbook=store)
    return app, TestClient(app, client=(host, 50000))


def test_the_pc_writes_imports_and_clears_the_logbook(store):
    _app, client = _client(store)
    assert client.get("/api/logbook").json()["stats"]["flights"] == 0

    saved = client.put("/api/logbook", json={"entries": [flight("a", "2026-10-01T10:00:00Z")]})
    assert saved.json()["stats"]["flights"] == 1

    imported = client.post("/api/logbook/import", json={"entries": [
        flight("a", "x"), flight("old", "2026-09-01T10:00:00Z"),
    ]})
    assert [entry["id"] for entry in imported.json()["entries"]] == ["a", "old"]

    assert client.delete("/api/logbook").json()["entries"] == []
    assert store.entries() == []


def test_a_tablet_reads_the_same_logbook_but_cannot_change_it(store):
    store.replace([flight("a", "2026-10-01T10:00:00Z")])
    _app, tablet = _client(store, host="192.168.1.20")
    assert tablet.get("/api/logbook").json()["entries"][0]["id"] == "a"
    assert tablet.get("/api/logbook.csv").status_code == 200
    assert tablet.put("/api/logbook", json={"entries": []}).status_code == 403
    assert tablet.delete("/api/logbook").status_code == 403
    assert tablet.post("/api/logbook/import", json={"entries": []}).status_code == 403
    assert tablet.post("/api/logbook/export", headers={"X-NaviXav-Logbook": "export"}).status_code == 403
    assert len(store.entries()) == 1


def test_export_writes_the_csv_where_the_pilot_chose(store, tmp_path):
    store.replace([flight("a", "2026-10-01T10:00:00Z")])
    app, client = _client(store)
    assert client.post("/api/logbook/export").status_code == 403
    assert client.post("/api/logbook/export", headers={"X-NaviXav-Logbook": "export"}).status_code == 409

    app.state.request_logbook_export_path = lambda name: str(tmp_path / "mine")
    response = client.post("/api/logbook/export", headers={"X-NaviXav-Logbook": "export"})
    assert response.json() == {"saved": True, "file": "mine.csv"}
    assert "EGLL" in (tmp_path / "mine.csv").read_text(encoding="utf-8")


def test_a_malformed_body_is_refused(store):
    _app, client = _client(store)
    assert client.put("/api/logbook", json={"entries": "nope"}).status_code == 422
