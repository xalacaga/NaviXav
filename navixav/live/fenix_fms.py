"""Lecture du plan de vol actif du FMGC Fenix.

Le Fenix A320 ne synchronise pas son plan avec le simulateur : les SimVars
``GPS …`` restent vides. Mais l'EFB Fenix est servi par une passerelle GraphQL
locale (``127.0.0.1:8083``) qui publie, entre autres références, le plan de
vol complet du FMGC en XML — segments restants à partir du point actif,
pseudo-points ``(T/C)``, ``(T/D)``, ``(LIM)``, ``(DECEL)`` compris, puis le
plan de dégagement.

Ce module ne fait que **lire**. La passerelle accepte des écritures ; aucune
n'est jamais émise d'ici. Il est aussi silencieux : passerelle absente, XML
malformé ou champ manquant donnent un plan indisponible, jamais une exception
vers l'interface. C'est une API interne de Fenix, non documentée, qui peut
changer à une mise à jour.

Le plan lu ici n'est jamais écrit dans le journal : c'est la route complète.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field, replace
from typing import Any

logger = logging.getLogger(__name__)

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 8083
GATEWAY_URL = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}/graphql"

# Références lues à chaque relevé. Toutes sont déclarées lisibles par la
# passerelle ; une référence absente revient nulle.
FMS_DATAREFS = (
    "fenix.ready",
    "aircraft.fms.origin",
    "aircraft.fms.destination",
    "aircraft.fms.alternate",
    "aircraft.fms.flightPhase",
    "aircraft.fms.flightPlanXml",
    "aircraft.fms.perf.takeOff.v1",
    "aircraft.fms.perf.takeOff.vr",
    "aircraft.fms.perf.takeOff.v2",
    "aircraft.fms.perf.takeOff.flaps",
    "aircraft.fms.perf.takeOff.flexTemp",
    "aircraft.fms.perf.takeOff.ths",
    "aircraft.weight.zfw",
    "aircraft.weight.gross",
    "aircraft.fuel.total.amount.kg",
    "fenix.cids.flightNumber",
    "aircraft.mcdu1.display",
    "aircraft.mcdu2.display",
)

# Codes de mise en forme de l'affichage MCDU : une lettre minuscule change la
# couleur ou la taille du texte qui suit, le texte lui-même est en capitales.
_MCDU_COLOURS = {
    "g": "green", "w": "white", "m": "magenta", "a": "amber",
    "c": "cyan", "y": "yellow", "r": "red",
}
_MCDU_SIZES = {"s": "small", "l": "large"}
_MCDU_GLYPHS = {"`": "\u00b0", "\u00a3": "\u2191", "\u00a2": "\u2193", "\u00a4": "\u25a1"}

# Un relevé au plus toutes les `MIN_INTERVAL_S` secondes ; sans passerelle, un
# nouveau test de connexion au plus toutes les `RETRY_INTERVAL_S` secondes.
MIN_INTERVAL_S = 2.0
RETRY_INTERVAL_S = 20.0

# Types de segments qui ne sont pas des points de la route.
_END_OF_ROUTE = {"endofflightplan"}
_END_OF_ALTERNATE = {"endofalternate"}
_DISCONTINUITY = {"disco"}
# Points sans repère publié : T-P d'un DIR TO, position présente (PPOS).
_PSEUDO_TYPES = {"turningpoint", "presentposition"}


@dataclass(frozen=True)
class FmsLeg:
    """Un segment du plan actif, tel que le FMGC le présente."""

    ident: str
    via: str
    lat: float | None
    lon: float | None
    distance_nm: float | None
    bearing_deg: float | None
    eta: str
    type: str
    # Pseudo-point du profil (T/C, T/D, LIM, DECEL…) : pas un repère publié.
    pseudo: bool
    # Vrai quand le FMGC affiche une discontinuité juste avant ce segment.
    after_discontinuity: bool = False


@dataclass(frozen=True)
class FmsPlan:
    """Le plan actif du FMGC, prêt à être servi à l'interface."""

    source: str
    phase: str
    origin: str
    destination: str
    alternate: str
    origin_runway: str
    destination_runway: str
    cruise_level_ft: int | None
    flight_number: str
    legs: list[FmsLeg] = field(default_factory=list)
    alternate_legs: list[FmsLeg] = field(default_factory=list)
    read_at: float = 0.0
    # Saisies et états lus à côté du plan : PERF TAKEOFF, masses, écrans MCDU.
    perf_takeoff: dict[str, Any] = field(default_factory=dict)
    weights: dict[str, Any] = field(default_factory=dict)
    mcdu: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["available"] = True
        destination = next(
            (leg for leg in self.legs if leg.type.lower() == "destination"), None
        )
        data["destination_eta"] = destination.eta if destination else ""
        # Comme la page F-PLN : la première ligne est le point FROM, déjà
        # séquencé ; le point actif (TO) est la deuxième.
        data["from"] = asdict(self.legs[0]) if self.legs else None
        data["active"] = asdict(self.legs[1]) if len(self.legs) > 1 else None
        data["toc"] = _profile_point(self.legs, "toc")
        data["tod"] = _profile_point(self.legs, "tod")
        data["speed_limit"] = _profile_point(self.legs, "lim")
        data["decel"] = _profile_point(self.legs, "decel")
        return data


def _profile_point(legs: list[FmsLeg], kind: str) -> dict[str, Any] | None:
    """Le pseudo-point T/C ou T/D, avec sa distance le long des segments.

    La distance du segment TO est celle de l'avion au point actif, tenue à
    jour par le FMGC ; celles des segments suivants vont de point en point.
    `to_distance_nm` est rendue à part : si le FMGC ne la donne pas,
    l'interface la remplace par la distance directe avion → point actif.
    """
    beyond_active_nm = 0.0
    for index, leg in enumerate(legs):
        if index > 1 and leg.distance_nm is not None:
            beyond_active_nm += leg.distance_nm
        if index >= 1 and leg.pseudo and leg_kind(leg) == kind and leg.lat is not None:
            return {
                "ident": leg.ident,
                "lat": leg.lat,
                "lon": leg.lon,
                "to_distance_nm": legs[1].distance_nm,
                "distance_from_active_nm": round(beyond_active_nm, 1),
                "index": index,
            }
    return None


def leg_kind(leg: FmsLeg) -> str | None:
    """Le pseudo-point que porte le segment : toc, tod, lim, decel ou None."""
    label = leg.ident.upper().replace(" ", "")
    kind = leg.type.lower()
    if "(T/D)" in label or "topofdescent" in kind:
        return "tod"
    if "(T/C)" in label or "topofclimb" in kind:
        return "toc"
    if "(LIM)" in label or "(SPDLIM)" in label or "speedlimit" in kind:
        return "lim"
    if "(DECEL)" in label or kind == "decel":
        return "decel"
    return None


# --------------------------------------------------------------------------- #
# Analyse du XML
# --------------------------------------------------------------------------- #


def parse_mcdu_display(text: str) -> dict[str, Any] | None:
    """L'écran d'un MCDU en segments (texte, couleur, taille), ligne par ligne.

    Les balises ``{S}…{/S}`` des vents sont lues comme du petit texte. Les
    glyphes propriétaires connus sont remplacés (degré, flèches, case) ; les
    autres passent tels quels.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    return {
        "title": _mcdu_segments(_text(root, "title")),
        "lines": [_mcdu_segments(node.text or "") for node in root.findall("line")],
        "scratchpad": _mcdu_segments(_text(root, "scratchpad")),
    }


def _mcdu_segments(raw: str) -> list[dict[str, str]]:
    segments: list[dict[str, str]] = []
    colour, size, buffer = "white", "large", []
    raw = raw.replace("{S}", "s").replace("{/S}", "l")

    def flush() -> None:
        if buffer:
            segments.append({"text": "".join(buffer), "color": colour, "size": size})
            buffer.clear()

    for char in raw:
        if char in _MCDU_COLOURS:
            flush()
            colour = _MCDU_COLOURS[char]
        elif char in _MCDU_SIZES:
            flush()
            size = _MCDU_SIZES[char]
        elif char.islower():
            continue
        else:
            buffer.append(_MCDU_GLYPHS.get(char, char))
    flush()
    return segments


def _text(node: ET.Element | None, name: str) -> str:
    child = node.find(name) if node is not None else None
    return (child.text or "").strip() if child is not None else ""


def _number(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _number_or_none(value: Any) -> float | None:
    """Un nombre de la passerelle, ou None pour une valeur absente ou nulle."""
    if isinstance(value, bool):
        return None
    number = _number(value) if isinstance(value, str) else (
        float(value) if isinstance(value, (int, float)) else None
    )
    return number if number else None


def parse_flight_plan_xml(text: str, *, phase: str = "", read_at: float = 0.0) -> FmsPlan | None:
    """Traduit le XML du FMGC en `FmsPlan`, ou None s'il ne décrit pas un plan."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    route = root.find("routeData/route")
    if route is None:
        return None

    legs: list[FmsLeg] = []
    alternate: list[FmsLeg] = []
    target = legs
    pending_discontinuity = False
    for node in route.findall("legs/leg"):
        leg_type = _text(node, "type")
        lowered = leg_type.lower()
        if lowered in _END_OF_ROUTE:
            target = alternate
            pending_discontinuity = False
            continue
        if lowered in _END_OF_ALTERNATE:
            break
        if lowered in _DISCONTINUITY:
            pending_discontinuity = True
            continue
        ident = _text(node, "displayString")
        lat = _number(_text(node, "latitude"))
        lon = _number(_text(node, "longitude"))
        # Le FMGC met 0/0 sur les lignes sans position ; ce n'est jamais un
        # point de route.
        if lat is not None and lon is not None and lat == 0 and lon == 0:
            lat = lon = None
        target.append(FmsLeg(
            ident=ident,
            via=_text(node, "via") or "DCT",
            lat=lat,
            lon=lon,
            distance_nm=_number(_text(node, "distance")),
            bearing_deg=_number(_text(node, "bearing")),
            eta=_text(node, "ETA"),
            type=leg_type,
            # Les pseudo-points sont entre parenthèses ; le T-P d'un DIR TO
            # n'en porte pas mais n'est pas davantage un repère publié.
            pseudo=(ident.startswith("(") and ident.endswith(")")) or lowered in _PSEUDO_TYPES,
            after_discontinuity=pending_discontinuity,
        ))
        pending_discontinuity = False

    cruise = _number(_text(root, "cruiseLevel"))
    return FmsPlan(
        source="fenix",
        phase=phase,
        origin=_text(route, "origin"),
        destination=_text(route, "destination"),
        alternate="",
        origin_runway=_text(route, "originRunway"),
        destination_runway=_text(route, "destinationRunway"),
        cruise_level_ft=int(cruise) if cruise else None,
        flight_number=_text(root, "routeData/flightNumber"),
        legs=legs,
        alternate_legs=alternate,
        read_at=read_at,
    )


# --------------------------------------------------------------------------- #
# Passerelle
# --------------------------------------------------------------------------- #


def gateway_listening(host: str = GATEWAY_HOST, port: int = GATEWAY_PORT) -> bool:
    """Vrai si un service écoute sur la passerelle (simple test TCP local)."""
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def read_datarefs(names: tuple[str, ...] = FMS_DATAREFS, timeout_s: float = 4.0) -> dict[str, Any]:
    """Une requête de lecture `dataRefs` ; les valeurs par nom."""
    body = json.dumps({
        "query": "query($names: [String!]!) { dataRef { dataRefs(names: $names) { name value } } }",
        "variables": {"names": list(names)},
    }).encode("utf-8")
    request = urllib.request.Request(
        GATEWAY_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(str(payload["errors"][0].get("message", "erreur GraphQL")))
    entries = (payload.get("data") or {}).get("dataRef", {}).get("dataRefs", [])
    return {entry["name"]: entry.get("value") for entry in entries}


class FenixFmsReader:
    """Relevé cadencé du plan FMGC, tolérant à l'absence du Fenix."""

    def __init__(self, reader=read_datarefs, listening=gateway_listening) -> None:
        self._read = reader
        self._listening = listening
        self._lock = threading.Lock()
        self._plan: FmsPlan | None = None
        self._last_read = 0.0
        self._next_probe = 0.0
        self._available = False

    def read(self) -> dict[str, Any]:
        """Le plan courant sous forme de dictionnaire, ou `available: False`."""
        with self._lock:
            now = time.monotonic()
            if now - self._last_read >= MIN_INTERVAL_S:
                self._refresh(now)
            if self._plan is None:
                return {"available": False, "source": "fenix", "reason": "gateway_unavailable" if not self._available else "no_plan"}
            return self._plan.to_dict()

    def _refresh(self, now: float) -> None:
        self._last_read = now
        if not self._available:
            if now < self._next_probe:
                return
            self._next_probe = now + RETRY_INTERVAL_S
            self._available = self._listening()
            if not self._available:
                self._plan = None
                return
        try:
            values = self._read()
        except (urllib.error.URLError, RuntimeError, OSError, ValueError) as exc:
            logger.info("Plan FMGC Fenix illisible (%s)", type(exc).__name__)
            self._available = False
            self._plan = None
            return
        xml = values.get("aircraft.fms.flightPlanXml") or ""
        plan = parse_flight_plan_xml(
            xml, phase=str(values.get("aircraft.fms.flightPhase") or ""), read_at=time.time()
        ) if xml else None
        if plan is None:
            self._plan = None
            return
        perf = {
            key: _number_or_none(values.get(f"aircraft.fms.perf.takeOff.{key}"))
            for key in ("v1", "vr", "v2", "flaps", "flexTemp", "ths")
        }
        weights = {
            "zfw_kg": _number_or_none(values.get("aircraft.weight.zfw")),
            "gross_kg": _number_or_none(values.get("aircraft.weight.gross")),
            "fuel_kg": _number_or_none(values.get("aircraft.fuel.total.amount.kg")),
        }
        mcdu = {}
        for unit in ("1", "2"):
            display = values.get(f"aircraft.mcdu{unit}.display")
            parsed = parse_mcdu_display(display) if display else None
            if parsed:
                mcdu[unit] = parsed
        self._plan = replace(
            plan,
            alternate=str(values.get("aircraft.fms.alternate") or ""),
            origin=plan.origin or str(values.get("aircraft.fms.origin") or ""),
            destination=plan.destination or str(values.get("aircraft.fms.destination") or ""),
            flight_number=plan.flight_number or str(values.get("fenix.cids.flightNumber") or ""),
            perf_takeoff=perf,
            weights=weights,
            mcdu=mcdu,
        )

    def close(self) -> None:
        """Rien à libérer : chaque relevé est une requête HTTP close."""
