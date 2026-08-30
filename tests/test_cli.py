"""Commandes de diagnostic en ligne de commande.

`navixav airport` sert à confronter la base à ce que le simulateur a réellement
donné. C'est la seule vue qui montre le nombre par lequel MSFS désigne un rôle
radio, en regard du sigle que NaviXav en tire.
"""

from __future__ import annotations

import argparse

from navixav.cli import cmd_airport
from navixav.navdata import msfs_store


def _airport_with_frequencies() -> dict:
    return {
        "icao": "TEST", "name": "Essai", "lat": 48.0, "lon": 7.0,
        "altitude_ft": 500.0, "transition_altitude_ft": 5000,
        "transition_level_ft": None,
        "runways": [{
            "primary": "05", "secondary": "23", "lat": 48.0, "lon": 7.0,
            "altitude_ft": 500.0, "heading_true": 48.6, "length_ft": 7900,
            "width_ft": 148, "surface": "asphalte",
            "primary_ils": "TST", "secondary_ils": None,
        }],
        "frequencies": [
            {"type": 1, "mhz": 128.075, "name": "ATIS"},
            {"type": 6, "mhz": 118.5, "name": "TOWER"},
            {"type": 99, "mhz": 130.0, "name": "INCONNU"},
        ],
        "approaches": [], "departures": [], "arrivals": [],
        "taxi_points": [], "taxi_parkings": [], "taxi_paths": [],
    }


def _store_at(path) -> str:
    connection = msfs_store.connect(path)
    msfs_store.store_airport(connection, _airport_with_frequencies())
    connection.close()
    return str(path)


def test_the_airport_command_shows_the_frequencies_with_their_raw_type(
    tmp_path, capsys
):
    """Le sigle seul ne se vérifie pas : c'est le nombre en face qui le prouve.

    Sans lui, un pilote qui verrait « TWR 130.000 » ne saurait pas si c'est le
    simulateur ou la table de correspondance qui se trompe, ni quelle ligne
    corriger.
    """
    args = argparse.Namespace(
        icao="TEST", store=_store_at(tmp_path / "navixav.sqlite"), runway=None
    )
    assert cmd_airport(args, None) == 0

    printed = capsys.readouterr().out
    assert "Fréquences" in printed
    assert "ATIS" in printed
    assert "128.075" in printed
    assert "TWR" in printed
    # Le type brut accompagne chaque ligne, et le rôle que la table ne traduit
    # pas est signalé plutôt que passé sous silence.
    assert "99" in printed
    assert "FREQUENCY_CODES" in printed


def test_an_airport_without_frequencies_prints_no_empty_table(tmp_path, capsys):
    """Un tableau vide laisserait croire que le terrain n'en publie aucune.

    Il n'en publie pas *dans la base* : le terrain vient d'une extraction
    antérieure à cette lecture, et sa reprise l'y mettra.
    """
    airport = _airport_with_frequencies()
    airport["frequencies"] = []
    connection = msfs_store.connect(tmp_path / "navixav.sqlite")
    msfs_store.store_airport(connection, airport)
    connection.close()

    args = argparse.Namespace(
        icao="TEST", store=str(tmp_path / "navixav.sqlite"), runway=None
    )
    assert cmd_airport(args, None) == 0
    assert "Fréquences" not in capsys.readouterr().out
