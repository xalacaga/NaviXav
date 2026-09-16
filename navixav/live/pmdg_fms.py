"""Connecteur PMDG (737, 777) : l'écran du CDU diffusé par le SDK PMDG.

Le SDK PMDG publie, sur demande, l'écran de chaque CDU dans une zone
SimConnect *ClientData* : 24 colonnes × 14 lignes de cellules
``{symbole, couleur, drapeaux}`` suivies d'un octet « alimenté ». La
diffusion doit être activée par le pilote dans les options de l'avion
(``EnableCDUBroadcast.0=1`` — CDU du commandant — dans le fichier d'options
PMDG) ; sans cela la zone n'existe pas et le connecteur se tait.

Le SDK expose aussi un grand bloc de données de vol dont la disposition
dépend de la version : NaviXav ne le lit pas, pour ne pas décoder au hasard.
Rien n'est jamais écrit : la zone de commande PMDG n'est pas ouverte.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from navixav.live.mcdu_screen import screen, segment

logger = logging.getLogger(__name__)

CDU_COLUMNS = 24
CDU_ROWS = 14
CDU_CELL_SIZE = 3
CDU_SCREEN_SIZE = CDU_COLUMNS * CDU_ROWS * CDU_CELL_SIZE + 1

# Familles PMDG pour MSFS et leurs zones de CDU (commandant, copilote).
CDU_AREAS = {
    "PMDG 737": ("PMDG_NG3_CDU_0", "PMDG_NG3_CDU_1"),
    "PMDG 777": ("PMDG_777X_CDU_0", "PMDG_777X_CDU_1"),
}

_COLOURS = {0: "white", 1: "cyan", 2: "green", 3: "magenta", 4: "amber", 5: "red"}
_FLAG_SMALL = 0x01

MIN_INTERVAL_S = 2.0
RETRY_INTERVAL_S = 20.0


def parse_cdu_screen(payload: bytes) -> dict[str, Any] | None:
    """La zone binaire en écran commun ; None si le CDU est éteint ou la zone vide."""
    if len(payload) < CDU_SCREEN_SIZE:
        return None
    if not payload[CDU_COLUMNS * CDU_ROWS * CDU_CELL_SIZE]:
        return None
    rows: list[list[dict[str, str]]] = []
    for row in range(CDU_ROWS):
        segments: list[dict[str, str]] = []
        for column in range(CDU_COLUMNS):
            offset = (column * CDU_ROWS + row) * CDU_CELL_SIZE
            symbol, colour, flags = payload[offset], payload[offset + 1], payload[offset + 2]
            text = chr(symbol) if 32 <= symbol < 127 else (" " if symbol == 0 else "·")
            color = _COLOURS.get(colour, "white")
            size = "small" if flags & _FLAG_SMALL else "large"
            if segments and segments[-1]["color"] == color and segments[-1]["size"] == size:
                segments[-1]["text"] += text
            else:
                segments.append(segment(text, color, size))
        rows.append(segments)
    if all(not "".join(item["text"] for item in row).strip() for row in rows):
        return None
    return screen(rows[0], rows[1:CDU_ROWS - 1], rows[CDU_ROWS - 1])


class PmdgFmsReader:
    """Écrans CDU PMDG par ClientData, en lecture seule, tolérant à l'absence."""

    def __init__(self, client_factory=None) -> None:
        self._client_factory = client_factory
        self._client = None
        self._lock = threading.Lock()
        self._last_read = 0.0
        self._next_probe = 0.0
        self._family: str | None = None
        self._state: dict[str, Any] | None = None

    def read(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            if now - self._last_read >= MIN_INTERVAL_S:
                self._refresh(now)
            if self._state is None:
                return {"available": False, "source": "pmdg", "reason": "cdu_broadcast_unavailable"}
            return self._state

    def _open(self):
        if self._client is None:
            if self._client_factory is not None:
                self._client = self._client_factory()
            else:
                from navixav.msfs.client import SimConnectClient

                self._client = SimConnectClient()
        return self._client

    def _read_area(self, name: str) -> bytes | None:
        from navixav.msfs.client import SimConnectError

        try:
            return self._open().read_client_data(name, CDU_SCREEN_SIZE, timeout_s=1.0)
        except SimConnectError:
            return None
        except Exception as exc:  # noqa: BLE001 - la DLL absente ne doit rien casser
            logger.info("CDU PMDG illisible (%s)", type(exc).__name__)
            self._close_client()
            return None

    def _refresh(self, now: float) -> None:
        self._last_read = now
        if self._family is None:
            if now < self._next_probe:
                return
            self._next_probe = now + RETRY_INTERVAL_S
            for family, areas in CDU_AREAS.items():
                if self._read_area(areas[0]) is not None:
                    self._family = family
                    break
            if self._family is None:
                self._state = None
                return
        screens: dict[str, Any] = {}
        for unit, name in enumerate(CDU_AREAS[self._family], start=1):
            payload = self._read_area(name)
            parsed = parse_cdu_screen(payload) if payload is not None else None
            if parsed:
                screens[str(unit)] = parsed
            elif unit == 1 and payload is None:
                # La zone du commandant a disparu : l'avion a changé ou la
                # diffusion a été coupée ; on resondera plus tard.
                self._family = None
                self._state = None
                return
        self._state = {
            "available": True,
            "source": "pmdg",
            "aircraft_family": self._family,
            "phase": "",
            "origin": "", "destination": "", "alternate": "",
            "origin_runway": "", "destination_runway": "",
            "cruise_level_ft": None, "flight_number": "", "destination_eta": "",
            "legs": [], "alternate_legs": [],
            "from": None, "active": None, "toc": None, "tod": None,
            "speed_limit": None, "decel": None,
            "perf_takeoff": {}, "weights": {},
            "mcdu": screens,
            "read_at": time.time(),
        }

    def _close_client(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
            self._client = None

    def close(self) -> None:
        with self._lock:
            self._close_client()
