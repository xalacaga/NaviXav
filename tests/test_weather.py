from __future__ import annotations

from datetime import datetime, timezone

import pytest

from navixav.simbrief.parser import DispatchSummary, OfpSummary
from navixav.weather.briefing import build_briefing
from navixav.weather.decode import decode_metar
from navixav.weather.taf import summarise_taf

NOW = datetime(2026, 8, 2, 13, 0, tzinfo=timezone.utc)


def _no_fetch(icao: str) -> None:
    """Sentinelle : le briefing ne doit rien demander au réseau dans ces tests."""
    raise AssertionError(f"appel réseau inattendu pour {icao}")


# ------------------------------------------------------------------ décodage


def test_decode_metar_essentials():
    report = decode_metar(
        "LFPG",
        "LFPG 021230Z AUTO 27012G28KT 3000 -RA BR BKN008 OVC015 12/11 Q1008",
        role="departure",
        source="simbrief",
        now=NOW,
    )
    assert report.icao == "LFPG"
    assert (report.wind.direction_deg, report.wind.speed_kt, report.wind.gust_kt) == (270, 12, 28)
    assert report.visibility_m == 3000
    assert report.ceiling_ft == 800
    assert (report.temperature_c, report.dew_point_c, report.spread_c) == (12, 11, 1)
    assert report.qnh_hpa == 1008
    assert report.auto
    assert report.flight_category == "IFR"
    assert [layer["cover"] for layer in report.clouds] == ["BKN", "OVC"]
    assert [item["code"] for item in report.phenomena] == ["-RA", "BR"]


def test_decode_metar_negative_temperature():
    report = decode_metar("ENGM", "ENGM 021220Z 09006KT 9999 FEW020 M03/M07 Q1021", now=NOW)
    assert (report.temperature_c, report.dew_point_c, report.spread_c) == (-3, -7, 4)


def test_decode_metar_cavok_has_no_ceiling():
    report = decode_metar("LFBO", "LFBO 021230Z 00000KT CAVOK 25/12 Q1015 NOSIG", now=NOW)
    assert report.cavok
    assert report.no_significant_change
    assert report.visibility_m == 10000
    assert report.ceiling_ft is None
    assert report.flight_category == "VFR"


def test_decode_metar_statute_miles():
    """La visibilité nord-américaine s'exprime en milles terrestres."""
    report = decode_metar("KJFK", "KJFK 021251Z 18008KT 1 1/2SM BR OVC004 19/18 A2992", now=NOW)
    assert report.visibility_m == pytest.approx(2414, abs=2)
    assert report.ceiling_ft == 400
    assert report.flight_category == "LIFR"
    assert report.altimeter_inhg == pytest.approx(29.92, abs=0.01)


def test_decode_metar_age_and_staleness():
    fresh = decode_metar("LFPG", "LFPG 021230Z 27012KT CAVOK 12/05 Q1008", now=NOW)
    assert fresh.age_minutes == 30
    assert not fresh.stale

    old = decode_metar("LFPG", "LFPG 020600Z 27012KT CAVOK 12/05 Q1008", now=NOW)
    assert old.age_minutes == 420
    assert old.stale


def test_decode_metar_ignores_trend_and_remarks():
    """Un TEMPO décrit le futur : il ne doit pas dégrader l'observation."""
    report = decode_metar(
        "LFRN",
        "LFRN 021230Z 25010KT 9999 SCT030 18/12 Q1013 TEMPO 3000 SHRA BKN008 RMK QFE1005",
        now=NOW,
    )
    assert report.visibility_m == 9999
    assert report.ceiling_ft is None
    assert report.flight_category == "VFR"


def test_decode_metar_without_report_is_empty():
    report = decode_metar("LFPG", None)
    assert report.raw_metar is None
    assert report.flight_category is None
    assert report.clouds == []


def test_decode_metar_icao_is_not_read_as_phenomenon():
    """« LFRA » contient « RA » : l'indicateur ne doit pas passer pour de la pluie."""
    report = decode_metar("LFRA", "LFRA 021230Z 25010KT CAVOK 18/12 Q1013", now=NOW)
    assert report.phenomena == []


# ----------------------------------------------------------------------- TAF


def test_summarise_taf_keeps_baseline_and_significant_periods():
    taf = (
        "TAF LFPG 021100Z 0212/0318 27010KT 9999 SCT025 "
        "TEMPO 0214/0218 4000 SHRA BKN012 "
        "FM022200 24015G30KT 8000 -RA BKN008 "
        "PROB40 0300/0306 1200 BR BKN003"
    )
    periods = summarise_taf(taf)
    assert [period.kind for period in periods] == ["base", "TEMPO", "FM", "PROB40"]

    base, tempo, fm, prob = periods
    assert base.flight_category == "VFR"
    assert (tempo.visibility_m, tempo.ceiling_ft, tempo.flight_category) == (4000, 1200, "IFR")
    assert fm.wind.gust_kt == 30
    assert (prob.visibility_m, prob.ceiling_ft, prob.flight_category) == (1200, 300, "LIFR")


def test_summarise_taf_validity_is_not_a_visibility():
    """« 0212/0318 » est une fenêtre de validité, pas 212 m de visibilité."""
    periods = summarise_taf("TAF LFBO 021100Z 0212/0318 18008KT CAVOK")
    assert len(periods) == 1
    assert periods[0].flight_category == "VFR"
    assert periods[0].visibility_m is None


def test_summarise_taf_drops_periods_without_impact():
    taf = "TAF LFBO 021100Z 0212/0318 18008KT 9999 SCT030 BECMG 0215/0217 20010KT 9999 SCT035"
    assert [period.kind for period in summarise_taf(taf)] == ["base"]


def test_summarise_taf_without_forecast_is_empty():
    assert summarise_taf(None) == []
    assert summarise_taf("   ") == []


# ------------------------------------------------------------------ briefing


def _ofp() -> OfpSummary:
    return OfpSummary(
        origin_icao="LFPG",
        destination_icao="LFBO",
        alternate_icao="LFML",
        cruise_altitude_ft=36000,
        origin_metar="LFPG 021230Z 27012G28KT 3000 -RA BR BKN008 12/11 Q1008",
        destination_metar="LFBO 021230Z 18008KT CAVOK 25/12 Q1015",
        origin_taf="TAF LFPG 021100Z 0212/0318 27010KT 9999 SCT025 TEMPO 0214/0218 4000 SHRA BKN012",
        destination_taf="TAF LFBO 021100Z 0212/0318 18008KT CAVOK",
        dispatch=DispatchSummary(
            average_wind_direction="270",
            average_wind_speed="45",
            average_wind_component="-018",
            average_temperature_dev="+11",
            tropopause_ft=37000,
            alternate_metar="LFML 021230Z 12006KT 9999 FEW030 24/14 Q1014",
            alternate_taf="TAF LFML 021100Z 0212/0318 12008KT CAVOK",
        ),
    )


def test_build_briefing_covers_the_whole_flight():
    briefing = build_briefing(_ofp(), metar_source="none")
    assert briefing.departure.icao == "LFPG"
    assert briefing.departure.role == "departure"
    assert briefing.departure.flight_category == "IFR"
    assert briefing.arrival.icao == "LFBO"
    assert briefing.arrival.flight_category == "VFR"
    assert briefing.alternate.icao == "LFML"
    assert briefing.alternate.role == "alternate"


def test_build_briefing_uses_the_metar_already_chosen_by_the_engine():
    """Le moteur a déjà arbitré le METAR : le briefing ne réinterroge personne."""
    briefing = build_briefing(
        _ofp(),
        metar_source="awc",
        departure_metar="LFPG 021300Z 09004KT CAVOK 20/08 Q1012",
        arrival_metar="LFBO 021300Z 18008KT CAVOK 25/12 Q1015",
        metar_fetcher=_no_fetch,
        taf_fetcher=_no_fetch,
    )
    assert briefing.departure.raw_metar.startswith("LFPG 021300Z")
    assert briefing.departure.flight_category == "VFR"


def test_build_briefing_in_simbrief_mode_never_touches_the_network():
    """Le mode par défaut ne doit pas rallonger le calcul du plan d'un appel."""
    ofp = _ofp()
    ofp.origin_taf = None
    ofp.dispatch.alternate_metar = None
    ofp.dispatch.alternate_taf = None
    briefing = build_briefing(
        ofp, metar_source="simbrief", metar_fetcher=_no_fetch, taf_fetcher=_no_fetch
    )
    assert briefing.departure.raw_taf is None
    assert briefing.departure.taf_periods == []
    assert briefing.alternate.raw_metar is None


def test_build_briefing_completes_a_missing_taf_when_the_source_is_live():
    ofp = _ofp()
    ofp.origin_taf = None
    briefing = build_briefing(
        ofp,
        metar_source="live",
        metar_fetcher=_no_fetch,
        taf_fetcher=lambda icao: "TAF LFPG 021100Z 0212/0318 27010KT 9999 SCT025"
        if icao == "LFPG"
        else None,
    )
    assert briefing.departure.raw_taf is not None
    assert [period.kind for period in briefing.departure.taf_periods] == ["base"]


def test_build_briefing_fetches_the_alternate_metar_when_the_source_is_live():
    """Le dégagement ne passe pas par le moteur : c'est ici qu'il est complété."""
    ofp = _ofp()
    ofp.dispatch.alternate_metar = None
    briefing = build_briefing(
        ofp,
        metar_source="live",
        departure_metar=ofp.origin_metar,
        arrival_metar=ofp.destination_metar,
        metar_fetcher=lambda icao: "LFML 021230Z 12006KT 9999 FEW030 24/14 Q1014"
        if icao == "LFML"
        else None,
        taf_fetcher=lambda icao: None,
    )
    assert briefing.alternate.source == "awc"
    assert briefing.alternate.flight_category == "VFR"


def test_forced_live_refresh_replaces_ofp_metar_and_taf():
    briefing = build_briefing(
        _ofp(),
        metar_source="live",
        force_live=True,
        metar_fetcher=lambda icao: (
            f"{icao} 021300Z 09004KT CAVOK 20/08 Q1012"
        ),
        taf_fetcher=lambda icao: (
            f"TAF {icao} 021100Z 0212/0318 09005KT CAVOK"
        ),
    )
    assert briefing.departure.raw_metar.startswith("LFPG 021300Z")
    assert briefing.departure.raw_taf.startswith("TAF LFPG")
    assert briefing.departure.source == "awc"
    assert briefing.arrival.source == "awc"
    assert briefing.alternate.source == "awc"


def test_build_briefing_enroute_comes_from_the_ofp():
    briefing = build_briefing(_ofp(), metar_source="none")
    enroute = briefing.enroute
    assert enroute.cruise_altitude_ft == 36000
    assert (enroute.wind_direction_deg, enroute.wind_speed_kt) == (270, 45)
    assert enroute.wind_component_kt == -18
    assert enroute.temperature_dev_c == 11
    # Standard −56,5 °C au niveau 360, plus l'écart ISA annoncé par SimBrief.
    assert enroute.outside_air_temperature_c == pytest.approx(-45, abs=1)
    assert any("face" in note for note in enroute.notes)


def test_build_briefing_raises_operational_notes():
    briefing = build_briefing(_ofp(), metar_source="none")
    notes = " ".join(briefing.departure.notes)
    assert "brouillard" in notes  # écart température/point de rosée de 1 °C
    assert "28 kt" in notes  # rafales


def test_build_briefing_warns_when_weather_is_missing():
    ofp = _ofp()
    ofp.origin_metar = None
    briefing = build_briefing(
        ofp, metar_source="none", metar_fetcher=_no_fetch, taf_fetcher=_no_fetch
    )
    assert "Météo indisponible pour LFPG." in briefing.warnings
    assert briefing.departure.notes == ["Aucun METAR disponible pour ce terrain."]


def test_briefing_serialises_for_the_interface():
    payload = build_briefing(_ofp(), metar_source="none").to_dict()
    assert set(payload) == {"departure", "enroute", "arrival", "alternate", "warnings"}
    departure = payload["departure"]
    assert departure["stale"] is False
    assert departure["observed_at"].endswith("+00:00")
    assert isinstance(departure["taf_periods"], list)
