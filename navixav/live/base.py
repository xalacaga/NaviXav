"""Types communs aux sources de position.

Une source doit rester silencieuse quand le simulateur n'est pas là : elle lève
`PositionUnavailable` avec un motif lisible, jamais une exception technique.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


class PositionUnavailable(RuntimeError):
    """Le simulateur n'est pas joignable, avec le motif à afficher."""


@dataclass(frozen=True)
class AircraftCapabilities:
    """Ce que l'avion chargé sait faire.

    Sans cela, l'interface alerterait sur un train non sorti au-dessus d'un
    appareil à train fixe. Une capacité absente n'est jamais surveillée.
    """

    retractable_gear: bool = False
    flaps: bool = False
    spoilers: bool = False
    flap_positions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AircraftConfiguration:
    """Configuration et instruments de l'avion, hors position.

    Tout est optionnel : les avions n'exposent pas les mêmes variables, et un
    bloc illisible ne doit jamais empêcher le suivi de position.
    """

    # Configuration
    gear_handle_down: bool | None = None
    gear_extended_pct: float | None = None
    flaps_handle_index: int | None = None
    flaps_effective_index: int | None = None
    flaps_surface_index: int | None = None
    flaps_handle_pct: float | None = None
    flaps_extended_pct: float | None = None
    # Braquage réel du volet gauche. SimConnect ne publie pas le marquage
    # inscrit sur le levier ; hors Airbus, ce marquage est justement cet angle.
    flaps_angle_deg: float | None = None
    spoilers_handle_pct: float | None = None
    spoilers_surface_pct: float | None = None
    spoilers_armed: bool | None = None
    parking_brake: bool | None = None
    lights: dict[str, bool] = field(default_factory=dict)

    # Altimétrie
    #
    # Trois altitudes coexistent et ne sont pas interchangeables :
    # `AircraftState.altitude_ft` est l'altitude vraie, `indicated_altitude_ft`
    # ce que l'altimètre affiche avec le calage courant, et
    # `pressure_altitude_ft` la hauteur dans l'atmosphère standard à 1013,25
    # hPa. Seule cette dernière donne le niveau de vol : en air chaud,
    # l'altitude vraie la dépasse de plus de mille pieds en croisière.
    altimeter_hpa: float | None = None
    indicated_altitude_ft: float | None = None
    pressure_altitude_ft: float | None = None

    # Automatismes
    autopilot_master: bool | None = None
    autopilot_nav_lock: bool | None = None
    autopilot_approach_hold: bool | None = None
    autopilot_glideslope_hold: bool | None = None
    autothrottle_active: bool | None = None
    selected_altitude_ft: float | None = None
    selected_heading_deg: float | None = None

    # Radionavigation
    nav1_frequency_mhz: float | None = None
    nav1_course_deg: float | None = None
    nav1_has_localizer: bool | None = None
    nav1_has_glide_slope: bool | None = None

    # Masses et carburant, en kilogrammes
    fuel_total_kg: float | None = None
    total_weight_kg: float | None = None

    # Atmosphère
    wind_direction_deg: float | None = None
    wind_speed_kt: float | None = None
    total_air_temperature_c: float | None = None
    in_cloud: bool | None = None
    engine_anti_ice: bool | None = None

    # Alertes émises par le simulateur
    stall_warning: bool | None = None
    overspeed_warning: bool | None = None
    flap_speed_exceeded: bool | None = None
    barber_pole_kt: float | None = None
    mach: float | None = None

    # Contexte de session
    simulation_rate: float | None = None

    capabilities: AircraftCapabilities | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AircraftState:
    latitude: float
    longitude: float
    altitude_ft: float | None = None
    height_above_ground_ft: float | None = None
    heading_true_deg: float | None = None
    heading_magnetic_deg: float | None = None
    ground_speed_kt: float | None = None
    indicated_airspeed_kt: float | None = None
    vertical_speed_fpm: float | None = None
    on_ground: bool = False
    title: str = ""
    source: str = ""
    configuration: AircraftConfiguration | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PositionSource(Protocol):
    """Fournisseur de position, interrogé à la demande."""

    @property
    def name(self) -> str: ...

    def is_available(self) -> bool:
        """Vrai si la source a une chance d'aboutir, sans coût notable."""
        ...

    def read(self) -> AircraftState: ...

    def close(self) -> None: ...
