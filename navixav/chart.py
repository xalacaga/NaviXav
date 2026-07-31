"""Plan de terrain : pistes, voies de circulation, postes de stationnement.

La géométrie est projetée en mètres locaux autour du point de référence de
l'aéroport (x vers l'est, y vers le nord). À l'échelle d'un aérodrome, une
projection équirectangulaire est exacte à quelques centimètres près et évite
toute dépendance cartographique.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from navixav.navdata.base import NavdataProvider

EARTH_RADIUS_M = 6378137.0
FEET_PER_METRE = 3.280839895


@dataclass(frozen=True)
class Projection:
    """Conversion latitude/longitude vers mètres locaux."""

    origin_lat: float
    origin_lon: float

    def to_xy(self, latitude: float, longitude: float) -> tuple[float, float]:
        x = (
            math.radians(longitude - self.origin_lon)
            * EARTH_RADIUS_M
            * math.cos(math.radians(self.origin_lat))
        )
        y = math.radians(latitude - self.origin_lat) * EARTH_RADIUS_M
        return (x, y)


def build_chart(
    provider: NavdataProvider, icao: str, highlight_runway: str | None = None
) -> dict[str, Any]:
    """Assemble le plan complet d'un aéroport depuis la base NaviXav."""
    airport = provider.airport(icao)
    if airport is None:
        raise LookupError(f"{icao.upper()} absent de la base de navigation.")

    projection = Projection(airport.lat, airport.lon)
    physical: dict[tuple[tuple[float, float], tuple[float, float]], dict] = {}
    for runway in provider.runways(airport.ident):
        start = projection.to_xy(runway.lat, runway.lon)
        length_m = runway.length_ft / FEET_PER_METRE
        heading = math.radians(runway.heading_true_deg)
        end = (
            start[0] + math.sin(heading) * length_m,
            start[1] + math.cos(heading) * length_m,
        )
        key = tuple(sorted((
            (round(start[0], -1), round(start[1], -1)),
            (round(end[0], -1), round(end[1], -1)),
        )))
        entry = physical.setdefault(key, {
            "id": len(physical) + 1,
            "start": _point(start),
            "end": _point(end),
            "width_m": round((runway.width_ft or 150) / FEET_PER_METRE, 1),
            "length_ft": round(runway.length_ft),
            "surface": runway.surface,
            "ends": [],
        })
        entry["ends"].append({
            "name": runway.name,
            "heading": round(runway.heading_true_deg, 1),
            "ils": runway.ils_ident,
            "threshold": _point(start),
        })

    connection = provider._conn  # noqa: SLF001 - cache interne NaviXav
    taxiways = []
    for row in connection.execute(
        """
        SELECT p.start_idx, p.end_idx, p.width_m, p.kind, p.name, p.runway_name,
               a.x AS start_x, a.y AS start_y, a.kind AS start_kind,
               b.x AS end_x, b.y AS end_y, b.kind AS end_kind
        FROM taxi_path p
        JOIN taxi_point a ON a.icao = ? AND a.idx = p.start_idx
        JOIN taxi_point b ON b.icao = ? AND b.idx = p.end_idx
        WHERE p.icao = ?
        """,
        (airport.ident, airport.ident, airport.ident),
    ).fetchall():
        taxiways.append({
            "name": row["name"],
            "kind": row["kind"],
            "runway": row["runway_name"],
            "width_m": row["width_m"],
            "start": _point((row["start_x"], row["start_y"])),
            "end": _point((row["end_x"], row["end_y"])),
            # Un point d'attente borne le segment : c'est là que s'arrête un
            # roulage sans autorisation de traverser ou de s'aligner.
            "hold_short": _hold_short(row["start_kind"], row["end_kind"]),
        })

    parkings = [{
        "label": row["label"],
        "kind": row["kind"] or "poste",
        "radius_m": row["radius_m"],
        "heading": row["heading"] or 0,
        "jetway": False,
        "position": _point((row["x"], row["y"])),
    } for row in connection.execute(
        "SELECT * FROM parking WHERE icao = ?", (airport.ident,)
    ).fetchall()]

    chart = {
        "icao": airport.ident,
        "name": airport.name,
        "origin": {"lat": airport.lat, "lon": airport.lon},
        "elevation_ft": airport.altitude_ft,
        "mag_var": airport.mag_var,
        "highlight_runway": highlight_runway,
        "runways": list(physical.values()),
        "taxiways": taxiways,
        "parkings": parkings,
    }
    chart["bounds"] = _bounds(chart)
    return chart


# --------------------------------------------------------------------------- #


def _point(xy: tuple[float, float]) -> dict[str, float]:
    return {"x": round(xy[0], 1), "y": round(xy[1], 1)}


def _hold_short(*kinds: str | None) -> bool:
    """Une des extrémités du segment est-elle un point d'attente ?

    Les variantes « no draw » comptent autant que les autres : elles ne sont pas
    peintes au sol, mais elles arrêtent le roulage de la même façon.
    """
    return any(kind and "hold_short" in kind for kind in kinds)


def _bounds(chart: dict[str, Any]) -> dict[str, float]:
    """Emprise du plan, avec une marge pour la mise à l'échelle initiale."""
    xs: list[float] = []
    ys: list[float] = []

    def add(point: dict[str, float]) -> None:
        xs.append(point["x"])
        ys.append(point["y"])

    for runway in chart["runways"]:
        add(runway["start"])
        add(runway["end"])
    for taxiway in chart["taxiways"]:
        add(taxiway["start"])
        add(taxiway["end"])
    for parking in chart["parkings"]:
        add(parking["position"])

    if not xs:
        return {"min_x": -500, "max_x": 500, "min_y": -500, "max_y": 500}

    margin = 120.0
    return {
        "min_x": min(xs) - margin,
        "max_x": max(xs) + margin,
        "min_y": min(ys) - margin,
        "max_y": max(ys) + margin,
    }
