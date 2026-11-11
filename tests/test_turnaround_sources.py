"""Sources réelles du module Escale : zones de chargement MSFS et GSX installé."""

from __future__ import annotations

import pytest

from navixav.gsx import gsx_installed
from navixav.live.simconnect import classify_payload_station


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        # Noms relevés sur le Fenix A320 dans MSFS 2024.
        ("OA 1-9", {"kind": "cabin", "rows": [1, 9]}),
        ("OB 10-19", {"kind": "cabin", "rows": [10, 19]}),
        ("CP1", {"kind": "cargo", "position": "forward"}),
        ("CP4", {"kind": "cargo", "position": "aft"}),
        ("CP5", {"kind": "cargo", "position": "aft"}),
        # Formes courantes d'autres appareils.
        ("Forward Cargo", {"kind": "cargo", "position": "forward"}),
        ("Aft Cargo Hold", {"kind": "cargo", "position": "aft"}),
        ("Business Class", {"kind": "cabin", "rows": None}),
        ("Economy rows 20-30", {"kind": "cabin", "rows": [20, 30]}),
    ],
)
def test_cabin_zones_and_holds_are_recognised(name, expected):
    assert classify_payload_station(name) == expected


@pytest.mark.parametrize("name", ["CAPTAIN", "F/O", "JUMP", "GALLEY FWD", "WATER", "WASTE", "UNUSED", ""])
def test_crew_galleys_and_consumables_are_left_out(name):
    assert classify_payload_station(name) is None


def test_gsx_is_detected_from_its_msfs_data_folder(tmp_path):
    (tmp_path / "Virtuali" / "GSX" / "MSFS").mkdir(parents=True)

    assert gsx_installed(appdata=str(tmp_path), addon_manager_dirs=())


def test_gsx_is_detected_from_its_addon_manager_manifest(tmp_path):
    (tmp_path / "GSX Pro 3.0.lw.xml").write_text("<x/>", encoding="utf-8")

    assert gsx_installed(appdata="", addon_manager_dirs=(tmp_path,))


def test_without_gsx_the_turnaround_module_stays_hidden(tmp_path):
    assert not gsx_installed(appdata=str(tmp_path), addon_manager_dirs=(tmp_path,))
