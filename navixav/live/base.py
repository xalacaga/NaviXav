"""Types communs aux sources de position.

Une source doit rester silencieuse quand le simulateur n'est pas là : elle lève
`PositionUnavailable` avec un motif lisible, jamais une exception technique.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


class PositionUnavailable(RuntimeError):
    """Le simulateur n'est pas joignable, avec le motif à afficher."""


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
