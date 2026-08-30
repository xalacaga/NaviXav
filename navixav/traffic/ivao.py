"""Lecture du flux public officiel IVAO Whazzup v2."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import requests

from navixav.traffic.base import TrafficAircraft

LOGGER = logging.getLogger(__name__)
DATA_URL = "https://api.ivao.aero/v2/tracker/whazzup"
USER_AGENT = "NaviXav/0.1 (local flight simulation tool)"
TRAFFIC_TTL_S = 15.0
DEFAULT_TIMEOUT = 10
MAX_TRAFFIC = 3000


class IvaoError(RuntimeError):
    """Flux IVAO injoignable ou inexploitable."""


@dataclass(frozen=True)
class IvaoAircraftDetail:
    callsign: str
    aircraft: str = ""
    departure: str = ""
    arrival: str = ""
    altitude_ft: int = 0
    ground_speed_kt: int = 0
    heading_deg: int = 0

    def to_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def _number(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _text(value: object, maximum: int = 32) -> str:
    return str(value or "").strip()[:maximum]


def _aircraft(raw: object) -> TrafficAircraft | None:
    if not isinstance(raw, dict):
        return None
    track = raw.get("lastTrack")
    plan = raw.get("flightPlan")
    track = track if isinstance(track, dict) else {}
    plan = plan if isinstance(plan, dict) else {}
    aircraft = plan.get("aircraft")
    aircraft = aircraft if isinstance(aircraft, dict) else {}
    latitude = _number(track.get("latitude"))
    longitude = _number(track.get("longitude"))
    callsign = _text(raw.get("callsign")).upper()
    if not callsign or latitude is None or longitude is None:
        return None
    aircraft_type = _text(aircraft.get("icaoCode"), 8).upper() or None
    prefix = callsign[:3] if len(callsign) >= 4 and callsign[:3].isalpha() else ""
    identity = _text(raw.get("id"), 64) or callsign
    return TrafficAircraft(
        uid=f"ivao:{identity}",
        callsign=callsign,
        aircraft_type=aircraft_type,
        airline_icao=prefix or None,
        latitude=latitude,
        longitude=longitude,
        altitude_ft=_number(track.get("altitude")),
        ground_speed_kt=_number(track.get("groundSpeed")),
        heading_deg=_number(track.get("heading")),
        on_ground=track.get("onGround") if isinstance(track.get("onGround"), bool) else None,
        departure=_text(plan.get("departureId"), 8).upper(),
        arrival=_text(plan.get("arrivalId"), 8).upper(),
    )


class IvaoClient:
    """Source trafic IVAO publique, sans compte ni clé API."""

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        ttl_s: float = TRAFFIC_TTL_S,
    ) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout
        self._ttl_s = ttl_s
        self._lock = threading.Lock()
        self._feed: dict[str, Any] | None = None
        self._fetched_at = 0.0

    @property
    def name(self) -> str:
        return "IVAO"

    def _read(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            if self._feed is not None and now - self._fetched_at < self._ttl_s:
                return self._feed
            try:
                response = self._session.get(
                    DATA_URL,
                    timeout=self._timeout,
                    headers={"User-Agent": USER_AGENT},
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise IvaoError(f"Relevé IVAO injoignable : {exc}") from exc
            clients = payload.get("clients") if isinstance(payload, dict) else None
            if not isinstance(clients, dict) or not isinstance(clients.get("pilots"), list):
                raise IvaoError("Relevé IVAO inattendu.")
            self._feed = payload
            self._fetched_at = now
            return payload

    def traffic(self, limit: int | None = MAX_TRAFFIC) -> list[TrafficAircraft]:
        pilots = self._read()["clients"]["pilots"]
        found: list[TrafficAircraft] = []
        for raw in pilots:
            entry = _aircraft(raw)
            if entry is not None:
                found.append(entry)
                if limit is not None and len(found) >= limit:
                    break
        return found

    def detail(self, callsign: str) -> IvaoAircraftDetail | None:
        wanted = callsign.strip().upper()
        if not wanted:
            return None
        entry = next((item for item in self.traffic() if item.callsign == wanted), None)
        if entry is None:
            return None
        return IvaoAircraftDetail(
            callsign=entry.callsign,
            aircraft=entry.aircraft,
            departure=entry.departure,
            arrival=entry.arrival,
            altitude_ft=int(entry.altitude_ft or 0),
            ground_speed_kt=int(entry.ground_speed_kt or 0),
            heading_deg=int(entry.heading_deg or 0),
        )

    def updated_at(self) -> str:
        return _text(self._read().get("updatedAt"), 64)

    def close(self) -> None:
        closer = getattr(self._session, "close", None)
        if callable(closer):
            closer()
