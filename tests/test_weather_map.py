"""Contrats du radar, des METAR et du vent superposés à la carte."""

import re
from pathlib import Path

from navixav import desktop


def _static(name: str) -> str:
    return (Path(desktop.__file__).parent / "web" / "static" / name).read_text(
        encoding="utf-8"
    )


def test_weather_layers_are_real_map_controls_and_not_a_separate_panel():
    markup = _static("index.html")
    application = _static("app.js")
    map_source = _static("map.js")

    assert 'id="map-radar"' in markup
    assert 'id="map-weather-stations"' in markup
    assert 'fetch("/api/weather/radar"' in application
    assert "MAP.setRadarFrame(currentRadarFrame)" in application
    assert "MAP.setWeatherStations(stations)" in application
    assert "if (radarVisible) drawRadar();" in map_source
    assert "if (weatherStationsVisible) drawWeatherStations();" in map_source
    assert map_source.index("drawRadar();") < map_source.index("drawRoute();")


def test_weather_layer_choices_are_saved_and_the_sources_remain_visible():
    markup = _static("index.html")
    application = _static("app.js")

    assert "persistSetting({ map_weather_radar: visible })" in application
    assert "persistSetting({ map_weather_stations: visible })" in application
    assert 'id="map-weather-attribution"' in markup
    assert "RainViewer" in markup
    assert "aviationweather.gov" in markup
    assert 'id="map-weather-status"' in markup


def test_weather_map_copy_exists_in_all_interface_languages():
    translations = _static("i18n.js")

    for key in (
        "map_radar",
        "map_radar_title",
        "map_weather_stations",
        "map_weather_stations_title",
        "legend_radar",
        "legend_weather_stations",
        "map_radar_time",
    ):
        assert len(re.findall(rf"\b{re.escape(key)}:", translations)) == 8
