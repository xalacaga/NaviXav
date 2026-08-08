from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from navixav.config import (
    DEFAULT_TAXI_SPEED_LIMIT_KT,
    DEFAULT_TAXI_TURN_SPEED_LIMIT_KT,
    MAP_BASEMAPS,
    Settings,
    load_user_settings,
    save_user_settings,
)
from navixav.web import app as web_app
from navixav.web.app import SettingsRequest, create_app


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
    with pytest.raises(ValidationError):
        SettingsRequest(taxi_speed_limit_kt=0)
    with pytest.raises(ValidationError):
        SettingsRequest(taxi_turn_speed_limit_kt=200)


def test_taxi_speed_limits_survive_both_validation_paths(tmp_path):
    path = tmp_path / "settings.json"
    request = SettingsRequest(
        taxi_speed_limit_kt=30,
        taxi_turn_speed_limit_kt=12,
        taxi_speed_alarm_sound=False,
    )

    save_user_settings(Settings().with_user_values(request.model_dump()), path)
    restored = load_user_settings(Settings(), path)

    assert restored.taxi_speed_limit_kt == 30
    assert restored.taxi_turn_speed_limit_kt == 12
    assert restored.taxi_speed_alarm_sound is False


def test_default_taxi_speed_limits_match_common_practice():
    """Ni règlement ni limite publiée : des valeurs par défaut ajustables."""
    settings = Settings()

    assert settings.taxi_speed_limit_kt == DEFAULT_TAXI_SPEED_LIMIT_KT == 25
    assert settings.taxi_turn_speed_limit_kt == DEFAULT_TAXI_TURN_SPEED_LIMIT_KT == 10
    assert settings.taxi_speed_alarm_sound is True


def test_a_turn_limit_never_exceeds_the_straight_limit():
    """Au-dessus de la limite en ligne droite, elle ne se déclencherait jamais."""
    configured = Settings().with_user_values(
        {"taxi_speed_limit_kt": 15, "taxi_turn_speed_limit_kt": 40}
    )

    assert configured.taxi_speed_limit_kt == 15
    assert configured.taxi_turn_speed_limit_kt == 15


@pytest.mark.parametrize(
    "raw, expected",
    [(0, 25), (-5, 25), (999, 60), ("", 25), (None, 25), ("18", 18)],
)
def test_an_unusable_taxi_speed_falls_back_or_clamps(raw, expected):
    """Une limite nulle éteindrait l'alarme sans le dire."""
    assert Settings().with_user_values(
        {"taxi_speed_limit_kt": raw}
    ).taxi_speed_limit_kt == expected


def test_taxi_speed_limits_reach_a_remote_client_through_the_status(monkeypatch):
    """Un téléphone ne lit pas /api/settings : sans cela il alerterait à 25 kt
    alors que l'hôte a réglé 18."""
    monkeypatch.setattr(
        web_app,
        "MsfsProvider",
        lambda store, allow_fetch=True: SimpleNamespace(
            source_name="test",
            airac_cycle="2401",
            supports_rnp_flag=True,
            has_ground_geometry=True,
            stats=lambda: {},
            reference_counts=lambda: {},
            close=lambda: None,
        ),
    )
    settings = Settings().with_user_values(
        {
            "taxi_speed_limit_kt": 18,
            "taxi_turn_speed_limit_kt": 8,
            "taxi_speed_alarm_sound": False,
        }
    )
    app = create_app(settings)
    endpoint = next(
        route.endpoint for route in app.routes if route.path == "/api/status"
    )

    payload = endpoint(
        SimpleNamespace(
            client=SimpleNamespace(host="192.168.1.42"),
            url=SimpleNamespace(port=8765),
        )
    )

    assert payload["remote_client"] is True
    assert payload["taxi_speed_limit_kt"] == 18
    assert payload["taxi_turn_speed_limit_kt"] == 8
    assert payload["taxi_speed_alarm_sound"] is False
