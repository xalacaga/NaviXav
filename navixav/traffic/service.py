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
import threading
from typing import Callable, Protocol

from navixav.traffic.fsltl import FsltlInstallation, FsltlModelIndex, FsltlStatus
from navixav.traffic.injector import SimConnectTrafficInjector
from navixav.traffic.manager import TrafficManager

LOGGER = logging.getLogger(__name__)
DEFAULT_INTERVAL_S = 1.0
STOP_TIMEOUT_S = 3.0


class _Provider(Protocol):
    @property
    def name(self) -> str: ...


class TrafficService:
    """Détient l'injection et la relance à chaque changement de réglage."""

    def __init__(
        self,
        detect: Callable[[], FsltlInstallation],
        position: Callable[[], tuple[float, float]],
        altitude: Callable[[], float | None] | None = None,
        *,
        interval_s: float = DEFAULT_INTERVAL_S,
        injector_factory: Callable[[], SimConnectTrafficInjector] = SimConnectTrafficInjector,
        models_factory: Callable[[FsltlInstallation], FsltlModelIndex] = FsltlModelIndex,
    ) -> None:
        self._detect = detect
        self._position = position
        self._altitude = altitude
        self._interval_s = interval_s
        self._injector_factory = injector_factory
        # Les deux fabriques ne sont là que pour être remplacées : sans elles,
        # vérifier le cycle de vie exigerait un simulateur et le paquet FSLTL
        # sur le disque, c'est-à-dire ne jamais le vérifier.
        self._models_factory = models_factory
        self._lock = threading.RLock()
        self._manager: TrafficManager | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._fsltl = detect()

    # ------------------------------------------------------------ lecture

    @property
    def fsltl(self) -> FsltlInstallation:
        """Dernière détection connue, telle que l'interface l'affiche."""
        with self._lock:
            return self._fsltl

    @property
    def active(self) -> bool:
        """Vrai quand un gestionnaire tourne réellement."""
        with self._lock:
            return self._manager is not None

    # ------------------------------------------------------------ commande

    def configure(self, *, enabled: bool, provider: _Provider) -> None:
        """Arrête l'injection en cours, puis la relance si elle est demandée.

        La détection FSLTL est refaite à chaque appel : le chemin du paquet et
        le dossier Communauté sont des réglages, et une installation faite
        pendant que NaviXav tourne doit être vue sans redémarrage.
        """
        with self._lock:
            self.stop()
            self._fsltl = self._detect()
            if not enabled:
                return
            if self._fsltl.status is not FsltlStatus.DETECTED:
                LOGGER.warning("Injection désactivée : %s", self._fsltl.reason)
                return
            manager = TrafficManager(
                provider,
                self._models_factory(self._fsltl),
                self._injector_factory(),
                self._position,
                altitude=self._altitude,
            )
            self._manager = manager
            self._stop = threading.Event()
            stop = self._stop
            self._thread = threading.Thread(
                target=self._run,
                args=(manager, provider, stop),
                name=f"NaviXav-{provider.name}-traffic",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Arrête le fil et rend au simulateur les objets créés."""
        with self._lock:
            self._stop.set()
            thread, self._thread = self._thread, None
            manager, self._manager = self._manager, None
        # Hors verrou : le fil en cours de cycle a besoin de le prendre pour
        # lire l'état, et l'attendre en le tenant nous bloquerait tous les deux.
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=STOP_TIMEOUT_S)
        if manager is not None:
            manager.close()

    def close(self) -> None:
        self.stop()

    # ------------------------------------------------------------ interne

    def _run(
        self, manager: TrafficManager, provider: _Provider, stop: threading.Event
    ) -> None:
        LOGGER.info("Traffic source: %s", provider.name)
        # Un cycle qui suit les mêmes appareils n'a rien à dire, et le
        # journaliser chaque seconde noierait le fichier. Seul un
        # changement mérite une ligne — sans quoi des objets disparus du
        # simulateur le resteraient sans laisser la moindre trace.
        previous: dict[str, int] | None = None
        while not stop.is_set():
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
            except Exception as exc:  # le trafic ne doit jamais arrêter NaviXav
                LOGGER.warning("Cycle d'injection interrompu : %s", exc)
            stop.wait(self._interval_s)
