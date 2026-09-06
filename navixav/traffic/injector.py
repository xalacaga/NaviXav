"""Adaptateur SimConnect propriétaire des seuls objets créés par NaviXav."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable

from navixav.msfs.client import SimConnectClient, SimConnectError
from navixav.traffic.base import ResolvedAircraftModel, TrafficAircraft

LOGGER = logging.getLogger(__name__)

# Une seule variable suffit pour recenser les objets : le relevé ne sert qu'à
# lire les ObjectID que le simulateur porte encore, jamais leur état.
LIVE_PROBE_VARIABLES = (("PLANE LATITUDE", "degrees"),)


@dataclass(frozen=True)
class OwnedAircraft:
    uid: str
    request_id: int
    object_id: int
    model_title: str


class SimConnectTrafficInjector:
    """Crée, met à jour et retire exclusivement ses propres ObjectID."""

    def __init__(self, client_factory: Callable[[], SimConnectClient] = SimConnectClient) -> None:
        self._client_factory = client_factory
        self._client: SimConnectClient | None = None
        self._owned: dict[str, OwnedAircraft] = {}
        self._positions: dict[str, dict[str, object]] = {}
        self._lock = threading.RLock()
        self._motion_lock = threading.RLock()
        self._motion_client: SimConnectClient | None = None
        self._motion_objects: dict[str, OwnedAircraft] = {}
        self._motion_positions: dict[str, dict[str, object]] = {}
        self._closed = False

    def animate(self, aircraft: TrafficAircraft) -> None:
        """Write motion on a separate connection, without a lifecycle wait."""
        with self._motion_lock:
            owned = self._motion_objects.get(aircraft.uid)
            if self._closed or owned is None:
                return
            position = self._position(aircraft)
            if self._motion_positions.get(aircraft.uid) == position:
                return
            if self._motion_client is None:
                self._motion_client = self._client_factory()
            try:
                self._motion_client.update_ai_aircraft(owned.object_id, **position)
            except SimConnectError:
                self._motion_client.close()
                self._motion_client = None
                self._motion_positions.clear()
                raise
            self._motion_positions[aircraft.uid] = position

    @property
    def owned(self) -> dict[str, OwnedAircraft]:
        with self._lock:
            return dict(self._owned)

    def _client_or_open(self) -> SimConnectClient:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    @staticmethod
    def _position(aircraft: TrafficAircraft) -> dict[str, object]:
        if any(value is None for value in (
            aircraft.altitude_ft, aircraft.heading_deg, aircraft.ground_speed_kt,
            aircraft.on_ground,
        )):
            raise ValueError("position AI incomplète")
        return {
            "latitude": aircraft.latitude,
            "longitude": aircraft.longitude,
            "altitude_ft": aircraft.altitude_ft,
            "heading_deg": aircraft.heading_deg,
            "airspeed_kt": aircraft.ground_speed_kt,
            "on_ground": aircraft.on_ground,
        }

    def upsert(self, aircraft: TrafficAircraft, model: ResolvedAircraftModel) -> OwnedAircraft:
        with self._lock:
            if self._closed:
                raise RuntimeError("Injecteur fermé")
            client = self._client_or_open()
            previous = self._owned.get(aircraft.uid)
            if previous and previous.model_title != model.title:
                self._remove_locked(aircraft.uid)
                previous = None
            position = self._position(aircraft)
            if previous is None:
                request_id, object_id = client.create_ai_aircraft(
                    model.title, aircraft.callsign, **position
                )
                previous = OwnedAircraft(
                    aircraft.uid, request_id, object_id, model.title
                )
                self._owned[aircraft.uid] = previous
                self._positions[aircraft.uid] = position
                with self._motion_lock:
                    self._motion_objects[aircraft.uid] = previous
                LOGGER.info(
                    "%s %s/%s → %s %s → %s",
                    aircraft.callsign, aircraft.aircraft_type or "?",
                    aircraft.airline_icao or "?", model.match_kind.value,
                    model.provider, model.title,
                )
            else:
                with self._motion_lock:
                    # Once animation owns movement, a slow sync result must not
                    # overwrite its newer position with a quarter-second step.
                    if (aircraft.uid not in self._motion_positions
                            and self._positions.get(aircraft.uid) != position):
                        client.update_ai_aircraft(previous.object_id, **position)
                        self._positions[aircraft.uid] = position
            return previous

    def reconcile(self, radius_m: int) -> list[str]:
        """Oublie les appareils que le simulateur ne porte plus.

        Un objet AI ne survit pas toujours à ce qui se passe autour de lui :
        rechargement d'un vol, changement de zone, relecture des paquets de la
        Communauté. SimConnect n'en avertit pas son propriétaire. Sans ce
        relevé, `_owned` garderait des ObjectID morts : les mises à jour
        suivantes passeraient sans erreur puisqu'elles ne lisent aucune
        réponse, plus rien ne serait recréé, et l'injection resterait vide
        sans que rien ne le signale. Les oublier suffit : le cycle qui suit
        les recrée.
        """
        with self._lock:
            if not self._owned:
                return []
            client = self._client_or_open()
            live = {
                int(row["object_id"])
                for row in client.read_objects(LIVE_PROBE_VARIABLES, radius_m)
                if "object_id" in row
            }
            if not live:
                # L'avion du joueur fait toujours partie de l'énumération : un
                # relevé vide est un relevé manqué, pas un simulateur vide.
                # Rien ne justifie alors d'oublier ce qui vole peut-être encore.
                return []
            lost = [
                uid for uid, owned in self._owned.items()
                if owned.object_id not in live
            ]
            for uid in lost:
                # Une énumération tronquée par son délai rendrait un objet
                # bien vivant pour disparu. Le supprimer avant de l'oublier
                # rend l'opération sûre dans les deux cas : sans effet s'il
                # n'existe plus, et sans laisser d'orphelin que plus personne
                # ne posséderait s'il existait encore.
                try:
                    self._remove_locked(uid)
                except SimConnectError:
                    pass
            if lost:
                LOGGER.info(
                    "%d appareil(s) AI disparu(s) du simulateur, à recréer", len(lost)
                )
            return lost

    def _remove_locked(self, uid: str) -> None:
        with self._motion_lock:
            self._motion_objects.pop(uid, None)
            self._motion_positions.pop(uid, None)
            owned = self._owned.pop(uid, None)
            self._positions.pop(uid, None)
            if owned is not None and self._client is not None:
                self._client.remove_ai_object(owned.object_id)

    def remove(self, uid: str) -> None:
        with self._lock:
            self._remove_locked(uid)

    def close(self) -> None:
        with self._lock:
            with self._motion_lock:
                self._closed = True
                self._motion_objects.clear()
                self._motion_positions.clear()
                if self._motion_client is not None:
                    self._motion_client.close()
                    self._motion_client = None
            for uid in list(self._owned):
                try:
                    self._remove_locked(uid)
                except SimConnectError as exc:
                    LOGGER.warning("Objet AI %s non retiré à la fermeture : %s", uid, exc)
            self._owned.clear()
            self._positions.clear()
            if self._client is not None:
                self._client.close()
                self._client = None
