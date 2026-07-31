"""Réseau de circulation d'un aérodrome, tiré de la base NaviXav.

Les points et les segments arrivent de MSFS déjà exprimés en mètres locaux
autour du point de référence du terrain — exactement le repère du plan de
terrain. Le graphe se construit donc sans aucune projection, et ses coordonnées
se superposent au tracé affiché.

Un poste de stationnement, lui, n'est pas un nœud du réseau : le simulateur le
publie à part, à quelques dizaines de mètres du premier point de circulation
(6 à 100 m sur les terrains vérifiés). Il est raccroché ici au nœud qui le
dessert, et la distance restante est conservée : c'est la ligne de guidage que
l'avion parcourt seul, avant ou après l'itinéraire calculé.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

from navixav.chart import Projection
from navixav.navdata.base import normalise_runway, reciprocal_runway

# Natures de segment interdites au roulage d'un aéronef.
FORBIDDEN_KINDS = frozenset({"closed", "vehicle"})

# Nature des segments qui desservent un poste de stationnement.
PARKING_KIND = "parking"
RUNWAY_KIND = "runway"


class GroundError(RuntimeError):
    """Le réseau ne permet pas de répondre, avec le motif à afficher."""


@dataclass(frozen=True)
class TaxiNode:
    """Intersection ou extrémité de segment."""

    index: int
    x: float
    y: float
    kind: str | None

    @property
    def is_hold_short(self) -> bool:
        """Point d'attente, y compris les variantes non peintes au sol.

        Les variantes « no draw » ne portent pas de marquage mais arrêtent le
        roulage de la même façon : les ignorer ferait franchir une limite.
        """
        return bool(self.kind and "hold_short" in self.kind)


@dataclass(frozen=True)
class TaxiEdge:
    """Segment reliant deux points, dans le sens où le simulateur le publie."""

    start: int
    end: int
    length_m: float
    width_m: float
    kind: str | None
    name: str | None
    runway: str | None

    @property
    def is_runway(self) -> bool:
        return self.kind == RUNWAY_KIND

    def other(self, node: int) -> int:
        return self.end if node == self.start else self.start


@dataclass(frozen=True)
class Parking:
    """Poste de stationnement et son raccordement au réseau."""

    label: str
    kind: str | None
    x: float
    y: float
    radius_m: float
    heading: float
    node: int
    lead_in_m: float


@dataclass
class TaxiGraph:
    """Réseau de circulation exploitable d'un aérodrome."""

    icao: str
    origin_lat: float
    origin_lon: float
    nodes: dict[int, TaxiNode]
    edges: tuple[TaxiEdge, ...]
    parkings: tuple[Parking, ...]
    adjacency: dict[int, tuple[TaxiEdge, ...]] = field(default_factory=dict)
    # Seuil de chaque piste, en mètres locaux comme le reste du réseau.
    thresholds: dict[str, tuple[float, float]] = field(default_factory=dict)

    @property
    def has_kinds(self) -> bool:
        """La nature des segments est-elle connue ?

        Fausse sur un terrain importé avant que NaviXav ne la demande. Sans
        elle, impossible de distinguer une piste d'une route de service : le
        calcul d'itinéraire doit refuser de conclure plutôt que d'inventer.
        """
        return any(edge.kind for edge in self.edges)

    @property
    def has_names(self) -> bool:
        return any(edge.name for edge in self.edges)

    def neighbours(self, node: int) -> tuple[TaxiEdge, ...]:
        return self.adjacency.get(node, ())

    def distance(self, a: int, b: int) -> float:
        first, second = self.nodes[a], self.nodes[b]
        return math.hypot(first.x - second.x, first.y - second.y)

    def nearest_node(
        self, x: float, y: float, *, among: Iterable[int] | None = None
    ) -> int:
        """Nœud le plus proche d'une position, en mètres locaux."""
        candidates = list(among) if among is not None else list(self.nodes)
        if not candidates:
            raise GroundError(f"{self.icao} n'a aucun point de circulation.")
        return min(
            candidates,
            key=lambda index: math.hypot(
                self.nodes[index].x - x, self.nodes[index].y - y
            ),
        )

    def to_local(self, latitude: float, longitude: float) -> tuple[float, float]:
        """Position géographique en mètres locaux, repère du réseau."""
        return Projection(self.origin_lat, self.origin_lon).to_xy(latitude, longitude)

    def parking(self, label: str) -> Parking | None:
        """Poste désigné par son libellé, sans distinction de casse."""
        wanted = label.strip().casefold()
        for parking in self.parkings:
            if parking.label.casefold() == wanted:
                return parking
        return None

    def runway_entries(self, runway_name: str) -> tuple[int, ...]:
        """Nœuds où le réseau de circulation rejoint une piste.

        Ce sont les points d'entrée en piste : un nœud qui touche à la fois un
        segment de la piste demandée et un segment qui n'en est pas. Les autres
        nœuds de la piste sont intérieurs à celle-ci et ne mènent nulle part.

        Les deux seuils d'une même bande sont acceptés indifféremment : le
        simulateur n'en nomme qu'un — la 23 à Strasbourg, la 14 à Toulouse — et
        s'en tenir au nom demandé priverait d'entrées tous les départs faits
        dans l'autre sens.
        """
        if not self.has_kinds:
            raise GroundError(
                f"Le tracé au sol de {self.icao} ne distingue pas les pistes "
                "des voies de circulation.",
            )
        wanted = {normalise_runway(runway_name), reciprocal_runway(runway_name)}
        entries = []
        for index in self.nodes:
            edges = self.neighbours(index)
            on_runway = any(
                edge.is_runway and edge.runway in wanted for edge in edges
            )
            if on_runway and any(not edge.is_runway for edge in edges):
                entries.append(index)
        # Un point d'attente publié est l'entrée normale ; à défaut, toute
        # jonction avec la piste fait l'affaire.
        holding = [index for index in entries if self.nodes[index].is_hold_short]
        return tuple(holding or entries)

    def takeoff_entry(self, runway_name: str) -> tuple[int, ...]:
        """Entrée à utiliser pour décoller du seuil demandé.

        Les deux seuils d'une bande partagent leurs entrées, mais on ne décolle
        pas des deux au même endroit : la 32R se prend à un bout, la 14L à
        l'autre. Sans ce tri, un départ en 05 à Strasbourg partirait du seuil de
        la 23, soit toute la longueur de piste à contresens.

        Si le seuil demandé est inconnu de la base, toutes les entrées sont
        rendues : mieux vaut un point d'attente approximatif que pas de route.
        """
        entries = self.runway_entries(runway_name)
        threshold = self.thresholds.get(normalise_runway(runway_name))
        if threshold is None or not entries:
            return entries
        closest = min(
            entries,
            key=lambda index: math.hypot(
                self.nodes[index].x - threshold[0],
                self.nodes[index].y - threshold[1],
            ),
        )
        return (closest,)

    def runway_names(self) -> tuple[str, ...]:
        """Pistes que le réseau au sol sait desservir."""
        return tuple(sorted({
            edge.runway for edge in self.edges if edge.is_runway and edge.runway
        }))


# Réseaux déjà assemblés, par base et par terrain. Reconstruire celui de LFPO
# demande 130 ms : tenable à l'ouverture d'une carte, ruineux au rythme d'un
# guidage interrogé chaque seconde.
_CACHE: dict[tuple[str, str], tuple[str, TaxiGraph]] = {}
_CACHE_LIMIT = 6


def build_graph(provider: Any, icao: str, *, cache: bool = True) -> TaxiGraph:
    """Assemble le réseau d'un aérodrome depuis la base NaviXav.

    Le résultat est mémorisé avec la date d'import du terrain : une reprise au
    simulateur la change, et le réseau est réassemblé sans qu'on ait à y penser.
    """
    key = icao.strip().upper()
    connection = provider._conn  # noqa: SLF001 - cache interne NaviXav
    identity = (str(getattr(provider, "_path", "")), key)

    def stamp() -> str:
        row = connection.execute(
            "SELECT fetched_at FROM airport WHERE icao = ?", (key,)
        ).fetchone()
        return (row["fetched_at"] if row else "") or ""

    if cache:
        cached = _CACHE.get(identity)
        if cached and cached[0] == stamp():
            return cached[1]

    graph = _build_graph(provider, key, connection)
    if cache:
        # La date est relue après coup : la construction déclenche au besoin
        # l'import du terrain, qui la change.
        if len(_CACHE) >= _CACHE_LIMIT:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[identity] = (stamp(), graph)
    return graph


def forget_graphs() -> None:
    """Vide le cache des réseaux."""
    _CACHE.clear()


def _build_graph(provider: Any, key: str, connection: Any) -> TaxiGraph:
    airport = provider.airport(key)
    if airport is None:
        raise GroundError(f"{key} est absent de la base de navigation.")

    nodes = {
        row["idx"]: TaxiNode(
            index=row["idx"], x=row["x"], y=row["y"], kind=row["kind"]
        )
        for row in connection.execute(
            "SELECT idx, x, y, kind FROM taxi_point WHERE icao = ?", (key,)
        )
    }
    if not nodes:
        raise GroundError(f"{key} n'a pas de tracé au sol dans la base.")

    edges = []
    for row in connection.execute(
        """SELECT start_idx, end_idx, width_m, kind, name, runway_name
           FROM taxi_path WHERE icao = ?""",
        (key,),
    ):
        start, end = row["start_idx"], row["end_idx"]
        # Un segment dont un bout manque ne relie rien : le garder ferait
        # échouer la recherche sur une arête sans géométrie.
        if start not in nodes or end not in nodes or start == end:
            continue
        edges.append(TaxiEdge(
            start=start,
            end=end,
            length_m=math.hypot(
                nodes[start].x - nodes[end].x, nodes[start].y - nodes[end].y
            ),
            width_m=row["width_m"],
            kind=row["kind"],
            name=row["name"],
            runway=normalise_runway(row["runway_name"]) if row["runway_name"] else None,
        ))

    adjacency: dict[int, list[TaxiEdge]] = {index: [] for index in nodes}
    for edge in edges:
        adjacency[edge.start].append(edge)
        adjacency[edge.end].append(edge)

    # Les seuils arrivent en latitude/longitude ; le réseau est en mètres
    # locaux. La projection est celle du plan de terrain, pour que les deux se
    # superposent exactement.
    projection = Projection(airport.lat, airport.lon)
    thresholds = {
        normalise_runway(runway.name): projection.to_xy(runway.lat, runway.lon)
        for runway in provider.runways(key)
    }

    graph = TaxiGraph(
        icao=key,
        origin_lat=airport.lat,
        origin_lon=airport.lon,
        nodes=nodes,
        edges=tuple(edges),
        parkings=(),
        adjacency={index: tuple(items) for index, items in adjacency.items()},
        thresholds=thresholds,
    )
    graph.parkings = _attach_parkings(graph, connection, key)
    return graph


def _attach_parkings(
    graph: TaxiGraph, connection: Any, icao: str
) -> tuple[Parking, ...]:
    """Raccroche chaque poste au nœud qui le dessert.

    Les nœuds portés par un segment de desserte sont préférés : ce sont les
    entrées de poste voulues par le concepteur du terrain. Un raccordement au
    nœud le plus proche tous segments confondus pourrait viser une voie de
    circulation qui passe devant le poste sans y mener.
    """
    served = {
        node
        for edge in graph.edges
        if edge.kind == PARKING_KIND
        for node in (edge.start, edge.end)
    }
    candidates = served or None

    parkings = []
    for row in connection.execute(
        "SELECT label, kind, x, y, radius_m, heading FROM parking WHERE icao = ?",
        (icao,),
    ):
        node = graph.nearest_node(row["x"], row["y"], among=candidates)
        parkings.append(Parking(
            label=row["label"],
            kind=row["kind"],
            x=row["x"],
            y=row["y"],
            radius_m=row["radius_m"],
            heading=row["heading"] or 0.0,
            node=node,
            lead_in_m=math.hypot(
                graph.nodes[node].x - row["x"], graph.nodes[node].y - row["y"]
            ),
        ))
    return tuple(parkings)
