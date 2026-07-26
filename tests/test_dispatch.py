"""Extraction du dispatch SimBrief : masses, carburant, temps, dégagement."""

from __future__ import annotations

from navixav.format import clock, duration, mass, ratio
from navixav.planner.engine import CompletionEngine
from navixav.preferences import AirportPreferences
from navixav.simbrief.parser import parse_ofp


def test_units_and_weights(ofp):
    d = ofp.dispatch
    assert d.unit_label == "kg"
    assert d.zfw == 60340
    assert d.max_zfw == 64300
    assert d.takeoff_weight == 66077
    assert d.landing_weight == 62937
    assert d.passengers == 162
    assert d.cargo == 1200


def test_fuel_breakdown(ofp):
    d = ofp.dispatch
    assert d.block_fuel == 5737
    assert d.taxi_fuel == 200
    assert d.trip_fuel == 3140
    assert d.reserve_fuel == 1150
    assert d.alternate_fuel == 1090
    assert d.landing_fuel == 2397


def test_profile_and_distances(ofp):
    d = ofp.dispatch
    assert d.cost_index == "24"
    assert d.route_distance_nm == 311
    assert d.great_circle_distance_nm == 298
    assert d.tropopause_ft == 37000
    assert d.average_wind_direction == "268"


def test_times(ofp):
    d = ofp.dispatch
    assert duration(d.time_enroute_s) == "1h25"
    assert duration(d.block_time_s) == "1h50"
    assert clock(d.off_block) is not None


def test_alternate_details(ofp):
    d = ofp.dispatch
    assert d.alternate_distance_nm == 94
    assert d.alternate_burn == 1090
    assert d.alternate_altitude_ft == 20000
    assert d.alternate_metar.startswith("LFBP")


def test_aircraft_and_atc(ofp):
    d = ofp.dispatch
    assert d.registration == "F-HXAV"
    assert d.selcal == "AB-CD"
    assert d.atc_flightplan_text.startswith("(FPL-AFR1234")


def test_missing_dispatch_sections_do_not_raise():
    summary = parse_ofp({"origin": {"icao_code": "LFST"}})
    assert summary.dispatch.zfw is None
    assert summary.dispatch.unit_label == ""


def test_dispatch_reaches_the_plan(provider, settings, ofp):
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(ofp)
    assert plan.dispatch.block_fuel == 5737


def test_dispatch_is_serialised_without_empty_fields(provider, settings, ofp):
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(ofp)
    payload = plan.to_dict()["dispatch"]
    assert payload["block_fuel"] == 5737
    # Zéro est une valeur réelle (« pas de carburant supplémentaire ») et doit
    # être conservée ; seuls les champs absents de l'OFP sont omis.
    assert payload["extra_fuel"] == 0
    assert "ofp_pdf_link" not in payload
    assert all(value not in (None, "") for value in payload.values())


# --------------------------------------------------------------------------- #
# Mise en forme
# --------------------------------------------------------------------------- #


def test_mass_uses_thin_separators():
    assert mass(60340, "kg") == "60 340 kg"


def test_ratio_shows_the_remaining_margin():
    assert ratio(60340, 64300, "kg") == "60 340 kg  (max 64 300 kg, marge 3 960 kg)"


def test_ratio_flags_an_overweight():
    assert "marge -" in ratio(65000, 64300, "kg")


def test_duration_under_an_hour():
    assert duration(2700) == "45 min"


def test_duration_of_zero_is_absent():
    assert duration(0) is None
