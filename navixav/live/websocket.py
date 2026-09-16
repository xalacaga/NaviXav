"""Client WebSocket minimal (RFC 6455), texte seulement, sans dépendance.

Il sert à lire le MCDU distant de SimBridge (FlyByWire). Un client complet
serait disproportionné : NaviXav envoie deux mots et lit des trames texte.
Les trames de contrôle (ping, close) sont honorées ; les trames binaires sont
ignorées.
"""

from __future__ import annotations

import base64
import os
import socket
import struct
from urllib.parse import urlparse

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OPCODE_TEXT = 0x1
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA


class WebSocketError(RuntimeError):
    """La connexion n'a pas pu s'établir ou a été rompue."""


def _mask(payload: bytes, key: bytes) -> bytes:
    return bytes(byte ^ key[index % 4] for index, byte in enumerate(payload))


def encode_frame(payload: bytes, opcode: int = OPCODE_TEXT) -> bytes:
    """Une trame masquée, comme tout client doit en envoyer."""
    head = bytes([0x80 | opcode])
    length = len(payload)
    if length < 126:
        head += bytes([0x80 | length])
    elif length < 0x10000:
        head += bytes([0x80 | 126]) + struct.pack(">H", length)
    else:
        head += bytes([0x80 | 127]) + struct.pack(">Q", length)
    key = os.urandom(4)
    return head + key + _mask(payload, key)


def decode_frame(buffer: bytes) -> tuple[int, bytes, int] | None:
    """(opcode, charge, octets consommés) ou None si la trame est incomplète."""
    if len(buffer) < 2:
        return None
    opcode = buffer[0] & 0x0F
    masked = bool(buffer[1] & 0x80)
    length = buffer[1] & 0x7F
    offset = 2
    if length == 126:
        if len(buffer) < 4:
            return None
        length = struct.unpack(">H", buffer[2:4])[0]
        offset = 4
    elif length == 127:
        if len(buffer) < 10:
            return None
        length = struct.unpack(">Q", buffer[2:10])[0]
        offset = 10
    key = b""
    if masked:
        if len(buffer) < offset + 4:
            return None
        key = buffer[offset:offset + 4]
        offset += 4
    if len(buffer) < offset + length:
        return None
    payload = buffer[offset:offset + length]
    if masked:
        payload = _mask(payload, key)
    return opcode, payload, offset + length


class WebSocketClient:
    """Une connexion texte, bloquante, avec délai d'attente."""

    def __init__(self, url: str, timeout_s: float = 3.0) -> None:
        parts = urlparse(url)
        if parts.scheme != "ws":
            raise WebSocketError("Seul ws:// est pris en charge.")
        self._host = parts.hostname or "127.0.0.1"
        self._port = parts.port or 80
        self._path = parts.path or "/"
        self._timeout = timeout_s
        self._socket: socket.socket | None = None
        self._buffer = b""

    def connect(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            f"GET {self._path} HTTP/1.1\r\n"
            f"Host: {self._host}:{self._port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        try:
            self._socket = socket.create_connection((self._host, self._port), timeout=self._timeout)
            self._socket.sendall(request.encode())
            response = b""
            while b"\r\n\r\n" not in response:
                chunk = self._socket.recv(4096)
                if not chunk:
                    raise WebSocketError("Connexion fermée pendant la poignée de main.")
                response += chunk
        except OSError as exc:
            self.close()
            raise WebSocketError(str(exc)) from exc
        head, _, rest = response.partition(b"\r\n\r\n")
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            self.close()
            raise WebSocketError("Le serveur a refusé la mise à niveau WebSocket.")
        self._buffer = rest

    def send_text(self, text: str) -> None:
        if self._socket is None:
            raise WebSocketError("Connexion fermée.")
        try:
            self._socket.sendall(encode_frame(text.encode("utf-8")))
        except OSError as exc:
            self.close()
            raise WebSocketError(str(exc)) from exc

    def receive_text(self) -> str:
        """La prochaine trame texte ; les pings sont rendus, une fermeture lève."""
        if self._socket is None:
            raise WebSocketError("Connexion fermée.")
        while True:
            decoded = decode_frame(self._buffer)
            if decoded is None:
                try:
                    chunk = self._socket.recv(65536)
                except OSError as exc:
                    self.close()
                    raise WebSocketError(str(exc)) from exc
                if not chunk:
                    self.close()
                    raise WebSocketError("Connexion fermée par le serveur.")
                self._buffer += chunk
                continue
            opcode, payload, consumed = decoded
            self._buffer = self._buffer[consumed:]
            if opcode == OPCODE_TEXT:
                return payload.decode("utf-8", errors="replace")
            if opcode == OPCODE_PING:
                self._socket.sendall(encode_frame(payload, OPCODE_PONG))
            elif opcode == OPCODE_CLOSE:
                self.close()
                raise WebSocketError("Connexion fermée par le serveur.")

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
