"""Pilote la caméra de MSFS 2024, image après image.

Le service tient sa propre connexion SimConnect, abonnée à chaque image de
simulation, comme celui de la turbulence : la caméra suit le rythme du
simulateur sans encombrer le suivi de vol. NaviXav ne prend la caméra que
lorsque MSFS la laisse libre (ni menu, ni chargement, ni cinématique), la
reprend d'elle-même ensuite, et la rend au pilote dès qu'on l'arrête.

NaviXav donne une position et un point à cadrer ; c'est MSFS qui oriente
l'objectif. Les plans fixes demandent en plus au simulateur de garder chargé
le décor autour de la caméra.
"""

from __future__ import annotations

import logging
import math
import random
import struct
import threading
import time
from typing import Any, Callable, Sequence

from navixav.camera.director import Director
from navixav.camera.motion import Glide
from navixav.camera.scene import DEFAULT_SPAN_M, FT, AircraftState, Kinematics
from navixav.camera.shots import (
    ADJUSTABLE,
    ANGLE_RANGE,
    ATTACHED,
    DISTANCE_RANGE,
    HEIGHT_RANGE,
    SHOTS,
    WORLD,
    Framing,
    Shot,
)
from navixav.msfs.client import (
    CAMERA_AVAILABILITY_USER_DISABLED,
    CAMERA_FLAG_ABOVE_GROUND,
    CAMERA_LOCKER_FAIL,
    CAMERA_REFERENTIAL_SIMOBJECT,
    CAMERA_REFERENTIAL_WORLD,
    EXCEPTION_CAMERA_API,
    RECV_ID_CAMERA_DATA,
    RECV_ID_CAMERA_STATUS,
    RECV_ID_CAMERA_WORLD_LOCKER,
    SimConnectClient,
    SimConnectError,
    SimConnectLayout,
    SimConnectRefused,
    unpack_camera_fov,
)

LOGGER = logging.getLogger(__name__)

CORE_VARIABLES = (
    ("PLANE LATITUDE", "Degrees"),
    ("PLANE LONGITUDE", "Degrees"),
    ("PLANE ALTITUDE", "Meters"),
    ("PLANE ALT ABOVE GROUND", "Meters"),
    ("PLANE HEADING DEGREES TRUE", "Degrees"),
    ("SIM ON GROUND", "Bool"),
    ("CAMERA STATE", "Number"),
)
# Facultative : sans elle, les plans gardent la taille d'un moyen-courrier.
EXTRA_VARIABLES = (("WING SPAN", "Feet"),)
CAMERA_STATE_VARIABLE = (("CAMERA STATE", "Number"),)
# Vue extérieure de MSFS : si le pilote y était, il la retrouve en sortant.
CAMERA_STATE_EXTERNAL = 3

OFF, AUTO = "off", "auto"
MODES = (OFF, AUTO, *SHOTS)
# Rythme du montage : facteur appliqué à la durée de tenue des plans.
PACES = {"calm": 1.6, "normal": 1.0, "dynamic": 0.55}
# Passage d'un plan à l'autre : coupe franche, ou travelling autour de l'avion.
TRANSITIONS = ("cut", "glide")
GLIDE_S = 3.5
# Les tours des aérodromes du plan sont relues quand le plan change.
TOWER_CHECK_S = 10.0
RETRY_S = 5.0
MAX_STEP_S = 0.25
_HEADER = 12  # SIMCONNECT_RECV : taille, version, identifiant


def _finite(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


# Le SDK ne dit pas l'unité du champ de vision, et une valeur posée reste en
# place dans MSFS d'une image à l'autre : une unité mal devinée déforme tous
# les plans suivants en fisheye. NaviXav lit donc le champ de la vue du pilote
# et le renvoie tel quel ; le plan Tour ne fait que le resserrer.
NATIVE_FOV_PLAUSIBLE = (0.05, 179.0)
RADIANS_BELOW = 3.2


def lens_for(wanted_deg: float | None, native: float | None) -> float | None:
    """Champ à envoyer : celui du pilote, resserré pour un zoom, jamais élargi."""
    if native is None:
        return None
    if wanted_deg is None:
        return native
    native_deg = math.degrees(native) if native < RADIANS_BELOW else native
    return native * min(1.0, max(0.05, wanted_deg / native_deg))


class _Link:
    """Ce que MSFS dit de la caméra, et ce que NaviXav en détient."""

    def __init__(self) -> None:
        self.game_controlled = False
        self.user_disabled = False
        self.taken_by_other = False
        self.acquired = False
        self.locked: tuple[float, float, float] | None = None
        self.locker_failed = False
        # Champ de vision de la vue du pilote, dans l'unité de MSFS.
        self.native_fov: float | None = None
        self.fov_requested = False

    @property
    def free(self) -> bool:
        return not (self.game_controlled or self.user_disabled)

    def on_message(self, recv_id: int, raw: bytes) -> None:
        if recv_id == RECV_ID_CAMERA_STATUS and len(raw) >= _HEADER + 8:
            availability, game_controlled = struct.unpack_from("<Ii", raw, _HEADER)
            self.game_controlled = bool(game_controlled)
            self.user_disabled = availability == CAMERA_AVAILABILITY_USER_DISABLED
            self.taken_by_other = availability == 2
            if not self.free:
                # MSFS reprend la main : il faudra redemander la caméra.
                self.acquired = False
                self.locked = None
        elif recv_id == RECV_ID_CAMERA_DATA and self.native_fov is None:
            fov = unpack_camera_fov(raw, _HEADER)
            if fov is not None and NATIVE_FOV_PLAUSIBLE[0] <= fov <= NATIVE_FOV_PLAUSIBLE[1]:
                self.native_fov = fov
                LOGGER.info("Caméra : champ de vision du simulateur %.4f", fov)
        elif recv_id == RECV_ID_CAMERA_WORLD_LOCKER and len(raw) >= _HEADER + 4:
            (status,) = struct.unpack_from("<i", raw, _HEADER)
            if status == CAMERA_LOCKER_FAIL and not self.locker_failed:
                LOGGER.info("Caméra : le simulateur n'a pas pu réserver le décor du plan fixe")
                self.locker_failed = True


class CameraService:
    def __init__(
        self,
        client_factory: Callable[[], SimConnectClient] = SimConnectClient,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
        airports: Callable[[], Sequence[str]] = tuple,
    ) -> None:
        self._client_factory = client_factory
        # Aérodromes du plan chargé : leurs tours servent au plan « Tour ».
        self._airports = airports
        self._towers: dict[str, tuple[float, float, float]] = {}
        self._towers_for: tuple[str, ...] | None = None
        self._towers_checked = -math.inf
        self._tower_thread: threading.Thread | None = None
        self._playlist: frozenset[str] = frozenset(SHOTS)
        self._transition = "cut"
        self._held = False
        self._glide: Glide | None = None
        # Cadrage de chaque plan, réglé depuis la régie.
        self._framing: dict[str, Framing] = {name: Framing() for name in SHOTS}
        self._replant = False
        self._last_attached: tuple[float, float, float] | None = None
        self._clock = clock
        self._rng = rng or random.Random()
        self._director = Director(self._rng)
        self._kinematics = Kinematics()
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._mode = OFF
        self._state = "off"
        self._shot_name: str | None = None
        self._phase: str | None = None
        self._next_cut_s: float | None = None
        self._hold_s: float | None = None
        self._pace = "normal"
        self._skip = False
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------ #

    def start(self, mode: str = AUTO) -> None:
        if mode not in MODES:
            raise ValueError(f"Plan inconnu : {mode}")
        if mode == OFF:
            self.stop()
            return
        with self._lock:
            previous, self._mode = self._mode, mode
            if previous == OFF:
                self._state = "waiting"
        if previous != mode:
            LOGGER.info("Caméra : %s", "réalisateur automatique" if mode == AUTO else f"plan {mode}")
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name="navixav-camera", daemon=True)
            self._thread.start()
        self._wake.set()

    def set_pace(self, pace: str) -> None:
        if pace not in PACES:
            raise ValueError(f"Rythme inconnu : {pace}")
        with self._lock:
            self._pace = pace

    def set_playlist(self, shots: Sequence[str]) -> None:
        """Plans que le réalisateur peut utiliser ; au moins un."""
        chosen = frozenset(shots)
        if not chosen or not chosen <= set(SHOTS):
            raise ValueError("Sélection de plans invalide.")
        with self._lock:
            self._playlist = chosen

    def set_transition(self, transition: str) -> None:
        if transition not in TRANSITIONS:
            raise ValueError(f"Transition inconnue : {transition}")
        with self._lock:
            self._transition = transition

    def set_held(self, held: bool) -> None:
        """Garde le plan en cours : le réalisateur ne coupe plus de lui-même."""
        with self._lock:
            self._held = bool(held)

    def set_framing(
        self,
        shot: str,
        *,
        distance: float | None = None,
        height: float | None = None,
        angle: float | None = None,
    ) -> None:
        """Règle le cadrage d'un plan ; le plan à l'image change aussitôt."""
        if shot not in SHOTS:
            raise ValueError(f"Plan inconnu : {shot}")
        framing = self._framing[shot]
        allowed = ADJUSTABLE[shot]
        if distance is not None and "distance" in allowed:
            framing.distance = min(DISTANCE_RANGE[1], max(DISTANCE_RANGE[0], float(distance)))
        if height is not None and "height" in allowed:
            framing.height = min(HEIGHT_RANGE[1], max(HEIGHT_RANGE[0], float(height)))
        if angle is not None and "angle" in allowed:
            framing.angle = min(ANGLE_RANGE[1], max(ANGLE_RANGE[0], float(angle)))
        self._replant_if_fixed(shot)

    def reset_framing(self, shot: str | None = None) -> None:
        """Remet un plan, ou tous (None), au cadrage d'origine."""
        names = list(SHOTS) if shot is None else [shot]
        for name in names:
            if name not in SHOTS:
                raise ValueError(f"Plan inconnu : {name}")
            framing = self._framing[name]
            framing.distance, framing.height, framing.angle = 1.0, 0.0, 0.0
            self._replant_if_fixed(name)

    def _replant_if_fixed(self, shot: str) -> None:
        # Un plan posé dans le décor se replace avec son nouveau cadrage ;
        # un plan qui suit l'avion glisse de lui-même vers sa nouvelle place.
        with self._lock:
            if self._shot_name == shot and SHOTS[shot].world:
                self._replant = True

    def next_shot(self) -> None:
        """Coupe tout de suite : nouveau plan, ou nouvel emplacement du plan fixé."""
        with self._lock:
            if self._mode != OFF:
                self._skip = True

    def stop(self) -> None:
        with self._lock:
            was_on, self._mode = self._mode != OFF, OFF
        if was_on:
            LOGGER.info("Caméra rendue au pilote")
        self._wake.set()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "mode": self._mode,
                "state": self._state,
                "shot": self._shot_name,
                "phase": self._phase,
                "next_cut_s": None if self._next_cut_s is None else round(self._next_cut_s, 1),
                "hold_s": None if self._hold_s is None else round(self._hold_s, 1),
                "pace": self._pace,
                "playlist": [name for name in SHOTS if name in self._playlist],
                "transition": self._transition,
                "held": self._held,
                "towers": sorted(self._towers),
                "framing": {
                    name: {"distance": round(f.distance, 2), "height": round(f.height, 2), "angle": round(f.angle)}
                    for name, f in self._framing.items()
                },
                "adjustable": {name: list(keys) for name, keys in ADJUSTABLE.items()},
                "shots": list(SHOTS),
                "paces": list(PACES),
                "transitions": list(TRANSITIONS),
            }

    def close(self) -> None:
        self.stop()
        self._stop.set()
        self._wake.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3)

    # ------------------------------------------------------------------ #

    def _set(self, **values: Any) -> None:
        with self._lock:
            for key, value in values.items():
                setattr(self, f"_{key}", value)

    def _requested(self) -> str:
        with self._lock:
            return self._mode

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._requested() == OFF:
                with self._lock:
                    # Un refus de MSFS reste affiché jusqu'à la prochaine demande.
                    if self._state != "refused":
                        self._state = "off"
                    self._shot_name = self._phase = self._next_cut_s = self._hold_s = None
                    self._skip = False
                self._wake.wait(1.0)
                self._wake.clear()
                continue
            self._set(state="waiting")
            client: SimConnectClient | None = None
            try:
                client = self._client_factory()
                self._session(client)
            except SimConnectError as exc:
                LOGGER.info("Caméra : simulateur indisponible (%s)", type(exc).__name__)
            except Exception:  # noqa: BLE001 - le fil ne doit jamais mourir en silence
                LOGGER.exception("Caméra : erreur inattendue")
            finally:
                if client is not None:
                    client.close()
            self._kinematics.reset()
            if self._requested() != OFF and not self._stop.is_set():
                self._stop.wait(RETRY_S)

    def _session(self, client: SimConnectClient) -> None:
        """Une connexion : prise de la caméra, plans successifs, restitution."""
        if not client.camera_supported:
            self._set(state="unsupported")
            while self._requested() != OFF and not self._stop.is_set():
                self._wake.wait(1.0)
                self._wake.clear()
            return
        variables = CORE_VARIABLES + EXTRA_VARIABLES
        request = client.subscribe_simvars(variables)
        client.camera_subscribe_status()
        link = _Link()
        pilot_view: float | None = None
        try:
            pilot_view = self._film(client, link, variables, request)
        finally:
            self._give_back(client, link, pilot_view)

    def _film(
        self, client: SimConnectClient, link: _Link, variables: tuple, request: int
    ) -> float | None:
        receiving = False
        shot: Shot | None = None
        shot_mode: str | None = None
        pilot_view: float | None = None
        self._director.reset()
        last = self._clock()
        while not self._stop.is_set():
            mode = self._requested()
            if mode == OFF:
                return pilot_view
            try:
                frame = client.next_frame(request, variables, timeout_s=1.0, on_message=link.on_message)
            except SimConnectRefused as exc:
                if EXCEPTION_CAMERA_API in exc.codes:
                    LOGGER.warning("Caméra : MSFS refuse la commande de caméra, arrêt du réalisateur")
                    with self._lock:
                        self._mode = OFF
                        self._state = "refused"
                    return pilot_view
                if not receiving and variables != CORE_VARIABLES:
                    variables = CORE_VARIABLES
                    request = client.subscribe_simvars(variables)
                    continue
                raise
            except SimConnectLayout:
                raise SimConnectError("Image de simulation illisible.")
            now = self._clock()
            dt = min(MAX_STEP_S, max(0.0, now - last))
            last = now
            if frame is None:
                # Pause ou chargement : la caméra reste où elle est.
                continue
            receiving = True
            state = self._aircraft(frame, now)
            if not link.free:
                shot = None
                self._set(state="blocked" if link.user_disabled else "waiting", shot_name=None)
                continue
            if not link.acquired:
                if link.taken_by_other:
                    self._set(state="taken", shot_name=None)
                    continue
                if pilot_view is None:
                    pilot_view = _finite(frame.get("CAMERA STATE"), 0.0)
                if not link.fov_requested and getattr(client, "camera_get_supported", False):
                    # Avant de prendre la caméra : c'est encore la vue du pilote.
                    client.camera_get(CAMERA_REFERENTIAL_SIMOBJECT)
                    link.fov_requested = True
                client.camera_acquire()
                client.camera_enable_flag(CAMERA_FLAG_ABOVE_GROUND)
                link.acquired = True
                shot = None
                self._last_attached = None
                self._glide = None
            self._maybe_refresh_towers(now)
            if mode != AUTO and not SHOTS[mode].suits(state) and SHOTS[mode].world:
                # Plan fixé impossible ici (pas de tour à portée, avion arrêté…) :
                # on le dit, sans déplacer la caméra.
                self._set(state="unavailable", shot_name=mode, phase=None, next_cut_s=None, hold_s=None)
                shot = None
                continue
            shot, shot_mode = self._direct(state, now, mode, shot, shot_mode)
            command = shot.update(state, dt)
            position = command.position
            if command.referential == WORLD:
                self._last_attached = None
                self._glide = None
            else:
                if self._glide is not None:
                    position = self._glide.step(position, dt)
                    if self._glide.finished:
                        self._glide = None
                self._last_attached = position
            if command.lock != link.locked:
                if link.locked is not None:
                    client.camera_unlock_world()
                if command.lock is not None:
                    client.camera_lock_world(*command.lock)
                link.locked = command.lock
            referential = CAMERA_REFERENTIAL_WORLD if command.referential == WORLD else CAMERA_REFERENTIAL_SIMOBJECT
            fov = lens_for(command.fov_deg, link.native_fov)
            client.camera_set(position, referential, command.target, fov)
            held = mode == AUTO and self._director.held
            self._set(
                state="active",
                shot_name=shot.name,
                phase=self._director.phase,
                next_cut_s=self._director.next_cut_in(now) if mode == AUTO and not held else None,
                hold_s=self._director.hold_s if mode == AUTO and not held else None,
            )
        return pilot_view

    # ------------------------------------------------------------------ #
    # Tours de contrôle des aérodromes du plan

    def _maybe_refresh_towers(self, now: float) -> None:
        if now - self._towers_checked < TOWER_CHECK_S:
            return
        self._towers_checked = now
        try:
            airports = tuple(dict.fromkeys(code.strip().upper() for code in self._airports() if code))
        except Exception:  # noqa: BLE001 - sans plan, simplement pas de tour
            airports = ()
        if airports == self._towers_for:
            return
        if self._tower_thread is not None and self._tower_thread.is_alive():
            return
        self._towers_for = airports
        if not airports:
            with self._lock:
                self._towers = {}
            return
        self._tower_thread = threading.Thread(
            target=self._read_towers, args=(airports,), name="navixav-camera-towers", daemon=True
        )
        self._tower_thread.start()

    def _read_towers(self, airports: tuple[str, ...]) -> None:
        """Lit les tours sur une connexion à part : une requête ne retarde aucune image."""
        client: SimConnectClient | None = None
        try:
            client = self._client_factory()
            towers = client.read_towers(airports)
        except SimConnectError as exc:
            LOGGER.info("Caméra : tours de contrôle indisponibles (%s)", type(exc).__name__)
            self._towers_for = None
            return
        finally:
            if client is not None:
                client.close()
        with self._lock:
            self._towers = towers
        LOGGER.info("Caméra : %d tour(s) de contrôle connue(s) pour le plan", len(towers))

    def _direct(
        self, state: AircraftState, now: float, mode: str, shot: Shot | None, shot_mode: str | None
    ) -> tuple[Shot, str]:
        """Garde le plan en cours ou en choisit un autre."""
        with self._lock:
            skip, self._skip = self._skip, False
            replant, self._replant = self._replant, False
            self._director.pace = PACES[self._pace]
            self._director.allowed = self._playlist
            self._director.held = self._held
            transition = self._transition
        if skip:
            self._director.cut_now()
        if replant and shot is not None and shot_mode == mode and not skip:
            again = SHOTS[shot.name]()
            again.framing = self._framing[shot.name]
            again.start(state, self._rng)
            return again, mode
        if shot is not None and shot_mode == mode and not skip:
            done = shot.done(state)
            if mode == AUTO:
                if not self._director.should_cut(state, now, done):
                    return shot, mode
            elif not done:
                return shot, mode
        if mode != AUTO:
            name = mode
            self._director.phase = None
        elif self._director.held and shot is not None and not skip and SHOTS[shot.name].suits(state):
            # Plan gardé dont l'avion est passé : on le replace, même plan.
            name = shot.name
        else:
            name = self._director.choose(state, now)
        new_shot = SHOTS[name]()
        new_shot.framing = self._framing[name]
        new_shot.start(state, self._rng)
        if transition == "glide" and name in ATTACHED and self._last_attached is not None:
            self._glide = Glide(self._last_attached, GLIDE_S)
        else:
            self._glide = None
        return new_shot, mode

    def _aircraft(self, frame: dict[str, float], now: float) -> AircraftState:
        latitude = _finite(frame.get("PLANE LATITUDE"), 0.0)
        longitude = _finite(frame.get("PLANE LONGITUDE"), 0.0)
        altitude = _finite(frame.get("PLANE ALTITUDE"), 0.0)
        speed, track, vertical = self._kinematics.update(now, latitude, longitude, altitude)
        span_ft = _finite(frame.get("WING SPAN"), 0.0)
        with self._lock:
            towers = tuple(self._towers.values())
        return AircraftState(
            latitude=latitude,
            longitude=longitude,
            altitude_m=altitude,
            height_m=max(0.0, _finite(frame.get("PLANE ALT ABOVE GROUND"), 0.0)),
            heading_deg=_finite(frame.get("PLANE HEADING DEGREES TRUE"), 0.0) % 360.0,
            on_ground=bool(frame.get("SIM ON GROUND")),
            span_m=span_ft * FT if span_ft > 0 else DEFAULT_SPAN_M,
            ground_speed_mps=speed,
            track_deg=track,
            vertical_speed_mps=vertical,
            towers=towers,
        )

    def _give_back(self, client: SimConnectClient, link: _Link, pilot_view: float | None) -> None:
        """Rend la caméra, et la vue extérieure si c'était celle du pilote."""
        if not link.acquired:
            return
        try:
            if link.locked is not None:
                client.camera_unlock_world()
            client.camera_release()
            if pilot_view is not None and round(pilot_view) == CAMERA_STATE_EXTERNAL:
                client.write_simvars(CAMERA_STATE_VARIABLE, (CAMERA_STATE_EXTERNAL,))
        except SimConnectError as exc:
            LOGGER.info("Caméra : restitution incomplète (%s)", type(exc).__name__)
        link.acquired = False
        link.locked = None
