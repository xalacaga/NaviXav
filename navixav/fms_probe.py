"""Sonde de diagnostic : ce que l'avion chargé expose de son FMS.

Deux canaux sont relevés, indépendamment l'un de l'autre :

* les SimVars ``GPS …`` de SimConnect, qui décrivent le plan de vol *du
  simulateur* — renseignées quand l'avionique de l'avion s'y synchronise
  (avions de série, WorkingTitle, FBW avec FP sync), vides sinon ;
* la passerelle locale de l'EFB Fenix (``http://127.0.0.1:8083/graphql``),
  qui publie des références de données ``dataRef`` — dont le plan de vol
  complet du FMGC en XML, l'affichage des MCDU et les vitesses de décollage.
  Elle n'existe que lorsque le Fenix A320 tourne.

La sonde ne fait que **lire**. La passerelle Fenix accepte aussi des
écritures ; la sonde n'en émet aucune et ne déclare aucune mutation.

Le relevé complet est écrit dans un fichier de diagnostic à part, jamais dans
le journal tournant : il contient la route entière, que le journal ne doit pas
recevoir.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from navixav.paths import user_data_path

FENIX_GATEWAY_HOST = "127.0.0.1"
FENIX_GATEWAY_PORT = 8083
FENIX_GATEWAY_URL = f"http://{FENIX_GATEWAY_HOST}:{FENIX_GATEWAY_PORT}/graphql"

# Références Fenix pertinentes pour le suivi de vol. Toutes sont déclarées
# lisibles par la passerelle ; celles qui manquent reviennent simplement nulles.
FENIX_FMS_DATAREFS = (
    "fenix.ready",
    "fenix.msfsVersion",
    "fenix.efb.aircraft.type",
    "simulator.aircraft.title",
    "simulator.connected",
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
    "aircraft.mcdu1.display",
    "aircraft.mcdu2.display",
    "aircraft.latitude",
    "aircraft.longitude",
    "aircraft.altitude",
    "aircraft.altitude.aboveGround",
    "aircraft.speed.ground",
    "aircraft.speed.ias",
    "aircraft.speed.mach",
    "aircraft.verticalspeed",
    "aircraft.ground",
    "aircraft.weight.gross",
    "aircraft.weight.zfw",
    "aircraft.fuel.total.amount.kg",
    "environment.wind.heading.magnetic",
    "environment.wind.speed",
    "environment.isadev",
    "fenix.efb.simbriefPlanImported",
    "fenix.cids.flightNumber",
)

# SimVars du plan de vol du simulateur. Chaque variable est lue seule : une
# variable refusée par SimConnect n'empêche pas de lire les autres.
GPS_NUMERIC_SIMVARS = (
    ("GPS IS ACTIVE FLIGHT PLAN", "Bool"),
    ("GPS IS ACTIVE WAY POINT", "Bool"),
    ("GPS IS ACTIVE WP LOCKED", "Bool"),
    ("GPS IS DIRECTTO FLIGHTPLAN", "Bool"),
    ("GPS IS ARRIVED", "Bool"),
    ("GPS FLIGHT PLAN WP COUNT", "Number"),
    ("GPS FLIGHT PLAN WP INDEX", "Number"),
    ("GPS FLIGHTPLAN TOTAL DISTANCE", "Nautical miles"),
    ("GPS WP PREV VALID", "Bool"),
    ("GPS WP PREV LAT", "Degrees"),
    ("GPS WP PREV LON", "Degrees"),
    ("GPS WP PREV ALT", "Feet"),
    ("GPS WP NEXT LAT", "Degrees"),
    ("GPS WP NEXT LON", "Degrees"),
    ("GPS WP NEXT ALT", "Feet"),
    ("GPS WP DISTANCE", "Nautical miles"),
    ("GPS WP BEARING", "Degrees"),
    ("GPS WP TRUE BEARING", "Degrees"),
    ("GPS WP CROSS TRK", "Nautical miles"),
    ("GPS WP DESIRED TRACK", "Degrees"),
    ("GPS WP TRACK ANGLE ERROR", "Degrees"),
    ("GPS WP ETE", "Seconds"),
    ("GPS WP ETA", "Seconds"),
    ("GPS WP VERTICAL SPEED", "Feet per minute"),
    ("GPS ETE", "Seconds"),
    ("GPS ETA", "Seconds"),
    ("GPS TARGET DISTANCE", "Nautical miles"),
    ("GPS TARGET ALTITUDE", "Feet"),
    ("GPS VERTICAL ANGLE", "Degrees"),
    ("GPS VERTICAL ANGLE ERROR", "Degrees"),
    ("GPS VERTICAL ERROR", "Feet"),
    ("GPS HAS GLIDEPATH", "Bool"),
    ("GPS IS APPROACH LOADED", "Bool"),
    ("GPS IS APPROACH ACTIVE", "Bool"),
    ("GPS APPROACH MODE", "Number"),
    ("GPS APPROACH WP TYPE", "Number"),
    ("GPS APPROACH IS FINAL", "Bool"),
    ("GPS APPROACH IS MISSED", "Bool"),
    ("GPS APPROACH SEGMENT TYPE", "Number"),
    ("GPS APPROACH WP COUNT", "Number"),
    ("GPS APPROACH WP INDEX", "Number"),
    ("GPS OBS ACTIVE", "Bool"),
    ("GPS DRIVES NAV1", "Bool"),
    ("GPS POSITION LAT", "Degrees"),
    ("GPS POSITION LON", "Degrees"),
    ("GPS POSITION ALT", "Feet"),
    ("GPS GROUND SPEED", "Knots"),
)
GPS_STRING_SIMVARS = (
    "GPS WP NEXT ID",
    "GPS WP PREV ID",
    "GPS APPROACH AIRPORT ID",
    "GPS APPROACH APPROACH ID",
    "GPS APPROACH TRANSITION ID",
    "ATC FLIGHT NUMBER",
    "ATC ID",
    "TITLE",
)


def gateway_listening(host: str = FENIX_GATEWAY_HOST, port: int = FENIX_GATEWAY_PORT) -> bool:
    """Vrai si un service écoute sur la passerelle Fenix (test TCP local)."""
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _graphql(query: str, variables: dict[str, Any] | None = None, timeout_s: float = 10.0) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    request = urllib.request.Request(
        FENIX_GATEWAY_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(
            "; ".join(str(error.get("message")) for error in payload["errors"])
        )
    return payload.get("data") or {}


def probe_fenix_gateway() -> dict[str, Any]:
    """Relève l'inventaire des références Fenix et les valeurs du FMS."""
    report: dict[str, Any] = {
        "url": FENIX_GATEWAY_URL,
        "listening": gateway_listening(),
        "datarefs": [],
        "values": {},
        "error": None,
    }
    if not report["listening"]:
        return report
    try:
        listing = _graphql(
            "{ dataRef { list { name description canRead canWrite dataType dataUnit } } }"
        )
        report["datarefs"] = listing.get("dataRef", {}).get("list", [])
        readable = {
            entry["name"] for entry in report["datarefs"] if entry.get("canRead")
        }
        wanted = [name for name in FENIX_FMS_DATAREFS if not readable or name in readable]
        values = _graphql(
            "query($names: [String!]!) { dataRef { dataRefs(names: $names) { name value } } }",
            {"names": wanted},
        )
        report["values"] = {
            entry["name"]: entry.get("value")
            for entry in values.get("dataRef", {}).get("dataRefs", [])
        }
    except (urllib.error.URLError, RuntimeError, OSError, ValueError) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    return report


def probe_simconnect_gps() -> dict[str, Any]:
    """Lit une à une les SimVars du plan de vol du simulateur."""
    from navixav.msfs.client import SimConnectClient, SimConnectError

    report: dict[str, Any] = {"connected": False, "values": {}, "refused": [], "error": None}
    try:
        client = SimConnectClient()
    except SimConnectError as exc:
        report["error"] = str(exc)
        return report
    try:
        report["connected"] = True
        for name, unit in GPS_NUMERIC_SIMVARS:
            try:
                report["values"][name] = client.read_simvars([(name, unit)], timeout_s=1.5)[name]
            except SimConnectError as exc:
                report["refused"].append({"name": name, "reason": str(exc)})
        for name in GPS_STRING_SIMVARS:
            try:
                report["values"][name] = client.read_string_simvar(name, timeout_s=1.5)
            except SimConnectError as exc:
                report["refused"].append({"name": name, "reason": str(exc)})
    finally:
        client.close()
    return report


def probe_simbridge() -> dict[str, Any]:
    """SimBridge (FlyByWire) : présent ou non, et l'écran MCDU s'il répond."""
    from navixav.live.fbw_fms import FbwFmsReader, gateway_listening as simbridge_listening

    report: dict[str, Any] = {"listening": simbridge_listening(), "mcdu_units": [], "phase": ""}
    if not report["listening"]:
        return report
    reader = FbwFmsReader()
    try:
        state = reader.read()
    finally:
        reader.close()
    if state.get("available"):
        report["mcdu_units"] = sorted(state.get("mcdu", {}))
        report["phase"] = state.get("phase", "")
    return report


def probe_pmdg_cdu() -> dict[str, Any]:
    """Zones CDU PMDG diffusées par SimConnect, famille par famille."""
    from navixav.live.pmdg_fms import CDU_AREAS, PmdgFmsReader

    reader = PmdgFmsReader()
    try:
        state = reader.read()
    finally:
        reader.close()
    return {
        "families_known": list(CDU_AREAS),
        "available": bool(state.get("available")),
        "family": state.get("aircraft_family"),
        "mcdu_units": sorted(state.get("mcdu", {})) if state.get("available") else [],
    }


def run_probe() -> dict[str, Any]:
    """Exécute tous les relevés et assemble le rapport complet."""
    return {
        "probed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fenix_gateway": probe_fenix_gateway(),
        "simbridge": probe_simbridge(),
        "pmdg_cdu": probe_pmdg_cdu(),
        "simconnect_gps": probe_simconnect_gps(),
    }


def write_report(report: dict[str, Any], directory: Path | None = None) -> Path:
    """Écrit le rapport dans le dossier de diagnostic et renvoie son chemin."""
    target_dir = directory or user_data_path("diagnostics")
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = target_dir / f"fms_probe_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def summarize(report: dict[str, Any]) -> list[str]:
    """Résumé lisible du rapport, sans la route ni les affichages complets."""
    lines: list[str] = []
    gateway = report.get("fenix_gateway", {})
    if not gateway.get("listening"):
        lines.append("Passerelle Fenix : absente (le Fenix A320 n'est pas chargé).")
    elif gateway.get("error"):
        lines.append(f"Passerelle Fenix : erreur — {gateway['error']}")
    else:
        values = gateway.get("values", {})
        readable = sum(1 for entry in gateway.get("datarefs", []) if entry.get("canRead"))
        lines.append(
            f"Passerelle Fenix : {len(gateway.get('datarefs', []))} références, "
            f"{readable} lisibles."
        )
        lines.append(
            f"  FMS : {values.get('aircraft.fms.origin') or '----'} -> "
            f"{values.get('aircraft.fms.destination') or '----'} "
            f"(ALTN {values.get('aircraft.fms.alternate') or '----'}), "
            f"phase {values.get('aircraft.fms.flightPhase') or '?'}"
        )
        xml = values.get("aircraft.fms.flightPlanXml") or ""
        lines.append(
            f"  Plan de vol XML : {len(xml)} caractères, "
            f"{xml.count('<leg>')} segment(s)."
            if xml else "  Plan de vol XML : vide."
        )
        lines.append(
            "  Vitesses décollage : V1 "
            f"{values.get('aircraft.fms.perf.takeOff.v1')} / VR "
            f"{values.get('aircraft.fms.perf.takeOff.vr')} / V2 "
            f"{values.get('aircraft.fms.perf.takeOff.v2')}"
        )
        display = values.get("aircraft.mcdu1.display") or ""
        lines.append(
            f"  MCDU 1 : {display.count('<line>')} ligne(s) d'affichage."
            if display else "  MCDU 1 : affichage vide."
        )

    simbridge = report.get("simbridge", {})
    if not simbridge.get("listening"):
        lines.append("SimBridge FlyByWire : absent.")
    else:
        lines.append(
            f"SimBridge FlyByWire : présent, MCDU {simbridge.get('mcdu_units') or 'sans écran'}, "
            f"phase {simbridge.get('phase') or '?'}."
        )
    pmdg = report.get("pmdg_cdu", {})
    lines.append(
        f"CDU PMDG : {pmdg.get('family')} (MCDU {pmdg.get('mcdu_units')})."
        if pmdg.get("available") else "CDU PMDG : aucune diffusion (EnableCDUBroadcast ?)."
    )

    gps = report.get("simconnect_gps", {})
    if not gps.get("connected"):
        lines.append(f"SimConnect : indisponible — {gps.get('error')}")
    else:
        values = gps.get("values", {})
        lines.append(
            f"SimConnect GPS : {len(values)} variable(s) lue(s), "
            f"{len(gps.get('refused', []))} refusée(s)."
        )
        lines.append(
            f"  Plan actif : {bool(values.get('GPS IS ACTIVE FLIGHT PLAN'))}, "
            f"{int(values.get('GPS FLIGHT PLAN WP COUNT') or 0)} point(s), "
            f"index {int(values.get('GPS FLIGHT PLAN WP INDEX') or 0)}, "
            f"suivant '{values.get('GPS WP NEXT ID') or ''}' à "
            f"{float(values.get('GPS WP DISTANCE') or 0):.1f} NM."
        )
    return lines
