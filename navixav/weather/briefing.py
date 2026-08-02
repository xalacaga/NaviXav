"""Assemblage du briefing météo : départ, croisière, arrivée et dégagement.

Le briefing réutilise les METAR déjà lus par le moteur pour le choix de piste :
aucun terrain n'est interrogé deux fois. La croisière ne déclenche aucun appel
réseau, elle provient des vents et températures déjà calculés par SimBrief pour
l'OFP.
"""

from __future__ import annotations

from collections.abc import Callable

from navixav.models import AirportWeather, EnrouteWeather, WeatherBriefing
from navixav.simbrief.parser import OfpSummary
from navixav.weather.decode import decode_metar
from navixav.weather.metar import fetch_metar
from navixav.weather.taf import fetch_taf, summarise_taf

# Valeurs de metar_source qui autorisent une interrogation d'aviationweather.gov.
LIVE_SOURCES = frozenset({"awc", "live"})

# Un écart température/point de rosée sous ce seuil annonce brume ou brouillard.
FOG_RISK_SPREAD_C = 3
# En dessous, le givrage carburateur et la contamination piste deviennent un sujet.
FREEZING_TEMPERATURE_C = 3

MetarFetcher = Callable[[str], str | None]
TafFetcher = Callable[[str], str | None]


def build_briefing(
    ofp: OfpSummary,
    *,
    metar_source: str = "simbrief",
    departure_metar: str | None = None,
    arrival_metar: str | None = None,
    metar_fetcher: MetarFetcher = fetch_metar,
    taf_fetcher: TafFetcher = fetch_taf,
    force_live: bool = False,
) -> WeatherBriefing:
    """Construit le briefing météo du vol.

    `departure_metar` et `arrival_metar` sont les METAR déjà retenus par le
    moteur : les passer évite de réinterroger le service météo.
    """
    briefing = WeatherBriefing()
    live = metar_source.strip().lower() in LIVE_SOURCES

    briefing.departure = _airport(
        ofp.origin_icao,
        role="departure",
        metar=departure_metar or ofp.origin_metar,
        taf=ofp.origin_taf,
        live=live,
        force_live=force_live,
        metar_fetcher=metar_fetcher,
        taf_fetcher=taf_fetcher,
    )
    briefing.arrival = _airport(
        ofp.destination_icao,
        role="arrival",
        metar=arrival_metar or ofp.destination_metar,
        taf=ofp.destination_taf,
        live=live,
        force_live=force_live,
        metar_fetcher=metar_fetcher,
        taf_fetcher=taf_fetcher,
    )
    if ofp.alternate_icao:
        briefing.alternate = _airport(
            ofp.alternate_icao,
            role="alternate",
            metar=ofp.dispatch.alternate_metar,
            taf=ofp.dispatch.alternate_taf,
            live=live,
            force_live=force_live,
            metar_fetcher=metar_fetcher,
            taf_fetcher=taf_fetcher,
        )

    briefing.enroute = _enroute(ofp)
    briefing.warnings = _warnings(briefing)
    return briefing


def _airport(
    icao: str,
    *,
    role: str,
    metar: str | None,
    taf: str | None,
    live: bool,
    force_live: bool,
    metar_fetcher: MetarFetcher,
    taf_fetcher: TafFetcher,
) -> AirportWeather | None:
    if not icao:
        return None

    source = "simbrief" if metar else ""
    # Le dégagement n'est pas passé par le moteur : il peut manquer de METAR.
    # On ne va le chercher que si la source météo réglée l'autorise.
    if live and (force_live or not metar):
        fetched = metar_fetcher(icao)
        if fetched:
            metar, source = fetched, "awc"

    report = decode_metar(icao, metar, role=role, source=source)

    # Le TAF n'est complété par le réseau que si l'utilisateur a demandé une
    # source live : en mode « simbrief », le briefing se limite à ce que porte
    # l'OFP et ne rallonge jamais le calcul du plan d'un appel sortant.
    if live and (force_live or not taf):
        fetched_taf = taf_fetcher(icao)
        if fetched_taf:
            taf = fetched_taf
    if taf:
        report.raw_taf = " ".join(taf.split())
        report.taf_periods = summarise_taf(report.raw_taf)

    report.notes = _notes(report)
    return report


def _notes(report: AirportWeather) -> list[str]:
    """Points d'attention déduits du METAR, sans jamais inventer de minima."""
    notes: list[str] = []
    if report.raw_metar is None:
        notes.append("Aucun METAR disponible pour ce terrain.")
        return notes

    if report.stale and report.age_minutes is not None:
        notes.append(f"Observation vieille de {_age_label(report.age_minutes)}.")
    if report.spread_c is not None and report.spread_c <= FOG_RISK_SPREAD_C:
        notes.append(
            f"Écart température/point de rosée de {report.spread_c} °C : "
            "risque de brume ou de brouillard."
        )
    if report.temperature_c is not None and report.temperature_c <= FREEZING_TEMPERATURE_C:
        notes.append("Température basse : givrage et état de piste à vérifier.")
    if report.wind.gust_kt is not None:
        notes.append(f"Rafales à {report.wind.gust_kt} kt.")
    if report.flight_category in {"IFR", "LIFR"}:
        notes.append("Conditions IFR basses : vérifier les minima de l'approche.")
    return notes


def _age_label(minutes: int) -> str:
    """« 10 111 min » ne se lit pas : au-delà de l'heure, on passe à h puis à j."""
    if minutes < 60:
        return f"{minutes} min"
    if minutes < 48 * 60:
        hours, remainder = divmod(minutes, 60)
        return f"{hours} h {remainder:02d}" if remainder else f"{hours} h"
    return f"{minutes // (24 * 60)} jours"


def _enroute(ofp: OfpSummary) -> EnrouteWeather:
    dispatch = ofp.dispatch
    enroute = EnrouteWeather(
        cruise_altitude_ft=ofp.cruise_altitude_ft,
        wind_direction_deg=_int(dispatch.average_wind_direction),
        wind_speed_kt=_int(dispatch.average_wind_speed),
        wind_component_kt=_int(dispatch.average_wind_component),
        temperature_dev_c=_int(dispatch.average_temperature_dev),
        tropopause_ft=dispatch.tropopause_ft,
    )
    enroute.outside_air_temperature_c = _oat(
        enroute.cruise_altitude_ft, enroute.temperature_dev_c
    )

    if enroute.wind_component_kt is not None:
        if enroute.wind_component_kt < 0:
            enroute.notes.append(
                f"Vent de face moyen de {abs(enroute.wind_component_kt)} kt."
            )
        elif enroute.wind_component_kt > 0:
            enroute.notes.append(
                f"Vent arrière moyen de {enroute.wind_component_kt} kt."
            )
    if enroute.temperature_dev_c is not None and enroute.temperature_dev_c >= 10:
        enroute.notes.append(
            f"ISA +{enroute.temperature_dev_c} : plafond et performances dégradés."
        )
    if (
        enroute.tropopause_ft is not None
        and enroute.cruise_altitude_ft is not None
        and enroute.cruise_altitude_ft >= enroute.tropopause_ft
    ):
        enroute.notes.append("Croisière au niveau de la tropopause ou au-dessus.")
    return enroute


def _oat(cruise_altitude_ft: int | None, temperature_dev_c: int | None) -> int | None:
    """Température extérieure estimée : atmosphère standard plus l'écart ISA."""
    if cruise_altitude_ft is None or temperature_dev_c is None:
        return None
    # Standard : 15 °C au niveau de la mer, −1,98 °C par 1 000 ft, plancher à
    # −56,5 °C au-dessus de la tropopause standard (36 090 ft).
    standard = 15.0 - 1.98 * (min(cruise_altitude_ft, 36090) / 1000)
    return round(standard + temperature_dev_c)


def _warnings(briefing: WeatherBriefing) -> list[str]:
    warnings: list[str] = []
    for report in (briefing.departure, briefing.arrival, briefing.alternate):
        if report is None:
            continue
        if report.raw_metar is None:
            warnings.append(f"Météo indisponible pour {report.icao}.")
        elif report.flight_category == "LIFR":
            warnings.append(f"{report.icao} en conditions LIFR.")
    return warnings


def _int(value: str | int | None) -> int | None:
    """Les champs de profil SimBrief arrivent en texte, parfois signés ou vides."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    token = value.strip().replace("+", "")
    if not token:
        return None
    try:
        return int(float(token))
    except ValueError:
        return None
