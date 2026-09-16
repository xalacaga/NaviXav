"""Les connecteurs FMS autres que Fenix : FlyByWire (SimBridge) et PMDG (CDU)."""

from __future__ import annotations

import base64
import hashlib
import json
import socket
import threading

import pytest

from navixav.live import websocket as ws
from navixav.live.fbw_fms import FbwFmsReader, parse_markup, parse_update
from navixav.live.fms_hub import FmsHub
from navixav.live.mcdu_screen import compose, segment
from navixav.live.pmdg_fms import CDU_SCREEN_SIZE, PmdgFmsReader, parse_cdu_screen


# ----------------------------------------------------------------- WebSocket


def test_frames_round_trip_and_partial_frames_wait():
    frame = ws.encode_frame("bonjour".encode("utf-8"))
    opcode, payload, consumed = ws.decode_frame(frame + b"extra")

    assert opcode == ws.OPCODE_TEXT
    assert payload == b"bonjour"
    assert consumed == len(frame)
    assert ws.decode_frame(frame[:-1]) is None
    long = ws.encode_frame(b"x" * 300)
    assert ws.decode_frame(long)[1] == b"x" * 300


def _serve_once(messages: list[str]) -> int:
    """Un serveur WebSocket d'une connexion : poignée de main, puis il envoie
    `messages` dès qu'il reçoit une trame texte, et ferme."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)

    def run() -> None:
        connection, _ = server.accept()
        request = b""
        while b"\r\n\r\n" not in request:
            request += connection.recv(4096)
        key = next(
            line.split(b":", 1)[1].strip()
            for line in request.split(b"\r\n") if line.lower().startswith(b"sec-websocket-key")
        )
        accept = base64.b64encode(hashlib.sha1(key + ws._GUID.encode()).digest())
        connection.sendall(
            b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
            b"Connection: Upgrade\r\nSec-WebSocket-Accept: " + accept + b"\r\n\r\n"
        )
        buffer = b""
        while ws.decode_frame(buffer) is None:
            buffer += connection.recv(4096)
        for message in messages:
            # Un serveur n'a pas à masquer : trame non masquée.
            body = message.encode("utf-8")
            head = bytes([0x81]) + (bytes([len(body)]) if len(body) < 126 else bytes([126]) + len(body).to_bytes(2, "big"))
            connection.sendall(head + body)
        connection.close()
        server.close()

    threading.Thread(target=run, daemon=True).start()
    return server.getsockname()[1]


def test_the_client_performs_the_handshake_and_reads_text_frames():
    port = _serve_once(["hello", "update:{}"])
    client = ws.WebSocketClient(f"ws://127.0.0.1:{port}/interfaces/v1/mcdu", timeout_s=2.0)

    client.connect()
    client.send_text("requestUpdate")

    assert client.receive_text() == "hello"
    assert client.receive_text() == "update:{}"
    with pytest.raises(ws.WebSocketError):
        client.receive_text()


# ----------------------------------------------------------------- FlyByWire


def test_a32nx_markup_becomes_segments():
    segments = parse_markup("{small}FROM{end}{sp}{green}LFPG{end}X", size="large")

    assert segments == [
        {"text": "FROM", "color": "white", "size": "small"},
        {"text": " ", "color": "white", "size": "large"},
        {"text": "LFPG", "color": "green", "size": "large"},
        {"text": "X", "color": "white", "size": "large"},
    ]
    assert parse_markup("{inop}NOT YET{end}")[0]["color"] == "grey"
    assert parse_markup("") == []


def test_compose_aligns_left_right_and_centre_on_24_columns():
    line = compose([segment("LFPG")], [segment("LFBO")], [segment("--")])
    text = "".join(item["text"] for item in line)

    assert len(text) == 24
    assert text.startswith("LFPG") and text.endswith("LFBO")
    assert text.index("--") == 11
    # Un centre trop large pour l'espace libre s'efface devant gauche et droite.
    crowded = compose([segment("A" * 12)], [segment("B" * 10)], [segment("CCCC")])
    assert "".join(item["text"] for item in crowded) == "A" * 12 + "  " + "B" * 10


def test_a_simbridge_update_yields_one_screen_per_mcdu():
    message = "update:" + json.dumps({
        "left": {
            "title": "INIT", "titleLeft": "", "scratchpad": "{amber}NOT ALLOWED{end}",
            "lines": [["{small}CO RTE{end}", "FROM/TO", ""], ["{green}LFPGLFBO{end}", "LFPG/LFBO", ""]] + [["", "", ""]] * 10,
        },
        "right": {"title": "", "titleLeft": "", "scratchpad": "", "lines": [["", "", ""]] * 12},
    })

    screens = parse_update(message)

    assert set(screens) == {"1", "2"}
    assert screens["1"]["title"][0]["text"].strip() == "INIT" or any(
        item["text"] == "INIT" for item in screens["1"]["title"]
    )
    assert screens["1"]["scratchpad"] == [{"text": "NOT ALLOWED", "color": "amber", "size": "large"}]
    first = screens["1"]["lines"][0]
    assert first[0] == {"text": "CO RTE", "color": "white", "size": "small"}
    assert first[-1]["text"] == "FROM/TO"
    assert parse_update("event:left:A") is None
    assert parse_update("update:not json") is None


class _FakeSocket:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []
        self.closed = False

    def connect(self):
        pass

    def send_text(self, text):
        self.sent.append(text)

    def receive_text(self):
        if not self.messages:
            raise ws.WebSocketError("fin")
        return self.messages.pop(0)

    def close(self):
        self.closed = True


def test_the_fbw_reader_requests_an_update_and_maps_the_phase():
    update = "update:" + json.dumps({"left": {"title": "F-PLN", "lines": [["A", "", ""]] * 12, "scratchpad": ""}})
    fake = _FakeSocket(["ping-like noise", update])
    reader = FbwFmsReader(listening=lambda: True, client_factory=lambda: fake, phase_reader=lambda: 4.0)

    state = reader.read()

    assert fake.sent == ["requestUpdate"]
    assert state["available"] is True
    assert state["source"] == "fbw"
    assert state["phase"] == "Descent"
    assert state["legs"] == [] and state["active"] is None
    assert list(state["mcdu"]) == ["1"]
    # Les touches ne sont jamais envoyées : seule la demande d'écran part.
    assert all(not message.startswith("event:") for message in fake.sent)


def test_the_fbw_reader_is_silent_without_simbridge():
    reader = FbwFmsReader(listening=lambda: False, client_factory=lambda: _FakeSocket([]), phase_reader=lambda: None)

    assert reader.read() == {"available": False, "source": "fbw", "reason": "simbridge_unavailable"}


# ---------------------------------------------------------------------- PMDG


def _cdu_payload(text_rows: list[str], powered: bool = True) -> bytes:
    cells = bytearray(CDU_SCREEN_SIZE)
    for row, text in enumerate(text_rows):
        for column, char in enumerate(text[:24]):
            offset = (column * 14 + row) * 3
            cells[offset] = ord(char)
            cells[offset + 1] = 2 if char.isalpha() else 0  # lettres en vert
            cells[offset + 2] = 1 if row % 2 == 1 else 0     # libellés en petit
    cells[-1] = 1 if powered else 0
    return bytes(cells)


def test_the_cdu_area_is_decoded_column_major_with_colours_and_font():
    rows = [""] * 14
    rows[0] = "   RTE 1/2"
    rows[1] = " ORIGIN"
    rows[2] = "LFPG"
    rows[13] = "SELECT DESIRED WPT"

    display = parse_cdu_screen(_cdu_payload(rows))

    assert "".join(item["text"] for item in display["title"]).startswith("   RTE 1/2")
    assert display["lines"][0][1] == {"text": "ORIGIN", "color": "green", "size": "small"}
    assert display["lines"][1][0] == {"text": "LFPG", "color": "green", "size": "large"}
    assert "".join(item["text"] for item in display["scratchpad"]).startswith("SELECT DESIRED WPT")
    assert parse_cdu_screen(_cdu_payload(rows, powered=False)) is None
    assert parse_cdu_screen(b"\x00" * 10) is None


class _FakeSimConnect:
    def __init__(self, areas):
        self.areas = areas
        self.closed = False

    def read_client_data(self, name, size, timeout_s=1.0):
        from navixav.msfs.client import SimConnectRefused

        if name not in self.areas:
            raise SimConnectRefused("absente", [1])
        return self.areas[name]

    def close(self):
        self.closed = True


def test_the_pmdg_reader_finds_the_family_and_serves_both_cdus():
    rows = [""] * 14
    rows[0] = "  LEGS"
    payload = _cdu_payload(rows)
    fake = _FakeSimConnect({"PMDG_777X_CDU_0": payload, "PMDG_777X_CDU_1": payload})
    reader = PmdgFmsReader(client_factory=lambda: fake)

    state = reader.read()

    assert state["available"] is True
    assert state["aircraft_family"] == "PMDG 777"
    assert set(state["mcdu"]) == {"1", "2"}
    reader.close()
    assert fake.closed


def test_the_pmdg_reader_is_silent_without_broadcast():
    reader = PmdgFmsReader(client_factory=lambda: _FakeSimConnect({}))

    assert reader.read()["available"] is False


# ----------------------------------------------------------------------- Hub


def test_the_hub_serves_the_first_available_connector_and_lists_the_others():
    class Silent:
        def read(self):
            return {"available": False, "source": "fenix", "reason": "gateway_unavailable"}

    class Talking:
        def read(self):
            return {"available": True, "source": "fbw", "mcdu": {}}

    assert FmsHub([Silent(), Talking()]).read()["source"] == "fbw"
    assert FmsHub([Silent()]).read() == {"available": False, "sources": {"fenix": "gateway_unavailable"}}
