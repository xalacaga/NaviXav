"""Test de bout en bout : l'OFP de référence doit reproduire le panneau cible.

    LFST  RWY 05   EPIK8M / EPIKO
    LFBO  RWY 32R  AFRI8N / AFRIC  puis ILS Z RWY 32R / ADIMO
"""

from __future__ import annotations

from navixav.models import Confidence
from navixav.planner.engine import CompletionEngine, PlannerOverrides
from navixav.preferences import AirportPreferences


def _plan(provider, settings, ofp, overrides=None):
    engine = CompletionEngine(provider, settings, AirportPreferences.load())
    return engine.complete(ofp, overrides)


def test_departure_block(provider, settings, ofp):
    plan = _plan(provider, settings, ofp)
    departure = plan.departure
    assert departure.icao == "LFST"
    assert departure.runway.choice.value == "05"
    assert departure.sid.value == "EPIK8M"
    assert departure.sid_transition.value == "EPIKO"
    assert departure.sid.confidence is Confidence.HIGH
    assert departure.sid_transition.confidence is Confidence.HIGH


def test_arrival_block(provider, settings, ofp):
    plan = _plan(provider, settings, ofp)
    arrival = plan.arrival
    assert arrival.icao == "LFBO"
    assert arrival.runway.choice.value == "32R"
    assert arrival.star.value == "AFRI8N"
    assert arrival.star_transition.value == "AFRIC"
    assert arrival.approach.value == "ILS Z RWY 32R"
    assert arrival.approach_transition.value == "ADIMO"


def test_approach_chain_is_high_confidence(provider, settings, ofp):
    """ADIMO relie la sortie de STAR à la transition d'approche."""
    plan = _plan(provider, settings, ofp)
    assert plan.arrival.approach.confidence is Confidence.HIGH
    assert plan.arrival.approach_transition.confidence is Confidence.HIGH


def test_ils_frequency_is_resolved(provider, settings, ofp):
    plan = _plan(provider, settings, ofp)
    assert plan.arrival.ils_frequency_mhz is not None


def test_wind_is_read_from_the_ofp_metar(provider, settings, ofp):
    plan = _plan(provider, settings, ofp)
    assert plan.departure.wind.direction_deg == 40
    assert plan.arrival.wind.direction_deg == 330


def test_atc_route_is_rebuilt(provider, settings, ofp):
    plan = _plan(provider, settings, ofp)
    assert plan.atc_route() == "EPIK8M EPIKO LIRKO MOKIP GERVA AFRIC AFRI8N"
    first_leg = plan.enroute.route_legs[0]
    assert first_leg["via"] == "DCT"
    assert first_leg["to"] == "LIRKO"
    assert first_leg["stage"] == "CRZ"
    assert {"lat", "lon"} <= first_leg.keys()
    assert plan.enroute.route_path[0]["ident"] == "LFST"
    assert plan.enroute.route_path[-1]["ident"] == "LFBO"


def test_route_path_starts_and_ends_on_the_selected_runways(provider, settings, ofp):
    """Le tracé part du seuil de la 05 à LFST et finit sur celui de la 32R."""
    plan = _plan(provider, settings, ofp)

    def threshold(icao: str, name: str) -> tuple[float, float]:
        runway = next(r for r in provider.runways(icao) if r.name == name)
        return (runway.lat, runway.lon)

    first = plan.enroute.route_path[0]
    last = plan.enroute.route_path[-1]

    assert (first["lat"], first["lon"]) == threshold("LFST", "05")
    assert first["runway"] == "05"
    assert (last["lat"], last["lon"]) == threshold("LFBO", "32R")
    assert last["runway"] == "32R"

    airport = provider.airport("LFST")
    assert (first["lat"], first["lon"]) != (airport.lat, airport.lon)


def test_aircraft_information_reaches_web_payload(provider, settings, ofp):
    payload = _plan(provider, settings, ofp).to_dict()

    assert payload["aircraft"] == "A20N"
    assert payload["aircraft_name"] == "Airbus A320neo"
    assert payload["callsign"] == "AFR1234"
    assert payload["dispatch"]["registration"] == "F-HXAV"
    assert payload["dispatch"]["equipment"] == "SDE2E3FGHIRWXYZ/LB1"
    assert payload["dispatch"]["selcal"] == "AB-CD"


def test_overrides_take_precedence(provider, settings, ofp):
    plan = _plan(
        provider,
        settings,
        ofp,
        PlannerOverrides(arrival_runway="14L", approach="ILS Z RWY 14L"),
    )
    assert plan.arrival.runway.choice.value == "14L"
    assert plan.arrival.approach.value == "ILS Z RWY 14L"
    assert plan.arrival.runway.choice.source == "utilisateur"


def test_reversed_wind_flips_the_arrival_runway(provider, settings, ofp):
    plan = _plan(
        provider,
        settings,
        ofp,
        PlannerOverrides(arrival_metar="LFBO 260730Z 14015KT CAVOK 21/11 Q1018"),
    )
    assert plan.arrival.runway.choice.value.startswith("14")
    assert "14" in plan.arrival.approach.value


def test_plan_serialises_to_json(provider, settings, ofp):
    payload = _plan(provider, settings, ofp).to_dict()
    assert payload["departure"]["sid"]["value"] == "EPIK8M"
    assert payload["arrival"]["approach_transition"]["value"] == "ADIMO"
    assert payload["source"]["navdata_airac"]
    assert isinstance(payload["warnings"], list)
