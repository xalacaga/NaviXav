"""SIGMET en vigueur, lus sur aviationweather.gov et rapportés à la route.

Deux flux sans clé API couvrent le monde : les SIGMET internationaux, émis
par chaque FIR, et les SIGMET intérieurs américains, dont les SIGMET
convectifs. Ils sont ramenés à une même forme : phénomène, niveaux, validité
et un ou plusieurs polygones en latitude/longitude.

Le relevé est gardé quelques minutes : un SIGMET vaut quatre à six heures et
le service n'a pas à être interrogé à chaque rafraîchissement de la carte.
Un flux indisponible n'efface pas l'autre, et une panne complète garde le
dernier relevé plutôt que de faire disparaître la couche.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Sequence

import requests

LOGGER = logging.getLogger(__name__)

AWC_ISIGMET_URL = "https://aviationweather.gov/api/data/isigmet"
AWC_AIRSIGMET_URL = "https://aviationweather.gov/api/data/airsigmet"
DEFAULT_TIMEOUT = 15
CACHE_SECONDS = 600
RETRY_SECONDS = 60
# Au-delà de cette distance de la route, un SIGMET ne concerne pas le vol.
CORRIDOR_NM = 150.0
# Pas d'échantillonnage de la route pour le test d'intersection : plus fin
# que le plus petit SIGMET de zone utile.
ROUTE_STEP_NM = 10.0
EARTH_RADIUS_NM = 3440.065

# Les deux flux ne nomment pas les phénomènes de la même façon.
_HAZARDS = {
    "CONVECTIVE": "TS",
    "TS": "TS",
    "TSGR": "TS",
    "TURB": "TURB",
    "ICE": "ICE",
    "ICING": "ICE",
    "MTW": "MTW",
    "VA": "VA",
    "ASH": "VA",
    "TC": "TC",
    "RDOACT": "RDOACT",
    "DS": "DS",
    "SS": "DS",
}
# Types du flux américain qui ne sont pas des SIGMET en vigueur.
_SKIPPED_US_TYPES = frozenset({"OUTLOOK", "AIRMET"})

Point = tuple[float, float]


@dataclass(frozen=True)
class Sigmet:
    id: str
    hazard: str
    qualifier: str
    fir: str
    base_ft: int | None
    top_ft: int | None
    valid_from: int
    valid_to: int
    polygons: list[list[Point]]
    raw: str
    on_route: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["polygons"] = [[[lat, lon] for lat, lon in ring] for ring in self.polygons]
        return data


def _number(value: Any) -> int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if math.isfinite(number) else None


def _ring(coords: Any) -> list[Point]:
    ring: list[Point] = []
    for item in coords or []:
        if not isinstance(item, dict):
            continue
        try:
            lat, lon = float(item["lat"]), float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(lat) and math.isfinite(lon):
            ring.append((lat, lon))
    return ring if len(ring) >= 3 else []


def _rings(coords: Any) -> list[list[Point]]:
    """Un polygone, ou plusieurs quand le SIGMET couvre des zones disjointes."""
    if not isinstance(coords, list) or not coords:
        return []
    if isinstance(coords[0], list):
        return [ring for ring in (_ring(part) for part in coords) if ring]
    ring = _ring(coords)
    return [ring] if ring else []


def _hazard(value: Any) -> str:
    text = str(value or "").strip().upper()
    return _HAZARDS.get(text, text or "OTHER")


def parse_international(items: Iterable[dict[str, Any]]) -> list[Sigmet]:
    sigmets = []
    for item in items:
        polygons = _rings(item.get("coords"))
        start, end = _number(item.get("validTimeFrom")), _number(item.get("validTimeTo"))
        if not polygons or start is None or end is None:
            continue
        fir = str(item.get("firId") or "").strip()
        series = str(item.get("seriesId") or "").strip()
        sigmets.append(Sigmet(
            id=f"I-{fir}-{series}-{start}",
            hazard=_hazard(item.get("hazard")),
            qualifier=str(item.get("qualifier") or "").strip().upper(),
            fir=fir,
            base_ft=_number(item.get("base")),
            top_ft=_number(item.get("top")),
            valid_from=start,
            valid_to=end,
            polygons=polygons,
            raw=str(item.get("rawSigmet") or "").strip(),
        ))
    return sigmets


def parse_us(items: Iterable[dict[str, Any]]) -> list[Sigmet]:
    sigmets = []
    for item in items:
        kind = str(item.get("airSigmetType") or "").strip().upper()
        if kind in _SKIPPED_US_TYPES:
            continue
        polygons = _rings(item.get("coords"))
        start, end = _number(item.get("validTimeFrom")), _number(item.get("validTimeTo"))
        if not polygons or start is None or end is None:
            continue
        lows = [v for v in (_number(item.get("altitudeLow1")), _number(item.get("altitudeLow2")))
                if v is not None]
        highs = [v for v in (_number(item.get("altitudeHi1")), _number(item.get("altitudeHi2")))
                 if v is not None]
        series = str(item.get("seriesId") or "").strip()
        severity = _number(item.get("severity")) or 0
        sigmets.append(Sigmet(
            id=f"US-{series}-{start}",
            hazard=_hazard(item.get("hazard")),
            qualifier="SEV" if severity >= 4 else "",
            fir=str(item.get("icaoId") or "").strip(),
            base_ft=min(lows) if lows else None,
            top_ft=max(highs) if highs else None,
            valid_from=start,
            valid_to=end,
            polygons=polygons,
            raw=str(item.get("rawAirSigmet") or "").strip(),
        ))
    return sigmets


def active(sigmets: Iterable[Sigmet], now: float) -> list[Sigmet]:
    return [s for s in sigmets if s.valid_from <= now <= s.valid_to]


# ------------------------------------------------------------- géométrie


def _distance_nm(a: Point, b: Point) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_NM * math.asin(min(1.0, math.sqrt(h)))


def _wrap(lon: float, reference: float) -> float:
    """Longitude ramenée près de la référence : l'antiméridien ne coupe rien."""
    while lon - reference > 180:
        lon -= 360
    while lon - reference < -180:
        lon += 360
    return lon


def densify(route: Sequence[Point], step_nm: float = ROUTE_STEP_NM) -> list[Point]:
    """Points de la route tous les `step_nm` au plus, interpolés linéairement."""
    samples: list[Point] = []
    for index, point in enumerate(route):
        if index == 0:
            samples.append(point)
            continue
        previous = route[index - 1]
        lon = _wrap(point[1], previous[1])
        steps = max(1, math.ceil(_distance_nm(previous, point) / step_nm))
        for k in range(1, steps + 1):
            f = k / steps
            samples.append((
                previous[0] + (point[0] - previous[0]) * f,
                _wrap(previous[1] + (lon - previous[1]) * f, 0.0),
            ))
    return samples


def _unwrapped(ring: Sequence[Point]) -> list[Point]:
    """Anneau aux longitudes continues : un SIGMET à cheval sur l'antiméridien
    reste d'un seul tenant au lieu de s'étirer autour du globe."""
    result: list[Point] = []
    for lat, lon in ring:
        result.append((lat, _wrap(lon, result[-1][1]) if result else lon))
    return result


def contains(ring: Sequence[Point], point: Point) -> bool:
    """Point dans le polygone (règle pair-impair, longitudes continues)."""
    return _inside(_unwrapped(ring), point)


def _inside(ring: Sequence[Point], point: Point) -> bool:
    lat = point[0]
    centre = sum(vertex[1] for vertex in ring) / len(ring)
    lon = _wrap(point[1], centre)
    inside = False
    count = len(ring)
    for index in range(count):
        lat_a, lon_a = ring[index]
        lat_b, lon_b = ring[(index + 1) % count]
        if (lat_a > lat) != (lat_b > lat):
            crossing = lon_a + (lat - lat_a) * (lon_b - lon_a) / (lat_b - lat_a)
            if lon < crossing:
                inside = not inside
    return inside


def _near(ring: Sequence[Point], samples: Sequence[Point], margin_nm: float) -> bool:
    return any(_distance_nm(vertex, sample) <= margin_nm
               for vertex in ring for sample in samples[::3] or samples)


def _vertical_overlap(sigmet: Sigmet, cruise_ft: int | None) -> bool:
    """La route traverse tous les niveaux jusqu'à la croisière."""
    if cruise_ft is None or sigmet.base_ft is None:
        return True
    return sigmet.base_ft <= cruise_ft


def relate_to_route(
    sigmets: Iterable[Sigmet],
    route: Sequence[Point],
    cruise_ft: int | None,
    corridor_nm: float = CORRIDOR_NM,
) -> list[Sigmet]:
    """SIGMET proches de la route, marqués quand la route les traverse."""
    samples = densify(route)
    if not samples:
        return list(sigmets)
    # Un degré de latitude vaut soixante nautiques : hors de cette bande, un
    # SIGMET ne peut ni croiser la route ni s'en approcher.
    margin_deg = corridor_nm / 60.0
    south = min(lat for lat, _lon in samples) - margin_deg
    north = max(lat for lat, _lon in samples) + margin_deg
    related = []
    for sigmet in sigmets:
        rings = [_unwrapped(ring) for ring in sigmet.polygons
                 if min(lat for lat, _lon in ring) <= north
                 and max(lat for lat, _lon in ring) >= south]
        if not rings:
            continue
        crossed = any(_inside(ring, sample) for ring in rings for sample in samples)
        if not crossed and not any(_near(ring, samples, corridor_nm) for ring in rings):
            continue
        on_route = crossed and _vertical_overlap(sigmet, cruise_ft)
        related.append(Sigmet(**{**asdict(sigmet), "on_route": on_route}))
    related.sort(key=lambda s: (not s.on_route, s.hazard, s.id))
    return related


# ------------------------------------------------------------- service


@dataclass
class SigmetFeed:
    """Relevé mondial des SIGMET, gardé `CACHE_SECONDS` secondes."""

    session: requests.Session = field(default_factory=requests.Session)
    timeout: int = DEFAULT_TIMEOUT
    cache_seconds: float = CACHE_SECONDS
    _sigmets: list[Sigmet] = field(default_factory=list)
    _fetched_at: float = 0.0
    _wall: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _get(self, url: str) -> list[dict[str, Any]] | None:
        try:
            response = self.session.get(
                url, params={"format": "json"}, timeout=self.timeout,
                headers={"User-Agent": "NaviXav"},
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            LOGGER.warning("SIGMET indisponibles (%s) : %s", url.rsplit("/", 1)[-1],
                           type(exc).__name__)
            return None
        return data if isinstance(data, list) else []

    def current(self, now: float | None = None) -> tuple[list[Sigmet], float]:
        """SIGMET en vigueur et instant du relevé (horloge murale)."""
        with self._lock:
            monotonic = time.monotonic()
            if not self._fetched_at or monotonic - self._fetched_at >= self.cache_seconds:
                started = time.perf_counter()
                international = self._get(AWC_ISIGMET_URL)
                us = self._get(AWC_AIRSIGMET_URL)
                if international is not None or us is not None:
                    fresh = parse_international(international or []) + parse_us(us or [])
                    # Un flux muet garde ses SIGMET du relevé précédent.
                    if international is None:
                        fresh += [s for s in self._sigmets if s.id.startswith("I-")]
                    if us is None:
                        fresh += [s for s in self._sigmets if s.id.startswith("US-")]
                    self._sigmets = fresh
                    self._fetched_at = monotonic
                    self._wall = time.time()
                    LOGGER.info("SIGMET relevés : %d en %.2f s", len(fresh),
                                time.perf_counter() - started)
                elif not self._fetched_at:
                    raise requests.ConnectionError("aviationweather.gov injoignable")
                else:
                    # Panne : le relevé précédent reste affiché et le service
                    # n'est réinterrogé qu'une minute plus tard.
                    self._fetched_at = monotonic - self.cache_seconds + RETRY_SECONDS
            return active(self._sigmets, time.time() if now is None else now), self._wall

    def close(self) -> None:
        self.session.close()
