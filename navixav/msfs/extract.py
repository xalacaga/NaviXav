"""Extraction d'un aéroport complet depuis MSFS.

Les blocs arrivent à plat, dans l'ordre de parcours de l'arbre. On les recompose
en s'appuyant sur cet ordre : un bloc enfant appartient au dernier parent vu.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from navixav.msfs import fields as F
from navixav.msfs.client import (
    SimConnectClient,
    SimConnectRefused,
    FacilityDefinition,
    group_blocks,
)

LOGGER = logging.getLogger(__name__)

METRES_TO_FEET = 3.280839895


def airport_definition(with_taxi_names: bool = True) -> FacilityDefinition:
    """Définition couvrant tout ce dont NaviXav a besoin d'un aéroport.

    `with_taxi_names` permet de retirer le seul bloc que les versions plus
    anciennes du simulateur peuvent refuser ; voir `extract_airport`.
    """
    definition = FacilityDefinition()
    definition.open("AIRPORT", F.TYPE_AIRPORT, F.AIRPORT_FIELDS)

    definition.open("RUNWAY", F.TYPE_RUNWAY, F.RUNWAY_FIELDS).close()
    definition.open("FREQUENCY", F.TYPE_FREQUENCY, F.FREQUENCY_FIELDS).close()

    definition.open("APPROACH", F.TYPE_APPROACH, F.APPROACH_FIELDS)
    definition.open(
        "APPROACH_TRANSITION",
        F.TYPE_APPROACH_TRANSITION,
        F.APPROACH_TRANSITION_FIELDS,
    )
    definition.open("APPROACH_LEG", F.TYPE_APPROACH_LEG, F.LEG_FIELDS).close()
    definition.close()
    definition.open(
        "FINAL_APPROACH_LEG", F.TYPE_FINAL_APPROACH_LEG, F.LEG_FIELDS
    ).close()
    definition.open(
        "MISSED_APPROACH_LEG", F.TYPE_MISSED_APPROACH_LEG, F.LEG_FIELDS
    ).close()
    definition.close()

    for block, block_type in (("DEPARTURE", F.TYPE_DEPARTURE), ("ARRIVAL", F.TYPE_ARRIVAL)):
        definition.open(block, block_type, F.PROCEDURE_FIELDS)
        definition.open(
            "RUNWAY_TRANSITION",
            F.TYPE_RUNWAY_TRANSITION,
            F.RUNWAY_TRANSITION_FIELDS,
        )
        definition.open("APPROACH_LEG", F.TYPE_APPROACH_LEG, F.LEG_FIELDS).close()
        definition.close()
        definition.open(
            "ENROUTE_TRANSITION",
            F.TYPE_ENROUTE_TRANSITION,
            F.ENROUTE_TRANSITION_FIELDS,
        )
        definition.open("APPROACH_LEG", F.TYPE_APPROACH_LEG, F.LEG_FIELDS).close()
        definition.close()
        definition.open("APPROACH_LEG", F.TYPE_APPROACH_LEG, F.LEG_FIELDS).close()
        definition.close()

    definition.open("TAXI_POINT", F.TYPE_TAXI_POINT, F.TAXI_POINT_FIELDS).close()
    definition.open("TAXI_PARKING", F.TYPE_TAXI_PARKING, F.TAXI_PARKING_FIELDS).close()
    definition.open("TAXI_PATH", F.TYPE_TAXI_PATH, F.TAXI_PATH_FIELDS).close()
    if with_taxi_names:
        definition.open("TAXI_NAME", F.TYPE_TAXI_NAME, F.TAXI_NAME_FIELDS).close()

    return definition.close_all()


def extract_airport(client: SimConnectClient, icao: str) -> dict[str, Any]:
    """Récupère et recompose un aéroport.

    Un refus du simulateur invalide toute la définition, donc tout l'aéroport.
    Le bloc des noms de voies étant le seul dont la présence n'est pas acquise
    sur les versions antérieures, on réessaie une fois sans lui : mieux vaut un
    plan de terrain sans noms qu'aucune donnée du tout.
    """
    try:
        return _extract_airport(client, icao, with_taxi_names=True)
    except SimConnectRefused:
        LOGGER.warning(
            "Noms de voies de circulation refusés par le simulateur : "
            "nouvel essai sans eux"
        )
        return _extract_airport(client, icao, with_taxi_names=False)


def _extract_airport(
    client: SimConnectClient, icao: str, with_taxi_names: bool
) -> dict[str, Any]:
    definition = airport_definition(with_taxi_names)
    blocks = client.request(definition, icao)

    airport: dict[str, Any] = {
        "icao": icao.upper(),
        "runways": [],
        "frequencies": [],
        "approaches": [],
        "departures": [],
        "arrivals": [],
        "taxi_points": [],
        "taxi_parkings": [],
        "taxi_paths": [],
        "taxi_names": _taxi_names(blocks),
    }

    # Contexte courant : le dernier parent rencontré de chaque niveau.
    approach: dict[str, Any] | None = None
    procedure: dict[str, Any] | None = None
    transition: dict[str, Any] | None = None

    # Les noms sont déjà lus ci-dessus, sur la charge entière : les retirer des
    # dispositions évite que le découpage générique ne les redécoupe à tort.
    layouts = {
        block_type: fields
        for block_type, fields in definition.layouts.items()
        if block_type != F.TYPE_TAXI_NAME
    }

    for name, values in group_blocks(blocks, layouts):
        if name == "AIRPORT":
            airport.update(_airport(values))

        elif name == "RUNWAY":
            airport["runways"].append(_runway(values))

        elif name == "FREQUENCY":
            airport["frequencies"].append(
                {
                    "type": values["TYPE"],
                    "mhz": round(values["FREQUENCY"] / 1_000_000, 3),
                    "name": values["NAME"],
                }
            )

        elif name == "APPROACH":
            approach = _approach(values)
            airport["approaches"].append(approach)
            procedure = transition = None

        elif name == "APPROACH_TRANSITION":
            transition = {
                "ident": values["NAME"] or values.get("IAF_ICAO") or "",
                "iaf": values.get("IAF_ICAO") or None,
                "iaf_altitude_ft": _feet(values.get("IAF_ALTITUDE")),
                "legs": [],
            }
            if approach is not None:
                approach["transitions"].append(transition)

        elif name in ("FINAL_APPROACH_LEG", "MISSED_APPROACH_LEG"):
            if approach is not None:
                key = "legs" if name == "FINAL_APPROACH_LEG" else "missed_legs"
                approach[key].append(_leg(values))

        elif name in ("DEPARTURE", "ARRIVAL"):
            procedure = {
                "ident": values["NAME"],
                "runway_transitions": [],
                "enroute_transitions": [],
                "legs": [],
            }
            airport["departures" if name == "DEPARTURE" else "arrivals"].append(procedure)
            approach = transition = None

        elif name == "RUNWAY_TRANSITION":
            # Une transition de piste n'a pas de nom : elle EST la piste.
            transition = {
                "ident": F.runway_name(
                    values["RUNWAY_NUMBER"], values["RUNWAY_DESIGNATOR"]
                ),
                "legs": [],
            }
            if procedure is not None:
                procedure["runway_transitions"].append(transition)

        elif name == "ENROUTE_TRANSITION":
            transition = {"ident": values.get("NAME", ""), "legs": []}
            if procedure is not None:
                procedure["enroute_transitions"].append(transition)

        elif name == "APPROACH_LEG":
            leg = _leg(values)
            if transition is not None:
                transition["legs"].append(leg)
            elif procedure is not None:
                procedure["legs"].append(leg)
            elif approach is not None:
                approach["legs"].append(leg)

        elif name == "TAXI_POINT":
            airport["taxi_points"].append(
                {"x": values["BIAS_X"], "y": values["BIAS_Z"], "type": values["TYPE"]}
            )
        elif name == "TAXI_PARKING":
            airport["taxi_parkings"].append(_parking(values))
        elif name == "TAXI_PATH":
            airport["taxi_paths"].append(
                {
                    "type": values["TYPE"],
                    "width_m": values["WIDTH"],
                    "start": values["START"],
                    "end": values["END"],
                    "name_index": values["NAME_INDEX"],
                    # Renseignée sur les segments de piste et de sortie : c'est
                    # elle qui rattache un point d'attente à la piste qu'il
                    # protège.
                    "runway": _path_runway(values),
                }
            )

    return airport


def _path_runway(values: dict[str, Any]) -> str | None:
    """Piste dont un segment fait partie, ou None s'il n'en fait pas partie.

    Seuls les segments de piste renseignent ces champs. Ailleurs ils ne sont
    pas remis à zéro, et le contrôle de plage ne suffit pas à s'en protéger :
    un reste de mémoire tombe parfois entre 1 et 36 et désignerait une piste
    inexistante au beau milieu d'une voie de circulation.
    """
    if values.get("TYPE") != F.TAXI_PATH_TYPE_RUNWAY:
        return None
    number = values.get("RUNWAY_NUMBER") or 0
    if not 1 <= number <= 36:
        return None
    return F.runway_name(number, values.get("RUNWAY_DESIGNATOR", 0))


def _taxi_names(blocks: Sequence[tuple[int, int, bytes]]) -> list[str]:
    """Noms de voies, dans l'ordre où les segments les indexent.

    Le bloc ne portant qu'une chaîne, elle est lue sur toute la charge plutôt
    que sur une taille supposée : l'extraction reste juste même si le
    simulateur change la longueur du champ.
    """
    return [
        payload.split(b"\x00")[0].decode("utf-8", "replace").strip()
        for block_type, _index, payload in blocks
        if block_type == F.TYPE_TAXI_NAME
    ]


# --------------------------------------------------------------------------- #
# Conversions
# --------------------------------------------------------------------------- #


def _airport(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": values.get("NAME64", ""),
        "lat": values["LATITUDE"],
        "lon": values["LONGITUDE"],
        "altitude_ft": round(values["ALTITUDE"] * METRES_TO_FEET, 1),
        "transition_altitude_ft": _feet(values.get("TRANSITION_ALTITUDE")),
        "transition_level_ft": _feet(values.get("TRANSITION_LEVEL")),
        "counts": {
            key.lower(): values[key]
            for key in values
            if key.startswith("N_")
        },
    }


def _runway(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "primary": F.runway_name(values["PRIMARY_NUMBER"], values["PRIMARY_DESIGNATOR"]),
        "secondary": F.runway_name(
            values["SECONDARY_NUMBER"], values["SECONDARY_DESIGNATOR"]
        ),
        "lat": values["LATITUDE"],
        "lon": values["LONGITUDE"],
        "altitude_ft": round(values["ALTITUDE"] * METRES_TO_FEET, 1),
        "heading_true": round(values["HEADING"], 2),
        "length_ft": round(values["LENGTH"] * METRES_TO_FEET),
        "width_ft": round(values["WIDTH"] * METRES_TO_FEET),
        "surface": F.SURFACES.get(values["SURFACE"], str(values["SURFACE"])),
        "primary_ils": values.get("PRIMARY_ILS_ICAO") or None,
        "secondary_ils": values.get("SECONDARY_ILS_ICAO") or None,
    }


def _approach(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": F.APPROACH_TYPES.get(values["TYPE"], str(values["TYPE"])),
        "suffix": F.suffix_letter(values["SUFFIX"]),
        "runway": F.runway_name(values["RUNWAY_NUMBER"], values["RUNWAY_DESIGNATOR"]),
        "faf": values.get("FAF_ICAO") or None,
        "faf_altitude_ft": _feet(values.get("FAF_ALTITUDE")),
        "missed_altitude_ft": _feet(values.get("MISSED_ALTITUDE")),
        "transitions": [],
        "legs": [],
        "missed_legs": [],
    }


def _leg(values: dict[str, Any]) -> dict[str, Any]:
    speed = values.get("SPEED_LIMIT")
    return {
        "type": values["TYPE"],
        "fix": values.get("FIX_ICAO") or None,
        "region": values.get("FIX_REGION") or None,
        "course": round(values.get("COURSE", 0.0), 1),
        "distance_nm": round(values.get("DISTANCE_MINUTE", 0.0), 2),
        "altitude1_ft": _feet(values.get("ALTITUDE1")),
        "altitude2_ft": _feet(values.get("ALTITUDE2")),
        # -1 signale l'absence de limitation, pas une vitesse négative.
        "speed_limit_kt": int(speed) if speed and speed > 0 else None,
        "fly_over": bool(values.get("FLY_OVER")),
        "is_iaf": bool(values.get("IS_IAF")),
        "is_if": bool(values.get("IS_IF")),
        "is_faf": bool(values.get("IS_FAF")),
        "is_map": bool(values.get("IS_MAP")),
        "rnp": values.get("REQUIRED_NAVIGATION_PERFORMANCE") or None,
    }


def _parking(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "name_index": values["NAME"],
        "number": values["NUMBER"],
        "suffix": values["SUFFIX"],
        "type": values["TYPE"],
        "heading": round(values["HEADING"], 1),
        "radius_m": round(values["RADIUS"], 1),
        "x": values["BIAS_X"],
        "y": values["BIAS_Z"],
    }


def extract_navaid(
    client: SimConnectClient, ident: str, region: str = ""
) -> dict[str, Any] | None:
    """Installation radio : VOR, DME ou ILS. None si elle est inconnue."""
    definition = FacilityDefinition()
    definition.open("VOR", F.TYPE_VOR, F.NAVAID_FIELDS).close_all()
    try:
        blocks = client.request_raw(definition, ident, region, b"V", timeout_s=6)
    except Exception:
        return None

    for name, values in group_blocks(blocks, definition.layouts):
        if name != "VOR":
            continue
        return {
            "ident": ident.upper(),
            "region": region.upper(),
            "frequency_mhz": round(values["FREQUENCY"] / 1_000_000, 3) or None,
            "name": values.get("NAME", ""),
            "has_glide_slope": bool(values.get("HAS_GLIDE_SLOPE")),
            "has_dme": bool(values.get("IS_DME")),
            "localizer_course": round(values.get("LOCALIZER", 0.0), 1) or None,
            "glide_slope": round(values.get("GLIDE_SLOPE", 0.0), 2) or None,
            "lat": values.get("GS_LATITUDE") or None,
            "lon": values.get("GS_LONGITUDE") or None,
        }
    return None


def extract_waypoint(
    client: SimConnectClient, ident: str, region: str = ""
) -> dict[str, Any] | None:
    """Repère de navigation et routes aériennes qui le traversent."""
    definition = FacilityDefinition()
    definition.open("WAYPOINT", F.TYPE_WAYPOINT, F.WAYPOINT_FIELDS)
    definition.open("ROUTE", F.TYPE_ROUTE, F.ROUTE_FIELDS).close()
    definition.close_all()

    for type_char in (b"W", b"V", b"N"):
        try:
            blocks = client.request_raw(definition, ident, region, type_char, timeout_s=6)
        except Exception:
            continue

        waypoint: dict[str, Any] | None = None
        routes: list[dict[str, Any]] = []
        for name, values in group_blocks(blocks, definition.layouts):
            if name == "WAYPOINT":
                waypoint = {
                    "ident": ident.upper(),
                    "region": region.upper(),
                    "lat": values["LATITUDE"],
                    "lon": values["LONGITUDE"],
                    "routes": routes,
                }
            elif name == "ROUTE":
                routes.append(
                    {
                        "airway": values.get("NAME", ""),
                        "previous": values.get("PREV_ICAO") or None,
                        "previous_region": values.get("PREV_REGION") or None,
                        "next": values.get("NEXT_ICAO") or None,
                        "next_region": values.get("NEXT_REGION") or None,
                    }
                )
        if waypoint and (waypoint["lat"] or waypoint["lon"]):
            return waypoint
    return None


def _feet(metres: float | None) -> int | None:
    """Convertit en pieds ; 0 vaut « non renseigné » dans ces données."""
    if metres is None or metres <= 0:
        return None
    return round(metres * METRES_TO_FEET)
