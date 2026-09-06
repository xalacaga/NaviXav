from unittest.mock import patch

import pytest
from fastapi import HTTPException

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
