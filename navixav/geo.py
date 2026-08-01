"""Petits calculs géographiques (WGS84 approximé par une sphère)."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_NM = 3440.065

# Allongement toléré par rapport à la route directe avant de tenir un point
# pour aberrant : la moitié de la distance, et jamais moins de 300 NM afin de
# laisser respirer les vols courts, dont le tracé réel dévie beaucoup.
CORRIDOR_FACTOR = 1.5
CORRIDOR_MARGIN_NM = 300.0

# En deçà, le vol est trop court — ou trop circulaire — pour que la géométrie
# dise quoi que ce soit d'utile : on ne juge pas.
CORRIDOR_MIN_REACH_NM = 50.0

# Éloignement maximal d'un repère de procédure à son terrain. Les plus longues
# transitions de STAR du monde restent très en deçà ; au-delà, c'est un
# homonyme d'une autre région, pas le repère que la procédure désigne.
TERMINAL_FIX_RADIUS_NM = 300.0

# Éloignement maximal d'un repère nommé d'après une piste — « CF02 », « FI21L »,
# « DER07 ». Ces noms se répètent d'un aérodrome à l'autre partout dans le
# monde : la tolérance couvre l'interception la plus lointaine, pas le terrain
# voisin.
AXIS_FIX_RADIUS_NM = 50.0


def distance_nm(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Distance orthodromique en milles nautiques."""
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = phi2 - phi1
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_NM * asin(min(1.0, sqrt(a)))


def near_direct_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
    position: tuple[float, float],
    planned_nm: float | None = None,
) -> bool:
    """Le point reste-t-il dans le couloir plausible de la route ?

    Un identifiant de repère n'est unique que dans sa région du monde : la
    base en contient des homonymes, et rien dans le plan de vol ne dit lequel
    est visé. Celui qui allongerait la route de plus de la moitié n'est pas
    celui-là, et le tracer produirait un aller-retour à travers le monde.

    `planned_nm` est la distance réellement prévue par le plan. Elle compte
    autant que la route directe : sur un aller-retour, les deux aérodromes se
    confondent et la route directe ne mesure plus rien, alors que le vol
    s'éloigne bel et bien. Sans elle ni distance directe exploitable, aucun
    point n'est écarté — on ne rejette pas faute d'information.
    """
    direct = distance_nm(*origin, *destination)
    reach = max(direct, float(planned_nm or 0.0))
    if reach < CORRIDOR_MIN_REACH_NM:
        return True
    budget = max(reach * CORRIDOR_FACTOR, reach + CORRIDOR_MARGIN_NM)
    detour = distance_nm(*origin, *position) + distance_nm(*position, *destination)
    return detour <= budget
