"""Banque vocale livrée : complète, cohérente et alignée sur les alarmes.

La banque est générée hors de l'application (scripts/generate_voice_bank.py) ;
ces tests vérifient seulement ce qui est livré : un fichier pour chaque
phrase annoncée, dans chacune des huit langues de l'interface.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parent.parent / "navixav" / "web" / "static"
BANK = STATIC / "voice"
LANGUAGES = ("fr", "en", "de", "es", "it", "pt", "nl", "pl")


def _manifest(language: str) -> dict:
    return json.loads((BANK / language / "manifest.json").read_text(encoding="utf-8"))


def _alert_ids() -> list[str]:
    source = (STATIC / "app.js").read_text(encoding="utf-8").replace("\r\n", "\n")
    start = source.index("const ALERT_RULES = [")
    block = source[start: source.index("\n];\n", start)]
    return re.findall(r'^\s+id: "([a-z_]+)",$', block, flags=re.M)


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_language_has_a_complete_bank(language: str):
    manifest = _manifest(language)
    clips = manifest["clips"]

    assert manifest["language"] == language
    for name in clips.values():
        assert (BANK / language / name).is_file(), name
    for alert in _alert_ids():
        assert f"alert_{alert}" in clips, alert
    for key in ("master_caution", "master_warning", "voice_tod_now", "voice_test_phrase",
                "taxi_arrived", "taxi_off_route"):
        assert key in clips, key
    for digit in range(10):
        assert f"digit_{digit}" in clips
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        assert f"letter_{letter}" in clips
    for side in "LRC":
        assert f"runway_{side}" in clips
    for number in range(61):
        assert f"number_{number}" in clips


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_template_can_be_completed(language: str):
    manifest = _manifest(language)
    for key in ("voice_tod_prepare", "voice_tod_imminent", "taxi_hold_short",
                "taxi_turn_left", "taxi_turn_right", "taxi_continue"):
        segments = manifest["templates"][key]
        assert any("slot" in segment for segment in segments), key
        for segment in segments:
            if "clip" in segment:
                assert segment["clip"] in manifest["clips"], segment


def test_the_bank_stays_small_and_needs_no_engine():
    files = [path for path in BANK.rglob("*") if path.is_file()]
    total = sum(path.stat().st_size for path in files)

    assert total < 12 * 1024 * 1024
    assert all(path.suffix in {".ogg", ".json"} for path in files)


def test_the_page_loads_the_voice_engine_before_the_application():
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert html.index("/static/voice.js") < html.index("/static/app.js")


def test_the_index_lists_every_voice_with_the_default_first():
    index = json.loads((BANK / "index.json").read_text(encoding="utf-8"))

    assert set(index) == set(LANGUAGES)
    for language, voices in index.items():
        # La voix par défaut garde le dossier nommé d'après la langue.
        assert voices[0]["bank"] == language
        for voice in voices:
            manifest = json.loads((BANK / voice["bank"] / "manifest.json").read_text(encoding="utf-8"))
            assert manifest["language"] == language
            assert voice["label"]
    assert [voice["voice"] for voice in index["en"]] == ["af_heart", "af_bella", "bf_emma"]


def test_no_windows_voice_is_offered_any_more():
    voice = (STATIC / "voice.js").read_text(encoding="utf-8")

    assert "speechSynthesis" not in voice
    assert "SpeechSynthesisUtterance" not in voice
