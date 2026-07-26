"""Choix de la piste en service à partir du vent.

Le score combine composante de vent de face, pénalités de vent traversier et
arrière, longueur disponible et présence d'un ILS. Aucun de ces critères ne
remplace une configuration préférentielle publiée : le score sert à proposer,
pas à décider seul.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin
from typing import Sequence

from navixav.models import WindInfo
from navixav.navdata.base import Runway, normalise_runway

# Pondérations empiriques, volontairement lisibles plutôt que « réglées ».
TAILWIND_PENALTY = 6.0
CROSSWIND_PENALTY = 0.35
LENGTH_BONUS_PER_1000FT = 0.6
ILS_BONUS = 2.0
# Assez fort pour départager deux pistes parallèles, trop faible pour
# l'emporter sur une composante de vent défavorable.
PREFERENCE_BONUS = 3.0
HARD_LIMIT_PENALTY = 100.0


@dataclass
class RunwayScore:
    runway: Runway
    score: float
    headwind_kt: float
    crosswind_kt: float
    disqualified: bool = False
    preferred: bool = False
    notes: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.notes is None:
            self.notes = []

    @property
    def tailwind_kt(self) -> float:
        return max(0.0, -self.headwind_kt)


def wind_components(
    wind_direction_deg: float, wind_speed_kt: float, runway_heading_deg: float
) -> tuple[float, float]:
    """Retourne (composante de face, composante traversière absolue) en kt.

    Une composante de face négative correspond à du vent arrière.
    """
    angle = radians(wind_direction_deg - runway_heading_deg)
    return (wind_speed_kt * cos(angle), abs(wind_speed_kt * sin(angle)))


def score_runways(
    runways: list[Runway],
    wind: WindInfo,
    *,
    for_landing: bool,
    max_tailwind_kt: float = 10.0,
    max_crosswind_kt: float = 35.0,
    min_length_ft: float = 0.0,
    require_ils: bool = False,
    preferred: Sequence[str] = (),
) -> list[RunwayScore]:
    """Classe les pistes de la meilleure à la moins bonne.

    `preferred` liste les pistes de la configuration préférentielle de la
    plateforme, de la plus favorisée à la moins favorisée.
    """
    preference_rank = {
        normalise_runway(name): index for index, name in enumerate(preferred)
    }
    usable = [
        rwy
        for rwy in runways
        if (rwy.is_landing if for_landing else rwy.is_takeoff) or True
    ]

    # Vent utilisé pour le calcul : rafales incluses, plus conservateur.
    speed = float(wind.gust_kt or wind.speed_kt or 0)
    direction = wind.direction_deg

    results: list[RunwayScore] = []
    for rwy in usable:
        notes: list[str] = []
        disqualified = False

        if direction is None or speed == 0:
            headwind, crosswind = 0.0, 0.0
            if wind.variable:
                notes.append("vent variable : composantes non déterminantes")
            elif speed == 0:
                notes.append("vent calme")
            else:
                notes.append("direction du vent inconnue")
        else:
            headwind, crosswind = wind_components(direction, speed, rwy.heading_true_deg)

        score = headwind
        score -= CROSSWIND_PENALTY * crosswind
        if headwind < 0:
            score -= TAILWIND_PENALTY * min(-headwind, max_tailwind_kt)

        if min_length_ft and rwy.length_ft < min_length_ft:
            disqualified = True
            score -= HARD_LIMIT_PENALTY
            notes.append(f"piste plus courte que {min_length_ft:.0f} ft")

        if -headwind > max_tailwind_kt:
            disqualified = True
            score -= HARD_LIMIT_PENALTY
            notes.append(f"vent arrière {-headwind:.0f} kt > {max_tailwind_kt:.0f} kt")

        if crosswind > max_crosswind_kt:
            disqualified = True
            score -= HARD_LIMIT_PENALTY
            notes.append(f"vent traversier {crosswind:.0f} kt > {max_crosswind_kt:.0f} kt")

        score += LENGTH_BONUS_PER_1000FT * (rwy.length_ft / 1000.0)

        rank = preference_rank.get(rwy.name)
        is_preferred = rank is not None
        if is_preferred and not disqualified:
            score += PREFERENCE_BONUS / (rank + 1)
            notes.append("configuration préférentielle de la plateforme")

        if for_landing and rwy.has_ils:
            score += ILS_BONUS
        if require_ils and not rwy.has_ils:
            disqualified = True
            score -= HARD_LIMIT_PENALTY
            notes.append("pas d'ILS")

        results.append(
            RunwayScore(
                runway=rwy,
                score=score,
                headwind_kt=headwind,
                crosswind_kt=crosswind,
                disqualified=disqualified,
                preferred=is_preferred,
                notes=notes,
            )
        )

    results.sort(key=lambda r: (-r.score, r.runway.name))
    return results


def margin_between_best_two(scores: list[RunwayScore]) -> float:
    """Écart de score entre les deux meilleures pistes (0 si une seule)."""
    if len(scores) < 2:
        return float("inf")
    return scores[0].score - scores[1].score
