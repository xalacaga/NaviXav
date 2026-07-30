"""Vol de démonstration complet, du roulage au départ au parking d'arrivée.

Cette source rejoue la route réellement calculée par le moteur : elle suit la
géométrie SID → route → STAR → approche, avec un profil vertical cohérent
(roulage, décollage, montée, croisière, descente, approche, atterrissage) et
une configuration avion qui évolue comme en vol.

Le temps est comprimé par `TIME_FACTOR` pour qu'un vol complet reste
observable en quelques minutes. Les valeurs publiées restent cohérentes entre
elles : à 450 kt sol, la distance restante diminue bien de 450 NM par heure de
temps simulé. Le taux de simulation reste annoncé à 1.0, l'accélération portant
sur l'écoulement du temps simulé et non sur le comportement de l'avion.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence

from navixav.geo import distance_nm
from navixav.live.base import (
    AircraftCapabilities,
    AircraftConfiguration,
    AircraftState,
    PositionUnavailable,
)

# Accélération du temps simulé : un vol d'une heure tient en sept minutes.
TIME_FACTOR = 8.0

# Profil de vitesses, en nœuds sol.
TAXI_SPEED_KT = 14.0
ROTATE_SPEED_KT = 150.0
CLIMB_SPEED_KT = 310.0
CRUISE_SPEED_KT = 450.0
DESCENT_SPEED_KT = 300.0
APPROACH_SPEED_KT = 160.0
TOUCHDOWN_SPEED_KT = 135.0

CLIMB_RATE_FPM = 1900.0
DESCENT_GRADIENT_FT_PER_NM = 318.0  # ≈ 3°
DEFAULT_CRUISE_ALTITUDE_FT = 33000.0

TAKEOFF_ROLL_NM = 0.7
LANDING_ROLL_NM = 1.2
FINAL_NM = 8.0
GATE_HOLD_NM = 0.8
STOP_RAMP_NM = 0.12

# Attente moteurs tournants avant de s'aligner, en secondes simulées : sans
# elle la démonstration décollerait avant que l'utilisateur ait vu l'avion.
START_HOLD_S = 150.0

# Masses de référence d'un moyen-courrier, en kilogrammes.
START_FUEL_KG = 6200.0
TRIP_FUEL_KG = 3100.0
ZERO_FUEL_WEIGHT_KG = 58000.0

_CAPABILITIES = AircraftCapabilities(
    retractable_gear=True,
    flaps=True,
    spoilers=True,
    flap_positions=5,
)


class DemoFlightSource:
    """Avion de démonstration qui parcourt la route complète du plan."""

    def __init__(
        self,
        path: Sequence[tuple[float, float]],
        cruise_altitude_ft: float | None = None,
        departure_elevation_ft: float = 0.0,
        arrival_elevation_ft: float = 0.0,
        ils_frequency_mhz: float | None = None,
        time_factor: float = TIME_FACTOR,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        points = _clean_path(path)
        if len(points) < 2:
            raise ValueError("Route de démonstration trop courte.")

        self._points = points
        self._cumulative = [0.0]
        for start, end in zip(points, points[1:]):
            self._cumulative.append(
                self._cumulative[-1] + distance_nm(*start, *end)
            )
        self._total_nm = self._cumulative[-1]
        if self._total_nm <= 1.0:
            raise ValueError("Route de démonstration trop courte.")

        self._clock = clock
        self._time_factor = max(1.0, float(time_factor))
        self._departure_elevation_ft = float(departure_elevation_ft)
        self._arrival_elevation_ft = float(arrival_elevation_ft)
        self._ils_frequency_mhz = ils_frequency_mhz
        self._cruise_altitude_ft = _usable_cruise_altitude(
            cruise_altitude_ft, self._departure_elevation_ft, self._total_nm
        )

        self._takeoff_end_nm = min(TAKEOFF_ROLL_NM, self._total_nm * 0.02)
        climb_nm = (
            (self._cruise_altitude_ft - self._departure_elevation_ft)
            / CLIMB_RATE_FPM
            * (CLIMB_SPEED_KT / 60.0)
        )
        self._climb_end_nm = self._takeoff_end_nm + min(
            climb_nm, self._total_nm * 0.35
        )
        self._touchdown_nm = self._total_nm - LANDING_ROLL_NM
        self._final_start_nm = max(
            self._climb_end_nm + 1.0, self._touchdown_nm - FINAL_NM
        )
        descent_nm = (
            self._cruise_altitude_ft - self._arrival_elevation_ft - 2000.0
        ) / DESCENT_GRADIENT_FT_PER_NM
        self._descent_start_nm = max(
            self._climb_end_nm,
            self._final_start_nm - max(10.0, descent_nm),
        )

        self._travelled_nm = 0.0
        self._hold_remaining_s = START_HOLD_S
        self._last_clock = clock()

    @property
    def name(self) -> str:
        return "Démonstration"

    def is_available(self) -> bool:
        return True

    @property
    def finished(self) -> bool:
        return self._travelled_nm >= self._total_nm

    def read(self) -> AircraftState:
        self._advance()
        travelled = self._travelled_nm
        holding = self._hold_remaining_s > 0.0
        latitude, longitude, heading = self._position(travelled)
        ground_speed = 0.0 if holding else self._ground_speed(travelled)
        altitude = self._altitude(travelled)
        elevation = self._field_elevation(travelled)
        height_agl = max(0.0, altitude - elevation)
        on_ground = travelled < self._takeoff_end_nm or travelled >= self._touchdown_nm

        vertical_speed = (
            0.0 if on_ground else self._vertical_speed(travelled, ground_speed)
        )
        indicated = ground_speed / (1.0 + 0.02 * max(0.0, altitude) / 1000.0)
        mach = ground_speed / max(300.0, 661.5 - 0.0035 * max(0.0, altitude))
        configuration = self._configuration(
            travelled, altitude, height_agl, mach, on_ground, holding
        )

        return AircraftState(
            latitude=latitude,
            longitude=longitude,
            altitude_ft=round(altitude, 1),
            height_above_ground_ft=round(height_agl, 1),
            heading_true_deg=round(heading, 1),
            heading_magnetic_deg=round(heading, 1),
            ground_speed_kt=round(ground_speed, 1),
            indicated_airspeed_kt=round(indicated, 1),
            vertical_speed_fpm=round(vertical_speed, 0),
            on_ground=on_ground,
            title="Démonstration NaviXav",
            source=self.name,
            configuration=configuration,
        )

    def close(self) -> None:
        return None

    # --------------------------------------------------------------- #

    def _advance(self) -> None:
        """Avance l'avion du temps simulé écoulé depuis la lecture précédente."""
        now = self._clock()
        elapsed_s = max(0.0, now - self._last_clock) * self._time_factor
        self._last_clock = now
        if self.finished:
            self._travelled_nm = self._total_nm
            return
        if self._hold_remaining_s > 0.0:
            consumed = min(self._hold_remaining_s, elapsed_s)
            self._hold_remaining_s -= consumed
            elapsed_s -= consumed
            if elapsed_s <= 0.0:
                return
        speed = self._ground_speed(self._travelled_nm)
        self._travelled_nm = min(
            self._total_nm, self._travelled_nm + speed * elapsed_s / 3600.0
        )
        if self._total_nm - self._travelled_nm < 0.02:
            self._travelled_nm = self._total_nm

    def _position(self, travelled: float) -> tuple[float, float, float]:
        index = _leg_index(self._cumulative, travelled)
        start = self._points[index]
        end = self._points[index + 1]
        span = self._cumulative[index + 1] - self._cumulative[index]
        ratio = 0.0 if span <= 0 else (travelled - self._cumulative[index]) / span
        ratio = min(1.0, max(0.0, ratio))
        return (
            start[0] + (end[0] - start[0]) * ratio,
            start[1] + (end[1] - start[1]) * ratio,
            _bearing(start, end),
        )

    def _ground_speed(self, travelled: float) -> float:
        if travelled < self._takeoff_end_nm:
            ratio = travelled / max(0.01, self._takeoff_end_nm)
            return TAXI_SPEED_KT + (ROTATE_SPEED_KT - TAXI_SPEED_KT) * ratio
        if travelled < self._climb_end_nm:
            ratio = (travelled - self._takeoff_end_nm) / max(
                0.01, self._climb_end_nm - self._takeoff_end_nm
            )
            return ROTATE_SPEED_KT + (CLIMB_SPEED_KT - ROTATE_SPEED_KT) * min(1.0, ratio * 4)
        if travelled < self._descent_start_nm:
            return CRUISE_SPEED_KT
        if travelled < self._final_start_nm:
            ratio = (travelled - self._descent_start_nm) / max(
                0.01, self._final_start_nm - self._descent_start_nm
            )
            return DESCENT_SPEED_KT + (APPROACH_SPEED_KT - DESCENT_SPEED_KT) * ratio
        if travelled < self._touchdown_nm:
            ratio = (travelled - self._final_start_nm) / max(
                0.01, self._touchdown_nm - self._final_start_nm
            )
            return APPROACH_SPEED_KT + (TOUCHDOWN_SPEED_KT - APPROACH_SPEED_KT) * ratio
        # Freinage, dégagement de piste, puis roulage jusqu'à l'arrêt.
        remaining = self._total_nm - travelled
        if remaining <= 0.0:
            return 0.0
        if remaining > GATE_HOLD_NM:
            ratio = (remaining - GATE_HOLD_NM) / max(0.01, LANDING_ROLL_NM - GATE_HOLD_NM)
            return TAXI_SPEED_KT + (TOUCHDOWN_SPEED_KT - TAXI_SPEED_KT) * ratio
        if remaining > STOP_RAMP_NM:
            return TAXI_SPEED_KT
        # Plancher indispensable : sans lui l'avion ralentirait indéfiniment
        # sans jamais atteindre son point d'arrêt.
        return max(3.0, TAXI_SPEED_KT * (remaining / STOP_RAMP_NM))

    def _altitude(self, travelled: float) -> float:
        departure = self._departure_elevation_ft
        arrival = self._arrival_elevation_ft
        if travelled < self._takeoff_end_nm:
            return departure
        if travelled < self._climb_end_nm:
            ratio = (travelled - self._takeoff_end_nm) / max(
                0.01, self._climb_end_nm - self._takeoff_end_nm
            )
            return departure + (self._cruise_altitude_ft - departure) * ratio
        if travelled < self._descent_start_nm:
            return self._cruise_altitude_ft
        if travelled < self._final_start_nm:
            ratio = (travelled - self._descent_start_nm) / max(
                0.01, self._final_start_nm - self._descent_start_nm
            )
            target = arrival + 2000.0
            return self._cruise_altitude_ft + (target - self._cruise_altitude_ft) * ratio
        if travelled < self._touchdown_nm:
            ratio = (travelled - self._final_start_nm) / max(
                0.01, self._touchdown_nm - self._final_start_nm
            )
            return (arrival + 2000.0) + (arrival - (arrival + 2000.0)) * ratio
        return arrival

    def _vertical_speed(self, travelled: float, ground_speed: float) -> float:
        step = 0.25
        ahead = min(self._total_nm, travelled + step)
        behind = max(0.0, travelled - step)
        if ahead <= behind:
            return 0.0
        gradient = (self._altitude(ahead) - self._altitude(behind)) / (ahead - behind)
        return gradient * ground_speed / 60.0

    def _field_elevation(self, travelled: float) -> float:
        return (
            self._departure_elevation_ft
            if travelled < self._total_nm / 2
            else self._arrival_elevation_ft
        )

    def _configuration(
        self,
        travelled: float,
        altitude: float,
        height_agl: float,
        mach: float,
        on_ground: bool,
        holding: bool,
    ) -> AircraftConfiguration:
        before_takeoff = travelled < self._takeoff_end_nm
        after_landing = travelled >= self._touchdown_nm
        in_final = self._final_start_nm <= travelled < self._touchdown_nm
        in_descent = self._descent_start_nm <= travelled < self._final_start_nm
        in_cruise = self._climb_end_nm <= travelled < self._descent_start_nm
        stopped = travelled >= self._total_nm
        # Volets et aérofreins restent sortis tant que la piste n'est pas
        # dégagée : ils ne se rangent qu'une fois l'avion arrêté.
        rolling_out = after_landing and not stopped

        gear_down = on_ground or (in_final and height_agl < 2500) or height_agl < 1000
        if rolling_out:
            flaps_index, flaps_pct = 4, 100.0
        elif before_takeoff or (not on_ground and height_agl < 1000 and not in_final):
            flaps_index, flaps_pct = 1, 20.0
        elif in_final and height_agl < 1800:
            flaps_index, flaps_pct = 4, 100.0
        elif in_final or (in_descent and height_agl < 4000):
            flaps_index, flaps_pct = 2, 45.0
        else:
            flaps_index, flaps_pct = 0, 0.0

        spoilers_pct = 100.0 if rolling_out else 0.0
        spoilers_armed = bool(in_descent or in_final)

        landing_lights = bool(
            (not on_ground and altitude < 10000)
            or (before_takeoff and not holding)
            or in_final
            or rolling_out
        )
        lights = {
            "landing": landing_lights,
            "taxi": bool(on_ground),
            "strobe": not holding,
            "nav": True,
            "beacon": True,
            "logo": altitude < 10000,
            "wing": on_ground,
        }

        autopilot = bool(
            not on_ground
            and height_agl > 800
            and not (in_final and height_agl < 250)
        )
        progress = min(1.0, travelled / self._total_nm)
        fuel = START_FUEL_KG - TRIP_FUEL_KG * progress
        isa_temperature = max(-56.5, 15.0 - 1.98 * max(0.0, altitude) / 1000.0)

        if in_cruise:
            selected_altitude = self._cruise_altitude_ft
        elif in_descent or in_final or after_landing:
            selected_altitude = self._arrival_elevation_ft + 2000.0
        else:
            selected_altitude = self._cruise_altitude_ft

        return AircraftConfiguration(
            gear_handle_down=gear_down,
            gear_extended_pct=100.0 if gear_down else 0.0,
            flaps_handle_index=flaps_index,
            flaps_extended_pct=flaps_pct,
            spoilers_handle_pct=spoilers_pct,
            spoilers_armed=spoilers_armed,
            parking_brake=stopped or holding,
            lights=lights,
            altimeter_hpa=1013.0 if altitude > 6000 else 1017.0,
            indicated_altitude_ft=round(altitude, 1),
            autopilot_master=autopilot,
            autopilot_nav_lock=autopilot,
            autopilot_approach_hold=bool(in_final and autopilot),
            autopilot_glideslope_hold=bool(in_final and autopilot),
            autothrottle_active=bool(not on_ground),
            selected_altitude_ft=selected_altitude,
            selected_heading_deg=self._position(travelled)[2],
            nav1_frequency_mhz=self._ils_frequency_mhz or 0.0,
            nav1_course_deg=self._position(self._touchdown_nm)[2],
            nav1_has_localizer=bool(self._ils_frequency_mhz and (in_final or in_descent)),
            nav1_has_glide_slope=bool(self._ils_frequency_mhz and in_final),
            fuel_total_kg=round(fuel, 1),
            total_weight_kg=round(ZERO_FUEL_WEIGHT_KG + fuel, 1),
            wind_direction_deg=250.0,
            wind_speed_kt=12.0 if altitude < 10000 else 45.0,
            total_air_temperature_c=round(isa_temperature + mach**2 * 30.0, 1),
            in_cloud=False,
            engine_anti_ice=False,
            stall_warning=False,
            overspeed_warning=False,
            flap_speed_exceeded=False,
            barber_pole_kt=340.0,
            mach=round(mach, 3),
            # L'accélération porte sur le temps simulé : du point de vue de
            # l'avion, la session tourne au taux normal.
            simulation_rate=1.0,
            capabilities=_CAPABILITIES,
        )


def _clean_path(path: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for entry in path:
        try:
            latitude = float(entry[0])
            longitude = float(entry[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not math.isfinite(latitude) or not math.isfinite(longitude):
            continue
        if points and points[-1] == (latitude, longitude):
            continue
        points.append((latitude, longitude))
    return points


def _usable_cruise_altitude(
    requested: float | None, departure_elevation_ft: float, total_nm: float
) -> float:
    """Altitude de croisière plausible pour la distance à parcourir."""
    altitude = float(requested or 0.0)
    if altitude <= departure_elevation_ft + 1000.0:
        altitude = DEFAULT_CRUISE_ALTITUDE_FT
    # Sur une route courte, une croisière au niveau demandé ne laisserait pas la
    # place à une montée et à une descente réalistes.
    ceiling = departure_elevation_ft + total_nm * 220.0
    return max(departure_elevation_ft + 3000.0, min(altitude, ceiling))


def _leg_index(cumulative: list[float], travelled: float) -> int:
    low, high = 0, len(cumulative) - 2
    while low < high:
        middle = (low + high + 1) // 2
        if cumulative[middle] <= travelled:
            low = middle
        else:
            high = middle - 1
    return low


def _bearing(start: tuple[float, float], end: tuple[float, float]) -> float:
    phi1, phi2 = math.radians(start[0]), math.radians(end[0])
    delta = math.radians(end[1] - start[1])
    x = math.sin(delta) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta)
    return (math.degrees(math.atan2(x, y)) + 360) % 360
