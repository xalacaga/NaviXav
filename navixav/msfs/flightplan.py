"""Lecture d'un plan de vol MSFS (fichier `.PLN`).

Tout le monde ne prépare pas ses vols sur SimBrief. Le planificateur de MSFS
écrit un fichier XML `FlightPlan.FlightPlan` qui porte l'essentiel de ce dont
le moteur a besoin : terrains, altitude de croisière, points de la route avec
leur voie aérienne, noms de SID et de STAR, pistes prévues. Ce module le lit
et le présente sous la même forme normalisée que l'OFP SimBrief, si bien que
le moteur, les procédures et le suivi de vol n'ont pas à savoir d'où vient le
plan.

Ce qu'un `.PLN` ne contient pas — masses, carburant, météo, avion — reste
simplement vide : chaque champ de l'`OfpSummary` est déjà optionnel, et la
météo se prend en direct.

Rien n'est écrit ici : le fichier est lu, jamais modifié.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from navixav.simbrief.parser import DispatchSummary, NavlogFix, OfpSummary

logger = logging.getLogger(__name__)

PLAN_SOURCE_MSFS = "msfs"

# `N49° 0' 35.00",E2° 32' 52.00",+000392.00` tel que MSFS l'écrit. Le symbole
# degré peut manquer ou être remplacé selon l'outil qui a produit le fichier.
_DMS = re.compile(
    r"""(?P<hemisphere>[NSEW])\s*(?P<degrees>\d{1,3})\s*[°º]?\s*
        (?P<minutes>\d{1,2})\s*'?\s*(?P<seconds>\d{1,2}(?:\.\d+)?)\s*"?""",
    re.VERBOSE,
)

# `26`, `26R`, `08L` : une position de départ qui est une piste, pas un poste.
_RUNWAY = re.compile(r"^(?:RW)?(\d{1,2})([LRCW]?)$")

_DESIGNATORS = {"LEFT": "L", "RIGHT": "R", "CENTER": "C", "WATER": "W"}

_FIX_TYPES = {
    "airport": "apt",
    "intersection": "wpt",
    "vor": "vor",
    "ndb": "ndb",
    "user": "ltlg",
    "runway": "rwy",
}


class MsfsPlanError(RuntimeError):
    """Le fichier `.PLN` est absent ou ne décrit pas un vol exploitable."""


# --------------------------------------------------------------------------- #
# Où MSFS range le vol courant
# --------------------------------------------------------------------------- #


def _environment_path(variable: str, *parts: str) -> Path | None:
    root = os.getenv(variable, "").strip()
    return Path(root).joinpath(*parts) if root else None


def current_flight_candidates() -> list[Path]:
    """Emplacements MS Store et Steam du vol courant de MSFS 2024.

    MSFS y recopie le plan du dernier vol chargé depuis le planificateur, quel
    que soit l'endroit où l'utilisateur l'a lui-même enregistré.
    """
    candidates = [
        _environment_path(
            "LOCALAPPDATA", "Packages", "Microsoft.Limitless_8wekyb3d8bbwe",
            "LocalState", "MISSIONS", "Custom", "CustomFlight", "CustomFlight.PLN",
        ),
        _environment_path(
            "APPDATA", "Microsoft Flight Simulator 2024",
            "MISSIONS", "Custom", "CustomFlight", "CustomFlight.PLN",
        ),
    ]
    return [path for path in candidates if path is not None]


def current_flight_plan(candidates: list[Path] | None = None) -> Path | None:
    """Le vol courant le plus récent parmi les emplacements connus, s'il existe."""
    found: list[tuple[float, Path]] = []
    for path in candidates if candidates is not None else current_flight_candidates():
        try:
            if path.is_file():
                found.append((path.stat().st_mtime, path))
        except OSError:
            continue
    if not found:
        return None
    found.sort(reverse=True)
    return found[0][1]


# --------------------------------------------------------------------------- #
# Lecture
# --------------------------------------------------------------------------- #


def load_pln(path: Path | str) -> OfpSummary:
    """Lit un `.PLN` et le présente comme un OFP normalisé."""
    file = Path(path)
    try:
        text = file.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        raise MsfsPlanError(f"Plan de vol MSFS illisible : {file.name}") from exc
    summary = parse_pln(text, name=file.name)
    try:
        summary.generated_at = datetime.fromtimestamp(
            file.stat().st_mtime, tz=timezone.utc
        )
    except OSError:
        pass
    return summary


def parse_pln(text: str, *, name: str = "plan de vol") -> OfpSummary:
    """Construit l'`OfpSummary` d'un fichier `.PLN` déjà lu."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise MsfsPlanError(f"Plan de vol MSFS illisible : {name}") from exc

    plan = root.find(".//FlightPlan.FlightPlan")
    if plan is None:
        raise MsfsPlanError(
            f"{name} n'est pas un plan de vol MSFS (bloc FlightPlan.FlightPlan absent)."
        )

    origin = _text(plan, "DepartureID").upper()
    destination = _text(plan, "DestinationID").upper()
    origin_lat, origin_lon = _lat_lon(_text(plan, "DepartureLLA"))
    destination_lat, destination_lon = _lat_lon(_text(plan, "DestinationLLA"))

    waypoints = [_waypoint(node) for node in plan.findall("ATCWaypoint")]
    navlog = [fix for fix, _ in waypoints]

    # Les terrains figurent en tête et en queue du navlog ; s'ils manquent,
    # l'identifiant de tête reste la seule source.
    if not origin and navlog and navlog[0].fix_type == "apt":
        origin = navlog[0].ident
    if not destination and navlog and navlog[-1].fix_type == "apt":
        destination = navlog[-1].ident
    if origin_lat is None and navlog and navlog[0].fix_type == "apt":
        origin_lat, origin_lon = navlog[0].lat, navlog[0].lon
    if destination_lat is None and navlog and navlog[-1].fix_type == "apt":
        destination_lat, destination_lon = navlog[-1].lat, navlog[-1].lon

    if not origin or not destination:
        raise MsfsPlanError(
            f"{name} ne nomme pas à la fois un terrain de départ et d'arrivée."
        )

    # Les terrains portent parfois le nom de leur procédure ; le point de
    # raccord, lui, est un point de la procédure, jamais le terrain.
    sid_fixes = [
        fix for fix, meta in waypoints if meta["sid"] and fix.fix_type != "apt"
    ]
    star_fixes = [
        fix for fix, meta in waypoints if meta["star"] and fix.fix_type != "apt"
    ]
    sid = next((meta["sid"] for _, meta in waypoints if meta["sid"]), None)
    star = next((meta["star"] for _, meta in waypoints if meta["star"]), None)

    departure_runway = _runway_from_position(_text(plan, "DeparturePosition"))
    if departure_runway is None:
        departure_runway = next(
            (meta["runway"] for _, meta in waypoints if meta["sid"] and meta["runway"]),
            None,
        )
    arrival_runway = next(
        (
            meta["runway"]
            for _, meta in waypoints
            if meta["runway"] and (meta["approach"] or meta["star"])
        ),
        None,
    )
    if arrival_runway is None and waypoints and waypoints[-1][0].fix_type == "apt":
        # Le terrain d'arrivée lui-même porte parfois la piste de l'approche.
        arrival_runway = waypoints[-1][1]["runway"]

    summary = OfpSummary(
        origin_icao=origin,
        destination_icao=destination,
        cruise_altitude_ft=_int(_text(plan, "CruisingAlt")),
        origin_planned_runway=departure_runway,
        destination_planned_runway=arrival_runway,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        destination_lat=destination_lat,
        destination_lon=destination_lon,
        navlog=navlog,
        simbrief_sid=sid,
        simbrief_star=star,
        sid_exit_hint=sid_fixes[-1].ident if sid_fixes else None,
        star_entry_hint=star_fixes[0].ident if star_fixes else None,
        dispatch=DispatchSummary(),
        plan_source=PLAN_SOURCE_MSFS,
    )
    summary.route = _route_text(summary, sid, star)
    summary.plan_fingerprint = _plan_fingerprint(summary)
    return summary


def _plan_fingerprint(summary: OfpSummary) -> str:
    """Empreinte courte du plan : terrains, niveau et points, pas la date du fichier."""
    parts = [
        summary.origin_icao,
        summary.destination_icao,
        str(summary.cruise_altitude_ft or ""),
        summary.origin_planned_runway or "",
        summary.destination_planned_runway or "",
        *(fix.ident for fix in summary.navlog),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


def _waypoint(node: ET.Element) -> tuple[NavlogFix, dict[str, str | None]]:
    """Un `ATCWaypoint` et ce qu'il dit de la procédure qui le porte."""
    ident = (node.get("id") or _text(node, "ICAO/ICAOIdent")).strip().upper()
    raw_type = _text(node, "ATCWaypointType").strip().lower()
    lat, lon = _lat_lon(_text(node, "WorldPosition"))
    sid = _text(node, "DepartureFP").strip().upper() or None
    star = _text(node, "ArrivalFP").strip().upper() or None
    approach = _text(node, "ApproachTypeFP").strip().upper() or None
    number = _text(node, "RunwayNumberFP").strip()
    designator = _text(node, "RunwayDesignatorFP").strip().upper()
    runway = None
    if number.isdigit():
        runway = f"{int(number):02d}{_DESIGNATORS.get(designator, '')}"

    fix = NavlogFix(
        ident=ident,
        name=_text(node, "Descr").strip(),
        fix_type=_FIX_TYPES.get(raw_type, raw_type),
        via_airway=_text(node, "ATCAirway").strip().upper(),
        is_sid_star=bool(sid or star),
        lat=lat,
        lon=lon,
    )
    return fix, {"sid": sid, "star": star, "approach": approach, "runway": runway}


def _route_text(summary: OfpSummary, sid: str | None, star: str | None) -> str:
    """Route au format OACI : `LFPG ERIX5A ERIXU UN860 KOTIS DCT ABC LFBO`."""
    tokens = [summary.origin_icao]
    if sid:
        tokens.append(sid)
    airway = ""
    for leg in summary.enroute_route:
        via = leg["via"]
        if via != "DCT" and via != airway:
            tokens.append(via)
        elif via == "DCT" and airway:
            tokens.append("DCT")
        airway = "" if via == "DCT" else via
        tokens.append(leg["to"])
    if star:
        tokens.append(star)
    tokens.append(summary.destination_icao)
    return " ".join(tokens)


def _runway_from_position(value: str) -> str | None:
    """`DeparturePosition` est une piste ou un poste : seule la piste compte."""
    match = _RUNWAY.match(value.strip().upper())
    if not match:
        return None
    return f"{int(match.group(1)):02d}{match.group(2)}"


def _lat_lon(value: str) -> tuple[float | None, float | None]:
    lat: float | None = None
    lon: float | None = None
    for match in _DMS.finditer(value or ""):
        degrees = (
            int(match.group("degrees"))
            + int(match.group("minutes")) / 60
            + float(match.group("seconds")) / 3600
        )
        hemisphere = match.group("hemisphere")
        if hemisphere in "NS":
            lat = -degrees if hemisphere == "S" else degrees
        else:
            lon = -degrees if hemisphere == "W" else degrees
    if lat is None or lon is None or abs(lat) > 90 or abs(lon) > 180:
        return None, None
    return round(lat, 6), round(lon, 6)


def _text(node: ET.Element, path: str) -> str:
    child = node.find(path)
    return (child.text or "") if child is not None else ""


def _int(value: str) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
