"""Décodage des éléments essentiels d'un METAR.

Le décodage reste volontairement partiel : on extrait ce qui décide d'un vol
(vent, visibilité, plafond, température, QNH, phénomènes) et on laisse le METAR
brut disponible pour le reste. Aucun appel réseau ici : la même fonction sert
aussi bien au METAR de l'OFP SimBrief qu'à celui récupéré en direct.

Le vent est référencé au **nord vrai**, comme dans navixav.weather.metar.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from navixav.models import STALE_AFTER_MINUTES, AirportWeather
from navixav.weather.metar import parse_wind

__all__ = [
    "STALE_AFTER_MINUTES",
    "ceiling_ft",
    "decode_metar",
    "flight_category",
    "parse_clouds",
    "parse_phenomena",
    "parse_visibility",
]

# « 251230Z » : jour du mois, heure et minute UTC.
_TIME_RE = re.compile(r"\b(?P<day>\d{2})(?P<hour>\d{2})(?P<minute>\d{2})Z\b")
# Visibilité métrique : « 9999 », « 0800 », éventuellement suivie d'un secteur.
_VIS_M_RE = re.compile(r"\b(?P<metres>\d{4})(?P<sector>[NSEW]{1,2})?\b")
# Visibilité en milles terrestres (Amérique du Nord) : « 10SM », « 1 1/2SM ».
_VIS_SM_RE = re.compile(r"\b(?:(?P<whole>\d{1,2})\s)?(?P<fraction>\d{1,2}(?:/\d{1,2})?)SM\b")
CLOUD_RE = re.compile(r"\b(?P<cover>FEW|SCT|BKN|OVC|VV)(?P<height>\d{3})(?P<type>CB|TCU)?\b")
_TEMP_RE = re.compile(r"(?<![\w/])(?P<temp>M?\d{2})/(?P<dew>M?\d{2})(?![\w/])")
_CAVOK_RE = re.compile(r"\bCAVOK\b")
_NOSIG_RE = re.compile(r"\bNOSIG\b")
_AUTO_RE = re.compile(r"\bAUTO\b")

# Phénomènes significatifs. L'intensité (« + », « - », « VC ») est conservée.
_PHENOMENA_RE = re.compile(
    r"(?P<intensity>[+-]|VC)?"
    r"(?P<descriptor>MI|BC|PR|DR|BL|SH|TS|FZ)?"
    r"(?P<phenomenon>DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)"
    r"(?P<extra>DZ|RA|SN|SG|PL|GR|GS)?\b"
)

_INTENSITY_LABELS = {"+": "forte", "-": "faible", "VC": "à proximité"}
_DESCRIPTOR_LABELS = {
    "MI": "mince",
    "BC": "en bancs",
    "PR": "partiel",
    "DR": "chasse-poussière basse",
    "BL": "chasse-poussière élevée",
    "SH": "averse de",
    "TS": "orage",
    "FZ": "verglaçant",
}
_PHENOMENON_LABELS = {
    "DZ": "bruine",
    "RA": "pluie",
    "SN": "neige",
    "SG": "neige en grains",
    "IC": "cristaux de glace",
    "PL": "granules de glace",
    "GR": "grêle",
    "GS": "grésil",
    "UP": "précipitation inconnue",
    "BR": "brume",
    "FG": "brouillard",
    "FU": "fumée",
    "VA": "cendres volcaniques",
    "DU": "poussière",
    "SA": "sable",
    "HZ": "brume sèche",
    "PY": "embruns",
    "PO": "tourbillons de poussière",
    "SQ": "grain",
    "FC": "tornade",
    "SS": "tempête de sable",
    "DS": "tempête de poussière",
}
_COVER_LABELS = {
    "FEW": "peu",
    "SCT": "épars",
    "BKN": "fragmenté",
    "OVC": "couvert",
    "VV": "ciel invisible",
}

# Les couches à partir desquelles on parle de plafond.
_CEILING_COVERS = frozenset({"BKN", "OVC", "VV"})

_SM_TO_M = 1609.344


def decode_metar(
    icao: str,
    metar: str | None,
    *,
    role: str = "",
    name: str = "",
    source: str = "",
    now: datetime | None = None,
) -> AirportWeather:
    """Décode les éléments essentiels d'un METAR. Tolérant : jamais d'exception."""
    report = AirportWeather(icao=icao.strip().upper(), name=name, role=role, source=source)
    if not metar or not metar.strip():
        return report

    text = " ".join(metar.split())
    report.raw_metar = text

    wind = parse_wind(text)
    report.wind = wind
    report.qnh_hpa = wind.qnh_hpa
    report.altimeter_inhg = wind.altimeter_inhg

    body = _strip_remarks(text)
    report.auto = bool(_AUTO_RE.search(body))
    report.no_significant_change = bool(_NOSIG_RE.search(body))
    report.cavok = bool(_CAVOK_RE.search(body))

    report.observed_at = _parse_observation_time(body, now=now)
    report.age_minutes = _age_minutes(report.observed_at, now=now)

    report.temperature_c, report.dew_point_c = _parse_temperature(body)
    report.spread_c = (
        report.temperature_c - report.dew_point_c
        if report.temperature_c is not None and report.dew_point_c is not None
        else None
    )

    if report.cavok:
        # CAVOK : visibilité 10 km ou plus et aucun nuage sous 5 000 ft.
        report.visibility_m = 10000
        report.clouds = []
    else:
        report.visibility_m = parse_visibility(body)
        report.clouds = parse_clouds(body)

    report.ceiling_ft = ceiling_ft(report.clouds)
    report.phenomena = parse_phenomena(body)
    report.flight_category = flight_category(report.visibility_m, report.ceiling_ft, report.cavok)
    return report


def _strip_remarks(metar: str) -> str:
    """Coupe la section RMK : elle contient des groupes non normalisés."""
    head = metar.split(" RMK", 1)[0]
    # Les tendances TEMPO/BECMG décrivent le futur, pas l'observation courante.
    for marker in (" TEMPO ", " BECMG "):
        head = head.split(marker, 1)[0]
    return head


def _parse_observation_time(metar: str, *, now: datetime | None) -> datetime | None:
    match = _TIME_RE.search(metar)
    if not match:
        return None

    reference = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    day, hour, minute = (int(match.group(key)) for key in ("day", "hour", "minute"))
    if not (1 <= day <= 31 and hour <= 23 and minute <= 59):
        return None

    # Le METAR ne porte ni mois ni année : on prend le mois courant, et le mois
    # précédent quand le jour est postérieur à aujourd'hui (bascule de mois).
    candidate = _with_day(reference, day)
    if candidate is None:
        return None
    if candidate > reference + timedelta(hours=6):
        previous = (reference.replace(day=1) - timedelta(days=1))
        candidate = _with_day(previous, day)
    if candidate is None:
        return None
    return candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _with_day(reference: datetime, day: int) -> datetime | None:
    try:
        return reference.replace(day=day)
    except ValueError:
        # Jour absent du mois (le 31 d'un mois court) : donnée inexploitable.
        return None


def _age_minutes(observed_at: datetime | None, *, now: datetime | None) -> int | None:
    if observed_at is None:
        return None
    reference = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    delta = reference - observed_at
    minutes = int(delta.total_seconds() // 60)
    return max(0, minutes)


def _parse_temperature(metar: str) -> tuple[int | None, int | None]:
    match = _TEMP_RE.search(metar)
    if not match:
        return None, None
    return _signed(match.group("temp")), _signed(match.group("dew"))


def _signed(token: str) -> int:
    return -int(token[1:]) if token.startswith("M") else int(token)


def parse_visibility(metar: str) -> int | None:
    statute = _VIS_SM_RE.search(metar)
    if statute:
        miles = float(int(statute.group("whole") or 0))
        fraction = statute.group("fraction")
        if "/" in fraction:
            numerator, denominator = fraction.split("/", 1)
            if int(denominator):
                miles += int(numerator) / int(denominator)
        else:
            miles += int(fraction)
        return round(miles * _SM_TO_M)

    # « 9999 » vaut « 10 km ou plus ». On ignore le groupe de vent, déjà lu.
    body = _WIND_GROUP_RE.sub(" ", metar)
    best: int | None = None
    for match in _VIS_M_RE.finditer(body):
        metres = int(match.group("metres"))
        if metres > 9999:
            continue
        # La visibilité principale précède les visibilités sectorielles ; on
        # garde la plus faible, qui est la plus contraignante.
        best = metres if best is None else min(best, metres)
    return best


_WIND_GROUP_RE = re.compile(
    r"\b(?:\d{3}|VRB)\d{2,3}(?:G\d{2,3})?(?:KT|MPS|KMH)\b|\b\d{3}V\d{3}\b"
)


def parse_clouds(metar: str) -> list[dict[str, object]]:
    layers: list[dict[str, object]] = []
    for match in CLOUD_RE.finditer(metar):
        cover = match.group("cover")
        height_ft = int(match.group("height")) * 100
        layers.append(
            {
                "cover": cover,
                "cover_label": _COVER_LABELS.get(cover, cover),
                "height_ft": height_ft,
                "convective": match.group("type") or None,
            }
        )
    layers.sort(key=lambda layer: layer["height_ft"])
    return layers


def ceiling_ft(clouds: list[dict[str, object]]) -> int | None:
    for layer in clouds:
        if layer["cover"] in _CEILING_COVERS:
            return int(layer["height_ft"])
    return None


def parse_phenomena(metar: str) -> list[dict[str, str]]:
    # Le corps du METAR commence après l'indicateur et l'horodatage : on évite
    # ainsi de lire l'OACI (« LFRN ») comme un groupe de phénomènes.
    body = _TIME_RE.split(metar, maxsplit=1)[-1]
    body = _WIND_GROUP_RE.sub(" ", body)
    body = CLOUD_RE.sub(" ", body)

    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in _PHENOMENA_RE.finditer(body):
        code = match.group(0)
        if code in seen:
            continue
        seen.add(code)
        found.append({"code": code, "label": _phenomenon_label(match)})
    return found


def _phenomenon_label(match: re.Match[str]) -> str:
    descriptor = match.group("descriptor")
    phenomenon = _PHENOMENON_LABELS.get(match.group("phenomenon"), match.group("phenomenon"))
    extra = match.group("extra")

    if descriptor == "TS":
        label = f"orage avec {phenomenon}" if match.group("phenomenon") else "orage"
    elif descriptor == "SH":
        label = f"averse de {phenomenon}"
    elif descriptor == "FZ":
        label = f"{phenomenon} verglaçante"
    elif descriptor:
        label = f"{phenomenon} {_DESCRIPTOR_LABELS[descriptor]}"
    else:
        label = phenomenon

    if extra:
        label = f"{label} et {_PHENOMENON_LABELS.get(extra, extra)}"

    intensity = match.group("intensity")
    if intensity == "VC":
        return f"{label} à proximité"
    if intensity:
        return f"{label} {_INTENSITY_LABELS[intensity]}"
    return label


def flight_category(
    visibility_m: int | None, ceiling_ft: int | None, cavok: bool
) -> str | None:
    """Catégorie de vol OACI/FAA : LIFR, IFR, MVFR ou VFR."""
    if cavok:
        return "VFR"
    if visibility_m is None and ceiling_ft is None:
        return None

    # Une donnée absente ne doit pas dégrader la catégorie : on la neutralise.
    visibility_sm = (visibility_m / _SM_TO_M) if visibility_m is not None else float("inf")
    ceiling = ceiling_ft if ceiling_ft is not None else 99_999

    if ceiling < 500 or visibility_sm < 1:
        return "LIFR"
    if ceiling < 1000 or visibility_sm < 3:
        return "IFR"
    if ceiling <= 3000 or visibility_sm <= 5:
        return "MVFR"
    return "VFR"
