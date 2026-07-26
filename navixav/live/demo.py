"""Source simulée : un avion qui roule vers sa piste de départ.

Sert à valider la carte et le suivi sans lancer le simulateur. Le trajet part
d'un poste de stationnement et rejoint le seuil de piste en ligne droite, à une
vitesse de roulage réaliste.
"""

from __future__ import annotations

import math
import time

from navixav.geo import distance_nm
from navixav.live.base import AircraftState, PositionUnavailable

TAXI_SPEED_KT = 15.0
LOOP_PAUSE_S = 6.0


class DemoSource:
    """Rejoue un roulage en boucle entre deux points de l'aéroport."""

    def __init__(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        heading_deg: float | None = None,
    ) -> None:
        self.start = start
        self.end = end
        self.heading_deg = heading_deg
        self._t0 = time.monotonic()
        self._distance_nm = distance_nm(*start, *end)

    @property
    def name(self) -> str:
        return "Démonstration"

    def is_available(self) -> bool:
        return True

    def read(self) -> AircraftState:
        if self._distance_nm <= 0:
            raise PositionUnavailable("Trajet de démonstration invalide.")

        duration_s = self._distance_nm / TAXI_SPEED_KT * 3600.0
        elapsed = (time.monotonic() - self._t0) % (duration_s + LOOP_PAUSE_S)
        progress = min(1.0, elapsed / duration_s)

        latitude = self.start[0] + (self.end[0] - self.start[0]) * progress
        longitude = self.start[1] + (self.end[1] - self.start[1]) * progress

        heading = self.heading_deg
        if heading is None:
            heading = _bearing(self.start, self.end)

        moving = progress < 1.0
        return AircraftState(
            latitude=latitude,
            longitude=longitude,
            altitude_ft=None,
            height_above_ground_ft=0.0,
            heading_true_deg=heading,
            heading_magnetic_deg=heading,
            ground_speed_kt=TAXI_SPEED_KT if moving else 0.0,
            vertical_speed_fpm=0.0,
            on_ground=True,
            title="Démonstration",
            source=self.name,
        )

    def close(self) -> None:
        return None


def _bearing(start: tuple[float, float], end: tuple[float, float]) -> float:
    phi1, phi2 = math.radians(start[0]), math.radians(end[0])
    delta = math.radians(end[1] - start[1])
    x = math.sin(delta) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta)
    return (math.degrees(math.atan2(x, y)) + 360) % 360
