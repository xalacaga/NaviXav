"""Comptes rendus de turbulence des pilotes (PIREP et AIREP), près de la route.

aviationweather.gov publie sans clé les comptes rendus des trois dernières
heures : PIREP américains et AIREP du monde entier. Ce sont des observations,
pas des prévisions — un avion a réellement rencontré cette turbulence, à ce
niveau, à cette heure. Ils sont demandés dans le cadre de la route, gardés
quelques minutes, et rapportés au vol : distance à la route, et proximité du
niveau de croisière.

Un compte rendu « NEG » (vol calme) est gardé aussi : savoir qu'un avion est
passé sans secousse à son niveau vaut autant que l'inverse.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

import requests

from navixav.weather.sigmet import _distance_nm, densify

LOGGER = logging.getLogger(__name__)

AWC_PIREP_URL = "https://aviationweather.gov/api/data/pirep"
DEFAULT_TIMEOUT = 15
CACHE_SECONDS = 300
AGE_HOURS = 3
CORRIDOR_NM = 100.0
# Un compte rendu à moins de cette hauteur du niveau de croisière concerne le vol.
LEVEL_MARGIN_FT = 4000

# Intensités, de la plus faible à la plus forte. Les formes composées
# (« LGT-MOD ») prennent la plus forte : c'est celle qu'il faut prévoir.
_RANKS = {"NEG": 0, "SMTH": 0, "LGT": 1, "LIGHT": 1, "MOD": 2, "SEV": 3, "EXTRM": 4, "EXTREME": 4}


@dataclass(frozen=True)
class TurbulenceReport:
    id: str
    kind: str
    latitude: float
    longitude: float
    level_ft: int | None
    observed: int
    intensity: str
    rank: int
    type: str
    base_ft: int | None
    top_ft: int | None
    aircraft: str
    raw: str
    route_distance_nm: float | None = None
    near_level: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _hundreds(value: Any) -> int | None:
    """Niveaux publiés en centaines de pieds (« 339 » pour 33 900 ft)."""
    number = _number(value)
    return int(number * 100) if number is not None else None


def intensity_rank(text: str) -> tuple[str, int] | None:
    """« MOD-SEV » -> (« MOD-SEV », 3) ; None si aucune intensité lisible."""
    parts = [part for part in str(text or "").upper().replace(" ", "-").split("-") if part]
    ranks = [_RANKS[part] for part in parts if part in _RANKS]
    if not ranks:
        return None
    return "-".join(parts), max(ranks)


def parse(items: Sequence[dict[str, Any]]) -> list[TurbulenceReport]:
    reports = []
    for item in items:
        if not isinstance(item, dict):
            continue
        intensity = intensity_rank(item.get("tbInt1"))
        latitude, longitude = _number(item.get("lat")), _number(item.get("lon"))
        observed = _number(item.get("obsTime"))
        if intensity is None or latitude is None or longitude is None or observed is None:
            continue
        label, rank = intensity
        reports.append(TurbulenceReport(
            id=f"{item.get('pirepType') or 'PIREP'}-{int(observed)}-{latitude:.2f}-{longitude:.2f}",
            kind=str(item.get("pirepType") or "PIREP").upper(),
            latitude=latitude,
            longitude=longitude,
            level_ft=_hundreds(item.get("fltLvl")),
            observed=int(observed),
            intensity=label,
            rank=rank,
            type=str(item.get("tbType1") or "").strip().upper(),
            base_ft=_hundreds(item.get("tbBas1")),
            top_ft=_hundreds(item.get("tbTop1")),
            aircraft=str(item.get("acType") or "").strip(),
            raw=str(item.get("rawOb") or "").strip(),
        ))
    return reports


def _near_level(report: TurbulenceReport, cruise_ft: int | None) -> bool:
    if cruise_ft is None:
        return False
    if report.base_ft is not None and report.top_ft is not None:
        return report.base_ft - LEVEL_MARGIN_FT <= cruise_ft <= report.top_ft + LEVEL_MARGIN_FT
    return report.level_ft is not None and abs(report.level_ft - cruise_ft) <= LEVEL_MARGIN_FT


def relate_to_route(
    reports: Sequence[TurbulenceReport],
    route: Sequence[tuple[float, float]],
    cruise_ft: int | None,
    corridor_nm: float = CORRIDOR_NM,
) -> list[TurbulenceReport]:
    """Comptes rendus dans le couloir de la route, les plus pertinents d'abord."""
    samples = densify(route) if route else []
    related = []
    for report in reports:
        distance = None
        if samples:
            distance = min(_distance_nm((report.latitude, report.longitude), point) for point in samples[::2] or samples)
            if distance > corridor_nm:
                continue
        related.append(TurbulenceReport(**{
            **asdict(report),
            "route_distance_nm": round(distance, 1) if distance is not None else None,
            "near_level": _near_level(report, cruise_ft),
        }))
    related.sort(key=lambda r: (not r.near_level, -r.rank, -r.observed))
    return related


def bounding_box(route: Sequence[tuple[float, float]], margin_nm: float = CORRIDOR_NM) -> tuple[float, float, float, float] | None:
    """Cadre de la route élargi du couloir, arrondi pour le cache."""
    if not route:
        return None
    margin = margin_nm / 60.0 + 0.5
    south = max(-90.0, math.floor(min(lat for lat, _ in route) - margin))
    north = min(90.0, math.ceil(max(lat for lat, _ in route) + margin))
    west = max(-180.0, math.floor(min(lon for _, lon in route) - margin * 1.5))
    east = min(180.0, math.ceil(max(lon for _, lon in route) + margin * 1.5))
    return south, west, north, east


@dataclass
class PirepFeed:
    """Comptes rendus des trois dernières heures, par cadre de route."""

    session: requests.Session = field(default_factory=requests.Session)
    timeout: int = DEFAULT_TIMEOUT
    cache_seconds: float = CACHE_SECONDS
    _cache: dict[tuple, tuple[float, list[TurbulenceReport], float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def current(self, box: tuple[float, float, float, float] | None) -> tuple[list[TurbulenceReport], float]:
        """Comptes rendus du cadre, et instant du relevé (horloge murale)."""
        key = box or ()
        with self._lock:
            cached = self._cache.get(key)
            now = time.monotonic()
            if cached and now - cached[0] < self.cache_seconds:
                return cached[1], cached[2]
            params: dict[str, Any] = {"format": "json", "age": AGE_HOURS}
            if box:
                params["bbox"] = ",".join(f"{value:g}" for value in box)
            started = time.perf_counter()
            try:
                response = self.session.get(
                    AWC_PIREP_URL, params=params, timeout=self.timeout,
                    headers={"User-Agent": "NaviXav flight-simulation weather map"},
                )
                response.raise_for_status()
                data = response.json() if response.content else []
            except (requests.RequestException, ValueError) as exc:
                LOGGER.warning("Comptes rendus de pilotes indisponibles : %s", type(exc).__name__)
                if cached:
                    # Panne : le relevé précédent reste, nouvel essai dans une minute.
                    self._cache[key] = (now - self.cache_seconds + 60, cached[1], cached[2])
                    return cached[1], cached[2]
                raise requests.ConnectionError("aviationweather.gov injoignable") from exc
            reports = parse(data if isinstance(data, list) else [])
            self._cache = {key: (now, reports, time.time())}
            LOGGER.info("Comptes rendus de turbulence relevés : %d en %.2f s",
                        len(reports), time.perf_counter() - started)
            return reports, time.time()

    def close(self) -> None:
        self.session.close()
