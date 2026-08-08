import pytest
from pydantic import ValidationError

from navixav.config import (
    MAP_BASEMAPS,
    Settings,
    load_user_settings,
    save_user_settings,
)
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
            "map_basemap": "opentopo",
            "map_trail_color": "#ff5500",
            "aircraft_community_path": str(tmp_path / "Community"),
            "lan_enabled": True,
        }
    )

    save_user_settings(configured, path)
    restored = load_user_settings(Settings(), path)

    assert restored.simbrief_pilot_id == "123456"
    assert restored.simbrief_username == "xavier"
    assert restored.approach_preference == ("ILS", "RNAV")
    assert restored.aircraft_rnp_capable is False
    assert restored.map_basemap == "opentopo"
    assert restored.map_trail_color == "#ff5500"
    assert restored.aircraft_community_path == tmp_path / "Community"
    assert restored.lan_enabled is True
    # Aucun jeton n'est généré : l'accès mobile repose sur le seul lien local.
    assert not hasattr(restored, "lan_access_token")


def test_settings_request_accepts_interface_values():
    request = SettingsRequest(
        simbrief_pilot_id="654321",
        approach_preference=["ILS", "GLS", "RNAV"],
        min_runway_length_ft=4500,
        map_basemap="opentopo",
        map_trail_color="#AABBCC",
        aircraft_community_path=r"D:\MSFS\Community",
        lan_enabled=True,
    )

    assert request.simbrief_pilot_id == "654321"
    assert request.min_runway_length_ft == 4500
    assert request.map_basemap == "opentopo"
    assert request.aircraft_community_path == r"D:\MSFS\Community"
    assert request.lan_enabled is True


@pytest.mark.parametrize("basemap", sorted(MAP_BASEMAPS))
def test_every_basemap_survives_both_validation_paths(basemap, tmp_path):
    """Les fonds proposés dans l'interface doivent passer l'API et le disque."""
    assert SettingsRequest(map_basemap=basemap).map_basemap == basemap

    path = tmp_path / "settings.json"
    save_user_settings(Settings().with_user_values({"map_basemap": basemap}), path)

    assert load_user_settings(Settings(), path).map_basemap == basemap


def test_settings_request_rejects_invalid_limits():
    with pytest.raises(ValidationError):
        SettingsRequest(max_tailwind_kt=-1)
    with pytest.raises(ValidationError):
        SettingsRequest(map_basemap="proprietary")
    with pytest.raises(ValidationError):
        SettingsRequest(map_trail_color="red")
