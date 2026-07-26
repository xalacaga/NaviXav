"""Lecture du vent depuis un METAR.

Rappel important pour le choix de piste : le vent d'un METAR est référencé au
**nord vrai**, alors que le vent annoncé par la tour ou l'ATIS est magnétique.
Les caps de piste de la base de navigation étant eux aussi vrais, la
comparaison directe est cohérente.
"""

from __future__ import annotations

import re

import requests

from navixav.models import WindInfo

AWC_URL = "https://aviationweather.gov/api/data/metar"
DEFAULT_TIMEOUT = 15

_WIND_RE = re.compile(
    r"\b(?P<dir>\d{3}|VRB)(?P<speed>\d{2,3})(?:G(?P<gust>\d{2,3}))?(?P<unit>KT|MPS|KMH)\b"
)
_QNH_RE = re.compile(r"\bQ(?P<hpa>\d{4})\b")
_ALTIMETER_RE = re.compile(r"\bA(?P<hundredths>\d{4})\b")

_UNIT_TO_KT = {"KT": 1.0, "MPS": 1.94384, "KMH": 0.539957}


def parse_wind(metar: str | None) -> WindInfo:
    """Extrait le vent d'un METAR brut. Tolérant : renvoie un WindInfo vide."""
    if not metar:
        return WindInfo()

    text = metar.strip()
    qnh_hpa, altimeter_inhg = _parse_pressure(text)
    match = _WIND_RE.search(text)
    if not match:
        return WindInfo(
            raw_metar=text,
            qnh_hpa=qnh_hpa,
            altimeter_inhg=altimeter_inhg,
        )

    factor = _UNIT_TO_KT[match.group("unit")]
    speed = round(int(match.group("speed")) * factor)
    gust_raw = match.group("gust")
    gust = round(int(gust_raw) * factor) if gust_raw else None

    direction_token = match.group("dir")
    if direction_token == "VRB":
        return WindInfo(
            raw_metar=text, direction_deg=None, speed_kt=speed, gust_kt=gust,
            variable=True, qnh_hpa=qnh_hpa, altimeter_inhg=altimeter_inhg,
        )

    direction = int(direction_token) % 360
    # « 00000KT » : calme, aucune direction exploitable.
    if direction == 0 and speed == 0:
        return WindInfo(
            raw_metar=text,
            direction_deg=None,
            speed_kt=0,
            variable=False,
            qnh_hpa=qnh_hpa,
            altimeter_inhg=altimeter_inhg,
        )

    return WindInfo(
        raw_metar=text, direction_deg=direction, speed_kt=speed, gust_kt=gust,
        variable=False, qnh_hpa=qnh_hpa, altimeter_inhg=altimeter_inhg,
    )


def _parse_pressure(metar: str) -> tuple[int | None, float | None]:
    qnh = _QNH_RE.search(metar)
    if qnh:
        hpa = int(qnh.group("hpa"))
        return hpa, round(hpa / 33.8639, 2)

    altimeter = _ALTIMETER_RE.search(metar)
    if altimeter:
        inhg = int(altimeter.group("hundredths")) / 100
        return round(inhg * 33.8639), inhg
    return None, None


def fetch_metar(icao: str, timeout: int = DEFAULT_TIMEOUT) -> str | None:
    """Récupère le METAR courant depuis aviationweather.gov (sans clé API)."""
    try:
        response = requests.get(
            AWC_URL,
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
    # L'endpoint « raw » peut renvoyer plusieurs lignes : on garde la première.
    return text.splitlines()[0].strip() or None
