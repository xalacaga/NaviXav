from __future__ import annotations

from navixav.simbrief.parser import OfpSummary, parse_ofp


def test_basic_fields(ofp: OfpSummary):
    assert ofp.origin_icao == "LFST"
    assert ofp.destination_icao == "LFBO"
    assert ofp.alternate_icao == "LFBP"
    assert ofp.aircraft_icao == "A20N"
    assert ofp.aircraft_name == "Airbus A320neo"
    assert ofp.callsign == "AFR1234"
    assert ofp.cruise_altitude_ft == 34000
    assert ofp.airac == "2604"


def test_planned_runways(ofp: OfpSummary):
    assert ofp.origin_planned_runway == "05"
    # SimBrief n'a rien prévu à l'arrivée : c'est au moteur de trancher.
    assert ofp.destination_planned_runway is None


def test_airport_coordinates_are_available_as_route_fallbacks():
    summary = parse_ofp(
        {
            "origin": {"icao_code": "LCPH", "pos_lat": "34.7180", "pos_long": "32.4857"},
            "destination": {"icao_code": "EHAM", "pos_lat": "52.3086", "pos_long": "4.7639"},
        }
    )

    assert (summary.origin_lat, summary.origin_lon) == (34.718, 32.4857)
    assert (summary.destination_lat, summary.destination_lon) == (52.3086, 4.7639)


def test_procedure_names_from_navlog(ofp: OfpSummary):
    assert ofp.simbrief_sid == "EPIK8M"
    assert ofp.simbrief_star == "AFRI8N"


def test_connection_hints(ofp: OfpSummary):
    """Les points de raccord, pas les points en route, pilotent le chaînage."""
    assert ofp.sid_exit_hint == "EPIKO"
    assert ofp.star_entry_hint == "AFRIC"


def test_enroute_fixes_exclude_procedures_and_pseudo_points(ofp: OfpSummary):
    assert ofp.enroute_fixes == ["LIRKO", "MOKIP", "GERVA"]
    assert "TOC" not in ofp.enroute_fixes
    assert "TOD" not in ofp.enroute_fixes
    assert "LFBO" not in ofp.enroute_fixes


def test_enroute_route_keeps_via_to_pairs(ofp: OfpSummary):
    assert ofp.enroute_route == [
        {"via": "DCT", "to": "LIRKO", "stage": "CRZ"},
        {"via": "DCT", "to": "MOKIP", "stage": "CRZ"},
        {"via": "DCT", "to": "GERVA", "stage": "CRZ"},
    ]


def test_enroute_route_keeps_simbrief_coordinates():
    summary = parse_ofp(
        {
            "navlog": {
                "fix": [
                    {
                        "ident": "LIRKO",
                        "type": "wpt",
                        "via_airway": "DCT",
                        "stage": "crz",
                        "pos_lat": "48.1234",
                        "pos_long": "5.6789",
                    }
                ]
            }
        }
    )

    assert summary.enroute_route == [
        {
            "via": "DCT",
            "to": "LIRKO",
            "stage": "CRZ",
            "lat": 48.1234,
            "lon": 5.6789,
        }
    ]


def test_invalid_navlog_coordinates_are_ignored():
    summary = parse_ofp(
        {
            "navlog": [
                {
                    "ident": "LIRKO",
                    "type": "wpt",
                    "pos_lat": "nan",
                    "pos_long": "500",
                }
            ]
        }
    )

    assert summary.enroute_route == [
        {"via": "DCT", "to": "LIRKO", "stage": ""}
    ]


def test_metars_extracted(ofp: OfpSummary):
    assert ofp.origin_metar.startswith("LFST")
    assert ofp.destination_metar.startswith("LFBO")


def test_navlog_as_bare_list():
    """SimBrief renvoie parfois le navlog directement sous forme de liste."""
    summary = parse_ofp(
        {
            "origin": {"icao_code": "LFST"},
            "destination": {"icao_code": "LFBO"},
            "navlog": [
                {"ident": "EPIKO", "type": "wpt", "via_airway": "EPIK8M", "is_sid_star": "1"},
                {"ident": "LIRKO", "type": "wpt", "via_airway": "DCT", "is_sid_star": "0"},
            ],
        }
    )
    assert summary.simbrief_sid == "EPIK8M"
    assert summary.enroute_fixes == ["LIRKO"]


def test_missing_sections_do_not_raise():
    summary = parse_ofp({})
    assert summary.origin_icao == ""
    assert summary.enroute_fixes == []
    assert summary.sid_exit_hint is None
