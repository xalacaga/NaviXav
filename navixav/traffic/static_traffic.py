"""Trafic statique : des appareils garés aux postes réels du simulateur.

Les réseaux publient des vols ; cette source n'en publie aucun. Elle lit les
postes de stationnement que MSFS a déjà livrés à NaviXav — position, cap, rayon
et catégorie — et y gare des appareils plausibles. Un aérodrome désert cesse de
l'être sans réseau, sans compte, et sans second logiciel.

Rien n'y est aléatoire. Un poste donné reçoit toujours le même appareil, parce
que le tirage dérive de l'identifiant de l'aérodrome et du nom du poste : sans
cette stabilité, la flotte changerait de livrée à chaque relevé sous les yeux du
pilote, et le gestionnaire recréerait sans fin des objets qu'il vient de poser.

Ce n'est pas un moteur de trafic hors ligne : personne ne roule, ne décolle ni
n'atterrit. Cela reste le métier de FSLTL Injector et d'AIG Traffic Controller,
que NaviXav laisse travailler seuls quand ils tournent.
"""

from __future__ import annotations

import logging
import math
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable

from navixav.traffic.base import OWN_AIRCRAFT_RADIUS_NM, TrafficAircraft, distance_nm

LOGGER = logging.getLogger(__name__)

EARTH_RADIUS_M = 6371000.0
DEFAULT_RADIUS_NM = 40.0
DEFAULT_MAX_AIRCRAFT = 10
# Au-delà, la lecture coûte plus qu'elle ne rapporte : les aérodromes lointains
# sont hors de vue, et leurs appareils occuperaient la place des proches.
MAX_AIRPORTS = 8
# Un relevé par minute suffit à une flotte qui ne bouge pas ; le gestionnaire,
# lui, appelle `traffic()` chaque seconde.
REFRESH_S = 60.0
EMPTY_REFRESH_S = 3.0

# Types plausibles par catégorie de poste, telle que MSFS la déclare. L'ordre
# compte : le premier type disponible dans le jeu de modèles l'emporte.
STAND_TYPES: dict[str, tuple[str, ...]] = {
    "rampe GA": ("C172", "SR22", "BE58", "PC12", "C208"),
    "rampe cargo": ("B763", "A332", "B738", "AT76"),
    "rampe militaire": ("C130", "A400", "C17"),
    "porte petite": ("CRJ9", "E75L", "AT76", "DH8D", "E190"),
    "porte moyenne": ("A320", "B738", "A20N", "B38M", "A319"),
    "porte grande": ("B77W", "A359", "B789", "A333", "B788"),
    "dock": ("A320", "B738", "E190"),
}
# Un poste sans catégorie connue reste un poste : plutôt un monocouloir qu'un
# trou dans la rangée.
FALLBACK_TYPES = STAND_TYPES["porte moyenne"]


@dataclass(frozen=True)
class Stand:
    icao: str
    label: str
    kind: str | None
    latitude: float
    longitude: float
    heading: float
    altitude_ft: float


def _stable_seed(*parts: str) -> int:
    """Tirage reproductible d'une exécution à l'autre.

    `hash()` de Python est salé par processus : deux lancements donneraient
    deux flottes. Une somme de caractères suffit ici, et elle ne bouge jamais.
    """
    value = 0
    for part in parts:
        for character in part:
            value = (value * 131 + ord(character)) % 1_000_000_007
    return value


def _stand_position(
    origin_lat: float, origin_lon: float, x: float, y: float
) -> tuple[float, float]:
    """Inverse de la projection locale employée par les plans de terrain."""
    latitude = origin_lat + math.degrees(y / EARTH_RADIUS_M)
    longitude = origin_lon + math.degrees(
        x / (EARTH_RADIUS_M * math.cos(math.radians(origin_lat)))
    )
    return (latitude, longitude)


def read_stands(
    connection: sqlite3.Connection,
    centre: tuple[float, float],
    radius_nm: float,
    *,
    max_airports: int = MAX_AIRPORTS,
) -> list[Stand]:
    """Postes de stationnement des aérodromes autour du joueur.

    La sélection passe par un cadre en degrés avant la distance exacte : sans
    lui, chaque relevé lirait la table entière.
    """
    latitude, longitude = centre
    span_lat = radius_nm / 60.0
    cosine = max(0.1, math.cos(math.radians(latitude)))
    span_lon = span_lat / cosine
    try:
        airports = connection.execute(
            """SELECT icao, lat, lon, altitude_ft FROM airport
               WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?""",
            (
                latitude - span_lat, latitude + span_lat,
                longitude - span_lon, longitude + span_lon,
            ),
        ).fetchall()
    except sqlite3.Error as exc:
        LOGGER.warning("Trafic statique : base de navigation illisible (%s)", exc)
        return []

    near = sorted(
        (
            (distance_nm(centre, (row[1], row[2])), row)
            for row in airports
        ),
        key=lambda item: item[0],
    )
    near = [row for gap, row in near if gap <= radius_nm][:max_airports]
    if not near:
        return []

    stands: list[Stand] = []
    for icao, airport_lat, airport_lon, altitude_ft in near:
        try:
            rows = connection.execute(
                """SELECT label, kind, x, y, heading FROM parking
                   WHERE icao = ? ORDER BY label""",
                (icao,),
            ).fetchall()
        except sqlite3.Error:
            continue
        for label, kind, x, y, heading in rows:
            position = _stand_position(airport_lat, airport_lon, x, y)
            stands.append(Stand(
                icao=icao,
                label=str(label),
                kind=kind,
                latitude=position[0],
                longitude=position[1],
                heading=float(heading or 0.0) % 360.0,
                altitude_ft=float(altitude_ft or 0.0),
            ))
    return stands


class StaticTrafficProvider:
    """Source de trafic sans réseau, garée aux postes de l'aérodrome."""

    name = "static"

    def __init__(
        self,
        position: Callable[[], tuple[float, float]],
        connect: Callable[[], sqlite3.Connection],
        *,
        radius_nm: float = DEFAULT_RADIUS_NM,
        max_aircraft: int = DEFAULT_MAX_AIRCRAFT,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._position = position
        self._lock = threading.RLock()
        self._connect = connect
        self.radius_nm = radius_nm
        self.max_aircraft = max_aircraft
        self._clock = clock
        self._catalogue: dict[str, tuple[str, ...]] = {}
        self._fleet: list[TrafficAircraft] = []
        self._built_at: float | None = None
        self._built_cell: tuple[int, int] | None = None
        self._updated_at = ""
        self.stand_count = 0

    # ------------------------------------------------------------- modèles

    def bind_models(self, index: object) -> None:
        with self._lock:
            self._bind_models(index)

    def _bind_models(self, index: object) -> None:
        """Retient les couples type + compagnie que le jeu installé contient.

        Sans ce catalogue la source proposerait des compagnies au hasard, dont
        aucune n'aurait de livrée : le trafic resterait sur la carte. Avec lui,
        chaque appareil garé porte une livrée réellement installée.
        """
        self._built_at = None
        models = getattr(index, "models", None)
        if not models:
            self._catalogue = {}
            return
        catalogue: dict[str, list[str]] = {}
        for model in models:
            airlines = catalogue.setdefault(model.aircraft_type, [])
            airline = model.airline_icao
            if airline and airline != "ZZZZ" and airline not in airlines:
                airlines.append(airline)
        self._catalogue = {
            aircraft_type: tuple(sorted(airlines))
            for aircraft_type, airlines in catalogue.items()
        }
        LOGGER.info(
            "Trafic statique : %d type(s) disponibles dans le jeu de modèles",
            len(self._catalogue),
        )

    def _choose(self, stand: Stand) -> tuple[str, str]:
        """Type et compagnie du poste, stables et compatibles avec le jeu."""
        candidates = STAND_TYPES.get(stand.kind or "", FALLBACK_TYPES)
        seed = _stable_seed(stand.icao, stand.label)
        available = [
            aircraft_type for aircraft_type in candidates
            if not self._catalogue or aircraft_type in self._catalogue
        ]
        if not available:
            # Aucun type de la catégorie n'est installé — une rampe militaire
            # quand le jeu n'a pas de transport, par exemple. Le catalogue
            # décide alors, mais toujours par tirage : prendre le premier type
            # par ordre alphabétique poserait le même appareil sur tous les
            # postes de la même catégorie.
            available = sorted(self._catalogue) if self._catalogue else list(candidates)
        if not available:
            return ("", "")
        aircraft_type = available[seed % len(available)]
        airlines = self._catalogue.get(aircraft_type, ())
        airline = airlines[seed % len(airlines)] if airlines else ""
        return (aircraft_type, airline)

    # -------------------------------------------------------------- source

    def _cell(self, centre: tuple[float, float]) -> tuple[int, int]:
        """Case grossière : la flotte ne change qu'en changeant de secteur."""
        return (int(centre[0] * 20), int(centre[1] * 20))

    def _build(self, centre: tuple[float, float]) -> list[TrafficAircraft]:
        self.stand_count = 0
        try:
            connection = self._connect()
        except (OSError, sqlite3.Error) as exc:
            LOGGER.warning("Trafic statique indisponible : %s", exc)
            return []
        try:
            stands = read_stands(connection, centre, self.radius_nm)
            self.stand_count = len(stands)
        finally:
            try:
                connection.close()
            except sqlite3.Error:
                pass

        stands.sort(key=lambda stand: distance_nm(
            centre, (stand.latitude, stand.longitude)
        ))
        fleet: list[TrafficAircraft] = []
        for stand in stands:
            # Reserve the player's surroundings before applying the density
            # limit, otherwise nearby stands can consume every available slot.
            if distance_nm(centre, (stand.latitude, stand.longitude)) <= OWN_AIRCRAFT_RADIUS_NM:
                continue
            if len(fleet) >= self.max_aircraft:
                break
            aircraft_type, airline = self._choose(stand)
            if not aircraft_type:
                continue
            seed = _stable_seed(stand.icao, stand.label)
            callsign = (
                f"{airline}{seed % 900 + 100}" if airline
                else f"{stand.icao}{seed % 900 + 100}"
            )
            fleet.append(TrafficAircraft(
                uid=f"STATIC-{stand.icao}-{stand.label}",
                callsign=callsign[:12],
                aircraft_type=aircraft_type,
                airline_icao=airline or None,
                latitude=stand.latitude,
                longitude=stand.longitude,
                altitude_ft=stand.altitude_ft,
                ground_speed_kt=0.0,
                heading_deg=stand.heading,
                vertical_speed_fpm=0.0,
                on_ground=True,
                departure=stand.icao,
                arrival="",
            ))
        LOGGER.info(
            "Trafic statique : %d appareil(s) garé(s) sur %d poste(s) lus",
            len(fleet), len(stands),
        )
        return fleet

    def traffic(self, limit: int | None = None) -> list[TrafficAircraft]:
        with self._lock:
            return self._traffic(limit)

    def _traffic(self, limit: int | None = None) -> list[TrafficAircraft]:
        centre = self._position()
        cell = self._cell(centre)
        now = self._clock()
        stale = (
            self._built_at is None
            or cell != self._built_cell
            or now - self._built_at >= (REFRESH_S if self._fleet else EMPTY_REFRESH_S)
        )
        if stale:
            self._fleet = self._build(centre)
            self._built_at = now
            self._built_cell = cell
            self._updated_at = datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )
        return self._fleet[:limit] if limit else list(self._fleet)

    def updated_at(self) -> str:
        """Instant du dernier relevé des postes, comme pour un réseau.

        La flotte ne bouge pas, mais la carte et la fiche d'un appareil
        attendent ce champ de n'importe quelle source : sans lui, l'appel qui
        les alimente échoue et le trafic statique reste invisible.
        """
        return self._updated_at

    def detail(self, callsign: str) -> TrafficAircraft | None:
        """Appareil garé portant cet indicatif, pour la fiche de la carte."""
        wanted = callsign.strip().upper()
        return next(
            (entry for entry in self.traffic() if entry.callsign == wanted), None
        )

    def close(self) -> None:
        self._fleet = []
        self._built_at = None
        self._updated_at = ""
