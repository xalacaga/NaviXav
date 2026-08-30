"""Trafic ADS-B réel depuis l'API publique officielle OpenSky."""

from __future__ import annotations

import math
import threading
import time
from dataclasses import replace
from typing import Callable

import requests

from navixav.traffic.base import TrafficAircraft, generic_callsign
from navixav.traffic.registry import AircraftRegistry

DATA_URL = "https://opensky-network.org/api/states/all"
USER_AGENT = "NaviXav/0.1 (local non-commercial flight simulation tool)"
DEFAULT_TIMEOUT = 10
CACHE_TTL_S = 60.0
RADIUS_NM = 100.0
MAX_TRAFFIC = 500


class OpenSkyError(RuntimeError):
    """Flux OpenSky injoignable, limité ou inexploitable."""


def _number(value: object) -> float | None:
    try:
        result = float(value) if value is not None else None
        return result if result is None or math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


class OpenSkyClient:
    """Lit une boîte de 100 NM autour du joueur, sans compte utilisateur."""

    def __init__(
        self,
        position: Callable[[], tuple[float, float]],
        session: requests.Session | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        ttl_s: float = CACHE_TTL_S,
        registry: AircraftRegistry | None = None,
    ) -> None:
        self._position = position
        self._registry = registry if registry is not None else AircraftRegistry()
        self._session = session or requests.Session()
        self._timeout = timeout
        self._ttl_s = ttl_s
        self._lock = threading.Lock()
        self._aircraft: list[TrafficAircraft] | None = None
        self._updated_at = ""
        self._fetched_at = 0.0

    @property
    def name(self) -> str:
        return "OpenSky"

    def _refresh(self) -> None:
        with self._lock:
            now = time.monotonic()
            if self._aircraft is not None and now - self._fetched_at < self._ttl_s:
                return
            try:
                latitude, longitude = self._position()
                latitude = float(latitude)
                longitude = float(longitude)
            except Exception as exc:
                raise OpenSkyError("Position MSFS indisponible pour le trafic réel.") from exc
            lat_delta = RADIUS_NM / 60.0
            lon_delta = lat_delta / max(0.2, math.cos(math.radians(latitude)))
            params = {
                "lamin": max(-90.0, latitude - lat_delta),
                "lamax": min(90.0, latitude + lat_delta),
                "lomin": max(-180.0, longitude - lon_delta),
                "lomax": min(180.0, longitude + lon_delta),
            }
            try:
                response = self._session.get(
                    DATA_URL,
                    params=params,
                    timeout=self._timeout,
                    headers={"User-Agent": USER_AGENT},
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise OpenSkyError(f"Relevé OpenSky injoignable : {exc}") from exc
            states = payload.get("states") if isinstance(payload, dict) else None
            if states is None:
                states = []
            if not isinstance(states, list):
                raise OpenSkyError("Relevé OpenSky inattendu.")
            found: list[TrafficAircraft] = []
            for state in states[:MAX_TRAFFIC]:
                entry = self._parse(state)
                if entry is not None:
                    found.append(entry)
            timestamp = payload.get("time") if isinstance(payload, dict) else None
            self._aircraft = found
            self._updated_at = str(timestamp or "")
            self._fetched_at = now

    def _parse(self, state: object) -> TrafficAircraft | None:
        if not isinstance(state, list) or len(state) < 12:
            return None
        icao24 = str(state[0] or "").strip().lower()[:16]
        published = str(state[1] or "").strip().upper()[:32]
        longitude = _number(state[5])
        latitude = _number(state[6])
        if not icao24 or latitude is None or longitude is None:
            return None
        # L'ADS-B laisse le champ vide plus souvent qu'on ne croit : plutôt que
        # de montrer une adresse hexadécimale en guise d'indicatif, l'appareil
        # en reçoit un, stable et reconnaissable comme tel.
        callsign = published or generic_callsign(icao24)
        # Le type ne vient jamais du flux d'états : il est lu dans le registre
        # déjà constitué, et l'adresse inconnue part se faire résoudre en fond
        # pour que le cycle suivant la trouve.
        identity = self._registry.lookup(icao24)
        if identity is None:
            self._registry.request(icao24)
        # À défaut d'exploitant au registre, le préfixe de l'indicatif le donne,
        # comme sur les réseaux de simulation. Un indicatif fabriqué n'y donne
        # rien : son préfixe ne désignerait aucune compagnie.
        prefix = (
            published[:3]
            if len(published) >= 4 and published[:3].isalpha()
            else ""
        )
        airline = (identity.airline_icao if identity else "") or prefix
        on_ground = state[8] if isinstance(state[8], bool) else None
        altitude_m = _number(state[7])
        if altitude_m is None and len(state) > 13:
            altitude_m = _number(state[13])
        velocity_ms = _number(state[9])
        heading = _number(state[10])
        # Au parking, plusieurs transpondeurs publient la position et l'état
        # sol mais omettent altitude, vitesse ou route. Ces zéros ne prétendent
        # pas décrire un avion en vol : avec on_ground=True, SimConnect les
        # utilise seulement pour poser un objet immobile sur le terrain.
        if on_ground:
            if altitude_m is None:
                altitude_m = 0.0
            if velocity_ms is None:
                velocity_ms = 0.0
            if heading is None:
                heading = 0.0
        vertical_ms = _number(state[11])
        return TrafficAircraft(
            uid=f"opensky:{icao24}",
            callsign=callsign,
            aircraft_type=(identity.aircraft_type or None) if identity else None,
            airline_icao=airline or None,
            latitude=latitude,
            longitude=longitude,
            altitude_ft=altitude_m * 3.28084 if altitude_m is not None else None,
            ground_speed_kt=velocity_ms * 1.94384 if velocity_ms is not None else None,
            heading_deg=heading,
            vertical_speed_fpm=vertical_ms * 196.8504 if vertical_ms is not None else None,
            on_ground=on_ground,
        )

    def traffic(self, limit: int | None = MAX_TRAFFIC) -> list[TrafficAircraft]:
        self._refresh()
        aircraft = []
        for entry in self._aircraft or ():
            # Le relevé OpenSky reste en cache une minute, mais le registre se
            # remplit en arrière-plan entre-temps. Réappliquer son résultat à
            # chaque lecture rend l'appareil injectable dès qu'il est connu,
            # sans attendre le prochain appel à l'API d'états.
            icao24 = entry.uid.removeprefix("opensky:")
            identity = self._registry.lookup(icao24)
            if identity and identity.aircraft_type and not entry.aircraft_type:
                entry = replace(
                    entry,
                    aircraft_type=identity.aircraft_type,
                    airline_icao=identity.airline_icao or entry.airline_icao,
                )
            aircraft.append(entry)
        return aircraft if limit is None else aircraft[:limit]

    def updated_at(self) -> str:
        self._refresh()
        return self._updated_at

    def detail(self, callsign: str):
        wanted = callsign.strip().upper()
        return next((entry for entry in self.traffic() if entry.callsign == wanted), None)

    def close(self) -> None:
        self._registry.close()
        closer = getattr(self._session, "close", None)
        if callable(closer):
            closer()
