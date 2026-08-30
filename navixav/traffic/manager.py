"""Synchronisation bornée d'une source trafic vers l'injecteur."""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace

from navixav.traffic.base import (
    TrafficAircraft,
    TrafficProvider,
    distance_nm as _distance_nm,
    is_own_position,
)
from navixav.traffic.fsltl import FsltlModelIndex
from navixav.traffic.injector import SimConnectTrafficInjector

LOGGER = logging.getLogger(__name__)
DEFAULT_RADIUS_NM = 100.0
DEFAULT_MAX_AIRCRAFT = 100
GROUND_SPEED_MAX_KT = 50.0
AIRBORNE_SPEED_MIN_KT = 80.0
MISSING_GRACE_S = 90.0
MAX_EXTRAPOLATION_S = 90.0
RECONCILE_INTERVAL_S = 15.0


@dataclass
class _Track:
    aircraft: TrafficAircraft
    observed_at: float
    last_seen_at: float


def _same_motion(a: TrafficAircraft, b: TrafficAircraft) -> bool:
    return all(
        getattr(a, field) == getattr(b, field)
        for field in (
            "latitude", "longitude", "altitude_ft", "ground_speed_kt",
            "heading_deg", "vertical_speed_fpm", "on_ground",
        )
    )


def _extrapolate(aircraft: TrafficAircraft, elapsed_s: float) -> TrafficAircraft:
    """Prolonge un relevé figé sans dépasser sa fenêtre de confiance."""
    speed = aircraft.ground_speed_kt
    heading = aircraft.heading_deg
    elapsed = min(max(0.0, elapsed_s), MAX_EXTRAPOLATION_S)
    if elapsed == 0.0 or speed is None or heading is None or speed <= 0.0:
        return aircraft

    angular = (speed * elapsed / 3600.0) / 3440.065
    bearing = math.radians(heading)
    latitude = math.radians(aircraft.latitude)
    longitude = math.radians(aircraft.longitude)
    next_latitude = math.asin(
        math.sin(latitude) * math.cos(angular)
        + math.cos(latitude) * math.sin(angular) * math.cos(bearing)
    )
    next_longitude = longitude + math.atan2(
        math.sin(bearing) * math.sin(angular) * math.cos(latitude),
        math.cos(angular) - math.sin(latitude) * math.sin(next_latitude),
    )
    altitude = aircraft.altitude_ft
    if (
        aircraft.on_ground is not True
        and altitude is not None
        and aircraft.vertical_speed_fpm is not None
    ):
        altitude += aircraft.vertical_speed_fpm * elapsed / 60.0
    return replace(
        aircraft,
        latitude=math.degrees(next_latitude),
        longitude=(math.degrees(next_longitude) + 540.0) % 360.0 - 180.0,
        altitude_ft=altitude,
    )


class TrafficManager:
    """Effectue un cycle déterministe ; l'appelant choisit sa cadence."""

    def __init__(
        self,
        provider: TrafficProvider,
        models: FsltlModelIndex,
        injector: SimConnectTrafficInjector,
        position: Callable[[], tuple[float, float]],
        *,
        altitude: Callable[[], float | None] | None = None,
        radius_nm: float = DEFAULT_RADIUS_NM,
        max_aircraft: int = DEFAULT_MAX_AIRCRAFT,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.provider = provider
        self.models = models
        self.injector = injector
        self.position = position
        # L'altitude n'est pas obligatoire : elle départage seulement l'appareil
        # posé sur le joueur de celui qui le survole.
        self.altitude = altitude
        self.radius_nm = radius_nm
        self.max_aircraft = max_aircraft
        self._clock = clock
        self._tracks: dict[str, _Track] = {}
        self._last_reconcile_at: float | None = None
        self._lock = threading.Lock()

    def _tracked(self, aircraft: TrafficAircraft, now: float) -> TrafficAircraft:
        track = self._tracks.get(aircraft.uid)
        if track is None or not _same_motion(track.aircraft, aircraft):
            track = _Track(aircraft, now, now)
            self._tracks[aircraft.uid] = track
        else:
            track.last_seen_at = now
        return _extrapolate(track.aircraft, now - track.observed_at)

    @staticmethod
    def _injectable(aircraft: TrafficAircraft) -> TrafficAircraft | None:
        if aircraft.on_ground is None:
            # VATSIM ne publie pas de champ `on_ground`. Une vitesse faible est
            # néanmoins une preuve suffisante pour les appareils stationnés ou
            # au roulage ; sans cette déduction, tout le trafic aux portes est
            # écarté. La bande 50–80 kt reste volontairement indéterminée pour
            # ne pas poser au sol un appareil lent en vol.
            if aircraft.ground_speed_kt is None:
                return None
            if aircraft.ground_speed_kt <= GROUND_SPEED_MAX_KT:
                return replace(aircraft, on_ground=True)
            if aircraft.ground_speed_kt >= AIRBORNE_SPEED_MIN_KT:
                return replace(aircraft, on_ground=False)
            return None
        return aircraft

    def sync_once(self) -> dict[str, int]:
        if not self._lock.acquire(blocking=False):
            return {
                "created_or_updated": 0, "removed": 0, "recreated": 0, "skipped": 0
            }
        try:
            now = self._clock()
            # Avant tout, se remettre d'accord avec le simulateur : ce qu'il ne
            # porte plus doit être oublié, sinon il ne serait jamais recréé.
            # Un relevé impossible n'annule pas le cycle : mieux vaut suivre
            # les appareils déjà connus que ne rien injecter du tout.
            recreated = 0
            if (
                self._last_reconcile_at is None
                or now - self._last_reconcile_at >= RECONCILE_INTERVAL_S
            ):
                self._last_reconcile_at = now
                try:
                    recreated = len(
                        self.injector.reconcile(int(self.radius_nm * 1852))
                    )
                except (OSError, RuntimeError) as exc:
                    LOGGER.warning("Relevé des objets AI impossible : %s", exc)
            centre = self.position()
            own_altitude: float | None = None
            if self.altitude is not None:
                try:
                    own_altitude = self.altitude()
                except (OSError, RuntimeError, ValueError):
                    own_altitude = None
            reported = sorted(
                self.provider.traffic(),
                key=lambda item: _distance_nm(centre, (item.latitude, item.longitude)),
            )
            selected_raw = [
                item for item in reported
                if _distance_nm(centre, (item.latitude, item.longitude)) <= self.radius_nm
                # Le joueur est parfois rendu par son propre réseau : l'injecter
                # poserait une copie de son appareil dans son cockpit.
                and not is_own_position(item, centre, own_altitude)
            ][: self.max_aircraft]
            reported_uids = {item.uid for item in reported}
            selected_uids = {item.uid for item in selected_raw}
            selected = [self._tracked(item, now) for item in selected_raw]

            # Un relevé public peut omettre un appareil pendant un cycle. Le
            # supprimer aussitôt le fait clignoter puis recréer quinze ou
            # soixante secondes plus tard. On prolonge brièvement sa dernière
            # trajectoire, mais jamais s'il est encore publié hors de la bulle.
            for uid, track in list(self._tracks.items()):
                if uid in reported_uids:
                    if uid not in selected_uids:
                        self._tracks.pop(uid, None)
                    continue
                if now - track.last_seen_at > MISSING_GRACE_S:
                    self._tracks.pop(uid, None)
                    continue
                if len(selected) >= self.max_aircraft:
                    continue
                predicted = _extrapolate(track.aircraft, now - track.observed_at)
                if (
                    _distance_nm(
                        centre, (predicted.latitude, predicted.longitude)
                    ) <= self.radius_nm
                    and not is_own_position(predicted, centre, own_altitude)
                ):
                    selected.append(predicted)
                else:
                    self._tracks.pop(uid, None)
            active: set[str] = set()
            updated = skipped = 0
            owned = self.injector.owned
            for raw in selected:
                aircraft = self._injectable(raw)
                if aircraft is None:
                    # Une valeur momentanément ambiguë ne doit pas faire
                    # disparaître un objet déjà suivi. Il restera à sa dernière
                    # position jusqu'au prochain relevé exploitable.
                    if raw.uid in owned:
                        active.add(raw.uid)
                    skipped += 1
                    continue
                model = self.models.match(aircraft)
                if model is None and self.provider.name.casefold() == "opensky":
                    fallback = getattr(self.models, "generic_fallback", None)
                    if callable(fallback):
                        model = fallback(aircraft)
                if model is None:
                    if raw.uid in owned:
                        active.add(raw.uid)
                    skipped += 1
                    continue
                try:
                    self.injector.upsert(aircraft, model)
                except (OSError, ValueError, RuntimeError) as exc:
                    LOGGER.warning("Trafic %s non injecté : %s", aircraft.callsign, exc)
                    skipped += 1
                    continue
                active.add(aircraft.uid)
                updated += 1
            stale = set(self.injector.owned) - active
            removed = 0
            for uid in stale:
                try:
                    self.injector.remove(uid)
                    removed += 1
                except RuntimeError as exc:
                    LOGGER.warning("Trafic %s non retiré : %s", uid, exc)
            return {
                "created_or_updated": updated,
                "removed": removed,
                "recreated": recreated,
                "skipped": skipped,
            }
        finally:
            self._lock.release()

    def close(self) -> None:
        # Attend la fin d'un éventuel cycle avant de fermer SimConnect : aucun
        # upsert ne peut ainsi rouvrir une connexion pendant l'arrêt.
        with self._lock:
            self.injector.close()
            self._tracks.clear()
