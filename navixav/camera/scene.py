"""État de l'avion vu par la caméra, et géométrie sur la sphère terrestre.

La vitesse sol, la route et la vitesse verticale sont déduites des positions
successives plutôt que lues dans des variables dont l'axe ou l'unité varient
d'un avion à l'autre : un plan de passage peut ainsi viser l'endroit où
l'avion sera vraiment, virage et montée compris.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_008.8
FT = 0.3048
DEFAULT_SPAN_M = 34.0
# Fenêtre d'estimation de la vitesse : assez longue pour lisser le bruit de
# position, assez courte pour suivre un virage.
VELOCITY_WINDOW_S = 1.5
MIN_VELOCITY_WINDOW_S = 0.4


@dataclass(frozen=True)
class AircraftState:
    latitude: float
    longitude: float
    altitude_m: float
    height_m: float
    heading_deg: float
    on_ground: bool
    span_m: float = DEFAULT_SPAN_M
    ground_speed_mps: float = 0.0
    track_deg: float | None = None
    vertical_speed_mps: float = 0.0
    # Tours de contrôle connues à proximité : (latitude, longitude, altitude m).
    towers: tuple[tuple[float, float, float], ...] = ()

    @property
    def ground_elevation_m(self) -> float:
        return self.altitude_m - self.height_m

    @property
    def course_deg(self) -> float:
        """Route suivie quand l'avion avance, cap sinon."""
        if self.track_deg is not None and self.ground_speed_mps > 2.0:
            return self.track_deg
        return self.heading_deg


def destination(latitude: float, longitude: float, bearing_deg: float, distance_m: float) -> tuple[float, float]:
    """Point atteint en suivant un cap vrai sur une distance, sur la sphère."""
    angular = distance_m / EARTH_RADIUS_M
    lat1 = math.radians(latitude)
    lon1 = math.radians(longitude)
    bearing = math.radians(bearing_deg)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular) + math.cos(lat1) * math.sin(angular) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular) * math.cos(lat1),
        math.cos(angular) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), (math.degrees(lon2) + 540.0) % 360.0 - 180.0


def distance_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """Distance (m) et cap vrai initial (°) du premier point vers le second."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    distance = 2.0 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))
    bearing = math.degrees(math.atan2(
        math.sin(dlambda) * math.cos(phi2),
        math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda),
    ))
    return distance, bearing % 360.0


def along_track_m(state: AircraftState, latitude: float, longitude: float) -> float:
    """Distance d'un point devant (positive) ou derrière (négative) l'avion."""
    distance, bearing = distance_bearing(state.latitude, state.longitude, latitude, longitude)
    return distance * math.cos(math.radians(bearing - state.course_deg))


class Kinematics:
    """Vitesse sol, route et vitesse verticale tirées des dernières positions."""

    def __init__(self) -> None:
        self._samples: deque[tuple[float, float, float, float]] = deque()

    def reset(self) -> None:
        self._samples.clear()

    def update(
        self, t: float, latitude: float, longitude: float, altitude_m: float
    ) -> tuple[float, float | None, float]:
        samples = self._samples
        if samples and t <= samples[-1][0]:
            samples.clear()
        samples.append((t, latitude, longitude, altitude_m))
        while len(samples) > 2 and t - samples[1][0] >= VELOCITY_WINDOW_S:
            samples.popleft()
        t0, lat0, lon0, alt0 = samples[0]
        elapsed = t - t0
        if elapsed < MIN_VELOCITY_WINDOW_S:
            return 0.0, None, 0.0
        distance, bearing = distance_bearing(lat0, lon0, latitude, longitude)
        speed = distance / elapsed
        return speed, (bearing if speed > 1.0 else None), (altitude_m - alt0) / elapsed
