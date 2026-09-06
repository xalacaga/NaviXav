from unittest.mock import patch

import pytest
from fastapi import HTTPException

from navixav.config import Settings
from navixav.live import LiveTracker, PositionUnavailable
from navixav.traffic.service import TrafficService
from navixav.web.app import create_app


def test_taxi_api_distinguishes_failed_read_from_confirmed_empty_traffic():
    with patch.object(TrafficService, "configure"), patch.object(LiveTracker, "traffic") as read:
        app = create_app(Settings(traffic_enabled=True))
        try:
            endpoint = next(route.endpoint for route in app.routes if route.path == "/api/live/traffic")
            read.side_effect = PositionUnavailable("Temporary failure")
            with pytest.raises(HTTPException) as error:
                endpoint()
            assert error.value.status_code == 503
            read.assert_called_once_with(strict=True)
            read.side_effect = None
            read.return_value = []
            assert endpoint() == {"enabled": True, "traffic": []}
        finally:
            app.state.close_resources()
