"""Modèles de sortie : le plan de vol complété."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from navixav.constraints import ConstraintRow
from navixav.simbrief.parser import DispatchSummary


# Un METAR au-delà de cette ancienneté n'est plus représentatif.
STALE_AFTER_MINUTES = 90


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
class TafPeriod:
    """Un créneau de TAF retenu parce qu'il change la donne opérationnelle."""

    kind: str = ""  # "base" | "FM" | "TEMPO" | "BECMG" | "PROB30" | "PROB40"
    raw: str = ""
    from_time: str | None = None
    to_time: str | None = None
    wind: WindInfo | None = None
    visibility_m: int | None = None
    ceiling_ft: int | None = None
    phenomena: list[dict[str, str]] = field(default_factory=list)
    flight_category: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "raw": self.raw,
            "from_time": self.from_time,
            "to_time": self.to_time,
            "wind": self.wind.to_dict() if self.wind else None,
            "visibility_m": self.visibility_m,
            "ceiling_ft": self.ceiling_ft,
            "phenomena": self.phenomena,
            "flight_category": self.flight_category,
        }


@dataclass
class AirportWeather:
    """Météo décodée d'un terrain : l'essentiel, plus le brut pour le reste."""

    icao: str = ""
    name: str = ""
    role: str = ""  # "departure" | "arrival" | "alternate"
    source: str = ""  # "simbrief" | "awc" | "utilisateur"
    raw_metar: str | None = None
    raw_taf: str | None = None
    observed_at: datetime | None = None
    age_minutes: int | None = None
    wind: WindInfo = field(default_factory=WindInfo)
    visibility_m: int | None = None
    ceiling_ft: int | None = None
    clouds: list[dict[str, Any]] = field(default_factory=list)
    temperature_c: int | None = None
    dew_point_c: int | None = None
    spread_c: int | None = None
    qnh_hpa: int | None = None
    altimeter_inhg: float | None = None
    phenomena: list[dict[str, str]] = field(default_factory=list)
    flight_category: str | None = None
    cavok: bool = False
    auto: bool = False
    no_significant_change: bool = False
    taf_periods: list[TafPeriod] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def stale(self) -> bool:
        """Vrai quand l'observation est trop ancienne pour être représentative."""
        return self.age_minutes is not None and self.age_minutes > STALE_AFTER_MINUTES

    def to_dict(self) -> dict[str, Any]:
        return {
            "icao": self.icao,
            "name": self.name,
            "role": self.role,
            "source": self.source,
            "raw_metar": self.raw_metar,
            "raw_taf": self.raw_taf,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "age_minutes": self.age_minutes,
            "stale": self.stale,
            "wind": self.wind.to_dict(),
            "visibility_m": self.visibility_m,
            "ceiling_ft": self.ceiling_ft,
            "clouds": self.clouds,
            "temperature_c": self.temperature_c,
            "dew_point_c": self.dew_point_c,
            "spread_c": self.spread_c,
            "qnh_hpa": self.qnh_hpa,
            "altimeter_inhg": self.altimeter_inhg,
            "phenomena": self.phenomena,
            "flight_category": self.flight_category,
            "cavok": self.cavok,
            "auto": self.auto,
            "no_significant_change": self.no_significant_change,
            "taf_periods": [period.to_dict() for period in self.taf_periods],
            "notes": self.notes,
        }


@dataclass
class EnrouteWeather:
    """Conditions de croisière, telles que calculées par SimBrief pour l'OFP."""

    cruise_altitude_ft: int | None = None
    wind_direction_deg: int | None = None
    wind_speed_kt: int | None = None
    wind_component_kt: int | None = None
    temperature_dev_c: int | None = None
    outside_air_temperature_c: int | None = None
    tropopause_ft: int | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WeatherBriefing:
    """Briefing météo du vol : départ, croisière, arrivée et dégagement."""

    departure: AirportWeather | None = None
    enroute: EnrouteWeather = field(default_factory=EnrouteWeather)
    arrival: AirportWeather | None = None
    alternate: AirportWeather | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "departure": self.departure.to_dict() if self.departure else None,
            "enroute": self.enroute.to_dict(),
            "arrival": self.arrival.to_dict() if self.arrival else None,
            "alternate": self.alternate.to_dict() if self.alternate else None,
            "warnings": self.warnings,
        }


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
    weather: WeatherBriefing = field(default_factory=WeatherBriefing)
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
            "weather": self.weather.to_dict(),
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
