from unittest.mock import patch

import pytest

from navixav.config import Settings
from navixav.traffic.service import TrafficService
from navixav.web.app import SettingsRequest, create_app


def endpoint(app, path, method='GET'):
    return next(route.endpoint for route in app.routes
                if route.path == path and method in route.methods)


@pytest.mark.parametrize('source', ['vatsim', 'static'])
def test_unrelated_settings_and_repeated_panel_commands_keep_traffic(source):
    settings = Settings(traffic_enabled=True, traffic_source=source)
    with patch.object(TrafficService, 'configure') as configure, \
            patch('navixav.web.app.save_user_settings'):
        app = create_app(settings)
        try:
            assert configure.call_count == 1
            values = settings.user_values()
            values.update(map_trail_color='#123456', metar_source='live', taxi_speed_limit_kt=19)
            update = endpoint(app, '/api/settings', 'PUT')
            update(SettingsRequest(**values))
            endpoint(app, '/api/panel/traffic/{state}')('on')
            endpoint(app, '/api/panel/source/{name}')(source)
            assert configure.call_count == 1
            endpoint(app, '/api/panel/traffic/{state}')('off')
            endpoint(app, '/api/panel/traffic/{state}')('on')
            assert configure.call_count == 3
            endpoint(app, '/api/panel/source/{name}')('ivao')
            assert configure.call_count == 4
        finally:
            app.state.close_resources()


@pytest.mark.parametrize('source,change,expected', [
    ('vatsim', {'traffic_max_aircraft': 20}, 2),
    ('ivao', {'traffic_radius_nm': 20}, 2),
    ('static', {'traffic_max_aircraft': 20}, 2),
    ('static', {'traffic_radius_nm': 20}, 2),
    ('static', {'navdata_store': 'other.sqlite'}, 2),
    ('vatsim', {'aircraft_models': 'aig'}, 2),
    ('vatsim', {'fsltl_path': 'models'}, 2),
    ('vatsim', {'aircraft_community_path': 'Community'}, 2),
])
def test_traffic_configuration_changes_restart_only_affected_source(source, change, expected):
    settings = Settings(traffic_enabled=True, traffic_source=source)
    with patch.object(TrafficService, 'configure') as configure, \
            patch('navixav.web.app.save_user_settings'):
        app = create_app(settings)
        try:
            endpoint(app, '/api/settings', 'PUT')(SettingsRequest(**(settings.user_values() | change)))
            assert configure.call_count == expected
        finally:
            app.state.close_resources()


def test_failed_reconfiguration_can_be_retried_with_the_same_settings():
    settings = Settings(traffic_enabled=True)
    with patch.object(TrafficService, 'configure') as configure, \
            patch('navixav.web.app.save_user_settings'):
        app = create_app(settings)
        try:
            request = SettingsRequest(**(settings.user_values() | {'traffic_source': 'ivao'}))
            configure.side_effect = RuntimeError('initialisation failed')
            with pytest.raises(RuntimeError):
                endpoint(app, '/api/settings', 'PUT')(request)
            configure.side_effect = None
            endpoint(app, '/api/settings', 'PUT')(request)
            assert configure.call_count == 3
        finally:
            app.state.close_resources()


def test_all_sources_receive_the_user_traffic_limits():
    settings = Settings(
        traffic_enabled=True, traffic_source="opensky",
        traffic_radius_nm=40, traffic_max_aircraft=10,
    )
    with patch.object(TrafficService, 'configure') as configure:
        app = create_app(settings)
        try:
            assert configure.call_args.kwargs["radius_nm"] == 40
            assert configure.call_args.kwargs["max_aircraft"] == 10
        finally:
            app.state.close_resources()
