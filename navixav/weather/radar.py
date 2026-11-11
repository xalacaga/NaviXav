"""Dernière mosaïque radar RainViewer destinée au calque de la carte.

RainViewer ne fournit ici qu'un manifeste léger. Les tuiles transparentes sont
ensuite chargées directement par WebView2, comme les tuiles du fond de carte.
Le manifeste est mis en cache dix minutes : c'est la cadence native du flux et
cela évite qu'un changement d'onglet multiplie les appels réseau.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests

LOGGER = logging.getLogger(__name__)

RAINVIEWER_MANIFEST_URL = "https://api.rainviewer.com/public/weather-maps.json"
DEFAULT_TIMEOUT = 12
CACHE_SECONDS = 600
RETRY_SECONDS = 60
# Cadence des images RainViewer, et délai observé avant leur publication.
FRAME_INTERVAL_SECONDS = 600
PUBLICATION_DELAY_SECONDS = 90


def _safe_host(value: Any) -> str | None:
    """N'accepte que le serveur HTTPS publié par RainViewer."""
    host = str(value or "").rstrip("/")
    parsed = urlparse(host)
    if parsed.scheme != "https" or not parsed.hostname:
        return None
    if parsed.hostname != "rainviewer.com" and not parsed.hostname.endswith(
        ".rainviewer.com"
    ):
        return None
    return host


def _latest_frame(payload: Any) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    host = _safe_host(payload.get("host"))
    radar = payload.get("radar")
    frames = radar.get("past") if isinstance(radar, dict) else None
    if not host or not isinstance(frames, list):
        return None
    valid = []
    for item in frames:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        stamp = item.get("time")
        if path.startswith("/v2/radar/") and isinstance(stamp, (int, float)):
            valid.append((float(stamp), path))
    if not valid:
        return None
    stamp, path = max(valid)
    generated = payload.get("generated")
    return {
        "host": host,
        "path": path,
        "time": int(stamp),
        "generated": int(generated) if isinstance(generated, (int, float)) else None,
        "tile_url": f"{host}{path}/256/{{z}}/{{x}}/{{y}}/2/1_1.png",
        "max_zoom": 7,
        "source": "RainViewer",
        "source_url": "https://www.rainviewer.com/",
    }


@dataclass
class RadarFeed:
    """Manifeste de la dernière image radar, avec repli sur le relevé précédent."""

    session: requests.Session = field(default_factory=requests.Session)
    timeout: int = DEFAULT_TIMEOUT
    cache_seconds: float = CACHE_SECONDS
    _frame: dict[str, object] | None = None
    _fetched_at: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _due(self, now: float, wall: float) -> bool:
        """Faut-il relire le manifeste ?

        RainViewer publie une image toutes les dix minutes. Relire à heure
        fixe toutes les dix minutes laissait jusqu'à vingt minutes de retard
        quand le relevé tombait juste avant la nouvelle image. Le manifeste
        est donc relu dès que l'image suivante doit exister (dix minutes après
        la dernière, plus une marge de publication), et au plus toutes les
        minutes en attendant qu'elle paraisse.
        """
        if not self._fetched_at:
            return True
        elapsed = now - self._fetched_at
        if elapsed >= self.cache_seconds:
            return True
        stamp = (self._frame or {}).get("time")
        if isinstance(stamp, int) and wall >= stamp + FRAME_INTERVAL_SECONDS + PUBLICATION_DELAY_SECONDS:
            return elapsed >= RETRY_SECONDS
        return False

    def current(self, *, monotonic: float | None = None, wall: float | None = None) -> dict[str, object]:
        now = time.monotonic() if monotonic is None else monotonic
        wall_now = time.time() if wall is None else wall
        with self._lock:
            if self._due(now, wall_now):
                started = time.perf_counter()
                try:
                    response = self.session.get(
                        RAINVIEWER_MANIFEST_URL,
                        timeout=self.timeout,
                        headers={"User-Agent": "NaviXav flight-simulation weather map"},
                    )
                    response.raise_for_status()
                    fresh = _latest_frame(response.json())
                    if fresh is None:
                        raise ValueError("manifeste radar invalide")
                    self._frame = fresh
                    self._fetched_at = now
                    LOGGER.info(
                        "Manifeste radar relevé en %.2f s",
                        time.perf_counter() - started,
                    )
                except (requests.RequestException, ValueError, TypeError) as exc:
                    LOGGER.warning("Radar indisponible : %s", type(exc).__name__)
                    if self._frame is None:
                        raise requests.ConnectionError("radar indisponible") from exc
                    self._fetched_at = now - self.cache_seconds + RETRY_SECONDS
            return dict(self._frame or {})

    def close(self) -> None:
        self.session.close()
