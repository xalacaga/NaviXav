"""Applique la turbulence estimée à l'avion du joueur, image après image.

Le service tient sa propre connexion SimConnect, abonnée à chaque image de
simulation : l'écriture suit le rythme du simulateur, sans encombrer la
connexion du suivi de vol. MSFS en pause n'émet plus d'image, et le service
n'écrit alors plus rien.

Les sources (OFP, comptes rendus, relief au vent) sont relues par un second
fil, à cadence lente : une requête réseau ne doit jamais retarder une image.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Any, Callable

from navixav.msfs.client import (
    SimConnectClient,
    SimConnectError,
    SimConnectLayout,
    SimConnectRefused,
)
from navixav.turbulence.dynamics import (
    DEFAULT_SPAN_M,
    DEFAULT_WING_AREA_M2,
    FT,
    PITCH_GAIN,
    Airframe,
    GustField,
    Motion,
)
from navixav.turbulence.model import (
    WAVE_WIND_FLOOR_KT,
    Assessment,
    Conditions,
    Estimator,
    LiveShear,
    Sources,
)
from navixav.turbulence.terrain import TerrainProbe, TerrainSample

LOGGER = logging.getLogger(__name__)

SLUG_PER_FT3 = 515.379
SQFT = FT * FT

CORE_VARIABLES = (
    ("PLANE LATITUDE", "Degrees"),
    ("PLANE LONGITUDE", "Degrees"),
    ("PLANE ALTITUDE", "Feet"),
    ("PLANE ALT ABOVE GROUND", "Feet"),
    ("SIM ON GROUND", "Bool"),
    ("AIRSPEED TRUE", "Knots"),
    ("TOTAL WEIGHT", "Kilograms"),
    ("AMBIENT DENSITY", "Slugs per cubic feet"),
    ("AMBIENT WIND DIRECTION", "Degrees"),
    ("AMBIENT WIND VELOCITY", "Knots"),
    ("AMBIENT IN CLOUD", "Bool"),
    ("ROTATION VELOCITY BODY X", "Radians per second"),
    ("ROTATION VELOCITY BODY Z", "Radians per second"),
    ("VELOCITY BODY Y", "Feet per second"),
    ("PLANE BANK DEGREES", "Degrees"),
    ("PLANE PITCH DEGREES", "Degrees"),
)
# Variables utiles mais facultatives : un avion ou une version du simulateur
# qui en refuse une ne doit pas priver le pilote de turbulence.
EXTRA_VARIABLES = (
    ("WING AREA", "Square feet"),
    ("WING SPAN", "Feet"),
    ("AMBIENT PRECIP STATE", "Mask"),
    ("IS SLEW ACTIVE", "Bool"),
)
# MSFS ignore les accélérations écrites ; il prend la vitesse verticale telle
# quelle. Les vitesses de rotation ne sont jamais écrites : MSFS les amplifie
# (voir dynamics.py), et l'avion diverge.
WRITE_VARIABLES = (("VELOCITY BODY Y", "Feet per second"),)
# Coupure de sécurité : au-delà, l'avion ne vole plus normalement et NaviXav
# cesse aussitôt d'écrire, quoi qu'il arrive ensuite.
SAFETY_RATE_DEG_S = 12.0
SAFETY_BANK_DEG = 60.0
SAFETY_PITCH_DEG = 30.0
# Pause active : position strictement identique sur ces images consécutives.
FROZEN_KEYS = ("PLANE LATITUDE", "PLANE LONGITUDE", "PLANE ALTITUDE")
FROZEN_FRAMES = 3
# Effet mesuré : écart-type glissant des vitesses de rotation de l'avion.
FELT_WINDOW_S = 4.0
# Bits de AMBIENT PRECIP STATE : 2 sec, 4 pluie, 8 neige.
PRECIP_RAIN_OR_SNOW = 4 | 8

# Rien sous 200 ft sol, plein effet à partir de 500 ft : comme les réglages
# d'altitude minimale des utilitaires du genre, pour ne jamais secouer
# l'avion à l'arrondi.
MIN_HEIGHT_FT = 200.0
FULL_HEIGHT_FT = 500.0
SOURCE_REFRESH_S = 60.0
# Le relief est reconsidéré plus souvent ; la sonde ne refait une requête que
# si l'avion ou le vent ont assez changé.
TERRAIN_REFRESH_S = 15.0
RETRY_S = 5.0
MIN_INTENSITY_PCT, MAX_INTENSITY_PCT = 25, 200
# Une secousse se compte au-delà de 1,6 écart-type, et seulement quand la
# turbulence produit au moins 0,02 g efficace : en dessous, rien ne s'entend.
JOLT_THRESHOLD = 1.6
MIN_JOLT_SIGMA_G = 0.02


def height_factor(height_agl_ft: float) -> float:
    if height_agl_ft <= MIN_HEIGHT_FT:
        return 0.0
    if height_agl_ft >= FULL_HEIGHT_FT:
        return 1.0
    return (height_agl_ft - MIN_HEIGHT_FT) / (FULL_HEIGHT_FT - MIN_HEIGHT_FT)


def _unsafe(frame: dict[str, float]) -> bool:
    """Vrai si l'avion tourne trop vite ou a pris une attitude anormale."""
    rates = (frame.get("ROTATION VELOCITY BODY X"), frame.get("ROTATION VELOCITY BODY Z"))
    if any(abs(math.degrees(_finite(rate, 0.0))) > SAFETY_RATE_DEG_S for rate in rates):
        return True
    bank = abs(_finite(frame.get("PLANE BANK DEGREES"), 0.0))
    pitch = abs(_finite(frame.get("PLANE PITCH DEGREES"), 0.0))
    return bank > SAFETY_BANK_DEG or pitch > SAFETY_PITCH_DEG


def _finite(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


class TurbulenceService:
    def __init__(
        self,
        sources: Callable[[], Sources],
        client_factory: Callable[[], SimConnectClient] = SimConnectClient,
        clock: Callable[[], float] = time.monotonic,
        terrain: TerrainProbe | None = None,
    ) -> None:
        self._sources_provider = sources
        self._terrain = terrain
        self._terrain_sample: TerrainSample | None = None
        # Dernière position connue, pour le relevé du relief : (lat, lon,
        # vent d'où il vient, vent en kt, au sol).
        self._position: tuple[float, float, float, float, bool] | None = None
        self._client_factory = client_factory
        self._clock = clock
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._enabled = False
        self._intensity = 1.0
        self._sources = Sources()
        self._sources_loaded = False
        self._estimator = Estimator()
        self._gusts = GustField()
        self._shear = LiveShear()
        self._state = "off"
        self._assessment = Assessment(0.0)
        self._motion = Motion(0.0, 0.0, 0.0, 0.0)
        self._last_level: str | None = None
        # Secousses marquées, comptées pour que l'interface y cale ses sons :
        # le compteur monte à chaque franchissement, l'intensité dit sa force.
        self._felt = {"pitch": (0.0, 0.0), "roll": (0.0, 0.0)}
        self._jolts = 0
        self._jolt_g = 0.0
        self._above = False
        self._thread: threading.Thread | None = None
        self._refresher: threading.Thread | None = None

    # ------------------------------------------------------------------ #

    def configure(self, *, enabled: bool, intensity_pct: int) -> None:
        pct = min(MAX_INTENSITY_PCT, max(MIN_INTENSITY_PCT, int(intensity_pct)))
        with self._lock:
            changed = enabled != self._enabled
            self._enabled = enabled
            self._intensity = pct / 100.0
            if not enabled:
                self._state = "off"
        if changed:
            LOGGER.info("Turbulence ressentie %s (intensité %d %%)",
                        "activée" if enabled else "désactivée", pct)
        if enabled:
            self._start()
        self._wake.set()

    def refresh_sources(self) -> None:
        """Relit l'OFP et les comptes rendus ; appelé aussi au chargement d'un plan."""
        try:
            sources = self._sources_provider()
        except Exception as exc:  # noqa: BLE001 - une source absente n'arrête rien
            LOGGER.warning("Sources de turbulence indisponibles : %s", type(exc).__name__)
            return
        with self._lock:
            self._sources = sources
            self._sources_loaded = True

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": self._enabled,
                "intensity_pct": round(self._intensity * 100),
                "state": self._state,
                **self._assessment.to_dict(),
                "felt_edr": round(self._gusts.edr, 3),
                "load_sigma_g": round(self._motion.load_sigma_g, 3),
                "jolts": self._jolts,
                "jolt_g": round(self._jolt_g, 3),
                # Effet réellement obtenu dans MSFS, en degrés par seconde.
                "felt_pitch_deg_s": round(math.sqrt(self._felt["pitch"][1]), 2),
                "felt_roll_deg_s": round(math.sqrt(self._felt["roll"][1]), 2),
                "forecast_points": len(self._sources.forecast),
                "reports": len(self._sources.reports),
                "relief_ft": round(self._terrain_sample.relief_ft) if self._terrain_sample else None,
            }

    def refresh_terrain(self) -> None:
        """Relève le relief au vent quand une onde orographique est possible."""
        if self._terrain is None:
            return
        with self._lock:
            position = self._position
        if position is None:
            return
        lat, lon, wind_from, wind_kt, on_ground = position
        if on_ground or wind_kt < WAVE_WIND_FLOOR_KT:
            # Pas d'onde sans vent : le relevé serait une requête pour rien.
            with self._lock:
                self._terrain_sample = None
            return
        sample = self._terrain.probe(lat, lon, wind_from)
        with self._lock:
            self._terrain_sample = sample

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        for thread in (self._thread, self._refresher):
            if thread is not None and thread.is_alive():
                thread.join(timeout=3)
        if self._terrain is not None:
            self._terrain.close()

    # ------------------------------------------------------------------ #

    def _start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name="navixav-turbulence", daemon=True)
            self._thread.start()
        if self._refresher is None or not self._refresher.is_alive():
            self._refresher = threading.Thread(
                target=self._refresh_loop, name="navixav-turbulence-sources", daemon=True
            )
            self._refresher.start()

    def _refresh_loop(self) -> None:
        last_sources = -math.inf
        while not self._stop.is_set():
            if self._enabled:
                now = time.monotonic()
                if now - last_sources >= SOURCE_REFRESH_S:
                    self.refresh_sources()
                    last_sources = now
                try:
                    self.refresh_terrain()
                except Exception:  # noqa: BLE001 - le relief n'est qu'une source parmi d'autres
                    LOGGER.exception("Turbulence : relevé du relief en échec")
            self._stop.wait(TERRAIN_REFRESH_S)

    def _set_state(self, state: str) -> None:
        with self._lock:
            if self._enabled or state == "off":
                self._state = state

    def _run(self) -> None:
        while not self._stop.is_set():
            if not self._enabled:
                self._gusts.reset()
                self._wake.wait(1.0)
                self._wake.clear()
                continue
            self._set_state("waiting")
            client: SimConnectClient | None = None
            try:
                client = self._client_factory()
                self._session(client)
            except SimConnectError as exc:
                LOGGER.info("Turbulence : simulateur indisponible (%s)", type(exc).__name__)
            except Exception:  # noqa: BLE001 - le fil ne doit jamais mourir en silence
                LOGGER.exception("Turbulence : erreur inattendue")
            finally:
                if client is not None:
                    client.close()
            self._gusts.reset()
            if self._enabled and not self._stop.is_set():
                self._stop.wait(RETRY_S)

    def _session(self, client: SimConnectClient) -> None:
        """Une connexion, de l'abonnement jusqu'à la panne ou l'arrêt."""
        if not self._sources_loaded:
            # Première connexion : sans les sources, les premières minutes de
            # vol seraient calmes même au cœur d'une zone signalée.
            self.refresh_sources()
        variables = CORE_VARIABLES + EXTRA_VARIABLES
        request = client.subscribe_simvars(variables)
        receiving = False
        writing = True
        last = self._clock()
        previous_position: tuple[float, float, float] | None = None
        frozen = 0
        while self._enabled and not self._stop.is_set():
            try:
                frame = client.next_frame(request, variables, timeout_s=1.0)
            except SimConnectRefused:
                if not receiving and variables != CORE_VARIABLES:
                    LOGGER.info("Turbulence : variables facultatives refusées, jeu réduit")
                    variables = CORE_VARIABLES
                    request = client.subscribe_simvars(variables)
                    continue
                if receiving and writing:
                    # Les images arrivent : c'est l'écriture qui est refusée.
                    LOGGER.warning("Turbulence : MSFS refuse les accélérations de l'avion")
                    writing = False
                    self._set_state("refused")
                    continue
                raise
            except SimConnectLayout:
                raise SimConnectError("Image de simulation illisible.")
            now = self._clock()
            if frame is None:
                # Simulateur en pause ou chargement : pas d'image, pas d'effet.
                self._set_state("waiting" if writing else "refused")
                last = now
                continue
            receiving = True
            # Pause active de MSFS : les images arrivent encore, mais l'avion
            # en vol ne bouge plus d'un millimètre. Rien ne s'écrit alors.
            position = tuple(_finite(frame.get(name), 0.0) for name in FROZEN_KEYS)
            airborne = not frame.get("SIM ON GROUND")
            frozen = frozen + 1 if airborne and position == previous_position else 0
            previous_position = position
            if frozen >= FROZEN_FRAMES:
                self._set_state("waiting" if writing else "refused")
                last = now
                continue
            dt = now - last
            last = now
            motion = self._step(frame, dt, time.time())
            self._measure(frame, dt)
            if writing and _unsafe(frame):
                LOGGER.warning("Turbulence : attitude anormale, écriture arrêtée par sécurité")
                writing = False
                self._set_state("refused")
            kicks = motion.kicks(dt)
            if writing and any(kicks):
                current = (_finite(frame.get(name), 0.0) for name, _unit in WRITE_VARIABLES)
                client.write_simvars(WRITE_VARIABLES, tuple(c + k for c, k in zip(current, kicks)))
            if writing:
                self._set_state("active")

    def _measure(self, frame: dict[str, float], dt: float) -> None:
        """Écart-type glissant des vitesses de rotation : ce que l'avion fait vraiment."""
        if dt <= 0:
            return
        alpha = 1.0 - math.exp(-dt / FELT_WINDOW_S)
        with self._lock:
            for key, name in (("pitch", "ROTATION VELOCITY BODY X"), ("roll", "ROTATION VELOCITY BODY Z")):
                rate = math.degrees(_finite(frame.get(name), 0.0))
                mean, square = self._felt[key]
                mean += (rate - mean) * alpha
                square += ((rate - mean) ** 2 - square) * alpha
                self._felt[key] = (mean, square)

    def _note_jolt(self, motion: Motion) -> None:
        """Compte une secousse quand le tangage dépasse 1,6 fois son écart-type.

        Seul le franchissement montant compte : rester au-dessus du seuil
        pendant plusieurs images reste une seule secousse.
        """
        spread = PITCH_GAIN * motion.load_sigma_g
        if spread < MIN_JOLT_SIGMA_G * PITCH_GAIN:
            self._above = False
            return
        above = abs(motion.pitch) > JOLT_THRESHOLD * spread
        if above and not self._above:
            self._jolts += 1
            self._jolt_g = motion.load_sigma_g * abs(motion.pitch) / spread
        self._above = above

    def _step(self, frame: dict[str, float], dt: float, wall: float) -> Motion:
        on_ground = bool(frame.get("SIM ON GROUND")) or bool(frame.get("IS SLEW ACTIVE"))
        altitude = _finite(frame.get("PLANE ALTITUDE"), 0.0)
        height = _finite(frame.get("PLANE ALT ABOVE GROUND"), 0.0)
        wind_dir = _finite(frame.get("AMBIENT WIND DIRECTION"), 0.0)
        wind_kt = max(0.0, _finite(frame.get("AMBIENT WIND VELOCITY"), 0.0))
        precip = int(_finite(frame.get("AMBIENT PRECIP STATE"), 0.0))
        shear = 0.0 if on_ground else self._shear.update(wall, altitude, wind_dir, wind_kt)
        latitude = _finite(frame.get("PLANE LATITUDE"), 0.0)
        longitude = _finite(frame.get("PLANE LONGITUDE"), 0.0)
        with self._lock:
            self._position = (latitude, longitude, wind_dir, wind_kt, on_ground)
            terrain = self._terrain_sample
        conditions = Conditions(
            latitude=latitude,
            longitude=longitude,
            altitude_ft=altitude,
            height_agl_ft=height,
            on_ground=on_ground,
            in_cloud=bool(frame.get("AMBIENT IN CLOUD")),
            precipitating=bool(precip & PRECIP_RAIN_OR_SNOW),
            wind_speed_kt=wind_kt,
            live_shear_kt_per_kft=shear,
            ridge_ft=terrain.ridge_ft if terrain else None,
            relief_ft=terrain.relief_ft if terrain else 0.0,
        )
        with self._lock:
            sources, intensity = self._sources, self._intensity
        assessment = self._estimator.assess(conditions, sources, wall)
        target = 0.0 if on_ground else assessment.edr * height_factor(height)
        airframe = Airframe(
            weight_kg=max(300.0, _finite(frame.get("TOTAL WEIGHT"), 60000.0)),
            wing_area_m2=max(5.0, _finite(frame.get("WING AREA"), DEFAULT_WING_AREA_M2 / SQFT) * SQFT),
            span_m=max(5.0, _finite(frame.get("WING SPAN"), DEFAULT_SPAN_M / FT) * FT),
        )
        density = max(0.05, _finite(frame.get("AMBIENT DENSITY"), 0.0023769) * SLUG_PER_FT3)
        motion = self._gusts.step(
            dt, target, _finite(frame.get("AIRSPEED TRUE"), 0.0), height, density, airframe, intensity,
        )
        with self._lock:
            self._assessment = assessment
            self._motion = motion
            self._note_jolt(motion)
        if assessment.level != self._last_level:
            LOGGER.info("Turbulence : %s (EDR %.2f, source %s)",
                        assessment.level or "aucune", assessment.edr, assessment.dominant or "-")
            self._last_level = assessment.level
        return motion
