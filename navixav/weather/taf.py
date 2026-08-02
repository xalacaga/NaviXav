"""Récupération et résumé des TAF.

Un TAF complet est trop long pour un briefing de cockpit : on ne garde que les
créneaux qui changent la donne — dégradation de la catégorie de vol, vent fort
ou rafales, phénomène significatif. Le TAF brut reste disponible.
"""

from __future__ import annotations

import re

import requests

from navixav.models import TafPeriod
from navixav.weather.decode import (
    CLOUD_RE,
    ceiling_ft,
    flight_category,
    parse_clouds,
    parse_phenomena,
    parse_visibility,
)
from navixav.weather.metar import parse_wind

AWC_TAF_URL = "https://aviationweather.gov/api/data/taf"
DEFAULT_TIMEOUT = 15

# Le TAF n'est pertinent qu'à partir de ces seuils opérationnels.
SIGNIFICANT_GUST_KT = 25
SIGNIFICANT_WIND_KT = 25
DEGRADED_CATEGORIES = frozenset({"MVFR", "IFR", "LIFR"})

# Découpe le TAF en créneaux : l'en-tête, puis chaque FM/TEMPO/BECMG/PROB.
_CHANGE_RE = re.compile(r"\b(FM\d{6}|TEMPO|BECMG|PROB[34]0(?:\s+TEMPO)?)\b")
_FM_RE = re.compile(r"^FM(?P<day>\d{2})(?P<hour>\d{2})(?P<minute>\d{2})$")
_VALIDITY_RE = re.compile(r"\b(?P<from>\d{4})/(?P<to>\d{4})\b")


def fetch_taf(icao: str, timeout: int = DEFAULT_TIMEOUT) -> str | None:
    """Récupère le TAF courant depuis aviationweather.gov (sans clé API)."""
    try:
        response = requests.get(
            AWC_TAF_URL,
            params={"ids": icao.strip().upper(), "format": "raw"},
            timeout=timeout,
            headers={"User-Agent": "NaviXav/0.1"},
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    text = response.text.strip()
    if not text or text.lower().startswith("<!doctype"):
        return None
    # L'endpoint « raw » renvoie le TAF sur plusieurs lignes : on le remet à plat.
    flat = " ".join(text.split())
    return flat or None


def summarise_taf(taf: str | None, *, limit: int = 4) -> list[TafPeriod]:
    """Ne retient que les créneaux du TAF qui changent la donne."""
    if not taf or not taf.strip():
        return []

    periods = [_decode_period(kind, body) for kind, body in _split_periods(taf)]
    if not periods:
        return []

    # La tendance de base est toujours conservée : sans elle, un TEMPO isolé
    # se lit sans référence. Les créneaux suivants ne passent que s'ils changent
    # la donne.
    baseline = periods[0]
    retained = [baseline]
    for period in periods[1:]:
        if _is_significant(period, baseline):
            retained.append(period)
    return retained[:limit]


def _split_periods(taf: str) -> list[tuple[str, str]]:
    text = " ".join(taf.split())
    # On retire l'en-tête administratif pour ne garder que le corps prévisionnel.
    text = re.sub(r"^TAF\s+(?:AMD\s+|COR\s+)?", "", text.strip())

    tokens = _CHANGE_RE.split(text)
    periods: list[tuple[str, str]] = []
    head = tokens[0].strip()
    if head:
        periods.append(("base", head))
    for marker, body in zip(tokens[1::2], tokens[2::2]):
        periods.append((marker.strip(), body.strip()))
    return periods


def _decode_period(kind: str, body: str) -> TafPeriod:
    raw = f"{kind} {body}".strip() if kind != "base" else body
    period = TafPeriod(kind=_normalise_kind(kind), raw=raw)
    period.from_time, period.to_time = _period_window(kind, body)

    wind = parse_wind(body)
    # parse_wind renvoie un WindInfo vide plutôt que None quand il ne trouve rien.
    period.wind = wind if wind.speed_kt is not None or wind.variable else None

    # « 0212/0318 » est une fenêtre de validité : sans le retirer, ses quatre
    # premiers chiffres se lisent comme une visibilité de 212 m.
    forecast = _VALIDITY_RE.sub(" ", body)
    # Les couches nuageuses ne doivent pas non plus être lues comme une visibilité.
    period.visibility_m = parse_visibility(CLOUD_RE.sub(" ", forecast))
    period.ceiling_ft = ceiling_ft(parse_clouds(forecast))
    period.phenomena = parse_phenomena(forecast)
    period.flight_category = flight_category(
        period.visibility_m, period.ceiling_ft, "CAVOK" in forecast
    )
    return period


def _normalise_kind(kind: str) -> str:
    if kind.startswith("FM"):
        return "FM"
    return kind or "base"


def _period_window(kind: str, body: str) -> tuple[str | None, str | None]:
    """Fenêtre du créneau au format « JJHH » (jour du mois et heure UTC)."""
    match = _FM_RE.match(kind)
    if match:
        return f"{match.group('day')}{match.group('hour')}", None

    validity = _VALIDITY_RE.search(body)
    if validity:
        return validity.group("from"), validity.group("to")
    return None, None


def _is_significant(period: TafPeriod, baseline: TafPeriod | None) -> bool:
    if period.phenomena:
        return True
    if period.flight_category in DEGRADED_CATEGORIES:
        # Une dégradation par rapport à la base est ce qui intéresse le pilote.
        if baseline is None or period.flight_category != baseline.flight_category:
            return True
    wind = period.wind
    if wind:
        if wind.gust_kt is not None and wind.gust_kt >= SIGNIFICANT_GUST_KT:
            return True
        if wind.speed_kt is not None and wind.speed_kt >= SIGNIFICANT_WIND_KT:
            return True
    return False
