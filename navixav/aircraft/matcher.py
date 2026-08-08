"""Détection de l'appareil chargé, à partir de la base d'avions.

Le moteur ne connaît aucun avion. Il lit `aircraft_db/`, compare le titre publié
par le simulateur aux motifs déclarés par chaque famille, et renvoie la famille
et la variante retenues. Ajouter un appareil est un ajout de données, jamais de
code.

La base est une ressource livrée, donc faillible : un dossier illisible est
ignoré avec une trace, jamais propagé en exception. Une base absente rend
simplement la détection muette — le suivi de position, lui, doit continuer.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from navixav.paths import resource_path, user_data_path

logger = logging.getLogger(__name__)

DATABASE_DIRECTORY = "aircraft_db"


def database_root() -> Path:
    """Racine de la base livrée avec l'application."""
    return resource_path(DATABASE_DIRECTORY)


def user_database_root() -> Path:
    """Racine de la base de l'utilisateur, qui complète celle livrée.

    Aucun catalogue ne couvrira jamais les appareils installés chez les
    utilisateurs. Un dossier déposé ici ajoute une famille, ou en remplace une
    livrée quand l'utilisateur la juge fausse : c'est une donnée, pas une
    version de NaviXav.
    """
    return user_data_path(DATABASE_DIRECTORY)


def database_roots() -> list[Path]:
    """Racines lues, dans l'ordre. La dernière l'emporte à identifiant égal."""
    return [database_root(), user_database_root()]


def _normalise(title: str) -> str:
    """Titre réduit à sa forme comparable aux motifs, tous en minuscules."""
    return " ".join(title.lower().split())


@dataclass(frozen=True)
class Pattern:
    """Motifs d'un bloc `match`, en deux disjonctions.

    Un titre correspond si au moins un motif de `contains` apparaît **et**, si
    la seconde liste existe, au moins un motif de `also_contains`. C'est ce
    « et » qui distingue une variante précise d'une famille générique.
    """

    contains: tuple[str, ...] = ()
    also_contains: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: Any) -> Pattern:
        if not isinstance(data, dict):
            return cls()
        return cls(
            tuple(str(item) for item in data.get("title_contains", []) or ()),
            tuple(str(item) for item in data.get("title_also_contains", []) or ()),
        )

    def matched(self, title: str) -> str | None:
        """Le motif le plus long reconnu dans `title`, ou None."""
        if not self.contains:
            return None
        hits = [pattern for pattern in self.contains if pattern in title]
        if not hits:
            return None
        if self.also_contains and not any(p in title for p in self.also_contains):
            return None
        return max(hits, key=len)


@dataclass(frozen=True)
class AircraftVariant:
    """Un addon particulier d'une famille : Asobo, Fenix, FlyByWire…"""

    id: str
    label: str
    pattern: Pattern
    systems: dict[str, bool] = field(default_factory=dict)
    overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AircraftEntry:
    """Une famille de la base, avec ses variantes."""

    id: str
    manufacturer: str
    family: str
    model: str
    directory: Path
    pattern: Pattern
    priority: int = 0
    # « authored » : procédures écrites depuis le manuel de l'appareil.
    # « draft » : canevas de classe, juste pour le type mais pas pour le modèle.
    maturity: str = "draft"
    systems: dict[str, bool] = field(default_factory=dict)
    variants: tuple[AircraftVariant, ...] = ()
    default_variant: str | None = None
    # Vrai quand la famille vient de la base de l'utilisateur : l'interface doit
    # pouvoir dire d'où sort une procédure, surtout quand elle en remplace une.
    user_supplied: bool = False

    def variant_for(self, title: str) -> AircraftVariant | None:
        """Première variante reconnue, sinon celle déclarée par défaut."""
        for variant in self.variants:
            if variant.pattern.matched(title) is not None:
                return variant
        for variant in self.variants:
            if variant.id == self.default_variant:
                return variant
        return None


@dataclass(frozen=True)
class AircraftMatch:
    """Résultat de la détection, prêt pour le moteur de procédures."""

    entry: AircraftEntry
    variant: AircraftVariant | None
    title: str

    @property
    def systems(self) -> dict[str, bool]:
        """Systèmes de la famille, corrigés par ceux de la variante."""
        systems = dict(self.entry.systems)
        if self.variant is not None:
            systems.update(self.variant.systems)
        return systems

    def has(self, system: str) -> bool:
        """Vrai seulement si le système est déclaré présent.

        Un système non déclaré vaut absent : le moteur ne surveille jamais ce
        que la base n'affirme pas.
        """
        return self.systems.get(system, False) is True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.entry.id,
            "manufacturer": self.entry.manufacturer,
            "family": self.entry.family,
            "model": self.entry.model,
            "variant": self.variant.id if self.variant else None,
            "variant_label": self.variant.label if self.variant else None,
            "systems": self.systems,
            "maturity": self.entry.maturity,
            "user_supplied": self.entry.user_supplied,
        }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_entry(directory: Path, *, user_supplied: bool = False) -> AircraftEntry | None:
    """Charge une famille, ou None si son dossier est inexploitable."""
    try:
        metadata = _read_json(directory / "metadata.json")
        systems = _read_json(directory / "systems.json").get("systems", {})
        mapping = _read_json(directory / "mapping.json")
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        logger.warning("Avion ignoré, dossier illisible (%s) : %s", directory.name, exc)
        return None

    identifier = metadata.get("id")
    if not isinstance(identifier, str) or not identifier:
        logger.warning("Avion ignoré, identifiant absent : %s", directory)
        return None

    pattern = Pattern.from_dict(metadata.get("match"))
    if not pattern.contains:
        logger.warning("Avion ignoré, aucun motif de détection : %s", identifier)
        return None

    variants = []
    for raw in mapping.get("variants", []) or ():
        variant_id = raw.get("id")
        if not isinstance(variant_id, str) or not variant_id:
            continue
        variants.append(
            AircraftVariant(
                id=variant_id,
                label=str(raw.get("label", variant_id)),
                pattern=Pattern.from_dict(raw.get("match")),
                systems={
                    name: value
                    for name, value in (raw.get("systems") or {}).items()
                    if isinstance(value, bool)
                },
                overrides=dict(raw.get("overrides") or {}),
            )
        )

    priority = metadata.get("match", {}).get("priority", 0)
    return AircraftEntry(
        id=identifier,
        manufacturer=str(metadata.get("manufacturer", "")),
        family=str(metadata.get("family", "")),
        model=str(metadata.get("model", "")),
        directory=directory,
        pattern=pattern,
        priority=priority if isinstance(priority, int) else 0,
        maturity=metadata.get("maturity", "draft"),
        systems={name: value for name, value in systems.items() if isinstance(value, bool)},
        variants=tuple(variants),
        default_variant=mapping.get("default_variant"),
        user_supplied=user_supplied,
    )


def load_entries(
    roots: Path | Iterable[Path] | None = None,
    *,
    user_root: Path | None = None,
) -> list[AircraftEntry]:
    """Familles lisibles des racines données, triées par identifiant.

    Les racines sont lues dans l'ordre et, à identifiant égal, la dernière
    l'emporte : la base de l'utilisateur corrige celle livrée sans qu'il ait à
    la modifier — une mise à jour de NaviXav écraserait sa correction.
    """
    if roots is None:
        paths = database_roots()
    elif isinstance(roots, Path):
        paths = [roots] if user_root is None else [roots, user_root]
    else:
        paths = list(roots)

    found: dict[str, AircraftEntry] = {}
    for index, root in enumerate(paths):
        base = root / "aircraft"
        if not base.is_dir():
            logger.info("Base d'avions absente : %s", base)
            continue
        for metadata in sorted(base.glob("*/*/metadata.json")):
            entry = _load_entry(metadata.parent, user_supplied=index > 0)
            if entry is None:
                continue
            if entry.id in found:
                logger.info("Avion « %s » remplacé par %s", entry.id, root)
            found[entry.id] = entry
    return [found[key] for key in sorted(found)]


class AircraftMatcher:
    """Associe un titre d'appareil à une famille et à une variante de la base."""

    def __init__(
        self,
        roots: Path | Iterable[Path] | None = None,
        *,
        user_root: Path | None = None,
    ) -> None:
        self._entries = load_entries(roots, user_root=user_root)

    @property
    def entries(self) -> list[AircraftEntry]:
        return list(self._entries)

    def match(self, title: str) -> AircraftMatch | None:
        """Famille et variante correspondant à `title`, None si aucune.

        Départage, dans l'ordre : la priorité déclarée, puis la longueur du
        motif reconnu — « cessna 172 » l'emporte sur « c172 » —, puis
        l'identifiant, pour que deux bases identiques donnent le même résultat.
        """
        needle = _normalise(title)
        if not needle:
            return None

        best: tuple[int, int, str] | None = None
        chosen: AircraftEntry | None = None
        for entry in self._entries:
            matched = entry.pattern.matched(needle)
            if matched is None:
                continue
            rank = (entry.priority, len(matched), entry.id)
            if best is None or rank > best:
                best, chosen = rank, entry

        if chosen is None:
            logger.debug("Aucun avion de la base ne correspond à « %s »", title)
            return None
        return AircraftMatch(chosen, chosen.variant_for(needle), title)
