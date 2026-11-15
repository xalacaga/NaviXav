"""Mouvement de la caméra : ressorts amortis et dérive organique.

Le lissage est un ressort à amortissement critique intégré exactement : pour
une cible fixe, deux pas de 10 ms ou un pas de 20 ms mènent au même point.
La caméra garde donc la même douceur à 30 comme à 120 images par seconde, et
ne dépasse jamais sa cible quand une image tarde.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass
class Spring:
    """Un axe : valeur et vitesse, rappelées vers la cible sans oscillation."""

    value: float = 0.0
    velocity: float = 0.0

    def snap(self, value: float) -> None:
        self.value = value
        self.velocity = 0.0

    def step(self, target: float, dt: float, omega: float) -> float:
        """Avance de `dt` secondes ; `omega` (rad/s) règle la vivacité.

        Solution exacte de x'' = -2ωx' - ω²(x - cible) : le temps de réponse
        vaut environ 4/ω, quelle que soit la découpe en images.
        """
        if dt <= 0.0:
            return self.value
        offset = self.value - target
        decay = math.exp(-omega * dt)
        carried = (self.velocity + omega * offset) * dt
        self.velocity = (self.velocity - omega * carried) * decay
        self.value = target + (offset + carried) * decay
        return self.value


@dataclass
class Spring3:
    x: Spring = field(default_factory=Spring)
    y: Spring = field(default_factory=Spring)
    z: Spring = field(default_factory=Spring)

    def snap(self, point: tuple[float, float, float]) -> None:
        self.x.snap(point[0])
        self.y.snap(point[1])
        self.z.snap(point[2])

    def step(
        self,
        target: tuple[float, float, float],
        dt: float,
        omega: float,
        vertical_omega: float | None = None,
    ) -> tuple[float, float, float]:
        return (
            self.x.step(target[0], dt, omega),
            self.y.step(target[1], dt, vertical_omega or omega),
            self.z.step(target[2], dt, omega),
        )


class Drift:
    """Bruit lisse dans [-1, 1], somme de trois sinusoïdes incommensurables.

    Il imite la main d'un cadreur ou l'avion-caméra qui ne tient jamais tout
    à fait sa place, sans à-coup ni rebond sur une borne : la courbe est
    continue, ainsi que sa dérivée.
    """

    def __init__(self, rng: random.Random, period_s: float) -> None:
        base = 2.0 * math.pi / max(1.0, period_s)
        self._terms = [
            (base * ratio, rng.uniform(0.0, 2.0 * math.pi), weight)
            for ratio, weight in ((1.0, 0.55), (1.618, 0.3), (2.718, 0.15))
        ]

    def value(self, t: float) -> float:
        return sum(weight * math.sin(pulse * t + phase) for pulse, phase, weight in self._terms)


def _polar(point: tuple[float, float, float]) -> tuple[float, float, float]:
    """(angle depuis la queue, rayon horizontal, hauteur) d'un point du repère avion."""
    x, y, z = point
    return math.degrees(math.atan2(x, -z)), math.hypot(x, z), y


def _cartesian(angle: float, radius: float, height: float) -> tuple[float, float, float]:
    rad = math.radians(angle)
    return radius * math.sin(rad), height, -radius * math.cos(rad)


class Glide:
    """Travelling d'un plan à l'autre, en tournant autour de l'avion.

    Interpoler en ligne droite ferait passer la caméra à travers le
    fuselage quand elle change de côté. On interpole donc l'angle (par le
    plus court chemin), le rayon et la hauteur, avec une courbe douce au
    départ et à l'arrivée. Le rayon ne descend jamais sous celui des deux
    extrémités le plus petit : l'avion reste à distance pendant tout le
    mouvement.
    """

    def __init__(self, start: tuple[float, float, float], duration_s: float) -> None:
        self._start = _polar(start)
        self._duration = max(0.1, duration_s)
        self._t = 0.0

    @property
    def finished(self) -> bool:
        return self._t >= self._duration - 1e-9

    def step(self, goal: tuple[float, float, float], dt: float) -> tuple[float, float, float]:
        self._t = min(self._duration, self._t + max(0.0, dt))
        u = self._t / self._duration
        ease = u * u * (3.0 - 2.0 * u)
        a0, r0, h0 = self._start
        a1, r1, h1 = _polar(goal)
        angle = a0 + shortest_turn(a0, a1) * ease
        radius = max(min(r0, r1), r0 + (r1 - r0) * ease)
        return _cartesian(angle, radius, h0 + (h1 - h0) * ease)


def wrap_degrees(angle: float) -> float:
    return angle % 360.0


def shortest_turn(from_deg: float, to_deg: float) -> float:
    """Écart signé le plus court, dans [-180, 180)."""
    return (to_deg - from_deg + 180.0) % 360.0 - 180.0
