"""Lecture read-only des SimObjects hérités et matching par titre.

FSLTL et AIG livrent la même chose sous deux emballages : des dossiers
`SimObjects/Airplanes/*/aircraft.cfg` où chaque `[FLTSIM.n]` déclare un titre
spawnable, le type OACI de la cellule et parfois la compagnie. Ce qui les
sépare — nom du paquet, emplacement des règles VMR, conventions de titres —
tient à leur distribution, pas à leur contenu. Tout ce qui suit est donc
commun, et chaque fournisseur n'écrit que sa détection.

Rien n'est jamais modifié sur le disque : les paquets de la Communauté
appartiennent à l'utilisateur et aux outils qui les installent.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from navixav.traffic.base import MatchKind, ResolvedAircraftModel, TrafficAircraft

LOGGER = logging.getLogger(__name__)

MAX_CONFIG_BYTES = 2 * 1024 * 1024
MAX_VMR_BYTES = 20 * 1024 * 1024
MAX_VALUE_LENGTH = 512
_ENTRY = re.compile(r"^\s*([A-Za-z_0-9]+)\s*=\s*(.*?)\s*(?:;.*)?$")
_SECTION = re.compile(r"^\s*\[([^]]+)]")


@dataclass(frozen=True)
class SimObjectModel:
    title: str
    aircraft_type: str
    airline_icao: str
    source: Path


@dataclass(frozen=True)
class VmrRule:
    aircraft_type: str
    callsign_prefix: str
    model_titles: tuple[str, ...]

    @property
    def description(self) -> str:
        suffix = f" + {self.callsign_prefix}" if self.callsign_prefix else ""
        return f"VMR {self.aircraft_type}{suffix}"


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_CONFIG_BYTES or path.is_symlink():
            LOGGER.warning("aircraft.cfg ignoré (taille ou lien inattendu) : %s", path)
            return None
    except OSError:
        return None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError:
            return None
    return None


def parse_aircraft_config(path: Path) -> list[SimObjectModel]:
    """Extrait chaque titre FLTSIM avec les ICAO réellement déclarés.

    Le type est presque toujours déclaré une fois dans `[General]` et la
    compagnie dans chaque variation : la section commune sert donc de repli,
    sans quoi les paquets qui ne répètent pas le type par livrée — c'est le
    cas d'AIG, où un seul `icao_type_designator` couvre des dizaines de
    titres — ne rendraient aucun modèle.
    """
    text = read_text(path)
    if text is None:
        return []
    common: dict[str, str] = {}
    variations: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        section = _SECTION.match(line)
        if section:
            current = {} if section.group(1).casefold().startswith("fltsim") else None
            if current is not None:
                variations.append(current)
            continue
        match = _ENTRY.match(line)
        if not match:
            continue
        key = match.group(1).casefold()
        if key not in {"title", "icao_type_designator", "icao_airline"}:
            continue
        value = match.group(2).strip().strip('"').strip()
        if not value or len(value) > MAX_VALUE_LENGTH:
            continue
        (current if current is not None else common)[key] = value

    found: list[SimObjectModel] = []
    for block in variations:
        title = block.get("title", "").strip()
        aircraft_type = block.get(
            "icao_type_designator", common.get("icao_type_designator", "")
        ).strip().upper()
        airline = block.get("icao_airline", common.get("icao_airline", "")).strip().upper()
        if title and aircraft_type:
            found.append(SimObjectModel(title, aircraft_type, airline, path))
    return found


def parse_vmr(path: Path, label: str = "VMR") -> list[VmrRule]:
    """Lit le VMR en streaming, sans DTD, entité externe ni fichier démesuré."""
    try:
        size = path.stat().st_size
        if path.is_symlink():
            LOGGER.warning("VMR %s ignoré : lien symbolique", label)
            return []
        with path.open("rb") as stream:
            prefix = stream.read(4096)
    except OSError as exc:
        LOGGER.warning("VMR %s illisible : %s", label, exc)
        return []
    if size > MAX_VMR_BYTES:
        LOGGER.warning("VMR %s ignoré : %s octets", label, size)
        return []
    upper = prefix.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        LOGGER.warning("VMR %s refusé : DTD ou entité interdite", label)
        return []

    rules: list[VmrRule] = []
    try:
        for _event, element in ET.iterparse(path, events=("end",)):
            if element.tag.rsplit("}", 1)[-1] != "ModelMatchRule":
                element.clear()
                continue
            aircraft_type = str(element.attrib.get("TypeCode") or "").strip().upper()
            prefix_value = str(element.attrib.get("CallsignPrefix") or "").strip().upper()
            raw_models = str(element.attrib.get("ModelName") or "")
            titles = tuple(
                dict.fromkeys(
                    title.strip() for title in raw_models.split("//")
                    if title.strip() and len(title.strip()) <= MAX_VALUE_LENGTH
                )
            )
            if aircraft_type and titles:
                rules.append(VmrRule(aircraft_type, prefix_value, titles))
            element.clear()
    except (ET.ParseError, OSError) as exc:
        LOGGER.warning("VMR %s invalide : %s", label, exc)
        return []
    return rules


class SimObjectModelIndex:
    """Index construit une fois, avec résultats explicables et déterministes.

    L'ordre de résolution ne dépend pas du fournisseur : règle VMR exacte,
    couple type + compagnie lu dans les `aircraft.cfg`, règle VMR sur le seul
    type, modèle générique du type, enfin le repli MSFS explicite. Seul le
    contenu change d'un paquet à l'autre.
    """

    provider = "?"
    unavailable_reason = "model match unavailable"

    def __init__(self) -> None:
        self.models: list[SimObjectModel] = []
        self.rules: list[VmrRule] = []
        self._titles: dict[str, SimObjectModel] = {}
        self._exact: dict[tuple[str, str], list[VmrRule]] = defaultdict(list)
        self._type: dict[str, list[VmrRule]] = defaultdict(list)
        self._models: dict[tuple[str, str], list[SimObjectModel]] = defaultdict(list)

    def _index(
        self,
        roots: Iterable[Path],
        vmr_paths: Iterable[Path] = (),
        *,
        max_config_files: int,
    ) -> None:
        """Lit les paquets dans l'ordre reçu ; le premier titre vu l'emporte."""
        budget = max_config_files
        for root in roots:
            if budget <= 0:
                break
            planes = root / "SimObjects" / "Airplanes"
            for config in sorted(planes.glob("*/aircraft.cfg"))[:budget]:
                budget -= 1
                for model in parse_aircraft_config(config):
                    key = model.title.casefold()
                    if key not in self._titles:
                        self._titles[key] = model
                        self.models.append(model)
                        self._models[
                            (model.aircraft_type, model.airline_icao)
                        ].append(model)
        for path in vmr_paths:
            self.rules.extend(parse_vmr(path, self.provider))
        for rule in self.rules:
            if rule.callsign_prefix:
                self._exact[(rule.aircraft_type, rule.callsign_prefix)].append(rule)
            else:
                self._type[rule.aircraft_type].append(rule)

    def _from_rule(
        self, rule: VmrRule, kind: MatchKind, level: int
    ) -> ResolvedAircraftModel | None:
        for title in rule.model_titles:
            model = self._titles.get(title.casefold())
            if model:
                return ResolvedAircraftModel(
                    model.title, self.provider, kind, level,
                    "aircraft + airline exact match" if kind is MatchKind.EXACT
                    else "generic aircraft match",
                    rule.description,
                )
        return None

    def match(
        self, aircraft: TrafficAircraft, msfs_fallback_titles: Iterable[str] = ()
    ) -> ResolvedAircraftModel | None:
        aircraft_type = (aircraft.aircraft_type or "").strip().upper()
        airline = (aircraft.airline_icao or "").strip().upper()
        if not aircraft_type:
            return self._msfs_fallback(msfs_fallback_titles)
        if airline:
            for rule in self._exact.get((aircraft_type, airline), ()):
                result = self._from_rule(rule, MatchKind.EXACT, 0)
                if result:
                    return result
            direct = self._models.get((aircraft_type, airline), ())
            if direct:
                return ResolvedAircraftModel(
                    direct[0].title, self.provider, MatchKind.EXACT, 0,
                    "aircraft + airline exact match", "aircraft.cfg",
                )
        for rule in self._type.get(aircraft_type, ()):
            result = self._from_rule(rule, MatchKind.AIRCRAFT, 1)
            if result:
                return result
        generic = (
            self._models.get((aircraft_type, "ZZZZ"), ())
            or self._models.get((aircraft_type, ""), ())
        )
        if generic:
            return ResolvedAircraftModel(
                generic[0].title, self.provider, MatchKind.AIRCRAFT, 1,
                "generic aircraft match", "aircraft.cfg",
            )
        return self._msfs_fallback(msfs_fallback_titles)

    def _msfs_fallback(self, titles: Iterable[str]) -> ResolvedAircraftModel | None:
        title = next((str(item).strip() for item in titles if str(item).strip()), "")
        return ResolvedAircraftModel(
            title, "MSFS", MatchKind.MSFS, 3, self.unavailable_reason
        ) if title else None
