"""Analyse de l'atterrissage, calculée au toucher.

L'interface interroge le simulateur une fois par seconde : bien trop peu pour
mesurer un toucher en échantillonnant la vitesse verticale. MSFS, lui, fige au
contact du sol la vitesse normale, la position, le tangage et l'inclinaison
(`PLANE TOUCHDOWN ...`). Ces valeurs font foi ; la dernière vitesse verticale
échantillonnée n'est qu'un repli, signalé comme tel.

Le toucher est rapporté à la piste réellement utilisée, retrouvée dans la base
de navigation : distance après le seuil, écart à l'axe, composantes de vent.
La stabilisation est jugée sur les relevés de la finale. Rien n'est inventé :
un critère que l'avion ou la base ne permettent pas d'évaluer reste inconnu
et sort de la note au lieu de la pénaliser.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from typing import Any

from navixav.live.base import AircraftState, TouchdownSample
from navixav.navdata.base import Runway

EARTH_RADIUS_M = 6_371_000.0
FEET_PER_METRE = 3.280_84

# Une finale commence sous cette hauteur ; repasser au-dessus l'efface.
APPROACH_CEILING_FT = 2500.0
# Un « atterrissage » sans finale observée est un rechargement ou un slew.
MIN_APPROACH_SAMPLES = 8
APPROACH_MAX_SAMPLES = 900
# Les rebonds sont comptés pendant ce délai après le premier contact.
BOUNCE_WINDOW_S = 15.0
# Au-delà de cette distance, la valeur figée décrit un autre toucher.
TOUCHDOWN_MAX_DISTANCE_M = 3000.0
# Une piste n'est retenue que si l'avion se trouve dans son prolongement.
RUNWAY_MAX_HEADING_DIFF_DEG = 30.0
RUNWAY_MARGIN_M = 30.0

# Zone de toucher : la marque de visée est à 300 m, la zone s'étend à 900 m.
TDZ_IDEAL_M = (150.0, 600.0)
TDZ_LIMIT_M = (60.0, 900.0)

# Seuils de la note de toucher, en ft/min.
GRADES = (
    (120.0, "soft"),
    (240.0, "smooth"),
    (400.0, "firm"),
    (600.0, "hard"),
)

# Points de chaque composante de la note sur 100.
RATE_POINTS = 40.0
CENTERLINE_POINTS = 20.0
TDZ_POINTS = 20.0
STABILITY_POINTS = 20.0
BOUNCE_PENALTY = 10.0
RATE_FULL_FPM = 200.0
RATE_ZERO_FPM = 700.0
CENTERLINE_FULL_M = 1.5


@dataclass(frozen=True)
class RunwayContact:
    """Le toucher rapporté à une extrémité de piste."""

    airport: str
    runway: str
    heading_true_deg: float
    length_m: float
    width_m: float
    distance_from_threshold_m: float
    centerline_offset_m: float


@dataclass
class LandingReport:
    """Ce que l'interface affiche, enregistre au carnet et partage."""

    id: int
    touched_down_at: str
    rate_fpm: float
    rate_source: str
    grade: str
    score: int
    score_parts: dict[str, float]
    pitch_deg: float | None = None
    bank_deg: float | None = None
    ground_speed_kt: float | None = None
    indicated_airspeed_kt: float | None = None
    headwind_kt: float | None = None
    crosswind_kt: float | None = None
    airport: str | None = None
    runway: str | None = None
    runway_length_m: float | None = None
    distance_from_threshold_m: float | None = None
    centerline_offset_m: float | None = None
    in_touchdown_zone: bool | None = None
    bounces: int = 0
    stability: dict[str, bool | None] = field(default_factory=dict)
    aircraft: str = ""
    final: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #


def grade_for_rate(rate_fpm: float) -> str:
    for limit, grade in GRADES:
        if rate_fpm <= limit:
            return grade
    return "very_hard"


def _local_offset_m(lat0: float, lon0: float, lat: float, lon: float) -> tuple[float, float]:
    """Est et nord, en mètres, du point par rapport à l'origine."""
    east = math.radians(lon - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
    north = math.radians(lat - lat0) * EARTH_RADIUS_M
    return east, north


def _distance_m(lat0: float, lon0: float, lat: float, lon: float) -> float:
    east, north = _local_offset_m(lat0, lon0, lat, lon)
    return math.hypot(east, north)


def _angle_diff(first: float, second: float) -> float:
    return abs((first - second + 180.0) % 360.0 - 180.0)


def locate_on_runway(
    latitude: float,
    longitude: float,
    heading_true_deg: float | None,
    runways: Iterable[tuple[str, Runway]],
) -> RunwayContact | None:
    """L'extrémité de piste sur laquelle l'avion vient de se poser.

    Chaque extrémité porte la position de son seuil et son cap vrai. L'avion
    doit se trouver sur la longueur de la piste, à l'intérieur de sa largeur
    élargie d'une marge, et rouler dans son sens : une piste parallèle ou
    l'extrémité opposée ne sont jamais retenues par erreur.
    """
    best: tuple[float, RunwayContact] | None = None
    for airport, runway in runways:
        if heading_true_deg is not None and _angle_diff(
            heading_true_deg, runway.heading_true_deg
        ) > RUNWAY_MAX_HEADING_DIFF_DEG:
            continue
        east, north = _local_offset_m(runway.lat, runway.lon, latitude, longitude)
        heading = math.radians(runway.heading_true_deg)
        along = east * math.sin(heading) + north * math.cos(heading)
        # Positif à droite de l'axe, dans le sens de l'atterrissage.
        cross = east * math.cos(heading) - north * math.sin(heading)
        length_m = runway.length_ft / FEET_PER_METRE
        width_m = (runway.width_ft or 150.0) / FEET_PER_METRE
        if not -RUNWAY_MARGIN_M <= along <= length_m:
            continue
        if abs(cross) > width_m / 2 + RUNWAY_MARGIN_M:
            continue
        contact = RunwayContact(
            airport=airport,
            runway=runway.name,
            heading_true_deg=runway.heading_true_deg,
            length_m=length_m,
            width_m=width_m,
            distance_from_threshold_m=along,
            centerline_offset_m=cross,
        )
        if best is None or abs(cross) < best[0]:
            best = (abs(cross), contact)
    return best[1] if best else None


def wind_components(
    wind_direction_deg: float | None,
    wind_speed_kt: float | None,
    runway_heading_deg: float,
) -> tuple[float | None, float | None]:
    """Vent de face (positif) et de travers (positif venant de droite)."""
    if wind_direction_deg is None or wind_speed_kt is None:
        return None, None
    angle = math.radians(wind_direction_deg - runway_heading_deg)
    return wind_speed_kt * math.cos(angle), wind_speed_kt * math.sin(angle)


def stability_checks(approach: list[AircraftState]) -> dict[str, bool | None]:
    """Critères de stabilisation, jugés sur les relevés de la finale.

    - `configured_1000` : train sorti et volets braqués à 1 000 ft sol, pour les
      seuls systèmes que l'avion possède ;
    - `sink_rate` : jamais plus de 1 000 ft/min de descente entre 1 000 et
      50 ft sol ;
    - `speed_stable` : vitesse indiquée tenue à 10 kt près sous 500 ft sol.
    """
    def height(state: AircraftState) -> float | None:
        return state.height_above_ground_ft

    below_1000 = [s for s in approach if height(s) is not None and 50 <= height(s) <= 1000]
    below_500 = [s for s in approach if height(s) is not None and 50 <= height(s) <= 500]

    configured: bool | None = None
    gate = below_1000[0] if below_1000 else None
    configuration = gate.configuration if gate else None
    if configuration is not None:
        capabilities = configuration.capabilities
        checks: list[bool] = []
        if capabilities is None or capabilities.retractable_gear:
            if configuration.gear_extended_pct is not None:
                checks.append(configuration.gear_extended_pct >= 99)
        if capabilities is None or capabilities.flaps:
            if configuration.flaps_handle_index is not None:
                checks.append(configuration.flaps_handle_index > 0)
        configured = all(checks) if checks else None

    sink_rates = [s.vertical_speed_fpm for s in below_1000 if s.vertical_speed_fpm is not None]
    sink_rate = (min(sink_rates) >= -1000) if len(sink_rates) >= 2 else None

    speeds = [s.indicated_airspeed_kt for s in below_500 if s.indicated_airspeed_kt is not None]
    speed_stable = (max(speeds) - min(speeds) <= 10) if len(speeds) >= 2 else None

    return {
        "configured_1000": configured,
        "sink_rate": sink_rate,
        "speed_stable": speed_stable,
    }


def score_landing(
    rate_fpm: float,
    contact: RunwayContact | None,
    stability: dict[str, bool | None],
    bounces: int,
) -> tuple[int, dict[str, float]]:
    """Note sur 100 et détail de chaque composante.

    Une composante inconnue (piste introuvable, critère non mesurable) sort de
    la note, qui est ramenée sur 100 avec ce qui reste.
    """
    parts: dict[str, float] = {}
    available = 0.0

    ratio = (RATE_ZERO_FPM - rate_fpm) / (RATE_ZERO_FPM - RATE_FULL_FPM)
    parts["rate"] = round(RATE_POINTS * max(0.0, min(1.0, ratio)), 1)
    available += RATE_POINTS

    if contact is not None:
        half_width = max(CENTERLINE_FULL_M + 1, contact.width_m / 2)
        offset = abs(contact.centerline_offset_m)
        ratio = (half_width - offset) / (half_width - CENTERLINE_FULL_M)
        parts["centerline"] = round(CENTERLINE_POINTS * max(0.0, min(1.0, ratio)), 1)
        available += CENTERLINE_POINTS

        distance = contact.distance_from_threshold_m
        if TDZ_IDEAL_M[0] <= distance <= TDZ_IDEAL_M[1]:
            parts["touchdown_zone"] = TDZ_POINTS
        elif TDZ_LIMIT_M[0] <= distance <= TDZ_LIMIT_M[1]:
            parts["touchdown_zone"] = TDZ_POINTS / 2
        else:
            parts["touchdown_zone"] = 0.0
        available += TDZ_POINTS

    known = [value for value in stability.values() if value is not None]
    if known:
        parts["stability"] = round(STABILITY_POINTS * sum(known) / len(known), 1)
        available += STABILITY_POINTS

    if bounces:
        parts["bounces"] = -BOUNCE_PENALTY * bounces

    total = sum(parts.values())
    score = round(100 * total / available) if available else 0
    return max(0, min(100, score)), parts


# --------------------------------------------------------------------------- #


RunwayLookup = Callable[[], Iterable[tuple[str, Runway]]]


class LandingMonitor:
    """Suit la finale et produit un rapport à chaque atterrissage.

    `observe` reçoit chaque relevé de position, éventuellement plusieurs fois :
    un relevé déjà vu est ignoré. Le rapport est publié dès le premier contact
    puis complété des rebonds éventuels ; il devient `final` une fois la fenêtre
    de rebond écoulée.
    """

    def __init__(
        self,
        runway_lookup: RunwayLookup,
        *,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self._lookup = runway_lookup
        self._clock = clock
        self._wall_clock = wall_clock
        self._lock = threading.Lock()
        self._approach: deque[AircraftState] = deque(maxlen=APPROACH_MAX_SAMPLES)
        self._previous: AircraftState | None = None
        self._report: LandingReport | None = None
        self._touched_at = 0.0
        self._bounce_airborne = False
        self._contact: RunwayContact | None = None
        self._sequence = 0

    def latest(self) -> dict[str, Any] | None:
        with self._lock:
            return self._report.to_dict() if self._report else None

    def observe(self, state: AircraftState) -> dict[str, Any] | None:
        with self._lock:
            if state is self._previous:
                return self._report.to_dict() if self._report else None
            previous, self._previous = self._previous, state
            if state.paused:
                return self._report.to_dict() if self._report else None
            now = self._clock()

            if self._report is not None and not self._report.final:
                self._track_bounce(state, now)

            if not state.on_ground:
                height = state.height_above_ground_ft
                if height is not None and height > APPROACH_CEILING_FT:
                    self._approach.clear()
                else:
                    self._approach.append(state)
            elif previous is not None and not previous.on_ground and (
                self._report is None or self._report.final
            ):
                self._touchdown(state, previous, now)
            return self._report.to_dict() if self._report else None

    # ------------------------------------------------------------------ #

    def _track_bounce(self, state: AircraftState, now: float) -> None:
        report = self._report
        assert report is not None
        if now - self._touched_at > BOUNCE_WINDOW_S:
            report.final = True
            self._approach.clear()
            return
        if not state.on_ground:
            if not self._bounce_airborne:
                self._bounce_airborne = True
                report.bounces += 1
                report.score, report.score_parts = score_landing(
                    report.rate_fpm,
                    self._contact,
                    report.stability,
                    report.bounces,
                )
        else:
            self._bounce_airborne = False

    def _touchdown(
        self, state: AircraftState, previous: AircraftState, now: float
    ) -> None:
        approach = list(self._approach)
        self._approach.clear()
        if len(approach) < MIN_APPROACH_SAMPLES:
            # Rechargement, slew ou glissement d'un appareil déjà au sol.
            return

        touchdown = _fresh_touchdown(state.touchdown, state)
        if touchdown is not None and touchdown.normal_velocity_fpm is not None:
            rate = abs(touchdown.normal_velocity_fpm)
            rate_source = "simulator"
        else:
            rate = abs(min(0.0, previous.vertical_speed_fpm or 0.0))
            rate_source = "sampled"

        latitude = touchdown.latitude if touchdown and touchdown.latitude is not None else state.latitude
        longitude = touchdown.longitude if touchdown and touchdown.longitude is not None else state.longitude
        heading = (
            touchdown.heading_true_deg
            if touchdown and touchdown.heading_true_deg is not None
            else state.heading_true_deg
        )
        try:
            runways = list(self._lookup())
        except Exception:  # pragma: no cover - la base reste facultative
            runways = []
        contact = locate_on_runway(latitude, longitude, heading, runways)
        self._contact = contact

        configuration = previous.configuration or state.configuration
        headwind = crosswind = None
        if contact is not None and configuration is not None:
            headwind, crosswind = wind_components(
                configuration.wind_direction_deg,
                configuration.wind_speed_kt,
                contact.heading_true_deg,
            )

        stability = stability_checks(approach)
        score, parts = score_landing(rate, contact, stability, 0)
        self._sequence += 1
        self._touched_at = now
        self._bounce_airborne = False
        self._report = LandingReport(
            id=self._sequence,
            touched_down_at=time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._wall_clock())
            ),
            rate_fpm=round(rate),
            rate_source=rate_source,
            grade=grade_for_rate(rate),
            score=score,
            score_parts=parts,
            pitch_deg=_rounded(touchdown.pitch_deg if touchdown else None, 1),
            bank_deg=_rounded(touchdown.bank_deg if touchdown else None, 1),
            ground_speed_kt=_rounded(previous.ground_speed_kt, 0),
            indicated_airspeed_kt=_rounded(previous.indicated_airspeed_kt, 0),
            headwind_kt=_rounded(headwind, 0),
            crosswind_kt=_rounded(crosswind, 0),
            airport=contact.airport if contact else None,
            runway=contact.runway if contact else None,
            runway_length_m=_rounded(contact.length_m if contact else None, 0),
            distance_from_threshold_m=_rounded(
                contact.distance_from_threshold_m if contact else None, 0
            ),
            centerline_offset_m=_rounded(
                contact.centerline_offset_m if contact else None, 1
            ),
            in_touchdown_zone=(
                TDZ_LIMIT_M[0] <= contact.distance_from_threshold_m <= TDZ_LIMIT_M[1]
                if contact else None
            ),
            stability=stability,
            aircraft=state.title,
        )


def _fresh_touchdown(
    touchdown: TouchdownSample | None, state: AircraftState
) -> TouchdownSample | None:
    """La valeur figée par MSFS, si elle décrit bien ce toucher-ci.

    MSFS garde le dernier toucher jusqu'au suivant : sans position pour le
    rapprocher de l'avion, rien ne prouve qu'il s'agit de celui-ci.
    """
    if touchdown is None or touchdown.latitude is None or touchdown.longitude is None:
        return None
    distance = _distance_m(state.latitude, state.longitude, touchdown.latitude, touchdown.longitude)
    return touchdown if distance <= TOUCHDOWN_MAX_DISTANCE_M else None


def _rounded(value: float | None, digits: int) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits) if digits else float(round(value))
