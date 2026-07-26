"""Modèles de sortie : le plan de vol complété."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from navixav.constraints import ConstraintRow
from navixav.simbrief.parser import DispatchSummary


class Confidence(str, Enum):
    """Niveau de confiance d'un élément sélectionné automatiquement."""

    HIGH = "élevée"
    MEDIUM = "modérée"
    LOW = "faible"
    NONE = "aucune"


@dataclass
class Choice:
    """Un élément choisi par le moteur, avec sa justification."""

    value: str | None = None
    confidence: Confidence = Confidence.NONE
    source: str = "moteur"  # "simbrief" | "moteur" | "utilisateur"
    reason: str = ""
    alternatives: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "confidence": self.confidence.value,
            "source": self.source,
            "reason": self.reason,
            "alternatives": self.alternatives,
        }


@dataclass
class WindInfo:
    raw_metar: str | None = None
    direction_deg: int | None = None
    speed_kt: int | None = None
    gust_kt: int | None = None
    variable: bool = False
    qnh_hpa: int | None = None
    altimeter_inhg: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def label(self) -> str:
        if self.direction_deg is None and not self.variable:
            return "vent inconnu"
        if self.variable:
            return f"VRB {self.speed_kt or 0} kt"
        gust = f"G{self.gust_kt}" if self.gust_kt else ""
        return f"{self.direction_deg:03d}°/{self.speed_kt}{gust} kt"


@dataclass
class RunwayChoice:
    choice: Choice
    headwind_kt: float | None = None
    crosswind_kt: float | None = None
    length_ft: float | None = None
    ils_ident: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.choice.to_dict(),
            "headwind_kt": self.headwind_kt,
            "crosswind_kt": self.crosswind_kt,
            "length_ft": self.length_ft,
            "ils_ident": self.ils_ident,
        }


@dataclass
class DepartureBlock:
    icao: str
    name: str = ""
    wind: WindInfo = field(default_factory=WindInfo)
    runway: RunwayChoice | None = None
    sid: Choice = field(default_factory=Choice)
    sid_transition: Choice = field(default_factory=Choice)
    transition_altitude_ft: int | None = None
    sid_constraints: list[ConstraintRow] = field(default_factory=list)
    sid_path: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "icao": self.icao,
            "name": self.name,
            "wind": self.wind.to_dict(),
            "runway": self.runway.to_dict() if self.runway else None,
            "sid": self.sid.to_dict(),
            "sid_transition": self.sid_transition.to_dict(),
            "transition_altitude_ft": self.transition_altitude_ft,
            "sid_constraints": [c.to_dict() for c in self.sid_constraints],
            "sid_path": self.sid_path,
        }


@dataclass
class ArrivalBlock:
    icao: str
    name: str = ""
    wind: WindInfo = field(default_factory=WindInfo)
    runway: RunwayChoice | None = None
    star: Choice = field(default_factory=Choice)
    star_transition: Choice = field(default_factory=Choice)
    approach: Choice = field(default_factory=Choice)
    approach_transition: Choice = field(default_factory=Choice)
    ils_frequency_mhz: float | None = None
    ils_ident: str | None = None
    ils_course_deg: float | None = None
    glide_slope_deg: float | None = None
    glide_intercept_fix: str | None = None
    glide_intercept_altitude: str | None = None
    final_approach_distance_nm: float | None = None
    transition_level_ft: int | None = None
    star_constraints: list[ConstraintRow] = field(default_factory=list)
    approach_constraints: list[ConstraintRow] = field(default_factory=list)
    star_path: list[dict[str, Any]] = field(default_factory=list)
    approach_path: list[dict[str, Any]] = field(default_factory=list)
    missed_approach_altitude_ft: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "icao": self.icao,
            "name": self.name,
            "wind": self.wind.to_dict(),
            "runway": self.runway.to_dict() if self.runway else None,
            "star": self.star.to_dict(),
            "star_transition": self.star_transition.to_dict(),
            "approach": self.approach.to_dict(),
            "approach_transition": self.approach_transition.to_dict(),
            "ils_frequency_mhz": self.ils_frequency_mhz,
            "ils_ident": self.ils_ident,
            "ils_course_deg": self.ils_course_deg,
            "glide_slope_deg": self.glide_slope_deg,
            "glide_intercept_fix": self.glide_intercept_fix,
            "glide_intercept_altitude": self.glide_intercept_altitude,
            "final_approach_distance_nm": self.final_approach_distance_nm,
            "transition_level_ft": self.transition_level_ft,
            "star_constraints": [c.to_dict() for c in self.star_constraints],
            "approach_constraints": [c.to_dict() for c in self.approach_constraints],
            "star_path": self.star_path,
            "approach_path": self.approach_path,
            "missed_approach_altitude_ft": self.missed_approach_altitude_ft,
        }


@dataclass
class EnrouteBlock:
    raw_simbrief_route: str = ""
    first_fix: str | None = None
    last_fix: str | None = None
    waypoints: list[str] = field(default_factory=list)
    route_legs: list[dict[str, Any]] = field(default_factory=list)
    route_path: list[dict[str, Any]] = field(default_factory=list)
    cruise_altitude_ft: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FlightPlan:
    source: dict[str, Any] = field(default_factory=dict)
    aircraft: str = ""
    aircraft_name: str = ""
    callsign: str = ""
    departure: DepartureBlock | None = None
    enroute: EnrouteBlock = field(default_factory=EnrouteBlock)
    arrival: ArrivalBlock | None = None
    alternate_icao: str | None = None
    dispatch: DispatchSummary = field(default_factory=DispatchSummary)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "aircraft": self.aircraft,
            "aircraft_name": self.aircraft_name,
            "callsign": self.callsign,
            "departure": self.departure.to_dict() if self.departure else None,
            "enroute": self.enroute.to_dict(),
            "arrival": self.arrival.to_dict() if self.arrival else None,
            "alternate_icao": self.alternate_icao,
            "dispatch": {
                key: (value.isoformat() if hasattr(value, "isoformat") else value)
                for key, value in asdict(self.dispatch).items()
                if value not in (None, "")
            },
            "warnings": self.warnings,
        }

    def atc_route(self) -> str:
        """Route ATC reconstruite : SID TRANS ... TRANS STAR."""
        parts: list[str] = []
        if self.departure:
            if self.departure.sid.value:
                parts.append(self.departure.sid.value)
            if self.departure.sid_transition.value:
                parts.append(self.departure.sid_transition.value)
        parts.extend(self.enroute.waypoints)
        if self.arrival:
            if self.arrival.star_transition.value:
                parts.append(self.arrival.star_transition.value)
            if self.arrival.star.value:
                parts.append(self.arrival.star.value)

        deduped: list[str] = []
        for token in parts:
            if not token:
                continue
            if deduped and deduped[-1] == token:
                continue
            deduped.append(token)
        return " ".join(deduped)
