"""Position de l'avion lue directement dans MSFS par SimConnect."""

from __future__ import annotations

import threading
import time

from navixav.live.base import AircraftState, PositionSource, PositionUnavailable
from navixav.live.simconnect import SimConnectSource

# Intervalle minimal entre deux redécouvertes complètes.
_REDISCOVER_DELAY_S = 8.0


class LiveTracker:
    """Point d'entrée unique pour l'état courant de l'avion."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sources: list[PositionSource] = [SimConnectSource()]
        self._active: PositionSource | None = None
        self._demo: PositionSource | None = None
        self._last_attempt = 0.0
        self._last_reason = "Recherche du simulateur…"

    # ------------------------------------------------------------------ #

    def set_demo(self, source: PositionSource | None) -> None:
        with self._lock:
            self._demo = source

    def read(self, allow_demo: bool = False) -> AircraftState:
        with self._lock:
            if allow_demo and self._demo is not None:
                return self._demo.read()

            if self._active is not None:
                try:
                    return self._active.read()
                except PositionUnavailable as exc:
                    self._last_reason = str(exc)
                    self._active = None

            now = time.monotonic()
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

    @property
    def active_source(self) -> str | None:
        return self._active.name if self._active else None

    def close(self) -> None:
        with self._lock:
            for source in self._sources:
                try:
                    source.close()
                except Exception:  # pragma: no cover - fermeture au mieux
                    pass
            self._active = None
