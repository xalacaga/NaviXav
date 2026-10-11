"""Contrats indépendants de la source réseau et de SimConnect."""

from __future__ import annotations

import math
import threading
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from typing import Any, Iterable, Protocol, runtime_checkable

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

# Aucun flux ne publie le taux de virage : il se déduit de deux relevés
# successifs. Trop rapprochés, ils ne mesurent que le bruit de la route
# publiée ; trop espacés, ils ne disent plus si le virage dure encore. En deçà
# du dixième de degré par seconde, l'appareil est en ligne droite ; au-delà du
# taux standard, la mesure est fausse plutôt que l'avion acrobate.
TURN_MIN_INTERVAL_S = 5.0
TURN_MAX_INTERVAL_S = 300.0
TURN_MIN_RATE_DPS = 0.1
TURN_MAX_RATE_DPS = 3.0
# Sans indicateur sol (VATSIM), la vitesse tranche comme pour l'injection.
TURN_GROUND_SPEED_MAX_KT = 50.0


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
    # Unix seconds. Position age must not be inferred from the feed publication time.
    position_timestamp: float | None = None
    # Degrés par seconde, positif à droite. Mesuré entre deux relevés : seule
    # une source lente en a besoin pour anticiper un virage en cours.
    turn_rate_dps: float | None = None

    @property
    def aircraft(self) -> str:
        """Alias historique utilisé par la carte et ses tests."""
        return self.aircraft_type or ""

    def to_dict(self) -> dict[str, Any]:
        """Forme compatible avec l'API cartographique existante."""
        payload = asdict(self)
        payload["aircraft"] = self.aircraft_type or ""
        return payload


def turn_rate(
    previous: tuple[float, float] | None, current: tuple[float, float]
) -> float | None:
    """Taux de virage moyen entre deux relevés (horodatage, route)."""
    if previous is None:
        return None
    elapsed = current[0] - previous[0]
    if not TURN_MIN_INTERVAL_S <= elapsed <= TURN_MAX_INTERVAL_S:
        return None
    delta = (current[1] - previous[1] + 180.0) % 360.0 - 180.0
    rate = delta / elapsed
    if abs(rate) < TURN_MIN_RATE_DPS:
        return None
    return max(-TURN_MAX_RATE_DPS, min(TURN_MAX_RATE_DPS, rate))


class TurnRateTracker:
    """Mémoire des routes publiées, pour mesurer le virage de chaque appareil.

    Une source relit souvent le même relevé en cache, et parfois une partie
    seulement : la mémoire n'est donc purgée que par l'âge, jamais parce
    qu'un appareil manque à une lecture.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # uid -> (horodatage, route, taux mesuré)
        self._tracks: dict[str, tuple[float, float, float | None]] = {}
        self._latest = 0.0

    def apply(
        self, found: list[TrafficAircraft], stamp: float | None = None
    ) -> list[TrafficAircraft]:
        """Ajoute le virage mesuré depuis le relevé distinct précédent.

        `stamp` date tout le relevé quand la source ne date pas chaque
        position ; sinon `position_timestamp` fait foi.
        """
        result = []
        with self._lock:
            for entry in found:
                when = entry.position_timestamp if entry.position_timestamp else stamp
                heading = entry.heading_deg
                if when is None or heading is None or _grounded(entry):
                    result.append(entry)
                    continue
                self._latest = max(self._latest, when)
                known = self._tracks.get(entry.uid)
                if known is not None and when - known[0] < TURN_MIN_INTERVAL_S:
                    # Même relevé, ou relu trop tôt pour mesurer quoi que ce
                    # soit : la référence et la mesure précédentes valent encore.
                    rate = known[2]
                else:
                    rate = turn_rate(known[:2] if known else None, (when, heading))
                    self._tracks[entry.uid] = (when, heading, rate)
                result.append(
                    replace(entry, turn_rate_dps=rate) if rate is not None else entry
                )
            horizon = self._latest - TURN_MAX_INTERVAL_S
            for uid in [uid for uid, track in self._tracks.items() if track[0] < horizon]:
                del self._tracks[uid]
        return result


def _grounded(aircraft: TrafficAircraft) -> bool:
    if aircraft.on_ground is not None:
        return aircraft.on_ground
    speed = aircraft.ground_speed_kt
    return speed is None or speed <= TURN_GROUND_SPEED_MAX_KT


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
    """Une source produit des appareils sans connaître leur modèle MSFS.

    L'injection ne demande que `traffic()`, mais la carte et la fiche d'un
    appareil réclament les deux autres à n'importe quelle source : une source
    qui ne les porte pas se voit injectée sans jamais s'afficher.
    """

    @property
    def name(self) -> str: ...

    def traffic(self, limit: int | None = None) -> list[TrafficAircraft]: ...

    def updated_at(self) -> str: ...

    def detail(self, callsign: str) -> TrafficAircraft | None: ...

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


class InstallationStatus(StrEnum):
    """État d'un jeu de modèles sur le disque, quel qu'en soit le fournisseur.

    Un paquet peut manquer, être présent mais inutilisable, ou prêt à servir.
    La distinction vaut pour tous les jeux de modèles, et c'est elle que
    l'interface affiche : elle n'appartient donc à aucun d'eux en propre.
    """

    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    INCOMPLETE = "incomplete"


class ModelInstallation(Protocol):
    """Ce que le service a besoin de savoir d'un jeu de modèles installé."""

    status: InstallationStatus
    reason: str

    def to_dict(self) -> dict[str, Any]: ...


class ModelIndex(Protocol):
    """Un jeu de modèles interrogé sans que l'appelant sache lequel c'est.

    Le gestionnaire n'a jamais besoin de plus : il donne un appareil, il
    reçoit un titre spawnable et la raison de ce choix. Tout le reste — nom
    du paquet, règles VMR, conventions de titres — appartient au fournisseur.
    """

    def match(
        self, aircraft: TrafficAircraft, msfs_fallback_titles: Iterable[str] = ()
    ) -> ResolvedAircraftModel | None: ...


@runtime_checkable
class GenericFallbackIndex(ModelIndex, Protocol):
    """Jeu de modèles sachant proposer un appareil neutre faute de type.

    Le repli tient à une convention propre au fournisseur — chez FSLTL, la
    compagnie « ZZZZ » des modèles génériques. Un jeu qui n'en a pas reste un
    `ModelIndex` valide : le trafic sans type resté sur la carte vaut mieux
    qu'un monocouloir posé au hasard.
    """

    def generic_fallback(
        self, aircraft: TrafficAircraft
    ) -> ResolvedAircraftModel | None: ...
