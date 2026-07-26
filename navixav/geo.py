"""Petits calculs géographiques (WGS84 approximé par une sphère)."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_NM = 3440.065


def distance_nm(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Distance orthodromique en milles nautiques."""
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = phi2 - phi1
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_NM * asin(min(1.0, sqrt(a)))
