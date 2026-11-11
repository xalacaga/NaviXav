"""Banque pré-enregistrée de la tour : chaque morceau demandé par tower.js existe."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parent.parent / "navixav" / "web" / "static"


@pytest.mark.parametrize("language", ["en", "fr"])
def test_every_composable_clip_is_in_the_bank(language):
    manifest = json.loads((STATIC / "tower" / language / "manifest.json").read_text(encoding="utf-8"))
    clips = manifest["clips"]
    required = {"decimal", "contact_departure", "good_day", "wind_calm", "knots"}
    required |= {f"digit_{d}" for d in range(10)} | {f"letter_{chr(c)}" for c in range(65, 91)}
    required |= {f"airline_{code}" for code in manifest["airlines"]}
    # Groupes dits d'un souffle : toutes les pistes, tous les vents.
    for number in range(1, 37):
        for side in ("", "L", "R", "C"):
            required |= {f"rwy_{number:02d}{side}_lineup", f"rwy_{number:02d}{side}_takeoff"}
    required |= {f"wind_{direction:03d}" for direction in range(10, 361, 10)}
    required |= {f"knots_{speed}" for speed in range(3, manifest["max_knots"] + 1)}
    missing = sorted(clip for clip in required if clip not in clips)
    assert not missing
    for name in clips.values():
        assert (STATIC / "tower" / language / name).is_file(), name
