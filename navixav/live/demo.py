"""Source simulée : un avion qui roule vers sa piste de départ.

Sert à valider la carte et le suivi sans lancer le simulateur. Le trajet part
d'un poste de stationnement et rejoint le seuil de piste en ligne droite, à une
vitesse de roulage réaliste.
"""

from __future__ import annotations

import math
import time

from navixav.geo import distance_nm
from navixav.live.base import (
    AircraftCapabilities,
    AircraftConfiguration,
    AircraftState,
    PositionUnavailable,
)

TAXI_SPEED_KT = 15.0
LOOP_PAUSE_S = 6.0

# Configuration d'un roulage au départ, volontairement conforme : la
# démonstration sert à valider l'affichage, pas à déclencher des alarmes.
_DEMO_CONFIGURATION = AircraftConfiguration(
    gear_handle_down=True,
    gear_extended_pct=100.0,
    flaps_handle_index=1,
    flaps_extended_pct=20.0,
    spoilers_handle_pct=0.0,
    spoilers_armed=False,
    parking_brake=False,
    lights={
        "landing": False,
        "taxi": True,
        "strobe": False,
        "nav": True,
        "beacon": True,
        "logo": False,
        "wing": False,
    },
    altimeter_hpa=1013.0,
    indicated_altitude_ft=0.0,
    autopilot_master=False,
    autopilot_nav_lock=False,
    autopilot_approach_hold=False,
    autopilot_glideslope_hold=False,
    autothrottle_active=False,
    selected_altitude_ft=5000.0,
    selected_heading_deg=0.0,
    nav1_frequency_mhz=0.0,
    nav1_course_deg=0.0,
    nav1_has_localizer=False,
    nav1_has_glide_slope=False,
    fuel_total_kg=4200.0,
    total_weight_kg=62000.0,
    wind_direction_deg=250.0,
    wind_speed_kt=8.0,
    total_air_temperature_c=15.0,
    in_cloud=False,
    engine_anti_ice=False,
    stall_warning=False,
    overspeed_warning=False,
    flap_speed_exceeded=False,
    barber_pole_kt=340.0,
    mach=0.0,
    simulation_rate=1.0,
    capabilities=AircraftCapabilities(
        retractable_gear=True,
        flaps=True,
        spoilers=True,
        flap_positions=5,
    ),
)


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
            indicated_airspeed_kt=0.0,
            vertical_speed_fpm=0.0,
            on_ground=True,
            title="Démonstration",
            source=self.name,
            configuration=_DEMO_CONFIGURATION,
        )

    def close(self) -> None:
        return None


def _bearing(start: tuple[float, float], end: tuple[float, float]) -> float:
    phi1, phi2 = math.radians(start[0]), math.radians(end[0])
    delta = math.radians(end[1] - start[1])
    x = math.sin(delta) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta)
    return (math.degrees(math.atan2(x, y)) + 360) % 360
