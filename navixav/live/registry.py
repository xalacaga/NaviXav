"""Position de l'avion lue directement dans MSFS par SimConnect."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from navixav.live.base import (
    AircraftState,
    PositionSource,
    PositionUnavailable,
    TrafficReport,
)
from navixav.live.simconnect import SimConnectSource

# Intervalle minimal entre deux redécouvertes complètes.
_REDISCOVER_DELAY_S = 8.0
SNAPSHOT_MAX_AGE_S = 0.25


class LiveTracker:
    """Point d'entrée unique pour l'état courant de l'avion."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._lock = threading.Lock()
        self._clock = clock
        self._snapshot: AircraftState | None = None
        self._sampled_at = 0.0
        self._aircraft_hint: str | None = None
        self._closed = False
        self._sources: list[PositionSource] = [SimConnectSource()]
        self._active: PositionSource | None = None
        self._last_attempt = float("-inf")
        self._last_reason = "Recherche du simulateur…"

    # ------------------------------------------------------------------ #

    def set_aircraft_hint(self, hint: str | None) -> None:
        """Indique le modèle planifié aux adaptateurs qui en ont besoin."""
        with self._lock:
            if self._closed or hint == self._aircraft_hint:
                return
            self._aircraft_hint = hint
            self._snapshot = None
            for source in self._sources:
                setter = getattr(source, "set_aircraft_hint", None)
                if callable(setter):
                    setter(hint)

    def read(self) -> AircraftState:
        """Share one immutable, timestamped sample for at most 250 ms.

        The lock coalesces concurrent requests. An expired or failed sample is
        never returned as a fresh position; no polling thread is left to stop.
        """
        with self._lock:
            if self._closed:
                raise PositionUnavailable("Suivi du simulateur fermé.")
            if (self._snapshot is not None
                    and self._clock() - self._sampled_at < SNAPSHOT_MAX_AGE_S):
                return self._snapshot
            self._snapshot = None
            state = self._read_source()
            self._snapshot = state
            self._sampled_at = self._clock()
            return state

    def _read_source(self) -> AircraftState:
        # Called only while holding the shared snapshot lock.
        if self._active is not None:
            try:
                return self._active.read()
            except PositionUnavailable as exc:
                self._last_reason = str(exc)
                self._active = None
                self._last_attempt = self._clock()

        now = self._clock()
        if now - self._last_attempt < _REDISCOVER_DELAY_S:
            raise PositionUnavailable(self._last_reason)
        self._last_attempt = now

        reasons: list[str] = []
        for source in self._sources:
            if not source.is_available():
                continue
            try:
                state = source.read()
            except PositionUnavailable as exc:
                reasons.append(f"{source.name} : {exc}")
                continue
            self._active = source
            self._last_reason = ""
            return state

        self._last_reason = (
            " ".join(reasons)
            if reasons
            else (
                "Aucune source de position. Lance Microsoft Flight Simulator "
                "et charge un vol."
            )
        )
        raise PositionUnavailable(self._last_reason)

    def traffic(self, *, strict: bool = False) -> list[TrafficReport]:
        """Trafic voisin de la source active, s'il y en a une qui l'expose.

        Aucune découverte n'est déclenchée ici : le trafic accompagne un suivi
        déjà établi, et une source encore muette n'a rien à en dire.
        """
        with self._lock:
            source = self._active
        reader = getattr(source, "traffic", None) if source else None
        if not callable(reader):
            return []
        try:
            if strict and isinstance(source, SimConnectSource):
                return source.traffic(strict=True)
            return reader()
        except PositionUnavailable:
            if strict:
                raise
            return []

    @property
    def active_source(self) -> str | None:
        return self._active.name if self._active else None

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._snapshot = None
            for source in self._sources:
                try:
                    source.close()
                except Exception:  # pragma: no cover - fermeture au mieux
                    pass
            self._active = None
