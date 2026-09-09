"""Synchronisation bornée d'une source trafic vers l'injecteur."""

from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace

from navixav.traffic.base import (
    GenericFallbackIndex,
    ModelIndex,
    TrafficAircraft,
    TrafficProvider,
    distance_nm as _distance_nm,
    is_own_position,
)
from navixav.traffic.injector import SimConnectTrafficInjector
from navixav.live.base import AircraftState

LOGGER = logging.getLogger(__name__)
DEFAULT_RADIUS_NM = 40.0
DEFAULT_MAX_AIRCRAFT = 10
GROUND_SPEED_MAX_KT = 50.0
AIRBORNE_SPEED_MIN_KT = 80.0
MISSING_GRACE_S = 90.0
MAX_EXTRAPOLATION_S = 90.0
RECONCILE_INTERVAL_S = 15.0
GROUND_STATIONARY_MAX_KT = 2.0
GROUND_POSITION_DEADBAND_NM = 0.015
GROUND_SMOOTHING_S = 2.5
GROUND_PREDICTION_FULL_S = 2.0
GROUND_PREDICTION_STOP_S = 5.0
AIRBORNE_SMOOTHING_S = 4.0


@dataclass
class _Track:
    aircraft: TrafficAircraft
    observed_at: float
    last_seen_at: float
    rendered: TrafficAircraft
    rendered_at: float
    parked: TrafficAircraft | None = None


def _stationary(aircraft: TrafficAircraft) -> bool:
    return (aircraft.on_ground is True
            and aircraft.ground_speed_kt is not None
            and aircraft.ground_speed_kt <= GROUND_STATIONARY_MAX_KT)


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
    if aircraft.on_ground is True:
        if _stationary(aircraft):
            return replace(aircraft, ground_speed_kt=0.0, vertical_speed_fpm=0.0)
        # Intégrale d'une vitesse constante puis décroissante jusqu'à zéro.
        # L'âge est celui du relevé source, jamais celui de la dernière image.
        taper = GROUND_PREDICTION_STOP_S - GROUND_PREDICTION_FULL_S
        slowing = min(max(0.0, elapsed - GROUND_PREDICTION_FULL_S), taper)
        elapsed = min(elapsed, GROUND_PREDICTION_FULL_S) + slowing - slowing**2 / (2 * taper)
        aircraft = replace(aircraft, ground_speed_kt=(speed * (1 - slowing / taper)
                                                    if speed is not None else None))
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


def _blend_value(
    current: float | None, target: float | None, factor: float
) -> float | None:
    if target is None:
        return current
    if current is None:
        return target
    return current + (target - current) * factor


def _blend_heading(
    current: float | None, target: float | None, factor: float
) -> float | None:
    if target is None:
        return current
    if current is None:
        return target % 360.0
    delta = (target - current + 180.0) % 360.0 - 180.0
    return (current + delta * factor) % 360.0


def _blend_motion(
    current: TrafficAircraft, target: TrafficAircraft, factor: float
) -> TrafficAircraft:
    """Raccorde deux états sans téléporter l'objet au nouveau relevé."""
    longitude_delta = (target.longitude - current.longitude + 180.0) % 360.0 - 180.0
    return replace(
        target,
        latitude=current.latitude + (target.latitude - current.latitude) * factor,
        longitude=(current.longitude + longitude_delta * factor + 540.0) % 360.0 - 180.0,
        altitude_ft=_blend_value(current.altitude_ft, target.altitude_ft, factor),
        ground_speed_kt=_blend_value(
            current.ground_speed_kt, target.ground_speed_kt, factor
        ),
        heading_deg=_blend_heading(current.heading_deg, target.heading_deg, factor),
        vertical_speed_fpm=_blend_value(
            current.vertical_speed_fpm, target.vertical_speed_fpm, factor
        ),
    )


class TrafficManager:
    """Effectue un cycle déterministe ; l'appelant choisit sa cadence."""

    def __init__(
        self,
        provider: TrafficProvider,
        models: ModelIndex,
        injector: SimConnectTrafficInjector,
        position: Callable[[], tuple[float, float]],
        *,
        altitude: Callable[[], float | None] | None = None,
        radius_nm: float = DEFAULT_RADIUS_NM,
        max_aircraft: int = DEFAULT_MAX_AIRCRAFT,
        clock: Callable[[], float] = time.monotonic,
        state: Callable[[], AircraftState] | None = None,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self.provider = provider
        self.models = models
        self.injector = injector
        self.position = position
        # L'altitude n'est pas obligatoire : elle départage seulement l'appareil
        # posé sur le joueur de celui qui le survole.
        self.altitude = altitude
        self.state = state
        self.radius_nm = radius_nm
        self.max_aircraft = max_aircraft
        self._clock = clock
        self._wall_clock = wall_clock
        self._tracks: dict[str, _Track] = {}
        self._render_tracks: dict[str, _Track] = {}
        self._render_targets: tuple[_Track, ...] = ()
        self._render_centre: tuple[float, float] | None = None
        self._render_lock = threading.Lock()
        self._last_reconcile_at: float | None = None
        self._lock = threading.Lock()
        self._closed = False
        self._create_retry_at = 0.0
        self.progress: Callable[[dict], None] = lambda status: None
        self.cancelled: Callable[[], bool] = lambda: False

    def render_once(self) -> None:
        """Animate known objects while the source waits for its next report."""
        if not self._render_lock.acquire(blocking=False):
            return
        try:
            if self._closed:
                return
            now = self._clock()
            targets = self._render_targets
            retained = {track.aircraft.uid for track in targets}
            for uid in set(self._render_tracks) - retained:
                self._render_tracks.pop(uid, None)
            for track in targets:
                if now - track.observed_at > MAX_EXTRAPOLATION_S:
                    continue
                uid = track.aircraft.uid
                previous = self._render_tracks.get(uid)
                changed = previous is None or previous.aircraft != track.aircraft or previous.observed_at != track.observed_at
                if not changed:
                    # Once settled, a parked object needs no per-frame work.
                    if previous.parked is not None and previous.rendered == previous.parked:
                        continue
                    centre = self._render_centre
                    distance = (_distance_nm(centre, (track.aircraft.latitude, track.aircraft.longitude))
                                if centre is not None else 0.0)
                    interval = 0.2 if distance > 40 else 1 / 15 if distance > 10 else 0.0
                    if now - previous.rendered_at + 1e-9 < interval:
                        continue
                if uid not in self._render_tracks:
                    self._render_tracks[uid] = replace(track)
                aircraft = self._injectable(self._tracked(
                    track.aircraft, now, tracks=self._render_tracks,
                    observed_at=track.observed_at,
                ))
                if aircraft is None:
                    continue
                animate = getattr(self.injector, "animate", None)
                if callable(animate):
                    animate(aircraft)
                    continue
                if uid not in self.injector.owned:
                    continue
                model = self.models.match(aircraft)
                if (model is None and self.provider.name.casefold() == "opensky"
                        and isinstance(self.models, GenericFallbackIndex)):
                    model = self.models.generic_fallback(aircraft)
                if model is not None:
                    self.injector.upsert(aircraft, model)
        finally:
            self._render_lock.release()

    def _tracked(self, aircraft: TrafficAircraft, now: float, *,
                 tracks: dict[str, _Track] | None = None,
                 seen: bool = True, observed_at: float | None = None) -> TrafficAircraft:
        aircraft = self._injectable(aircraft) or aircraft
        timestamp = aircraft.position_timestamp
        if (timestamp is not None and (not math.isfinite(timestamp)
                or timestamp <= 0 or timestamp > self._wall_clock() + 5.0)):
            aircraft = replace(aircraft, position_timestamp=None)
            timestamp = None
        tracks = self._tracks if tracks is None else tracks
        track = tracks.get(aircraft.uid)
        if (track is not None and timestamp is not None
                and track.aircraft.position_timestamp is not None
                and timestamp < track.aircraft.position_timestamp):
            # An out-of-order report cannot move an aircraft back in time.
            aircraft = track.aircraft
            timestamp = aircraft.position_timestamp
        source_time = (observed_at if observed_at is not None else
                       now - max(0.0, self._wall_clock() - timestamp)
                       if timestamp is not None else now)
        if track is None:
            rendered = _extrapolate(aircraft, now - source_time)
            track = _Track(aircraft, source_time, now, rendered, now,
                           rendered if _stationary(aircraft) else None)
            tracks[aircraft.uid] = track
            return rendered

        elapsed = max(0.0, now - track.rendered_at)
        prediction_step = max(0.0, min(now - track.observed_at, MAX_EXTRAPOLATION_S)
                              - min(track.rendered_at - track.observed_at, MAX_EXTRAPOLATION_S))
        current = (track.rendered if aircraft.on_ground is True
                   else _extrapolate(track.rendered, prediction_step))
        fresh_timestamp = timestamp is not None and timestamp != track.aircraft.position_timestamp
        if not _same_motion(track.aircraft, aircraft) or fresh_timestamp:
            # Un transpondeur immobile bouge souvent de quelques mètres autour
            # de sa position GPS. Ces oscillations ne sont pas un pushback :
            # les reproduire ferait vibrer l'avion au parking.
            keep_parking = (
                _stationary(aircraft)
                and track.parked is not None
                and _distance_nm(
                    (track.parked.latitude, track.parked.longitude),
                    (aircraft.latitude, aircraft.longitude),
                ) <= GROUND_POSITION_DEADBAND_NM
            )
            if not keep_parking:
                track.parked = (_extrapolate(aircraft, 0.0)
                                if _stationary(aircraft) else None)
            if timestamp is None or fresh_timestamp:
                track.observed_at = source_time
            track.aircraft = aircraft

        if seen:
            track.last_seen_at = now
        target = track.parked or _extrapolate(track.aircraft, now - track.observed_at)
        smoothing = (
            GROUND_SMOOTHING_S
            if target.on_ground is True
            else AIRBORNE_SMOOTHING_S
        )
        factor = 1.0 - math.exp(-elapsed / smoothing) if elapsed > 0.0 else 1.0
        rendered = _blend_motion(current, target, factor)
        if target.on_ground is True:
            # Smooth acceleration, but honor a stop immediately: animation
            # must not reintroduce momentum once the source says parked.
            rendered = replace(rendered, ground_speed_kt=(0.0 if target.ground_speed_kt == 0.0
                                                        else rendered.ground_speed_kt),
                               vertical_speed_fpm=target.vertical_speed_fpm)
            if (target.ground_speed_kt == 0.0 and _distance_nm(
                    (rendered.latitude, rendered.longitude),
                    (target.latitude, target.longitude)) < 0.25 / 1852):
                rendered = target
        track.rendered = rendered
        track.rendered_at = now
        return rendered

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
        # Network/cache refresh must not hold the animation lock.
        reported = self.provider.traffic()
        if not self._lock.acquire(blocking=False):
            return {
                "created_or_updated": 0, "removed": 0, "recreated": 0, "skipped": 0
            }
        try:
            if self._closed:
                return {"created_or_updated": 0, "removed": 0, "recreated": 0, "skipped": 0}
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
            player = self.state() if self.state is not None else None
            centre = (player.latitude, player.longitude) if player is not None else self.position()
            self._render_centre = centre
            own_altitude: float | None = None
            if player is not None:
                own_altitude = player.altitude_ft
            elif self.altitude is not None:
                try:
                    own_altitude = self.altitude()
                except (OSError, RuntimeError, ValueError):
                    own_altitude = None
            reported = sorted(
                reported,
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
                predicted = self._tracked(track.aircraft, now, seen=False)
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
            # Immutable snapshot: animation never waits for the lifecycle lock.
            self._render_targets = tuple(replace(self._tracks[item.uid]) for item in selected)
            updated = skipped = 0
            owned = self.injector.owned
            failed = 0
            attempted = pending = 0
            loading = any(item.uid not in owned for item in selected)
            if loading:
                self.progress({"state": "loading", "confirmed": len(owned),
                               "selected": len(selected), "skipped": 0, "failed": 0})
            for raw in selected:
                if self.cancelled():
                    return {"created_or_updated": updated, "removed": 0,
                            "recreated": recreated, "skipped": skipped}
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
                if (
                    model is None
                    and self.provider.name.casefold() == "opensky"
                    # Tous les jeux de modèles n'ont pas de convention
                    # générique : celui qui n'en a pas laisse l'appareil sur
                    # la carte plutôt que de lui prêter une silhouette fausse.
                    and isinstance(self.models, GenericFallbackIndex)
                ):
                    model = self.models.generic_fallback(aircraft)
                if model is None:
                    if raw.uid in owned:
                        active.add(raw.uid)
                    skipped += 1
                    continue
                if raw.uid not in owned:
                    if now < self._create_retry_at:
                        pending += 1
                        failed += 1
                        continue
                    if attempted >= 4:
                        pending += 1
                        continue
                    attempted += 1
                try:
                    self.injector.upsert(aircraft, model)
                except (OSError, ValueError, RuntimeError) as exc:
                    LOGGER.warning("Trafic %s non injecté : %s", aircraft.callsign, exc)
                    skipped += 1
                    failed += 1
                    if raw.uid not in owned:
                        self._create_retry_at = self._clock() + 5.0
                    continue
                active.add(aircraft.uid)
                updated += 1
                if loading:
                    self.progress({"state": "loading", "confirmed": len(self.injector.owned),
                                   "selected": len(selected), "skipped": skipped, "failed": failed})
            stale = set(self.injector.owned) - active
            removed = 0
            for uid in stale:
                try:
                    self.injector.remove(uid)
                    removed += 1
                except RuntimeError as exc:
                    LOGGER.warning("Trafic %s non retiré : %s", uid, exc)
            self.progress({"state": "error" if failed else ("loading" if pending else ("active" if updated else "empty")),
                           "confirmed": len(self.injector.owned), "selected": len(selected),
                           "stands": getattr(self.provider, "stand_count", None),
                           "skipped": skipped, "failed": failed})
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
            with self._render_lock:
                self._closed = True
                self._render_targets = ()
                self._render_tracks.clear()
                self.injector.close()
                self._tracks.clear()
