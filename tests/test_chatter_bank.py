"""Échanges de l'ambiance radio : reproductibles et cohérents, sans moteur de synthèse."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import generate_chatter_bank as bank  # noqa: E402


def test_the_bank_is_reproducible_and_covers_every_position():
    first = bank.scripted_exchanges(10)
    second = bank.scripted_exchanges(10)

    assert [e.lines for e in first] == [e.lines for e in second]
    assert {e.position for e in first} == set(bank.POSITIONS)
    assert len({e.name for e in first}) == len(first)


def test_readbacks_repeat_the_values_of_the_instruction():
    for exchange in bank.scripted_exchanges(40):
        controller = [text for who, text in exchange.lines if who == "ATC"]
        pilot = [text for who, text in exchange.lines if who == "PILOT"]
        assert controller and pilot, exchange.name
        assert exchange.callsign
        assert all(exchange.callsign in text for _who, text in exchange.lines), exchange.name
        for level in re.findall(r"flight level ((?:\w+ ){2}\w+)", controller[-1]):
            assert any(level in text for text in pilot), exchange.name


def test_the_whispery_voice_is_never_used():
    voices = {voice for voice, _lang, _speed in bank.PILOTS}
    for options in bank.CONTROLLERS.values():
        voices |= {voice for voice, _lang, _speed in options}
    assert "af_nicole" not in voices


def test_phraseology_spells_digits_the_icao_way():
    assert bank.digits(1019) == "one zero one niner"
    text = " ".join(t for e in bank.scripted_exchanges(20) for _w, t in e.lines)
    assert not re.search(r"\d", text)
