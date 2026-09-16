"""Connecteur FlyByWire (A32NX, A380X) : MCDU distant de SimBridge et phase FMGC.

SimBridge, le service local optionnel de FlyByWire, relaie l'écran des deux
MCDU à qui se connecte à son WebSocket : c'est ce qu'utilise leur « Remote
MCDU ». NaviXav s'y connecte, demande l'écran courant (``requestUpdate``) et
reçoit des messages ``update:{…}`` portant, pour chaque MCDU, le titre, les
douze lignes (gauche, droite, centre) et le bloc-notes, balisés à la façon
A32NX : ``{green}``, ``{small}``, ``{end}``, ``{sp}``…

La phase FMGC est une variable locale de l'avion, lue par SimConnect. Rien
n'est jamais écrit : ni touche envoyée au MCDU, ni variable modifiée.

SimBridge n'est pas documenté comme une API publique : son protocole peut
changer à une mise à jour de FlyByWire, et le connecteur se tait alors.
"""

from __future__ import annotations

import json
import logging
import re
import socket
import threading
import time
from typing import Any

from navixav.live.mcdu_screen import compose, screen, segment
from navixav.live.websocket import WebSocketClient, WebSocketError

logger = logging.getLogger(__name__)

SIMBRIDGE_HOST = "127.0.0.1"
SIMBRIDGE_PORT = 8380
SIMBRIDGE_MCDU_URL = f"ws://{SIMBRIDGE_HOST}:{SIMBRIDGE_PORT}/interfaces/v1/mcdu"

PHASE_LVAR = "L:A32NX_FMGC_FLIGHT_PHASE"
PHASES = {
    0: "Preflight", 1: "Takeoff", 2: "Climb", 3: "Cruise",
    4: "Descent", 5: "Approach", 6: "GoAround", 7: "Done",
}

MIN_INTERVAL_S = 2.0
RETRY_INTERVAL_S = 20.0

_COLOURS = {"green", "amber", "cyan", "white", "magenta", "yellow", "red"}
_TOKEN = re.compile(r"\{(\w+)\}")


def gateway_listening(host: str = SIMBRIDGE_HOST, port: int = SIMBRIDGE_PORT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def parse_markup(text: str, *, size: str = "large", color: str = "white") -> list[dict[str, str]]:
    """Le balisage A32NX en segments ; ``{end}`` referme le dernier style ouvert."""
    segments: list[dict[str, str]] = []
    stack: list[tuple[str, str]] = []
    buffer: list[str] = []
    current_size, current_color = size, color

    def flush() -> None:
        if buffer:
            segments.append(segment("".join(buffer), current_color, current_size))
            buffer.clear()

    position = 0
    for match in _TOKEN.finditer(text or ""):
        buffer.append(text[position:match.start()])
        position = match.end()
        token = match.group(1).lower()
        if token == "sp":
            buffer.append(" ")
            continue
        if token in ("left", "right"):
            continue
        flush()
        if token == "end":
            if stack:
                current_size, current_color = stack.pop()
            continue
        stack.append((current_size, current_color))
        if token == "small":
            current_size = "small"
        elif token == "big":
            current_size = "large"
        elif token == "inop":
            current_color = "grey"
        elif token in _COLOURS:
            current_color = token
        else:
            stack.pop()
    buffer.append(text[position:] if text else "")
    flush()
    return [item for item in segments if item["text"]]


def parse_update(message: str) -> dict[str, Any] | None:
    """Un message ``update:{…}`` de SimBridge en écrans par MCDU (« 1 », « 2 »)."""
    if not message.startswith("update:"):
        return None
    try:
        payload = json.loads(message[len("update:"):])
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    units = {"1": payload.get("left"), "2": payload.get("right")}
    if units["1"] is None and units["2"] is None and "lines" in payload:
        units = {"1": payload}
    screens: dict[str, Any] = {}
    for unit, content in units.items():
        if isinstance(content, dict) and isinstance(content.get("lines"), list):
            screens[unit] = _screen(content)
    return screens or None


def _screen(content: dict[str, Any]) -> dict[str, Any]:
    title = compose(
        parse_markup(str(content.get("titleLeft") or ""), size="small"),
        [],
        parse_markup(str(content.get("title") or "")),
    )
    lines = []
    for index, row in enumerate(content.get("lines") or []):
        parts = list(row) if isinstance(row, (list, tuple)) else [row]
        parts += [""] * (3 - len(parts))
        # Les lignes paires sont les libellés, en petit sur l'écran réel.
        size = "small" if index % 2 == 0 else "large"
        lines.append(compose(
            parse_markup(str(parts[0] or ""), size=size),
            parse_markup(str(parts[1] or ""), size=size),
            parse_markup(str(parts[2] or ""), size=size),
        ))
    scratchpad = parse_markup(str(content.get("scratchpad") or ""))
    return screen(title, lines, scratchpad)


class FbwFmsReader:
    """Écran MCDU via SimBridge et phase FMGC via SimConnect, sans rien écrire."""

    def __init__(
        self,
        listening=gateway_listening,
        client_factory=None,
        phase_reader=None,
        url: str = SIMBRIDGE_MCDU_URL,
    ) -> None:
        self._listening = listening
        self._client_factory = client_factory or (lambda: WebSocketClient(url, timeout_s=2.0))
        self._phase_reader = phase_reader
        self._lock = threading.Lock()
        self._socket: WebSocketClient | None = None
        self._simconnect = None
        self._last_read = 0.0
        self._next_probe = 0.0
        self._available = False
        self._state: dict[str, Any] | None = None

    def read(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            if now - self._last_read >= MIN_INTERVAL_S:
                self._refresh(now)
            if self._state is None:
                return {"available": False, "source": "fbw", "reason": "simbridge_unavailable"}
            return self._state

    def _refresh(self, now: float) -> None:
        self._last_read = now
        if not self._available:
            if now < self._next_probe:
                return
            self._next_probe = now + RETRY_INTERVAL_S
            self._available = self._listening()
            if not self._available:
                self._state = None
                return
        screens = self._read_screens()
        if screens is None:
            self._available = False
            self._state = None
            return
        self._state = {
            "available": True,
            "source": "fbw",
            "phase": self._read_phase(),
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

    def _read_screens(self) -> dict[str, Any] | None:
        for attempt in range(2):
            try:
                if self._socket is None:
                    self._socket = self._client_factory()
                    self._socket.connect()
                self._socket.send_text("requestUpdate")
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline:
                    screens = parse_update(self._socket.receive_text())
                    if screens:
                        return screens
                return None
            except WebSocketError as exc:
                logger.info("MCDU SimBridge illisible (%s)", type(exc).__name__)
                if self._socket is not None:
                    self._socket.close()
                self._socket = None
                if attempt:
                    return None
        return None

    def _read_phase(self) -> str:
        """La phase FMGC ; vide si SimConnect ou la variable manquent."""
        if self._phase_reader is not None:
            value = self._phase_reader()
        else:
            value = self._read_phase_simconnect()
        try:
            return PHASES.get(int(round(float(value))), "") if value is not None else ""
        except (TypeError, ValueError):
            return ""

    def _read_phase_simconnect(self) -> float | None:
        from navixav.msfs.client import SimConnectClient, SimConnectError

        try:
            if self._simconnect is None:
                self._simconnect = SimConnectClient()
            return self._simconnect.read_simvars([(PHASE_LVAR, "Number")], timeout_s=1.0)[PHASE_LVAR]
        except SimConnectError:
            if self._simconnect is not None:
                self._simconnect.close()
            self._simconnect = None
            return None

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self._simconnect is not None:
            self._simconnect.close()
            self._simconnect = None
