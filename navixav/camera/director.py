"""Le réalisateur : quel plan, combien de temps, selon la phase du vol.

Un monteur ne filme pas un roulage comme une croisière. Au sol, la caméra
tourne autour de l'avion ou le suit ; sur la piste, elle se poste au bord
pour le voir passer ; près du sol en l'air, elle alterne passages et
poursuite ; en croisière, elle prend le temps d'une patrouille. Un
changement de phase (décollage, toucher) appelle aussitôt un nouveau plan,
et un plan fixe dont l'avion est passé cède la place sans attendre.
"""

from __future__ import annotations

import random
from collections import deque

from navixav.camera.scene import AircraftState
from navixav.camera.shots import SHOTS

PARKED, TAXI, RUNWAY, FINAL, LOW, ENROUTE = "parked", "taxi", "runway", "final", "low", "enroute"
TAXI_MAX_MPS = 20.0  # environ 40 kt : au-delà, c'est une course sur piste
LOW_MAX_M = 750.0  # environ 2 500 ft sol
# Courte finale : sous 1 000 ft sol, en descente de plus de 200 ft/min.
FINAL_MAX_M = 300.0
FINAL_SINK_MPS = -1.0
# Une phase doit tenir ce temps avant de provoquer une coupe : un rebond du
# train ou une rafale ne doit pas hacher le montage.
PHASE_SETTLE_S = 3.0
# Poids des plans et durée de tenue (s) pour chaque phase.
PLAN: dict[str, tuple[dict[str, float], tuple[float, float]]] = {
    PARKED: ({"orbit": 3.0, "chase": 1.0}, (25.0, 40.0)),
    TAXI: ({"chase": 3.0, "orbit": 2.0, "wingman": 1.0, "spotter": 1.0, "tower": 1.0}, (15.0, 25.0)),
    RUNWAY: ({"spotter": 4.0, "chase": 2.0, "tower": 2.0, "flyby": 1.0}, (7.0, 12.0)),
    FINAL: ({"spotter": 4.0, "tower": 3.0, "flyby": 2.0, "chase": 1.0}, (8.0, 14.0)),
    LOW: ({"flyby": 3.0, "chase": 3.0, "wingman": 2.0, "spotter": 1.0, "orbit": 1.0, "tower": 1.0}, (9.0, 16.0)),
    ENROUTE: ({"wingman": 3.0, "chase": 3.0, "orbit": 2.0, "flyby": 2.0}, (18.0, 35.0)),
}


def phase_of(state: AircraftState) -> str:
    if state.on_ground:
        if state.ground_speed_mps < 1.5:
            return PARKED
        return TAXI if state.ground_speed_mps < TAXI_MAX_MPS else RUNWAY
    if state.height_m < FINAL_MAX_M and state.vertical_speed_mps < FINAL_SINK_MPS:
        return FINAL
    return LOW if state.height_m < LOW_MAX_M else ENROUTE


class Director:
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._recent: deque[str] = deque(maxlen=2)
        self.phase: str | None = None
        self._candidate: tuple[str, float] | None = None
        self._cut_at: float | None = None
        self.hold_s: float | None = None
        # Rythme du montage : multiplie la durée de tenue de chaque plan.
        self.pace = 1.0
        # Plans que le spectateur autorise ; jamais vide.
        self.allowed: frozenset[str] = frozenset(SHOTS)
        # Plan gardé : plus de coupe automatique, sauf plan fixe terminé.
        self.held = False

    def reset(self) -> None:
        self._recent.clear()
        self.phase = None
        self._candidate = None
        self._cut_at = None
        self.hold_s = None

    def next_cut_in(self, now: float) -> float | None:
        return None if self._cut_at is None else max(0.0, self._cut_at - now)

    def choose(self, state: AircraftState, now: float) -> str:
        """Plan suivant, adapté à la phase, différent des deux précédents."""
        self.phase = phase_of(state)
        self._candidate = None
        weights, hold = PLAN[self.phase]
        usable = {
            name: w for name, w in weights.items() if name in self.allowed and SHOTS[name].suits(state)
        }
        if not usable:
            # La sélection écarte tous les plans de cette phase : on prend ce
            # qu'elle autorise et qui convient, à poids égal.
            usable = {name: 1.0 for name in sorted(self.allowed) if SHOTS[name].suits(state)}
        if not usable:
            attached = sorted(name for name in self.allowed if not SHOTS[name].world)
            usable = {name: 1.0 for name in attached} or {"orbit": 1.0}
        fresh = {name: w for name, w in usable.items() if name not in self._recent}
        if not fresh and self._recent:
            # Une seule possibilité : on accepte de la répéter, pas l'avant-dernière.
            fresh = {name: w for name, w in usable.items() if name != self._recent[-1]} or usable
        pool = fresh or {"orbit": 1.0}
        name = self._rng.choices(list(pool), list(pool.values()))[0]
        self._recent.append(name)
        self.hold_s = self._rng.uniform(*hold) * self.pace
        self._cut_at = now + self.hold_s
        return name

    def cut_now(self) -> None:
        """Le spectateur demande le plan suivant : la coupe tombe à l'image suivante."""
        self._cut_at = None

    def should_cut(self, state: AircraftState, now: float, shot_done: bool) -> bool:
        if self.held:
            return shot_done
        if shot_done or self._cut_at is None or now >= self._cut_at:
            return True
        phase = phase_of(state)
        if phase == self.phase:
            self._candidate = None
            return False
        if self._candidate is None or self._candidate[0] != phase:
            self._candidate = (phase, now)
            return False
        return now - self._candidate[1] >= PHASE_SETTLE_S
