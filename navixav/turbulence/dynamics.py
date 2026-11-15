"""Rafales au spectre de Dryden, et ce qu'elles font à l'avion.

Le modèle de Dryden (MIL-F-8785C, MIL-HDBK-1797) décrit la turbulence
atmosphérique comme un bruit coloré dont l'échelle dépend de la hauteur et dont
la vitesse de défilement dépend de la vitesse vraie. L'avion n'y répond pas
tous de la même manière : la charge alaire et la masse volumique de l'air fixent
la variation de facteur de charge qu'une rafale verticale produit, avec le
facteur d'atténuation de Pratt retenu par la certification (CS-25.341).
Un A320 lourd en croisière secoue donc moins qu'un turbopropulseur léger
traversant la même turbulence.

MSFS ignore les accélérations écrites sur l'avion du joueur (mesuré en vol le
2026-11-14 : 1,5 rad/s² ne bougent rien). La vitesse verticale écrite, elle,
est prise telle quelle : chaque image lui ajoute le coup de la rafale, et
l'aérodynamique de l'avion l'amortit comme une vraie rafale.

Les vitesses de rotation ne sont PAS écrites : MSFS multiplie la valeur reçue
par environ 3,2, si bien que la réécrire à chaque image la fait diverger.
Essai du 2026-11-14 : l'avion est parti en piqué engagé en cinq images.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

G = 9.80665
FT = 0.3048
KT = 0.514444

# Échelle de turbulence (MIL-F-8785C) : 1 750 ft au-dessus de 2 000 ft, égale
# à la hauteur sous 1 000 ft, interpolée entre les deux.
HIGH_ALTITUDE_SCALE_M = 1750 * FT
LOW_ALTITUDE_M = 1000 * FT
MEDIUM_ALTITUDE_M = 2000 * FT
# Relation de Kolmogorov entre EDR, intensité et échelle : σ² ≈ 0,7·ε^(2/3)·L^(2/3).
KOLMOGOROV = 0.7
# Pente de portance d'une aile en flèche de transport, par radian.
LIFT_SLOPE = 5.0

# Valeurs par défaut d'un biréacteur moyen, si MSFS ne donne pas la sienne.
DEFAULT_SPAN_M = 34.0
DEFAULT_WING_AREA_M2 = 122.6
REFERENCE_SPAN_M = 34.0

# Accélération angulaire efficace (rad/s²) par g de variation de charge efficace.
# Réglés pour qu'une turbulence modérée en croisière fasse varier le tangage
# d'environ 1,5°/s et le roulis d'environ 2,5°/s, une fois l'amortissement
# aérodynamique de l'avion passé (≈ 0,25 s mesurés en vol).
PITCH_GAIN = 1.6
ROLL_GAIN = 2.4
YAW_GAIN = 0.9
# Bornes de sécurité : jamais au-delà, quelle que soit l'intensité demandée.
MAX_PITCH_ACC = 1.0
MAX_ROLL_ACC = 1.6
MAX_YAW_ACC = 0.6
# Rafale verticale, calée sur les définitions des intensités plutôt que sur la
# seule charge de rafale (trop forte à basse altitude, mesuré en vol) :
# écart-type ≈ 0,05 g en légère (EDR 0,11), 0,16 g en modérée (0,25),
# 0,4 g en sévère (0,5), soit des crêtes d'environ 0,15, 0,5 et 1,2 g.
HEAVE_PER_EDR = 2.4  # 0,97 visé × 2,5 : MSFS n’en restitue qu’environ 40 % (mesuré en vol)
HEAVE_EDR_EXPONENT = 1.3
MAX_HEAVE_ACC = 12.0  # m/s², soit 1,2 g
# Réponse mesurée de MSFS à une vitesse verticale écrite : elle passe telle quelle.
VERTICAL_WRITE_RESPONSE = 0.95

# Entrée et sortie d'une zone de turbulence : quelques secondes, pas un mur.
ONSET_S = 4.0


def scale_length_m(height_agl_m: float) -> float:
    if height_agl_m >= MEDIUM_ALTITUDE_M:
        return HIGH_ALTITUDE_SCALE_M
    if height_agl_m <= LOW_ALTITUDE_M:
        return max(10.0, height_agl_m)
    ratio = (height_agl_m - LOW_ALTITUDE_M) / (MEDIUM_ALTITUDE_M - LOW_ALTITUDE_M)
    return LOW_ALTITUDE_M + ratio * (HIGH_ALTITUDE_SCALE_M - LOW_ALTITUDE_M)


def vertical_gust_sigma(edr: float, scale_m: float) -> float:
    """Écart-type de la rafale verticale (m/s) pour un EDR et une échelle."""
    return math.sqrt(KOLMOGOROV) * max(0.0, edr) * scale_m ** (1.0 / 3.0)


def gust_alleviation(wing_loading_pa: float, density: float, chord_m: float) -> float:
    """Facteur de Pratt Kg = 0,88 μ / (5,3 + μ), μ le rapport de masse de l'avion."""
    mu = 2.0 * wing_loading_pa / (density * chord_m * LIFT_SLOPE * G)
    return 0.88 * mu / (5.3 + mu)


def load_factor_sigma(
    sigma_w: float, tas_mps: float, density: float, wing_loading_pa: float, chord_m: float
) -> float:
    """Variation efficace du facteur de charge, en g, due à la rafale verticale."""
    if wing_loading_pa <= 0 or density <= 0 or tas_mps <= 0:
        return 0.0
    kg = gust_alleviation(wing_loading_pa, density, chord_m)
    return kg * density * tas_mps * LIFT_SLOPE * sigma_w / (2.0 * wing_loading_pa)


@dataclass(frozen=True)
class Airframe:
    weight_kg: float
    wing_area_m2: float = DEFAULT_WING_AREA_M2
    span_m: float = DEFAULT_SPAN_M

    @property
    def wing_loading_pa(self) -> float:
        return self.weight_kg * G / self.wing_area_m2

    @property
    def chord_m(self) -> float:
        return self.wing_area_m2 / self.span_m


@dataclass(frozen=True)
class Motion:
    pitch: float
    roll: float
    yaw: float
    load_sigma_g: float
    # Accélération verticale de la rafale, en m/s².
    heave: float = 0.0

    def as_tuple(self) -> tuple[float, float, float]:
        return self.pitch, self.roll, self.yaw

    def kicks(self, dt: float) -> tuple[float]:
        """Coup à ajouter sur une image à la vitesse verticale (ft/s)."""
        return (self.heave * dt / VERTICAL_WRITE_RESPONSE / FT,)


class _Markov:
    """Processus de Gauss-Markov d'écart-type unité, constante de temps τ."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.value = 0.0

    def step(self, dt: float, tau: float) -> float:
        decay = math.exp(-dt / max(tau, 1e-3))
        self.value = self.value * decay + math.sqrt(max(0.0, 1.0 - decay * decay)) * self.rng.gauss(0.0, 1.0)
        return self.value


@dataclass
class GustField:
    rng: random.Random = field(default_factory=random.Random)
    edr: float = 0.0

    def __post_init__(self) -> None:
        self._w = _Markov(self.rng)
        self._pitch = _Markov(self.rng)
        self._roll = _Markov(self.rng)
        self._yaw = _Markov(self.rng)
        self._heave = _Markov(self.rng)

    def reset(self) -> None:
        self.edr = 0.0
        for process in (self._w, self._pitch, self._roll, self._yaw, self._heave):
            process.value = 0.0

    def step(
        self,
        dt: float,
        target_edr: float,
        tas_kt: float,
        height_agl_ft: float,
        density: float,
        airframe: Airframe,
        scale: float = 1.0,
    ) -> Motion:
        dt = min(max(dt, 0.0), 0.2)
        if dt <= 0:
            return Motion(0.0, 0.0, 0.0, 0.0)
        self.edr += (target_edr - self.edr) * (1.0 - math.exp(-dt / ONSET_S))

        tas = max(30.0, tas_kt * KT)
        length = scale_length_m(height_agl_ft * FT)
        sigma_w = vertical_gust_sigma(self.edr, length)
        load_sigma = load_factor_sigma(sigma_w, tas, density, airframe.wing_loading_pa, airframe.chord_m)

        # Temps de traversée d'un tourbillon : plus on va vite, plus les
        # secousses sont rapprochées. Borné pour rester entre 0,6 et 3 Hz environ.
        tau = min(0.8, max(0.15, 0.25 * length / tas))
        gust = self._w.step(dt, length / tas)
        span_factor = math.sqrt(REFERENCE_SPAN_M / max(5.0, airframe.span_m))

        # La rafale verticale lente donne le fond du mouvement en tangage, le
        # bruit rapide ses à-coups.
        pitch = PITCH_GAIN * load_sigma * (0.5 * gust + 0.85 * self._pitch.step(dt, tau)) * scale
        roll = ROLL_GAIN * load_sigma * span_factor * self._roll.step(dt, tau) * scale
        yaw = YAW_GAIN * load_sigma * span_factor * self._yaw.step(dt, 1.5 * tau) * scale
        # La rafale verticale elle-même : l'avion monte et descend d'un bloc.
        heave_sigma = HEAVE_PER_EDR * self.edr ** HEAVE_EDR_EXPONENT * G
        heave = heave_sigma * (0.6 * gust + 0.8 * self._heave.step(dt, 1.5 * tau)) * scale
        return Motion(
            _clip(pitch, MAX_PITCH_ACC),
            _clip(roll, MAX_ROLL_ACC),
            _clip(yaw, MAX_YAW_ACC),
            load_sigma * scale,
            _clip(heave, MAX_HEAVE_ACC),
        )


def _clip(value: float, bound: float) -> float:
    return max(-bound, min(bound, value))
