"""Relief au vent de l'avion, pour la turbulence d'onde orographique.

Un vent fort qui franchit une chaîne de montagnes y lève des ondes et, sous
elles, des rotors : la turbulence s'étend sous le vent du relief, jusqu'à
plusieurs milliers de pieds au-dessus des crêtes. Il faut donc connaître le
relief *au vent* de l'avion, pas seulement celui qu'il survole.

L'altitude du terrain vient du service d'altitude d'Open-Meteo (modèle
numérique Copernicus à 90 m, sans clé). Une ligne de points est relevée vers
l'amont du vent, puis réutilisée tant que l'avion et le vent n'ont pas
sensiblement changé : quelques requêtes par heure de vol en montagne, aucune
en plaine ni par vent faible.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass, field

import requests

LOGGER = logging.getLogger(__name__)

ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
DEFAULT_TIMEOUT = 10
FT_PER_M = 3.28084
EARTH_RADIUS_NM = 3440.065

# Ligne relevée vers l'amont : de l'avion jusqu'à 45 NM, tous les 3 NM.
UPWIND_RANGE_NM = 45.0
UPWIND_STEP_NM = 3.0
# Un relevé reste valable tant que l'avion a parcouru moins de 4 NM et que le
# vent a tourné de moins de 15°, dans la limite de deux minutes.
REUSE_DISTANCE_NM = 4.0
REUSE_TURN_DEG = 15.0
REUSE_AGE_S = 120.0
# Après une panne du service, pas de nouvel essai avant une minute.
FAILURE_BACKOFF_S = 60.0


@dataclass(frozen=True)
class TerrainSample:
    latitude: float
    longitude: float
    wind_direction_deg: float
    ridge_ft: float
    valley_ft: float
    fetched: float

    @property
    def relief_ft(self) -> float:
        return max(0.0, self.ridge_ft - self.valley_ft)


def destination(lat: float, lon: float, bearing_deg: float, distance_nm: float) -> tuple[float, float]:
    """Point atteint sur un grand cercle, depuis (lat, lon), au cap et à la distance donnés."""
    phi1, lmb1 = math.radians(lat), math.radians(lon)
    theta = math.radians(bearing_deg)
    delta = distance_nm / EARTH_RADIUS_NM
    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    )
    lmb2 = lmb1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )
    return math.degrees(phi2), (math.degrees(lmb2) + 540.0) % 360.0 - 180.0


def upwind_line(lat: float, lon: float, wind_from_deg: float) -> list[tuple[float, float]]:
    """L'avion puis les points vers l'amont. Le vent est donné d'où il vient."""
    steps = int(UPWIND_RANGE_NM / UPWIND_STEP_NM)
    return [destination(lat, lon, wind_from_deg, i * UPWIND_STEP_NM) for i in range(steps + 1)]


def _turn(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((phi2 - phi1) / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_NM * math.asin(min(1.0, math.sqrt(a)))


@dataclass
class TerrainProbe:
    session: requests.Session = field(default_factory=requests.Session)
    timeout: int = DEFAULT_TIMEOUT
    _sample: TerrainSample | None = None
    _failed_at: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def current(self) -> TerrainSample | None:
        with self._lock:
            return self._sample

    def _reusable(self, lat: float, lon: float, wind_from_deg: float, now: float) -> bool:
        sample = self._sample
        return (
            sample is not None
            and now - sample.fetched < REUSE_AGE_S
            and _distance_nm(lat, lon, sample.latitude, sample.longitude) < REUSE_DISTANCE_NM
            and _turn(wind_from_deg, sample.wind_direction_deg) < REUSE_TURN_DEG
        )

    def probe(self, lat: float, lon: float, wind_from_deg: float, now: float | None = None) -> TerrainSample | None:
        """Relief au vent de la position, relu seulement s'il a pu changer."""
        now = time.monotonic() if now is None else now
        with self._lock:
            if self._reusable(lat, lon, wind_from_deg, now):
                return self._sample
            if self._failed_at is not None and now - self._failed_at < FAILURE_BACKOFF_S:
                return self._sample
        points = upwind_line(lat, lon, wind_from_deg)
        try:
            response = self.session.get(
                ELEVATION_URL,
                params={
                    "latitude": ",".join(f"{p[0]:.4f}" for p in points),
                    "longitude": ",".join(f"{p[1]:.4f}" for p in points),
                },
                timeout=self.timeout,
                headers={"User-Agent": "NaviXav flight-simulation turbulence"},
            )
            response.raise_for_status()
            elevations = [float(value) for value in response.json()["elevation"]]
            if len(elevations) != len(points) or not all(math.isfinite(v) for v in elevations):
                raise ValueError("relevé incomplet")
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            LOGGER.info("Relief au vent indisponible : %s", type(exc).__name__)
            with self._lock:
                self._failed_at = now
            return self.current()
        sample = TerrainSample(
            latitude=lat,
            longitude=lon,
            wind_direction_deg=wind_from_deg,
            # La mer et les dépressions comptent comme le niveau de la mer :
            # c'est la hauteur des crêtes au-dessus de l'aval qui lève l'onde.
            ridge_ft=max(0.0, max(elevations)) * FT_PER_M,
            valley_ft=max(0.0, min(elevations)) * FT_PER_M,
            fetched=now,
        )
        with self._lock:
            self._sample = sample
            self._failed_at = None
        return sample

    def close(self) -> None:
        self.session.close()
