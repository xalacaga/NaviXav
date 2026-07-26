import pytest
from pydantic import ValidationError

from navixav.config import Settings, load_user_settings, save_user_settings
from navixav.web.app import SettingsRequest


def test_user_settings_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    configured = Settings().with_user_values(
        {
            "simbrief_pilot_id": "123456",
            "simbrief_username": "xavier",
            "metar_source": "live",
            "approach_preference": ["ILS", "RNAV"],
            "max_tailwind_kt": 8,
            "max_crosswind_kt": 28,
            "min_runway_length_ft": 5000,
            "aircraft_rnp_capable": False,
        }
    )

    save_user_settings(configured, path)
    restored = load_user_settings(Settings(), path)

    assert restored.simbrief_pilot_id == "123456"
    assert restored.simbrief_username == "xavier"
    assert restored.approach_preference == ("ILS", "RNAV")
    assert restored.aircraft_rnp_capable is False


def test_settings_request_accepts_interface_values():
    request = SettingsRequest(
        simbrief_pilot_id="654321",
        approach_preference=["ILS", "GLS", "RNAV"],
        min_runway_length_ft=4500,
    )

    assert request.simbrief_pilot_id == "654321"
    assert request.min_runway_length_ft == 4500


def test_settings_request_rejects_invalid_limits():
    with pytest.raises(ValidationError):
        SettingsRequest(max_tailwind_kt=-1)
