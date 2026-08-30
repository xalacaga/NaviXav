"""Contrats indépendants de la source réseau et de SimConnect."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Protocol

# Un appareil posé à l'endroit exact du joueur est presque toujours le joueur
# lui-même, rendu par le réseau auquel il est connecté. L'afficher doublerait
# sa silhouette sur la carte, et l'injecter poserait une copie dans son propre
# cockpit. Le seuil reste serré pour ne pas escamoter le stationnement voisin,
# et l'altitude tranche le cas du survol.
OWN_AIRCRAFT_RADIUS_NM = 0.1
OWN_AIRCRAFT_ALTITUDE_FT = 300.0

# Indicatif donné à un appareil qui n'en publie aucun : le flux ADS-B en compte
# toujours quelques-uns. Une chaîne stable vaut mieux qu'un champ vide, que le
# simulateur afficherait comme une immatriculation manquante.
GENERIC_CALLSIGN_PREFIX = "TFC"


def distance_nm(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance orthodromique en milles marins."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 3440.065 * 2 * math.asin(math.sqrt(value))


def generic_callsign(seed: str) -> str:
    """Indicatif lisible, stable et propre à un appareil qui n'en publie pas.

    Il dérive de l'identifiant de l'appareil, jamais d'un compteur : le même
    avion garde le même indicatif d'un relevé au suivant, sinon il changerait
    de nom à chaque cycle sous les yeux du pilote.
    """
    cleaned = "".join(
        character for character in seed.upper() if character.isalnum()
    )[-4:]
    return f"{GENERIC_CALLSIGN_PREFIX}{cleaned or '0000'}"


@dataclass(frozen=True)
class TrafficAircraft:
    """Position et identité disponibles pour un appareil de trafic."""

    uid: str
    callsign: str
    aircraft_type: str | None
    airline_icao: str | None
    latitude: float
    longitude: float
    altitude_ft: float | None = None
    ground_speed_kt: float | None = None
    heading_deg: float | None = None
    vertical_speed_fpm: float | None = None
    on_ground: bool | None = None
    departure: str = ""
    arrival: str = ""

    @property
    def aircraft(self) -> str:
        """Alias historique utilisé par la carte et ses tests."""
        return self.aircraft_type or ""

    def to_dict(self) -> dict[str, Any]:
        """Forme compatible avec l'API cartographique existante."""
        payload = asdict(self)
        payload["aircraft"] = self.aircraft_type or ""
        return payload


def is_own_position(
    aircraft: TrafficAircraft,
    centre: tuple[float, float] | None,
    altitude_ft: float | None = None,
) -> bool:
    """Indique qu'un appareil occupe la place du joueur.

    Sans position connue du joueur, rien n'est écarté : mieux vaut une
    silhouette de trop qu'un trafic amputé sur une comparaison impossible.
    """
    if centre is None:
        return False
    if distance_nm(centre, (aircraft.latitude, aircraft.longitude)) > OWN_AIRCRAFT_RADIUS_NM:
        return False
    if altitude_ft is None or aircraft.altitude_ft is None:
        return True
    return abs(aircraft.altitude_ft - altitude_ft) <= OWN_AIRCRAFT_ALTITUDE_FT


class TrafficProvider(Protocol):
    """Une source produit des appareils sans connaître leur modèle MSFS."""

    @property
    def name(self) -> str: ...

    def traffic(self, limit: int | None = None) -> list[TrafficAircraft]: ...

    def close(self) -> None: ...


class MatchKind(StrEnum):
    EXACT = "exact"
    AIRCRAFT = "aircraft"
    FAMILY = "family"
    MSFS = "msfs"


@dataclass(frozen=True)
class ResolvedAircraftModel:
    """Titre réellement spawnable et explication de sa sélection."""

    title: str
    provider: str
    match_kind: MatchKind
    fallback_level: int
    reason: str
    source_rule: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
