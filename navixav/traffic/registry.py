"""Registre ICAO24 → type et exploitant, pour le trafic réel ADS-B.

Le flux d'états d'OpenSky ne porte pas le type de l'appareil. Sans lui aucun
modèle FSLTL ne peut être choisi, et le trafic réel resterait visible sur la
carte sans jamais entrer dans le simulateur.

OpenSky publiait ce lien, puis a retiré l'interrogation par adresse : elle
répond aujourd'hui 410. Deux registres publics la rendent, et leurs couvertures
ne se recouvrent pas — l'un connaît des planeurs que l'autre ignore, l'autre des
ULM absents du premier. Ils sont donc interrogés l'un après l'autre, et la
première réponse portant un code OACI l'emporte.

L'adresse est gravée dans le transpondeur : la réponse ne change pas. Elle est
conservée sur disque une fois pour toutes, et un vol ne coûte qu'une résolution
par appareil jamais rencontré. Les résolutions partent d'un fil dédié : le
relevé du trafic ne doit jamais attendre le réseau, quitte à ce qu'un appareil
inconnu n'entre dans le simulateur qu'au cycle suivant.
"""

from __future__ import annotations

import logging
import queue
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from navixav.paths import user_data_path

LOGGER = logging.getLogger(__name__)

USER_AGENT = "NaviXav/0.1 (local non-commercial flight simulation tool)"
DEFAULT_TIMEOUT = 8
DATABASE_NAME = "traffic_registry.sqlite"

# Une adresse restée sans réponse ne doit pas être redemandée à chaque vol :
# beaucoup d'appareils n'ont tout simplement pas de fiche. Elle est réessayée
# assez tard pour que le registre ait pu s'enrichir entre-temps.
UNKNOWN_RETRY_S = 30 * 24 * 3600.0

# Le registre est une courtoisie, pas un service dû : les demandes sont
# espacées, et une file pleine est vidée de ses plus anciennes plutôt que de
# faire enfler la mémoire quand le réseau ne suit pas.
MIN_INTERVAL_S = 0.5
MAX_PENDING = 500


@dataclass(frozen=True)
class AircraftIdentity:
    """Ce que le registre sait d'une adresse, éventuellement rien."""

    icao24: str
    aircraft_type: str = ""
    airline_icao: str = ""

    @property
    def known(self) -> bool:
        return bool(self.aircraft_type)


def _clean(value: object, maximum: int) -> str:
    return str(value or "").strip().upper()[:maximum]


def _from_hexdb(payload: dict) -> tuple[str, str]:
    return (
        _clean(payload.get("ICAOTypeCode"), 8),
        _clean(payload.get("OperatorFlagCode"), 4),
    )


def _from_adsbdb(payload: dict) -> tuple[str, str]:
    aircraft = payload.get("response")
    aircraft = aircraft.get("aircraft") if isinstance(aircraft, dict) else None
    if not isinstance(aircraft, dict):
        return "", ""
    return (
        _clean(aircraft.get("icao_type"), 8),
        _clean(aircraft.get("registered_owner_operator_flag_code"), 4),
    )


# L'ordre compte peu, la complémentarité seule importe : un appareil absent du
# premier registre est demandé au second, et une adresse trop récente pour les
# deux repart simplement sans type.
SOURCES = (
    ("hexdb", "https://hexdb.io/api/v1/aircraft/{icao24}", _from_hexdb),
    ("adsbdb", "https://api.adsbdb.com/v0/aircraft/{icao24}", _from_adsbdb),
)


class AircraftRegistry:
    """Cache persistant des identités, alimenté sans bloquer l'appelant."""

    def __init__(
        self,
        path: Path | None = None,
        session: requests.Session | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        min_interval_s: float = MIN_INTERVAL_S,
    ) -> None:
        self._path = Path(path) if path else user_data_path(DATABASE_NAME)
        self._session = session or requests.Session()
        self._timeout = timeout
        self._min_interval_s = min_interval_s
        self._lock = threading.Lock()
        self._pending: queue.Queue[str] = queue.Queue(maxsize=MAX_PENDING)
        self._queued: set[str] = set()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None
        self._connection: sqlite3.Connection | None = None
        self._open()

    # ------------------------------------------------------------ stockage

    def _open(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(
                self._path, check_same_thread=False, timeout=5.0
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS aircraft ("
                " icao24 TEXT PRIMARY KEY,"
                " aircraft_type TEXT NOT NULL,"
                " airline_icao TEXT NOT NULL,"
                " resolved_at REAL NOT NULL)"
            )
            connection.commit()
        except (OSError, sqlite3.Error) as exc:
            # Un cache impossible n'éteint pas le trafic réel : il le prive
            # seulement de sa mémoire d'un vol à l'autre.
            LOGGER.warning("Registre des appareils indisponible : %s", exc)
            self._connection = None
            return
        self._connection = connection

    def lookup(self, icao24: str) -> AircraftIdentity | None:
        """Identité déjà connue, sans jamais toucher au réseau."""
        key = icao24.strip().lower()
        if not key or self._connection is None:
            return None
        with self._lock:
            try:
                row = self._connection.execute(
                    "SELECT aircraft_type, airline_icao, resolved_at"
                    " FROM aircraft WHERE icao24 = ?",
                    (key,),
                ).fetchone()
            except sqlite3.Error:
                return None
        if row is None:
            return None
        aircraft_type, airline_icao, resolved_at = row
        if not aircraft_type and time.time() - resolved_at > UNKNOWN_RETRY_S:
            return None
        return AircraftIdentity(key, aircraft_type, airline_icao)

    def _store(self, identity: AircraftIdentity) -> None:
        if self._connection is None:
            return
        with self._lock:
            try:
                self._connection.execute(
                    "INSERT INTO aircraft (icao24, aircraft_type, airline_icao,"
                    " resolved_at) VALUES (?, ?, ?, ?)"
                    " ON CONFLICT(icao24) DO UPDATE SET"
                    " aircraft_type = excluded.aircraft_type,"
                    " airline_icao = excluded.airline_icao,"
                    " resolved_at = excluded.resolved_at",
                    (
                        identity.icao24,
                        identity.aircraft_type,
                        identity.airline_icao,
                        time.time(),
                    ),
                )
                self._connection.commit()
            except sqlite3.Error as exc:
                LOGGER.info("Identité %s non conservée : %s", identity.icao24, exc)

    # ------------------------------------------------------- résolution

    def request(self, icao24: str) -> None:
        """Demande la résolution d'une adresse, sans attendre son résultat."""
        key = icao24.strip().lower()
        if not key:
            return
        with self._lock:
            if key in self._queued:
                return
            self._queued.add(key)
        try:
            self._pending.put_nowait(key)
        except queue.Full:
            with self._lock:
                self._queued.discard(key)
            return
        self._ensure_worker()

    def _ensure_worker(self) -> None:
        with self._lock:
            if self._worker is not None and self._worker.is_alive():
                return
            self._stop.clear()
            self._worker = threading.Thread(
                target=self._run, name="NaviXav-traffic-registry", daemon=True
            )
            worker = self._worker
        worker.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                key = self._pending.get(timeout=1.0)
            except queue.Empty:
                continue
            try:
                identity = self._fetch(key)
                if identity is not None:
                    self._store(identity)
            finally:
                with self._lock:
                    self._queued.discard(key)
                self._pending.task_done()
            self._stop.wait(self._min_interval_s)

    def _fetch(self, icao24: str) -> AircraftIdentity | None:
        """Interroge les registres jusqu'à obtenir un code OACI.

        Rend `None` tant qu'un registre n'a pas pu répondre : une panne de
        réseau ne doit pas se figer en « appareil inconnu » pour un mois. Ne
        rend une identité vide que si chacun a dit, lui, ne pas le connaître.
        """
        definitive = True
        for name, template, parse in SOURCES:
            try:
                response = self._session.get(
                    template.format(icao24=icao24),
                    timeout=self._timeout,
                    headers={"User-Agent": USER_AGENT},
                )
            except requests.RequestException as exc:
                LOGGER.debug("Registre %s injoignable pour %s : %s", name, icao24, exc)
                definitive = False
                continue
            if response.status_code == 404:
                continue
            if response.status_code != 200:
                LOGGER.debug(
                    "Registre %s a répondu %s pour %s", name, response.status_code, icao24
                )
                definitive = False
                continue
            try:
                payload = response.json()
            except ValueError:
                definitive = False
                continue
            if not isinstance(payload, dict):
                definitive = False
                continue
            aircraft_type, airline_icao = parse(payload)
            if aircraft_type:
                # Sur un appareil privé, ces registres recopient le code du
                # type dans le champ exploitant. Le garder ferait chercher une
                # compagnie qui n'existe pas, là où le type seul suffit.
                if airline_icao == aircraft_type:
                    airline_icao = ""
                return AircraftIdentity(icao24, aircraft_type, airline_icao)
        # Toutes les sources ont répondu qu'elles ne connaissaient pas cette
        # adresse : la retenir vide évite de la redemander à chaque vol.
        return AircraftIdentity(icao24) if definitive else None

    def close(self) -> None:
        self._stop.set()
        worker = self._worker
        if worker is not None and worker is not threading.current_thread():
            worker.join(timeout=2.0)
        self._worker = None
        closer = getattr(self._session, "close", None)
        if callable(closer):
            closer()
        with self._lock:
            if self._connection is not None:
                try:
                    self._connection.close()
                except sqlite3.Error:
                    pass
                self._connection = None
