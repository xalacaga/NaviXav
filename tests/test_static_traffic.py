"""Trafic statique : une flotte garée, stable et compatible avec le jeu installé."""

import sqlite3
from pathlib import Path

from navixav.traffic.base import TrafficAircraft
from navixav.traffic.static_traffic import (
    STAND_TYPES,
    StaticTrafficProvider,
    read_stands,
)

LFPG = (49.0097, 2.5479)


def _database(tmp_path, stands=(("porte grande", 0.0, 0.0),)) -> Path:
    """Base sur disque : le fournisseur ouvre une connexion par relevé."""
    path = tmp_path / "navdata.sqlite"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE airport (icao TEXT, lat REAL, lon REAL, altitude_ft REAL)"
    )
    connection.execute(
        "CREATE TABLE parking (icao TEXT, label TEXT, kind TEXT, x REAL, y REAL,"
        " radius_m REAL, heading REAL)"
    )
    connection.execute(
        "INSERT INTO airport VALUES ('LFPG', ?, ?, 392)", LFPG
    )
    # Un aérodrome lointain, hors de tout rayon raisonnable.
    connection.execute("INSERT INTO airport VALUES ('LFBO', 43.63, 1.37, 499)")
    connection.execute(
        "INSERT INTO parking VALUES ('LFBO', 'gate 1', 'porte moyenne', 0, 0, 20, 90)"
    )
    for index, (kind, x, y) in enumerate(stands):
        connection.execute(
            "INSERT INTO parking VALUES ('LFPG', ?, ?, ?, ?, 25, 180)",
            (f"stand {index:02d}", kind, x, y),
        )
    connection.commit()
    connection.close()
    return path


class _Index:
    """Jeu de modèles réduit, comme `SimObjectModelIndex` l'expose."""

    def __init__(self, pairs):
        self.models = [
            type("M", (), {"aircraft_type": kind, "airline_icao": airline})()
            for kind, airline in pairs
        ]


def _provider(path, **kwargs) -> StaticTrafficProvider:
    return StaticTrafficProvider(
        lambda: LFPG, lambda: sqlite3.connect(path), **kwargs
    )


def test_only_the_airports_within_the_radius_are_read(tmp_path):
    connection = sqlite3.connect(_database(tmp_path))
    stands = read_stands(connection, LFPG, 15.0)
    assert {stand.icao for stand in stands} == {"LFPG"}
    # Toulouse est à plus de 300 NM : aucun rayon raisonnable ne l'atteint.
    assert read_stands(connection, LFPG, 100.0) == stands


def test_a_stand_keeps_its_real_position_and_heading(tmp_path):
    connection = sqlite3.connect(
        _database(tmp_path, (("porte moyenne", 500.0, 250.0),))
    )
    stand = read_stands(connection, LFPG, 15.0)[0]
    # 250 m vers le nord, 500 m vers l'est : la conversion doit rester fine.
    assert abs(stand.latitude - LFPG[0] - 0.00225) < 0.0005
    assert stand.longitude > LFPG[1]
    assert stand.heading == 180.0
    assert stand.altitude_ft == 392


def test_the_fleet_never_changes_between_two_readings(tmp_path):
    """Un poste garde son appareil : sinon la livrée changerait chaque seconde."""
    connection = _database(tmp_path, tuple(("porte moyenne", i * 60.0, 0.0) for i in range(6)))
    provider = _provider(connection)
    first = provider.traffic()
    second = provider.traffic()
    assert [aircraft.uid for aircraft in first] == [a.uid for a in second]
    assert [aircraft.aircraft_type for aircraft in first] == [
        a.aircraft_type for a in second
    ]
    # Et d'une instance à l'autre : le tirage ne dépend pas du processus.
    assert [a.uid for a in _provider(connection).traffic()] == [a.uid for a in first]


def test_the_stand_category_decides_the_size_of_the_aircraft(tmp_path):
    connection = _database(tmp_path, (
        ("rampe GA", 0.0, 0.0),
        ("porte grande", 100.0, 0.0),
    ))
    fleet = {a.departure + a.uid[-2:]: a for a in _provider(connection).traffic()}
    types = {a.uid[-2:]: a.aircraft_type for a in fleet.values()}
    assert types["00"] in STAND_TYPES["rampe GA"]
    assert types["01"] in STAND_TYPES["porte grande"]


def test_the_catalogue_of_the_installed_models_restricts_the_choice(tmp_path):
    connection = _database(tmp_path, tuple(("porte moyenne", i * 60.0, 0.0) for i in range(4)))
    provider = _provider(connection)
    provider.bind_models(_Index([("A320", "AFR"), ("A320", "BAW")]))
    fleet = provider.traffic()
    assert {a.aircraft_type for a in fleet} == {"A320"}
    assert {a.airline_icao for a in fleet} <= {"AFR", "BAW"}


def test_the_density_setting_caps_the_fleet(tmp_path):
    connection = _database(tmp_path, tuple(("porte moyenne", i * 60.0, 0.0) for i in range(30)))
    assert len(_provider(connection, max_aircraft=7).traffic()) == 7


def test_empty_parking_cache_retries_when_facilities_arrive(tmp_path):
    path = _database(tmp_path, ())
    now = [0.0]
    provider = _provider(path, clock=lambda: now[0])
    assert provider.traffic() == []
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO parking VALUES ('LFPG', 'A1', 'porte moyenne', 100, 0, 25, 90)")
    now[0] = 3.1
    assert len(provider.traffic()) == 1


def test_binding_catalogue_invalidates_fleet_already_read_by_map(tmp_path):
    provider = _provider(_database(tmp_path))
    provider.traffic()
    provider.bind_models(_Index([('A320', 'AFR')]))
    assert {entry.aircraft_type for entry in provider.traffic()} == {'A320'}
    assert {entry.airline_icao for entry in provider.traffic()} == {'AFR'}


def test_every_parked_aircraft_is_injectable_as_is(tmp_path):
    """Le gestionnaire écarte tout appareil dont l'état au sol est incertain."""
    connection = _database(tmp_path)
    aircraft = _provider(connection).traffic()[0]
    assert isinstance(aircraft, TrafficAircraft)
    assert aircraft.on_ground is True
    assert aircraft.ground_speed_kt == 0.0
    assert aircraft.heading_deg is not None and aircraft.altitude_ft is not None
    assert aircraft.callsign and len(aircraft.callsign) <= 12


def test_an_empty_or_broken_database_gives_an_empty_fleet(tmp_path):
    empty = tmp_path / "vide.sqlite"
    sqlite3.connect(empty).close()
    assert _provider(empty).traffic() == []


def test_the_source_answers_the_map_like_any_network(tmp_path):
    """La carte interroge toute source de la même façon.

    Sans `updated_at` ni `detail`, l'appel qui alimente la carte échouait sur
    la seule source statique : les appareils entraient dans le simulateur sans
    jamais apparaître à l'écran.
    """
    provider = _provider(_database(tmp_path))
    aircraft = provider.traffic()[0]
    assert provider.updated_at()
    found = provider.detail(aircraft.callsign.lower())
    assert found is not None and found.uid == aircraft.uid
    assert provider.detail("INCONNU") is None


def test_the_map_reads_the_static_source_like_the_networks(tmp_path):
    """Contrat commun : ce que l'API appelle sur n'importe quelle source."""
    from navixav.traffic.ivao import IvaoClient
    from navixav.traffic.opensky import OpenSkyClient
    from navixav.vatsim import VatsimClient

    provider = _provider(_database(tmp_path))
    for name in ("name", "traffic", "updated_at", "detail", "close"):
        assert hasattr(provider, name), name
        for network in (VatsimClient, IvaoClient, OpenSkyClient):
            assert hasattr(network, name), f"{network.__name__}.{name}"
