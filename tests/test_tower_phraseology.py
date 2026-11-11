"""Phraséologie de la radio et de l'interphone hors ligne, et route de synthèse."""

from __future__ import annotations

from fastapi.testclient import TestClient

from navixav.tower_phraseology import KINDS, SPEAKERS, TowerData, compose, squawk_for
from navixav.voice_engine import VoiceEngine


def test_known_airline_is_spoken_by_its_radio_callsign():
    text = compose("lineup", TowerData(callsign="AFR6142", runway="32R"), "en")
    assert text == "Air France six one four two, runway three two right, line up and wait."


def test_unknown_airline_is_spelled_like_a_controller_would():
    """ABF059, l'indicatif d'un OFP réel : la compagnie n'est pas connue."""
    text = compose("lineup", TowerData(callsign="ABF059", runway="05"), "en")
    assert text.startswith("Alfa Bravo Foxtrot zero five niner, runway zero five,")


def test_takeoff_gives_the_magnetic_wind_to_the_nearest_ten_degrees():
    data = TowerData(callsign="AFR6142", runway="32R", wind_direction_true=321,
                     wind_speed_kt=8.4, magnetic_variation=1.5)
    assert compose("takeoff", data, "en") == (
        "Air France six one four two, wind three two zero degrees, eight knots, "
        "runway three two right, cleared for takeoff."
    )


def test_light_wind_is_announced_calm_in_french():
    data = TowerData(callsign="AFR6142", runway="14L", wind_direction_true=90, wind_speed_kt=2)
    assert compose("takeoff", data, "fr") == (
        "Air France six un quatre deux, vent calme, piste un quatre gauche, autorisé décollage."
    )


def test_handoff_reads_the_frequency_without_trailing_zeros():
    data = TowerData(callsign="AFR6142", departure_mhz=124.35)
    assert compose("handoff", data, "fr") == (
        "Air France six un quatre deux, contactez Départ un deux quatre décimal trois cinq, au revoir."
    )


def test_clearance_names_the_destination_sid_runway_and_squawk():
    data = TowerData(callsign="AFR6142", runway="32R", destination="Nice", sid="LACOU5A", squawk="4521")
    assert compose("clearance", data, "en") == (
        "Air France six one four two, cleared to Nice via Lacou five Alfa departure, "
        "runway three two right, squawk four five two one."
    )
    assert compose("clearance", data, "fr") == (
        "Air France six un quatre deux, autorisé Nice, départ Lacou cinq Alfa, "
        "piste trois deux droite, transpondeur quatre cinq deux un."
    )


def test_the_invented_squawk_is_stable_octal_and_never_an_emergency_code():
    code = squawk_for("AFR6142|Nice|32R")
    assert code == squawk_for("AFR6142|Nice|32R")
    assert len(code) == 4 and set(code) <= set("01234567")
    assert code not in {"7500", "7600", "7700", "2000", "7000", "1200"}


def test_taxi_and_pushback_come_from_the_computed_ground_route():
    data = TowerData(callsign="AFR6142", runway="32R", taxiways=("N", "D1"), pushback_heading=178)
    assert compose("pushback_approved", data, "en") == "Air France six one four two, pushback approved, facing south."
    assert compose("taxi", data, "en") == (
        "Air France six one four two, taxi to holding point runway three two right via November, Delta one."
    )


def test_arrival_stand_drops_the_word_gate():
    data = TowerData(callsign="AFR6142", stand="porte U 21")
    assert compose("arrival_taxi", data, "fr") == "Air France six un quatre deux, roulez au poste Uniform deux un."


def test_cabin_and_ground_crew_speak_on_the_interphone():
    assert compose("cabin_boarding", TowerData(callsign="", passengers=180), "en") == (
        "Captain, cabin: boarding completed, one eight zero passengers on board."
    )
    assert compose("chocks", TowerData(callsign=""), "fr") == "Cales en place, vous pouvez couper les moteurs."


def test_every_message_has_a_speaker_with_a_voice_in_both_languages():
    for kind, speaker in KINDS.items():
        for language in ("en", "fr"):
            assert speaker in SPEAKERS[language], (kind, language)


def test_a_message_without_its_data_is_not_composed():
    assert compose("handoff", TowerData(callsign="AFR6142"), "en") is None
    assert compose("lineup", TowerData(callsign=""), "en") is None
    assert compose("clearance", TowerData(callsign="AFR6142", runway="32R"), "en") is None


def test_the_engine_is_absent_until_installed(tmp_path):
    assert not VoiceEngine(tmp_path).available()


def test_without_the_engine_the_tower_falls_back_to_recorded_voices(monkeypatch):
    import navixav.web.app as web

    monkeypatch.setattr(web.VoiceEngine, "available", lambda self: False)
    client = TestClient(web.create_app())
    response = client.post("/api/tower/speech", json={"kind": "lineup", "callsign": "AFR6142", "runway": "32R"})
    assert response.status_code == 404
