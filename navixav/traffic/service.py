"""Cycle de vie de l'injection de trafic : détection, gestionnaire et fil.

Ce service vivait en variables de fermeture dans `create_app`, partagées par
`nonlocal` entre la configuration, l'arrêt et le statut. Rien, du dehors, ne
pouvait observer si l'injection tournait vraiment : une injection éteinte y
était indiscernable d'une injection saine, et c'est précisément ce qui a rendu
une panne invisible pendant tout un vol.

L'état est donc porté par un objet : le simulateur d'un côté, la source réseau
de l'autre, et entre les deux un fil dont l'application ne connaît que trois
gestes — configurer, arrêter, fermer.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Callable, Protocol

from navixav.traffic.base import InstallationStatus, ModelIndex, ModelInstallation
from navixav.traffic.conflicts import running_injectors
from navixav.traffic.fsltl import FsltlModelIndex
from navixav.traffic.injector import SimConnectTrafficInjector
from navixav.traffic.manager import TrafficManager
from navixav.live.base import AircraftState

LOGGER = logging.getLogger(__name__)
# The lifecycle polls cached providers; motion has its own deadline and connection.
DEFAULT_INTERVAL_S = 0.25
ANIMATION_INTERVAL_S = 1.0 / 30.0
STOP_TIMEOUT_S = 3.0
# Un injecteur concurrent lancé après le décollage doit être vu sans
# attendre le prochain changement de réglage, mais énumérer les processus
# chaque seconde serait un gaspillage : le quart de minute suffit.
CONFLICT_INTERVAL_S = 15.0


class _Provider(Protocol):
    @property
    def name(self) -> str: ...


class TrafficService:
    """Détient l'injection et la relance à chaque changement de réglage."""

    def __init__(
        self,
        detect: Callable[[], ModelInstallation],
        position: Callable[[], tuple[float, float]],
        altitude: Callable[[], float | None] | None = None,
        *,
        interval_s: float = DEFAULT_INTERVAL_S,
        injector_factory: Callable[[], SimConnectTrafficInjector] = SimConnectTrafficInjector,
        models_factory: Callable[[ModelInstallation], ModelIndex] = FsltlModelIndex,
        conflict_probe: Callable[[], tuple[str, ...]] = running_injectors,
        state: Callable[[], AircraftState] | None = None,
    ) -> None:
        self._detect = detect
        self._position = position
        self._altitude = altitude
        self._state = state
        self._interval_s = interval_s
        self._injector_factory = injector_factory
        # Les deux fabriques ne sont là que pour être remplacées : sans elles,
        # vérifier le cycle de vie exigerait un simulateur et un jeu de modèles
        # sur le disque, c'est-à-dire ne jamais le vérifier.
        self._models_factory = models_factory
        self._conflict_probe = conflict_probe
        self._conflicts: tuple[str, ...] = ()
        self._lock = threading.RLock()
        self._configure_lock = threading.RLock()
        self._animation_thread: threading.Thread | None = None
        self._status: dict = {"state": "off", "confirmed": 0}
        self._manager: TrafficManager | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._installation = detect()
        self._cached_models: ModelIndex | None = None
        self._cached_installation = None

    # ------------------------------------------------------------ lecture

    @property
    def installation(self) -> ModelInstallation:
        """Dernière détection connue, telle que l'interface l'affiche."""
        with self._lock:
            return self._installation

    @property
    def fsltl(self) -> ModelInstallation:
        """Nom historique, encore employé par l'API et l'interface."""
        return self.installation

    @property
    def conflicts(self) -> tuple[str, ...]:
        """Injecteurs concurrents ayant empêché ou interrompu l'injection."""
        with self._lock:
            return self._conflicts

    @property
    def active(self) -> bool:
        """Vrai quand un gestionnaire tourne réellement."""
        with self._lock:
            return self._manager is not None

    # ------------------------------------------------------------ commande

    @property
    def status(self) -> dict:
        result = dict(self._status)
        updated = result.pop("updated", None)
        result["age_s"] = round(time.monotonic() - updated, 1) if updated else None
        if updated and result["age_s"] > 10 and result["state"] == "active":
            result["state"] = "stale"
        return result

    def configure(
        self, *, enabled: bool, provider: _Provider,
        radius_nm: float = 40.0, max_aircraft: int = 10,
    ) -> None:
        """Arrête l'injection en cours, puis la relance si elle est demandée.

        La détection du jeu de modèles est refaite à chaque appel : le chemin
        du paquet et le dossier Communauté sont des réglages, et une
        installation faite pendant que NaviXav tourne doit être vue sans
        redémarrage.
        """
        with self._configure_lock:
            self.stop()
            self._status = {"state": "loading" if enabled else "off", "confirmed": 0}
            self._installation = self._detect()
            self._conflicts = ()
            if not enabled:
                return
            # Deux injecteurs poseraient chacun leur copie du même vol, sans
            # jamais voir celle de l'autre. NaviXav cède la place plutôt que de
            # dédoubler le trafic, et n'arrête jamais le programme d'un tiers.
            self._conflicts = tuple(self._conflict_probe())
            if self._conflicts:
                self._status = {"state": "blocked", "confirmed": 0}
                LOGGER.warning(
                    "Injection refusée : %s injecte déjà du trafic",
                    ", ".join(self._conflicts),
                )
                return
            if self._installation.status is not InstallationStatus.DETECTED:
                self._status = {"state": "unavailable", "confirmed": 0}
                LOGGER.warning("Injection désactivée : %s", self._installation.reason)
                return
            # Changer de réseau ne demande pas de relire des milliers de
            # livrées : l'index ne dépend que du paquet, et le paquet est
            # décrit par la détection qu'on vient de refaire — version et
            # nombre de configurations comprises. Tant qu'elle rend la même
            # valeur, l'index en mémoire décrit toujours le disque ; une
            # installation, un retrait ou une mise à jour la change et le
            # reconstruit. Une durée de validité, elle, aurait fait payer
            # trois secondes à un enregistrement sur deux.
            if (
                self._cached_models is None
                or self._cached_installation != self._installation
            ):
                try:
                    self._cached_models = self._models_factory(self._installation)
                except Exception:
                    self._status = {"state": "error", "confirmed": 0}
                    raise
                self._cached_installation = self._installation
            models = self._cached_models
            # Une source qui invente son trafic a besoin de savoir ce que le
            # jeu de modèles contient vraiment : sans ce catalogue, elle
            # proposerait des compagnies sans livrée installée.
            bind = getattr(provider, "bind_models", None)
            if callable(bind):
                bind(models)
            manager = TrafficManager(
                provider,
                models,
                self._injector_factory(),
                self._position,
                altitude=self._altitude,
                state=self._state,
                radius_nm=radius_nm,
                max_aircraft=max_aircraft,
            )
            self._manager = manager
            def progress(value):
                if self._manager is manager:
                    self._status = {**value, "updated": time.monotonic()}
            manager.progress = progress
            self._stop = threading.Event()
            stop = self._stop
            manager.cancelled = stop.is_set
            self._thread = threading.Thread(
                target=self._run,
                args=(manager, provider, stop),
                name=f"NaviXav-{provider.name}-traffic",
                daemon=True,
            )
            self._thread.start()
            self._animation_thread = threading.Thread(
                target=self._animate, args=(manager, stop),
                name="NaviXav-traffic-animation", daemon=True,
            )
            self._animation_thread.start()

    def stop(self, *, expected: TrafficManager | None = None) -> None:
        """Arrête le fil et rend au simulateur les objets créés."""
        with self._lock:
            if expected is not None and self._manager is not expected:
                return
            self._stop.set()
            thread, self._thread = self._thread, None
            manager, self._manager = self._manager, None
            animation, self._animation_thread = self._animation_thread, None
            self._status = {"state": "off", "confirmed": 0}
        # Hors verrou : le fil en cours de cycle a besoin de le prendre pour
        # lire l'état, et l'attendre en le tenant nous bloquerait tous les deux.
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=STOP_TIMEOUT_S)
        if manager is not None:
            manager.close()
        if animation is not None and animation is not threading.current_thread():
            animation.join(timeout=STOP_TIMEOUT_S)

    def close(self) -> None:
        self.stop()

    # ------------------------------------------------------------ interne

    def _animate(self, manager: TrafficManager, stop: threading.Event) -> None:
        deadline = time.monotonic()
        report_at = deadline
        previous = deadline
        frames = 0
        longest_gap = 0.0
        while not stop.wait(max(0.0, deadline - time.monotonic())):
            started = time.monotonic()
            longest_gap = max(longest_gap, started - previous)
            previous = started
            try:
                manager.render_once()
            except (OSError, ValueError, RuntimeError):
                if self._manager is manager:
                    self._status = {**self._status, "state": "error"}
            frames += 1
            finished = time.monotonic()
            deadline += ANIMATION_INTERVAL_S
            if deadline < finished:
                # Keep the original cadence grid. A late frame skips expired
                # slots without adding a whole extra interval after its work.
                missed = int((finished - deadline) / ANIMATION_INTERVAL_S) + 1
                deadline += missed * ANIMATION_INTERVAL_S
            if finished - report_at >= 30.0:
                LOGGER.info("Animation trafic : %.1f Hz, intervalle maximal %.0f ms",
                            frames / (finished - report_at), longest_gap * 1000)
                report_at, frames, longest_gap = finished, 0, 0.0

    def _run(
        self, manager: TrafficManager, provider: _Provider, stop: threading.Event
    ) -> None:
        LOGGER.info("Traffic source: %s", provider.name)
        # Un cycle qui suit les mêmes appareils n'a rien à dire, et le
        # journaliser chaque seconde noierait le fichier. Seul un
        # changement mérite une ligne — sans quoi des objets disparus du
        # simulateur le resteraient sans laisser la moindre trace.
        previous: dict[str, int] | None = None
        previous_error = ""
        error_logged_at = 0.0
        next_conflict_check = time.monotonic() + CONFLICT_INTERVAL_S
        while not stop.is_set():
            if time.monotonic() >= next_conflict_check:
                next_conflict_check = time.monotonic() + CONFLICT_INTERVAL_S
                found = tuple(self._conflict_probe())
                if found:
                    LOGGER.warning(
                        "Injection interrompue : %s vient de démarrer",
                        ", ".join(found),
                    )
                    with self._lock:
                        if stop.is_set() or self._manager is not manager:
                            return
                        self._conflicts = found
                    # `stop` rend au simulateur les objets créés ; appelé
                    # depuis ce fil, il ne s'attend pas lui-même.
                    self.stop(expected=manager)
                    return
            try:
                counters = manager.sync_once()
                if counters != previous:
                    LOGGER.info(
                        "Injection %s : %d suivi(s), %d recréé(s), "
                        "%d retiré(s), %d écarté(s)",
                        provider.name,
                        counters["created_or_updated"],
                        counters["recreated"],
                        counters["removed"],
                        counters["skipped"],
                    )
                    previous = counters
                previous_error = ""
            except Exception as exc:  # le trafic ne doit jamais arrêter NaviXav
                if self._manager is manager:
                    status = {
                        **self._status, "state": "error", "reason": str(exc),
                        "updated": time.monotonic()
                    }
                    error_code = str(getattr(exc, "code", "") or "")
                    retry_after_s = getattr(exc, "retry_after_s", None)
                    if error_code:
                        status["error_code"] = error_code
                    if retry_after_s is not None:
                        status["retry_after_s"] = max(0, math.ceil(float(retry_after_s)))
                    self._status = status
                message = str(exc)
                now = time.monotonic()
                if message != previous_error or now - error_logged_at >= 30.0:
                    LOGGER.warning("Cycle d'injection interrompu : %s", exc)
                    previous_error, error_logged_at = message, now
            stop.wait(self._interval_s)
