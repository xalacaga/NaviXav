"""Contrôle et trafic en ligne sur le réseau VATSIM.

Le réseau publie lui-même l'état de ses contrôleurs et de ses pilotes : ce
n'est ni un agrégateur ni un redistributeur, c'est la source. Le module en
tire deux relevés de nature différente, et la distinction commande tout le
reste.

Les postes tenus changent au rythme d'une relève : une minute de cache suffit.
Le trafic, lui, vaut ce que vaut sa fraîcheur — le flux est rafraîchi toutes
les quinze secondes, et c'est aussi la cadence que le réseau demande de ne pas
dépasser. En croisière, quinze secondes valent trois kilomètres et demi : la
carte en route s'en accommode. Au roulage elles valent cent cinquante mètres,
plus qu'une largeur de voie, et le plan de terrain ne doit donc jamais s'y
alimenter : au sol, c'est le simulateur qui dit la vérité, là où les clients
réseau injectent le trafic en direct.

Le module ne connaît pas les terrains : il rend les postes en ligne d'un
indicatif d'aérodrome, et c'est l'appelant qui décide de ce qu'il en fait.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import requests

from navixav.traffic.base import TrafficAircraft

LOGGER = logging.getLogger(__name__)

DATA_URL = "https://data.vatsim.net/v3/vatsim-data.json"

# Le flux principal ne porte pas la fréquence des pilotes : le réseau publie
# leurs émetteurs à part. Ce second relevé n'est téléchargé que lorsqu'un
# appareil est ouvert, et non pour survoler la carte.
TRANSCEIVERS_URL = "https://data.vatsim.net/v3/transceivers-data.json"
USER_AGENT = "NaviXav/0.1 (local flight simulation tool)"
DEFAULT_TIMEOUT = 10

# Le réseau demande de ne pas interroger le flux plus d'une fois par quart de
# minute. Savoir qui est en ligne ne réclame pas cette fraîcheur : une minute
# évite d'y revenir à chaque rafraîchissement de l'interface.
CACHE_TTL_S = 60.0

# Le trafic, lui, demande toute la fraîcheur que le réseau accepte de donner.
TRAFFIC_TTL_S = 15.0

# Plafond du relevé rendu à l'interface. Le réseau dépasse rarement le millier
# d'appareils connectés : la borne protège d'un flux inattendu, pas d'un
# dimanche soir chargé.
MAX_TRAFFIC = 3000

# Un observateur est connecté sans tenir de position. Le réseau le signale par
# une catégorie nulle et par cette fréquence, qui n'en est pas une.
OBSERVER_FACILITY = 0
OBSERVER_FREQUENCY = "199.998"

# Suffixes d'indicatif du réseau, traduits dans le vocabulaire radio de
# NaviXav. Ce sont les mêmes sigles que ceux tirés des Facilities MSFS, ce qui
# permet de rapprocher un poste en ligne d'une fréquence publiée sans table
# intermédiaire.
POSITIONS = {
    "DEL": "DEL",
    "GND": "GND",
    "TWR": "TWR",
    "APP": "APP",
    "DEP": "DEP",
    "CTR": "CTR",
    "FSS": "FSS",
    "ATIS": "ATIS",
}


class VatsimError(RuntimeError):
    """Flux VATSIM injoignable ou inexploitable."""


@dataclass(frozen=True)
class ControllerPosition:
    """Un poste tenu en ligne, tel que le réseau le déclare."""

    icao: str
    code: str
    callsign: str
    frequency_mhz: float
    name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "icao": self.icao,
            "code": self.code,
            "callsign": self.callsign,
            "frequency_mhz": self.frequency_mhz,
            "name": self.name,
        }


@dataclass(frozen=True)
class AircraftDetail:
    """Ce qu'on sait d'un appareil ouvert sur la carte.

    Le plan de vol déposé est repris tel que le pilote l'a écrit : ni corrigé,
    ni complété. Un terrain inconnu de la base reste affiché par son code, qui
    est déjà une information.
    """

    callsign: str
    pilot: str = ""
    aircraft: str = ""
    departure: str = ""
    arrival: str = ""
    altitude_ft: int = 0
    ground_speed_kt: int = 0
    heading_deg: int = 0
    transponder: str = ""
    frequency_mhz: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "callsign": self.callsign,
            "pilot": self.pilot,
            "aircraft": self.aircraft,
            "departure": self.departure,
            "arrival": self.arrival,
            "altitude_ft": self.altitude_ft,
            "ground_speed_kt": self.ground_speed_kt,
            "heading_deg": self.heading_deg,
            "transponder": self.transponder,
            "frequency_mhz": self.frequency_mhz,
        }


class VatsimClient:
    """Lecture du flux public, avec un cache court partagé par les appels."""

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        ttl_s: float = CACHE_TTL_S,
    ) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout
        self._ttl_s = ttl_s
        self._lock = threading.Lock()
        self._feed: dict[str, Any] | None = None
        self._fetched_at = 0.0
        self._transceivers: list[Any] | None = None
        self._transceivers_at = 0.0

    # ------------------------------------------------------------------ #

    def positions(self, icaos: Sequence[str]) -> dict[str, list[ControllerPosition]]:
        """Postes en ligne pour chaque aérodrome demandé.

        Un aérodrome sans contrôleur rend une liste vide plutôt que d'être
        absent : l'interface distingue ainsi « personne en ligne » de « la
        question n'a pas été posée ».
        """
        wanted = [icao.strip().upper() for icao in icaos if icao and icao.strip()]
        found: dict[str, list[ControllerPosition]] = {icao: [] for icao in wanted}
        if not wanted:
            return found

        feed = self._read()
        for position in _controllers(feed):
            for icao in wanted:
                if _serves(position.icao, icao):
                    found[icao].append(position)
        for entries in found.values():
            entries.sort(key=lambda entry: (entry.code, entry.frequency_mhz))
        return found

    @property
    def name(self) -> str:
        return "VATSIM"

    def traffic(self, limit: int | None = MAX_TRAFFIC) -> list[TrafficAircraft]:
        """Appareils connectés au réseau, du plus récent relevé.

        Le relevé est rendu entier plutôt que découpé autour d'un point : la
        carte se déplace librement, et un filtrage côté service la laisserait
        vide dès qu'on regarde ailleurs que son propre avion. Quelques
        centaines de positions tiennent dans une réponse locale ; c'est
        l'affichage qui écarte ce qui sort du cadre.
        """
        feed = self._read(max_age_s=TRAFFIC_TTL_S)
        aircraft: list[TrafficAircraft] = []
        for raw in feed.get("pilots") or ():
            entry = _aircraft(raw)
            if entry is None:
                continue
            aircraft.append(entry)
            if limit is not None and len(aircraft) >= limit:
                break
        return aircraft

    def close(self) -> None:
        closer = getattr(self._session, "close", None)
        if callable(closer):
            closer()

    def detail(self, callsign: str) -> AircraftDetail | None:
        """Fiche d'un appareil, ou rien s'il a quitté le réseau.

        La fréquence est cherchée dans un second relevé, celui des émetteurs.
        Son absence n'annule pas la fiche : un pilote qui n'a pas encore réglé
        sa radio reste un appareil dont on veut lire la route.
        """
        wanted = callsign.strip().upper()
        if not wanted:
            return None

        for raw in self._read(max_age_s=TRAFFIC_TTL_S).get("pilots") or ():
            if not isinstance(raw, dict):
                continue
            if str(raw.get("callsign") or "").strip().upper() != wanted:
                continue
            plan = raw.get("flight_plan")
            plan = plan if isinstance(plan, dict) else {}
            return AircraftDetail(
                callsign=wanted,
                pilot=str(raw.get("name") or "").strip(),
                aircraft=str(plan.get("aircraft_short") or "").strip().upper(),
                departure=str(plan.get("departure") or "").strip().upper(),
                arrival=str(plan.get("arrival") or "").strip().upper(),
                altitude_ft=int(_number(raw.get("altitude")) or 0),
                ground_speed_kt=int(_number(raw.get("groundspeed")) or 0),
                heading_deg=int(_number(raw.get("heading")) or 0) % 360,
                transponder=str(raw.get("transponder") or "").strip(),
                frequency_mhz=self._frequency(wanted),
            )
        return None

    def updated_at(self) -> str:
        """Horodatage que le réseau donne à son propre relevé."""
        feed = self._read()
        general = feed.get("general") or {}
        return str(general.get("update_timestamp") or "")

    # ------------------------------------------------------------------ #

    def _frequency(self, callsign: str) -> float | None:
        try:
            entries = self._read_transceivers()
        except VatsimError as exc:
            # La fiche vaut mieux sans sa fréquence que pas de fiche du tout.
            LOGGER.info("Émetteurs VATSIM indisponibles : %s", exc)
            return None
        for raw in entries:
            if not isinstance(raw, dict):
                continue
            if str(raw.get("callsign") or "").strip().upper() == callsign:
                return _first_frequency(raw)
        return None

    def _read_transceivers(self) -> list[Any]:
        with self._lock:
            now = time.monotonic()
            if (
                self._transceivers is not None
                and now - self._transceivers_at < TRAFFIC_TTL_S
            ):
                return self._transceivers
            try:
                response = self._session.get(
                    TRANSCEIVERS_URL,
                    timeout=self._timeout,
                    headers={"User-Agent": USER_AGENT},
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise VatsimError(f"Relevé des émetteurs injoignable : {exc}") from exc
            if not isinstance(payload, list):
                raise VatsimError("Relevé des émetteurs inattendu.")
            self._transceivers = payload
            self._transceivers_at = now
            return payload

    def _read(self, max_age_s: float | None = None) -> dict[str, Any]:
        """Flux courant, retéléchargé s'il a dépassé l'âge demandé.

        Un appelant peut exiger mieux que le cache par défaut — le trafic le
        fait — mais jamais moins : le cache est partagé, et une lecture de
        postes ne doit pas relancer le téléchargement que le trafic vient de
        faire.
        """
        ttl = self._ttl_s if max_age_s is None else min(self._ttl_s, max_age_s)
        with self._lock:
            now = time.monotonic()
            if self._feed is not None and now - self._fetched_at < ttl:
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
                raise VatsimError(f"Flux VATSIM injoignable : {exc}") from exc
            if not isinstance(payload, dict):
                raise VatsimError("Flux VATSIM inattendu.")
            self._feed = payload
            self._fetched_at = now
            return payload


def _first_frequency(entry: dict[str, Any]) -> float | None:
    """Première fréquence tenue par un appareil, en mégahertz.

    Le réseau les publie en hertz, et un appareil en déclare autant qu'il a de
    boîtiers. La première est celle qu'affiche la fiche : les suivantes sont
    des veilles, pas la fréquence sur laquelle on l'appelle.
    """
    for transceiver in entry.get("transceivers") or ():
        if not isinstance(transceiver, dict):
            continue
        hertz = _number(transceiver.get("frequency"))
        if hertz:
            return round(hertz / 1_000_000, 3)
    return None


def _controllers(feed: dict[str, Any]) -> Iterable[ControllerPosition]:
    """Postes exploitables du flux, contrôleurs et ATIS confondus.

    Le réseau publie les ATIS dans une liste distincte des contrôleurs. Pour
    un pilote c'est pourtant une position comme une autre, avec sa fréquence.
    """
    for key in ("controllers", "atis"):
        for raw in feed.get(key) or ():
            position = _position(raw)
            if position is not None:
                yield position


def _position(raw: Any) -> ControllerPosition | None:
    if not isinstance(raw, dict):
        return None
    callsign = str(raw.get("callsign") or "").strip().upper()
    frequency = str(raw.get("frequency") or "").strip()
    if not callsign or "_" not in callsign:
        return None

    # Un observateur n'assure aucun service : l'afficher ferait croire à un
    # contrôle qui n'existe pas.
    if frequency == OBSERVER_FREQUENCY:
        return None
    if raw.get("facility") == OBSERVER_FACILITY and "ATIS" not in callsign:
        return None

    parts = callsign.split("_")
    code = POSITIONS.get(parts[-1])
    if code is None:
        return None
    try:
        mhz = float(frequency)
    except ValueError:
        return None

    return ControllerPosition(
        icao=parts[0],
        code=code,
        callsign=callsign,
        frequency_mhz=mhz,
        name=str(raw.get("name") or "").strip(),
    )


def _aircraft(raw: Any) -> TrafficAircraft | None:
    """Un appareil exploitable du flux, ou rien.

    Un client qui vient de se connecter sans avoir chargé son vol se déclare
    par défaut à l'intersection de l'équateur et du méridien de Greenwich. Le
    laisser passer poserait un avion en plein golfe de Guinée.
    """
    if not isinstance(raw, dict):
        return None
    callsign = str(raw.get("callsign") or "").strip().upper()
    latitude = _number(raw.get("latitude"))
    longitude = _number(raw.get("longitude"))
    if not callsign or latitude is None or longitude is None:
        return None
    if abs(latitude) > 90 or abs(longitude) > 180:
        return None
    if latitude == 0.0 and longitude == 0.0:
        return None

    plan = raw.get("flight_plan")
    plan = plan if isinstance(plan, dict) else {}
    altitude = _number(raw.get("altitude"))
    heading = _number(raw.get("heading"))
    groundspeed = _number(raw.get("groundspeed"))
    vertical_speed = _number(raw.get("vertical_speed"))
    raw_on_ground = raw.get("on_ground")
    on_ground = (
        bool(raw_on_ground)
        if isinstance(raw_on_ground, (bool, int)) and raw_on_ground in (False, True, 0, 1)
        else None
    )
    airline_match = re.match(r"^([A-Z]{3})(?=\d)", callsign)
    return TrafficAircraft(
        uid=callsign,
        callsign=callsign,
        latitude=latitude,
        longitude=longitude,
        altitude_ft=altitude,
        heading_deg=heading % 360 if heading is not None else None,
        ground_speed_kt=groundspeed,
        vertical_speed_fpm=vertical_speed,
        on_ground=on_ground,
        aircraft_type=str(plan.get("aircraft_short") or "").strip().upper() or None,
        airline_icao=airline_match.group(1) if airline_match else None,
        departure=str(plan.get("departure") or "").strip().upper(),
        arrival=str(plan.get("arrival") or "").strip().upper(),
    )


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _serves(prefix: str, icao: str) -> bool:
    """L'indicatif d'un poste désigne-t-il cet aérodrome ?

    Les contrôleurs nord-américains abrègent couramment l'OACI de sa première
    lettre : « JFK_TWR » tient KJFK, « YYZ_GND » tient CYYZ. Sans cette
    équivalence, la moitié d'un terrain canadien passerait pour non contrôlée.
    """
    if prefix == icao:
        return True
    return len(icao) == 4 and prefix == icao[1:]
