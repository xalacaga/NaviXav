"""Intensité de turbulence à la position de l'avion, en EDR.

L'EDR (eddy dissipation rate, ε^(1/3) en m^(2/3)/s) est la mesure que l'OACI
retient pour décrire la turbulence indépendamment de l'avion qui la traverse.
Chaque source y est ramenée avant d'être combinée :

* le cisaillement vertical prévu par l'OFP, point par point du navlog ;
* les PIREP et AIREP récents, c'est-à-dire de la turbulence réellement
  rencontrée par d'autres équipages ;
* ce que montre MSFS lui-même : nuage, précipitations, vent qui tourne avec
  l'altitude, vent fort près du sol ;
* le relief au vent, qui lève une onde orographique quand le vent le franchit.

La turbulence en air clair est faite de plaques de quelques dizaines de
kilomètres, pas d'un tapis continu : une prévision n'est donc ressentie que
dans les plaques que tire un bruit spatial propre au vol, d'autant plus
étendues que le risque est fort. Une observation, elle, est prise pour acquise.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

# Repères OACI d'intensité, en EDR de pointe : léger dès 0,10, modéré dès
# 0,20, fort au-delà de 0,45.
EDR_LIGHT = 0.10
EDR_MODERATE = 0.20
EDR_SEVERE = 0.45
EDR_MAX = 0.80

# Valeur retenue pour une intensité rapportée par un équipage.
REPORT_EDR = {0: 0.0, 1: 0.15, 2: 0.32, 3: 0.55, 4: 0.75}

# Cisaillement vertical (kt par 1 000 ft) -> EDR : léger à 3, modéré à 6,
# fort à 9, mêmes seuils que le risque affiché dans le dispatch.
SHEAR_TO_EDR = ((0.0, 0.0), (3.0, 0.10), (6.0, 0.24), (9.0, 0.46), (12.0, 0.60))

NM_PER_DEG = 60.0


def _interpolate(table: Sequence[tuple[float, float]], value: float) -> float:
    if value <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if value <= x1:
            return y0 + (y1 - y0) * (value - x0) / (x1 - x0)
    return table[-1][1]


def shear_to_edr(shear_kt_per_kft: float) -> float:
    return _interpolate(SHEAR_TO_EDR, max(0.0, shear_kt_per_kft))


def _fade(value: float, full: float, zero: float) -> float:
    """1 jusqu'à `full`, 0 au-delà de `zero`, linéaire entre les deux."""
    if value <= full:
        return 1.0
    if value >= zero:
        return 0.0
    return (zero - value) / (zero - full)


def distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * 3440.065 * math.asin(min(1.0, math.sqrt(a)))


def level(edr: float) -> str | None:
    """Intensité OACI correspondant à un EDR, None sous le seuil léger."""
    if edr >= EDR_SEVERE:
        return "SEV"
    if edr >= EDR_MODERATE:
        return "MOD"
    if edr >= EDR_LIGHT:
        return "LGT"
    return None


@dataclass(frozen=True)
class ForecastPoint:
    latitude: float
    longitude: float
    altitude_ft: float | None
    shear: float


@dataclass(frozen=True)
class Report:
    latitude: float
    longitude: float
    rank: int
    observed: float
    level_ft: float | None = None
    base_ft: float | None = None
    top_ft: float | None = None


@dataclass(frozen=True)
class Sources:
    """Ce que le vol sait de la turbulence avant de la rencontrer."""

    forecast: tuple[ForecastPoint, ...] = ()
    reports: tuple[Report, ...] = ()

    @classmethod
    def build(cls, profile: Iterable[dict[str, Any]] | None, reports: Iterable[Any] | None) -> "Sources":
        forecast = []
        for point in profile or ():
            try:
                forecast.append(ForecastPoint(
                    float(point["lat"]), float(point["lon"]),
                    float(point["altitude_ft"]) if point.get("altitude_ft") is not None else None,
                    float(point["shear"]),
                ))
            except (KeyError, TypeError, ValueError):
                continue
        observed = []
        for report in reports or ():
            get = report.get if isinstance(report, dict) else (lambda name, r=report: getattr(r, name, None))
            try:
                observed.append(Report(
                    float(get("latitude")), float(get("longitude")), int(get("rank")),
                    float(get("observed")),
                    _optional(get("level_ft")), _optional(get("base_ft")), _optional(get("top_ft")),
                ))
            except (TypeError, ValueError):
                continue
        return cls(tuple(forecast), tuple(observed))


def _optional(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


@dataclass(frozen=True)
class Conditions:
    """État de l'avion et de l'air autour de lui, tel que MSFS le donne."""

    latitude: float
    longitude: float
    altitude_ft: float
    height_agl_ft: float
    on_ground: bool
    in_cloud: bool = False
    precipitating: bool = False
    wind_speed_kt: float = 0.0
    live_shear_kt_per_kft: float = 0.0
    # Relief au vent : crête la plus haute et dénivelé sous le vent, connus
    # seulement quand le relief a été relevé.
    ridge_ft: float | None = None
    relief_ft: float = 0.0


@dataclass(frozen=True)
class Contribution:
    source: str
    edr: float


@dataclass(frozen=True)
class Assessment:
    edr: float
    contributions: tuple[Contribution, ...] = ()

    @property
    def level(self) -> str | None:
        return level(self.edr)

    @property
    def dominant(self) -> str | None:
        if not self.contributions:
            return None
        return max(self.contributions, key=lambda c: c.edr).source

    def to_dict(self) -> dict[str, Any]:
        return {
            "edr": round(self.edr, 3),
            "level": self.level,
            "dominant": self.dominant,
            "contributions": [
                {"source": c.source, "edr": round(c.edr, 3)} for c in self.contributions
            ],
        }


# --------------------------------------------------------------------------- #
# Plaques de turbulence


PATCH_CELL_NM = 12.0
PATCH_LAYER_FT = 3000.0


def _hash01(*values: int) -> float:
    """Pseudo-aléatoire reproductible dans [0, 1) pour une cellule."""
    h = 2166136261
    for value in values:
        h ^= value & 0xFFFFFFFF
        h = (h * 16777619) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    return h / 2 ** 32


def _smooth(t: float) -> float:
    return t * t * (3 - 2 * t)


def patch_noise(latitude: float, longitude: float, altitude_ft: float, seed: int) -> float:
    """Bruit de valeur continu dans [0, 1), à l'échelle d'une plaque de CAT."""
    y = latitude * NM_PER_DEG / PATCH_CELL_NM
    x = longitude * NM_PER_DEG * max(0.2, math.cos(math.radians(latitude))) / PATCH_CELL_NM
    z = altitude_ft / PATCH_LAYER_FT
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = _smooth(x - ix), _smooth(y - iy), _smooth(z - iz)
    total = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                weight = (fx if dx else 1 - fx) * (fy if dy else 1 - fy) * (fz if dz else 1 - fz)
                total += weight * _hash01(seed, ix + dx, iy + dy, iz + dz)
    return total


def patch_factor(noise: float, coverage: float) -> float:
    """Part de la prévision ressentie : nulle hors plaque, pleine au cœur."""
    coverage = min(1.0, max(0.0, coverage))
    edge = 1.0 - coverage
    if noise <= edge:
        return 0.0
    return _smooth(min(1.0, (noise - edge) / 0.15))


# --------------------------------------------------------------------------- #
# Sources


FORECAST_FULL_NM, FORECAST_ZERO_NM = 25.0, 70.0
FORECAST_FULL_FT, FORECAST_ZERO_FT = 2000.0, 6000.0
REPORT_FULL_NM, REPORT_ZERO_NM = 10.0, 30.0
REPORT_FULL_FT, REPORT_ZERO_FT = 1000.0, 4000.0
REPORT_FRESH_S, REPORT_STALE_S = 3600.0, 3 * 3600.0
# Un compte rendu « vol calme » tout proche atténue la prévision d'autant.
SMOOTH_REPORT_DAMPING = 0.5


def forecast_edr(conditions: Conditions, points: Sequence[ForecastPoint]) -> float:
    """Cisaillement prévu le plus proche, s'il concerne le niveau de l'avion."""
    best = 0.0
    for point in points:
        horizontal = _fade(
            distance_nm(conditions.latitude, conditions.longitude, point.latitude, point.longitude),
            FORECAST_FULL_NM, FORECAST_ZERO_NM,
        )
        if horizontal <= 0:
            continue
        vertical = 1.0
        if point.altitude_ft is not None:
            vertical = _fade(abs(conditions.altitude_ft - point.altitude_ft), FORECAST_FULL_FT, FORECAST_ZERO_FT)
        best = max(best, shear_to_edr(point.shear) * horizontal * vertical)
    return best


def _report_vertical(report: Report, altitude_ft: float) -> float:
    if report.base_ft is not None and report.top_ft is not None:
        low, high = sorted((report.base_ft, report.top_ft))
        gap = max(0.0, low - altitude_ft, altitude_ft - high)
        return _fade(gap, REPORT_FULL_FT, REPORT_ZERO_FT)
    if report.level_ft is None:
        return 0.0
    return _fade(abs(altitude_ft - report.level_ft), REPORT_FULL_FT, REPORT_ZERO_FT)


def report_edr(conditions: Conditions, reports: Sequence[Report], now: float) -> tuple[float, bool]:
    """Turbulence rapportée la plus forte à portée, et présence d'un vol calme."""
    best = 0.0
    smooth_nearby = False
    for report in reports:
        weight = (
            _fade(distance_nm(conditions.latitude, conditions.longitude, report.latitude, report.longitude),
                  REPORT_FULL_NM, REPORT_ZERO_NM)
            * _report_vertical(report, conditions.altitude_ft)
            * _fade(now - report.observed, REPORT_FRESH_S, REPORT_STALE_S)
        )
        if weight <= 0:
            continue
        if report.rank == 0:
            smooth_nearby = smooth_nearby or weight >= 0.5
            continue
        best = max(best, REPORT_EDR.get(report.rank, REPORT_EDR[4]) * weight)
    return best, smooth_nearby


# Nuage : stratiforme léger par défaut, convectif dès qu'il précipite.
CLOUD_EDR = 0.11
CONVECTIVE_EDR = 0.24
# Turbulence mécanique de la couche limite, par vent fort près du sol.
BOUNDARY_LAYER_FT = 3000.0
BOUNDARY_WIND_FLOOR_KT = 12.0
BOUNDARY_WIND_FULL_KT = 45.0
BOUNDARY_EDR = 0.30


def boundary_layer_edr(conditions: Conditions) -> float:
    if conditions.height_agl_ft >= BOUNDARY_LAYER_FT:
        return 0.0
    wind = (conditions.wind_speed_kt - BOUNDARY_WIND_FLOOR_KT) / (BOUNDARY_WIND_FULL_KT - BOUNDARY_WIND_FLOOR_KT)
    if wind <= 0:
        return 0.0
    return BOUNDARY_EDR * min(1.0, wind) * (1.0 - conditions.height_agl_ft / BOUNDARY_LAYER_FT)


# Onde orographique : il faut un relief marqué et un vent qui le franchit
# franchement (25 kt et plus en règle générale). La turbulence est la plus
# forte sous les crêtes et juste au-dessus, puis s'éteint vers 18 000 ft
# au-dessus d'elles.
WAVE_RELIEF_FLOOR_FT = 1500.0
WAVE_RELIEF_FULL_FT = 6500.0
WAVE_WIND_FLOOR_KT = 20.0
WAVE_WIND_FULL_KT = 60.0
WAVE_FULL_ABOVE_RIDGE_FT = 6000.0
WAVE_ZERO_ABOVE_RIDGE_FT = 18000.0
WAVE_EDR = 0.50


def mountain_wave_edr(conditions: Conditions) -> float:
    if conditions.ridge_ft is None:
        return 0.0
    relief = (conditions.relief_ft - WAVE_RELIEF_FLOOR_FT) / (WAVE_RELIEF_FULL_FT - WAVE_RELIEF_FLOOR_FT)
    wind = (conditions.wind_speed_kt - WAVE_WIND_FLOOR_KT) / (WAVE_WIND_FULL_KT - WAVE_WIND_FLOOR_KT)
    if relief <= 0 or wind <= 0:
        return 0.0
    vertical = _fade(
        conditions.altitude_ft - conditions.ridge_ft, WAVE_FULL_ABOVE_RIDGE_FT, WAVE_ZERO_ABOVE_RIDGE_FT
    )
    return WAVE_EDR * min(1.0, relief) * min(1.0, wind) * vertical


@dataclass
class Estimator:
    """Assemble les sources en une intensité unique, à la position donnée."""

    seed: int = field(default_factory=lambda: int(time.time()) & 0xFFFF)

    def assess(self, conditions: Conditions, sources: Sources, now: float | None = None) -> Assessment:
        if conditions.on_ground:
            return Assessment(0.0)
        now = time.time() if now is None else now
        contributions: list[Contribution] = []

        reported, smooth_nearby = report_edr(conditions, sources.reports, now)
        if reported > 0:
            contributions.append(Contribution("report", reported))

        forecast = forecast_edr(conditions, sources.forecast)
        if forecast > 0:
            # Plus le risque est fort, plus la plaque est étendue : un gros
            # tiers du couloir en léger, jusqu'à 80 % en fort.
            coverage = 0.25 + 0.55 * min(1.0, forecast / EDR_SEVERE)
            noise = patch_noise(conditions.latitude, conditions.longitude, conditions.altitude_ft, self.seed)
            felt = forecast * patch_factor(noise, coverage)
            if smooth_nearby:
                felt *= SMOOTH_REPORT_DAMPING
            if felt > 0:
                contributions.append(Contribution("forecast", felt))

        if conditions.live_shear_kt_per_kft > 0:
            live = shear_to_edr(conditions.live_shear_kt_per_kft)
            if live > 0:
                contributions.append(Contribution("wind_shear", live))

        if conditions.in_cloud:
            contributions.append(Contribution(
                "convective" if conditions.precipitating else "cloud",
                CONVECTIVE_EDR if conditions.precipitating else CLOUD_EDR,
            ))

        boundary = boundary_layer_edr(conditions)
        if boundary > 0:
            contributions.append(Contribution("boundary_layer", boundary))

        wave = mountain_wave_edr(conditions)
        if wave > 0:
            contributions.append(Contribution("mountain_wave", wave))

        # Les sources indépendantes s'additionnent en énergie, pas en EDR :
        # deux turbulences légères ne font pas une modérée.
        total = math.sqrt(sum(c.edr ** 2 for c in contributions))
        return Assessment(min(EDR_MAX, total), tuple(contributions))


# --------------------------------------------------------------------------- #
# Cisaillement mesuré dans MSFS


@dataclass
class LiveShear:
    """Cisaillement vertical du vent de MSFS, mesuré pendant les changements de niveau.

    Le vent n'est comparé qu'après au moins `min_climb_ft` de dénivelé : en
    palier, un écart de vent ne dit rien de la variation avec l'altitude.
    """

    min_climb_ft: float = 300.0
    window_s: float = 90.0
    memory_s: float = 120.0
    _anchor: tuple[float, float, float, float] | None = None
    _shear: float = 0.0
    _since: float = 0.0

    def update(self, now: float, altitude_ft: float, wind_dir_deg: float, wind_kt: float) -> float:
        rad = math.radians(wind_dir_deg)
        u, v = wind_kt * math.sin(rad), wind_kt * math.cos(rad)
        if self._anchor is None:
            self._anchor = (now, altitude_ft, u, v)
            return self._shear
        t0, alt0, u0, v0 = self._anchor
        climb = abs(altitude_ft - alt0)
        if climb >= self.min_climb_ft:
            self._shear = math.hypot(u - u0, v - v0) / climb * 1000.0
            self._since = now
            self._anchor = (now, altitude_ft, u, v)
        elif now - t0 > self.window_s:
            # Trop de chemin parcouru en palier : l'écart de vent mêlerait la
            # variation horizontale à la variation avec l'altitude.
            self._anchor = (now, altitude_ft, u, v)
        if now - self._since > self.memory_s:
            self._shear = 0.0
        return self._shear
