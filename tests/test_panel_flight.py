from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from navixav.config import Settings
from navixav.traffic.service import TrafficService
from navixav.web.app import PanelFlightSummary, create_app


def test_panel_snapshot_expires_and_rejects_wrong_plan_revision():
    with patch.object(TrafficService, "configure"):
        app = create_app(Settings(traffic_enabled=False))
    endpoints = {route.path: route.endpoint for route in app.routes if hasattr(route, "endpoint")}
    try:
        state = endpoints["/api/panel/state"]
        publish = endpoints["/api/panel/flight"]
        assert state()["flight"]["connected"] is False
        with patch("navixav.web.app.time.monotonic", return_value=1000):
            publish(PanelFlightSummary(connected=True, route="LFPG → EHAM",
                                      values={"flight-next-fix": "LGL"}))
            assert state()["flight"]["connected"] is True
            assert state()["flight"]["values"]["flight-next-fix"] == "LGL"
        with patch("navixav.web.app.time.monotonic", return_value=1011):
            assert state()["flight"]["fresh"] is False
            assert state()["flight"]["connected"] is False
        with pytest.raises(HTTPException) as error:
            publish(PanelFlightSummary(revision=1))
        assert error.value.status_code == 409
        publish(PanelFlightSummary(connected=False))
        assert state()["flight"]["connected"] is False
    finally:
        app.state.close_resources()

def test_panel_receives_active_alerts_and_rejects_unknown_severities():
    with patch.object(TrafficService, "configure"):
        app = create_app(Settings(traffic_enabled=False))
    endpoints = {route.path: route.endpoint for route in app.routes if hasattr(route, "endpoint")}
    try:
        publish(endpoints, PanelFlightSummary(
            connected=True,
            values={"flight-stability": "GEAR · V/S -1400"},
            alerts=[{"severity": "danger", "text": "Unstable approach · GEAR · V/S -1400"},
                    {"severity": "warning", "text": "SIGMET ahead · SEV TURB · FL250–FL390"}],
        ))
        flight = endpoints["/api/panel/state"]()["flight"]
        assert [alert["severity"] for alert in flight["alerts"]] == ["danger", "warning"]
        assert flight["values"]["flight-stability"] == "GEAR · V/S -1400"
        with pytest.raises(ValidationError):
            PanelFlightSummary(alerts=[{"severity": "panic", "text": "x"}])
        with pytest.raises(ValidationError):
            PanelFlightSummary(alerts=[{"severity": "info", "text": "x"}] * 7)
    finally:
        app.state.close_resources()


def publish(endpoints, summary):
    with patch("navixav.web.app.time.monotonic", return_value=1000):
        endpoints["/api/panel/flight"](summary)
