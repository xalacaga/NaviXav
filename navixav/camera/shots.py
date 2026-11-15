"""Plans de caméra : où se place l'opérateur, et quel point il cadre.

Toutes les distances se comptent en envergures : un plan pensé pour un
A320 cadre aussi bien un Cessna qu'un A380, sans profil par avion.

Repère avion de MSFS : x vers la droite, y vers le haut, z vers l'avant, en
mètres. L'angle d'une station se compte depuis la queue, dans le sens des
aiguilles d'une montre vu de dessus : 0° derrière, 90° à droite, 180° devant.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from navixav.camera.motion import Drift, Spring, Spring3
from navixav.camera.scene import AircraftState, along_track_m, destination, distance_bearing

AIRCRAFT = "aircraft"
WORLD = "world"
MIN_SIZE_M, MAX_SIZE_M = 9.0, 80.0
# Hauteur de l'œil d'un spectateur debout au bord de la piste.
EYE_HEIGHT_M = 1.7
MIN_WORLD_CLEARANCE_M = 3.0


@dataclass(frozen=True)
class Command:
    referential: str
    position: tuple[float, float, float]
    # Point cadré, dans le repère avion : un peu devant le nez, il laisse à
    # l'avion de la place pour avancer dans l'image.
    target: tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Point fixe dont le simulateur doit garder le décor chargé.
    lock: tuple[float, float, float] | None = None
    # Champ de vision en degrés, pour zoomer de loin ; None laisse celui de MSFS.
    fov_deg: float | None = None


@dataclass
class Framing:
    """Cadrage réglé par le spectateur pour un plan, appliqué en direct.

    `distance` multiplie l'éloignement (zoom pour la tour), `height` ajoute
    une hauteur exprimée en envergures, `angle` fait tourner la station vers
    l'avant de l'avion (degrés), du côté où elle se trouve.
    """

    distance: float = 1.0
    height: float = 0.0
    angle: float = 0.0


DISTANCE_RANGE = (0.4, 2.5)
HEIGHT_RANGE = (-1.0, 1.0)
ANGLE_RANGE = (-180.0, 180.0)
# Réglages proposés pour chaque plan : seuls ceux qui ont un sens.
ADJUSTABLE: dict[str, tuple[str, ...]] = {
    "orbit": ("distance", "height"),
    "chase": ("distance", "height", "angle"),
    "wingman": ("distance", "height", "angle"),
    "flyby": ("distance", "height"),
    "spotter": ("distance",),
    "tower": ("distance",),
}


# Distances de référence en mètres, celles de FSDirector, pensées pour un
# avion de ligne (envergure d'un A320). Elles suivent ensuite la taille de
# l'avion : un biplace s'approche, un gros-porteur recule.
REFERENCE_SPAN_M = 34.0


def scale_of(size: float) -> float:
    return max(0.45, size / REFERENCE_SPAN_M)


def size_of(state: AircraftState) -> float:
    return min(MAX_SIZE_M, max(MIN_SIZE_M, state.span_m))


def closest_m(size: float) -> float:
    """Distance sous laquelle la caméra entrerait dans la cellule."""
    return size * 0.55 + 3.0


def station(angle_deg: float, radius_m: float, height_m: float) -> tuple[float, float, float]:
    angle = math.radians(angle_deg)
    return (radius_m * math.sin(angle), height_m, -radius_m * math.cos(angle))


def _signed(rng: random.Random, value: float) -> float:
    return value if rng.random() < 0.5 else -value


class Shot:
    name = ""
    world = False
    # Remplacé par le service avant `start` : une référence partagée, que les
    # curseurs de la régie modifient pendant le plan.
    framing = Framing()

    def start(self, state: AircraftState, rng: random.Random) -> None:
        raise NotImplementedError

    def update(self, state: AircraftState, dt: float) -> Command:
        raise NotImplementedError

    def done(self, state: AircraftState) -> bool:
        """Vrai quand le plan n'a plus rien à montrer (avion passé)."""
        return False

    @staticmethod
    def suits(state: AircraftState) -> bool:
        return True


class Orbit(Shot):
    """Tour complet et régulier de l'avion, l'objectif tourné vers lui."""

    name = "orbit"

    def start(self, state: AircraftState, rng: random.Random) -> None:
        size = size_of(state)
        self._size = size
        scale = scale_of(size)
        self._radius = rng.uniform(35.0, 80.0) * scale
        self._height = rng.uniform(8.0, 28.0) * scale
        # Un grand avion tourne un peu moins vite : même rythme apparent.
        self._rate = _signed(rng, rng.uniform(3.5, 7.5) * (34.0 / size) ** 0.35)
        self._angle = rng.uniform(0.0, 360.0)
        self._spring = Spring3()
        self._spring.snap(station(self._angle, self._radius, self._height))

    def update(self, state: AircraftState, dt: float) -> Command:
        self._angle = (self._angle + self._rate * dt) % 360.0
        framing = self.framing
        radius = max(closest_m(self._size), self._radius * framing.distance)
        goal = station(self._angle, radius, self._height + framing.height * self._size)
        return Command(AIRCRAFT, self._spring.step(goal, dt, 3.0))


class Chase(Shot):
    """Station fixe autour de l'avion, tenue comme par un opérateur à la main."""

    name = "chase"
    # (angle depuis la queue, poids) : arrière, trois-quarts arrière,
    # travers, trois-quarts avant.
    STATIONS = ((0.0, 3.0), (38.0, 3.0), (90.0, 1.0), (138.0, 1.0))

    def start(self, state: AircraftState, rng: random.Random) -> None:
        size = size_of(state)
        angles = [angle for angle, _weight in self.STATIONS]
        weights = [weight for _angle, weight in self.STATIONS]
        # Un angle négatif place la station à gauche de l'avion.
        self._angle = _signed(rng, rng.choices(angles, weights)[0] + rng.uniform(-12.0, 12.0))
        scale = scale_of(size)
        self._radius = rng.uniform(25.0, 55.0) * scale
        self._height = rng.uniform(6.0, 20.0) * scale
        self._size = size
        self._lead = size * 0.2
        period = rng.uniform(12.0, 20.0)
        self._drift = (Drift(rng, period), Drift(rng, period * 1.3), Drift(rng, period * 0.8))
        self._t = 0.0
        self._spring = Spring3()
        self._spring.snap(station(self._angle, self._radius, self._height))

    def update(self, state: AircraftState, dt: float) -> Command:
        self._t += dt
        angle_drift, radius_drift, height_drift = (d.value(self._t) for d in self._drift)
        framing = self.framing
        side = 1.0 if self._angle >= 0 else -1.0
        goal = station(
            self._angle + side * framing.angle + 4.0 * angle_drift,
            max(closest_m(self._size), self._radius * framing.distance * (1.0 + 0.06 * radius_drift)),
            self._height + framing.height * self._size + 0.08 * self._size * height_drift,
        )
        return Command(AIRCRAFT, self._spring.step(goal, dt, 4.0), (0.0, 0.0, self._lead))


class Wingman(Shot):
    """Avion-caméra en patrouille : il ne tient jamais tout à fait sa place."""

    name = "wingman"

    def start(self, state: AircraftState, rng: random.Random) -> None:
        size = size_of(state)
        self._side = 1.0 if rng.random() < 0.5 else -1.0
        self._angle = 90.0 + rng.uniform(-20.0, 20.0)
        scale = scale_of(size)
        self._radius = rng.uniform(28.0, 33.0) * scale
        self._min_radius = 28.0 * scale
        self._height = rng.uniform(8.0, 30.0) * scale
        self._size = size
        self._lead = size * 0.25
        self._drift = tuple(Drift(rng, rng.uniform(18.0, 35.0)) for _ in range(3))
        self._t = 0.0
        self._spring = Spring3()
        self._spring.snap(self._goal())

    def _goal(self) -> tuple[float, float, float]:
        angle_drift, radius_drift, height_drift = (d.value(self._t) for d in self._drift)
        framing = self.framing
        angle = self._angle + framing.angle + 22.0 * angle_drift
        floor = max(closest_m(self._size), self._min_radius * framing.distance)
        radius = max(floor, self._radius * framing.distance * (1.0 + 0.18 * radius_drift))
        height = self._height + framing.height * self._size + 0.25 * self._size * height_drift
        return station(self._side * angle, radius, height)

    def update(self, state: AircraftState, dt: float) -> Command:
        self._t += dt
        return Command(AIRCRAFT, self._spring.step(self._goal(), dt, 2.0), (0.0, 0.0, self._lead))

    @staticmethod
    def suits(state: AircraftState) -> bool:
        return state.ground_speed_mps > 3.0


class _FixedPoint(Shot):
    """Caméra posée dans le décor, devant l'avion, qui le regarde passer."""

    world = True
    lead_s = (5.0, 8.0)

    def _place(self, state: AircraftState, rng: random.Random) -> tuple[float, float, float, float]:
        raise NotImplementedError

    def start(self, state: AircraftState, rng: random.Random) -> None:
        latitude, longitude, altitude, lateral = self._place(state, rng)
        self._point = (latitude, longitude, altitude)
        self._lateral = abs(lateral)
        self._passed_after_m = max(self._lateral * 4.0, state.ground_speed_mps * 3.5, 60.0)

    def update(self, state: AircraftState, dt: float) -> Command:
        return Command(WORLD, self._point, lock=self._point)

    def done(self, state: AircraftState) -> bool:
        return along_track_m(state, self._point[0], self._point[1]) < -self._passed_after_m

    def _ahead(self, state: AircraftState, rng: random.Random, minimum_m: float) -> tuple[float, float, float]:
        lead = rng.uniform(*self.lead_s)
        distance = max(state.ground_speed_mps * lead, minimum_m)
        latitude, longitude = destination(state.latitude, state.longitude, state.course_deg, distance)
        return latitude, longitude, lead


class FlyBy(_FixedPoint):
    """Passage : l'avion traverse l'image, à quelques envergures de l'objectif."""

    name = "flyby"

    def _place(self, state: AircraftState, rng: random.Random) -> tuple[float, float, float, float]:
        size = size_of(state)
        latitude, longitude, lead = self._ahead(state, rng, size * 3.0 + 60.0)
        lateral = _signed(rng, rng.uniform(12.0, 50.0) * scale_of(size) * self.framing.distance)
        side = state.course_deg + (90.0 if lateral > 0 else -90.0)
        latitude, longitude = destination(latitude, longitude, side, abs(lateral))
        altitude = (
            state.altitude_m + state.vertical_speed_mps * lead
            + rng.uniform(-10.0, 20.0) * scale_of(size) + size * self.framing.height
        )
        floor = state.ground_elevation_m + (EYE_HEIGHT_M if state.on_ground else MIN_WORLD_CLEARANCE_M)
        return latitude, longitude, max(altitude, floor), lateral

    @staticmethod
    def suits(state: AircraftState) -> bool:
        return state.ground_speed_mps > 12.0


class Spotter(_FixedPoint):
    """Bord de piste : un spectateur debout, à hauteur d'œil, regarde passer l'avion."""

    name = "spotter"
    lead_s = (6.0, 10.0)
    MAX_HEIGHT_M = 300.0

    def _place(self, state: AircraftState, rng: random.Random) -> tuple[float, float, float, float]:
        size = size_of(state)
        if not state.on_ground and state.vertical_speed_mps < -1.0:
            # En finale : le spectateur attend au point de toucher prévu,
            # là où la trajectoire de descente rencontre le sol.
            lead = min(45.0, max(6.0, state.height_m / -state.vertical_speed_mps))
            distance = max(state.ground_speed_mps * lead, size * 2.0 + 120.0)
            latitude, longitude = destination(state.latitude, state.longitude, state.course_deg, distance)
        else:
            latitude, longitude, _lead = self._ahead(state, rng, size * 2.0 + 120.0)
        lateral = _signed(rng, (size * rng.uniform(0.8, 1.4) + 25.0) * self.framing.distance)
        side = state.course_deg + (90.0 if lateral > 0 else -90.0)
        latitude, longitude = destination(latitude, longitude, side, abs(lateral))
        return latitude, longitude, state.ground_elevation_m + EYE_HEIGHT_M, lateral

    @classmethod
    def suits(cls, state: AircraftState) -> bool:
        return state.ground_speed_mps > 5.0 and (state.on_ground or state.height_m < cls.MAX_HEIGHT_M)


class Tower(Shot):
    """Depuis la vigie de la tour de contrôle, en zoomant sur l'avion.

    La position de la tour vient du simulateur lui-même (aérodromes de
    départ et d'arrivée du plan chargé). Plus l'avion est loin, plus le
    champ se resserre, pour qu'il occupe toujours une part lisible de l'image.
    """

    name = "tower"
    world = True
    MAX_RANGE_M = 4500.0
    MAX_HEIGHT_M = 900.0
    MIN_FOV_DEG, MAX_FOV_DEG = 6.0, 50.0
    # MSFS donne l'altitude du pied de la tour (8 m au-dessus du terrain à
    # Toulouse, au niveau du sol à Heathrow) : la vigie est bien plus haut.
    CAB_HEIGHT_M = 40.0
    # Un pas hors de l'axe de la tour, côté avion, pour ne pas filmer à
    # travers ses murs.
    CAB_OFFSET_M = 12.0

    @classmethod
    def nearest(cls, state: AircraftState) -> tuple[tuple[float, float, float], float] | None:
        best = None
        for tower in state.towers:
            distance, _bearing = distance_bearing(state.latitude, state.longitude, tower[0], tower[1])
            if best is None or distance < best[1]:
                best = (tower, distance)
        return best

    @classmethod
    def suits(cls, state: AircraftState) -> bool:
        found = cls.nearest(state)
        return (
            found is not None
            and found[1] < cls.MAX_RANGE_M
            and (state.on_ground or state.height_m < cls.MAX_HEIGHT_M)
        )

    def start(self, state: AircraftState, rng: random.Random) -> None:
        found = self.nearest(state)
        if found is None:
            raise ValueError("Aucune tour connue près de l'avion.")
        latitude, longitude, base = found[0]
        _distance, bearing = distance_bearing(latitude, longitude, state.latitude, state.longitude)
        latitude, longitude = destination(latitude, longitude, bearing, self.CAB_OFFSET_M)
        # Le terrain sous l'avion, tout proche, borne le pied d'une tour mal renseignée.
        self._point = (latitude, longitude, max(base, state.ground_elevation_m) + self.CAB_HEIGHT_M)
        self._size = size_of(state)
        self._zoom = Spring()
        self._zoom.snap(self._fov(state))

    def _distance(self, state: AircraftState) -> float:
        ground, _bearing = distance_bearing(self._point[0], self._point[1], state.latitude, state.longitude)
        return math.hypot(ground, state.altitude_m - self._point[2])

    def _fov(self, state: AircraftState) -> float:
        # L'avion occupe environ un tiers de la largeur de l'image.
        width = self._size * 3.0
        fov = math.degrees(2.0 * math.atan(width / (2.0 * max(1.0, self._distance(state)))))
        return min(self.MAX_FOV_DEG, max(self.MIN_FOV_DEG, fov))

    def update(self, state: AircraftState, dt: float) -> Command:
        target = min(self.MAX_FOV_DEG * 1.5, self._fov(state) * self.framing.distance)
        fov = self._zoom.step(target, dt, 1.5)
        return Command(WORLD, self._point, lock=self._point, fov_deg=fov)

    def done(self, state: AircraftState) -> bool:
        return self._distance(state) > self.MAX_RANGE_M * 1.2


SHOTS: dict[str, type[Shot]] = {
    shot.name: shot for shot in (Orbit, Chase, Wingman, FlyBy, Spotter, Tower)
}
# Plans qui suivent l'avion (repère avion) : seuls eux peuvent s'enchaîner
# en travelling ; un plan posé dans le décor commence toujours par une coupe.
ATTACHED = frozenset(name for name, shot in SHOTS.items() if not shot.world)
