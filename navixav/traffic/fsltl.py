"""Détection et indexation strictement read-only de FSLTL Base Models."""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Iterator

from navixav.aircraft.community import community_folders
from navixav.traffic.base import MatchKind, ResolvedAircraftModel, TrafficAircraft

LOGGER = logging.getLogger(__name__)

PACKAGE_NAME = "fsltl-traffic-base"
FSLTL_DOWNLOAD_URL = "https://flybywiresim.com/downloads/"
MAX_CONFIG_BYTES = 2 * 1024 * 1024
MAX_CONFIG_FILES = 5000
MAX_VMR_BYTES = 20 * 1024 * 1024
MAX_VALUE_LENGTH = 512
_ENTRY = re.compile(r"^\s*([A-Za-z_0-9]+)\s*=\s*(.*?)\s*(?:;.*)?$")
_SECTION = re.compile(r"^\s*\[([^]]+)]")


class FsltlStatus(StrEnum):
    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class FsltlInstallation:
    status: FsltlStatus
    root: Path | None = None
    version: str = ""
    reason: str = ""
    config_count: int = 0
    vmr_path: Path | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "detected": self.status is FsltlStatus.DETECTED,
            "version": self.version,
            "reason": self.reason,
            "models": self.config_count,
            "vmr": self.vmr_path is not None,
        }


@dataclass(frozen=True)
class FsltlModel:
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


def _package_children(folder: Path) -> Iterator[Path]:
    try:
        for child in folder.iterdir():
            if (
                child.is_dir()
                and not child.is_symlink()
                and child.name.casefold() == PACKAGE_NAME
            ):
                yield child
    except OSError:
        return


def detect_fsltl(
    folders: Iterable[Path] | None = None,
    *,
    explicit_path: Path | None = None,
) -> FsltlInstallation:
    """Localise le paquet et distingue absence, paquet incomplet et utilisable."""
    if explicit_path is not None:
        selected = Path(explicit_path).expanduser()
        if selected.is_symlink():
            return FsltlInstallation(
                FsltlStatus.NOT_DETECTED,
                reason="chemin FSLTL manuel invalide",
            )
        if selected.is_dir() and selected.name.casefold() == PACKAGE_NAME:
            candidates = [selected]
        else:
            candidates = list(_package_children(selected)) if selected.is_dir() else []
        if not candidates:
            return FsltlInstallation(
                FsltlStatus.NOT_DETECTED,
                reason="FSLTL Base Models absent du chemin manuel",
            )
    else:
        roots = list(folders) if folders is not None else community_folders()
        candidates = [child for folder in roots for child in _package_children(Path(folder))]
    if not candidates:
        return FsltlInstallation(FsltlStatus.NOT_DETECTED, reason="FSLTL Base Models absent")

    root = candidates[0]
    manifest = root / "manifest.json"
    version = ""
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if isinstance(raw, dict):
            version = str(raw.get("package_version") or "")[:64]
    except (OSError, ValueError):
        return FsltlInstallation(
            FsltlStatus.INCOMPLETE, root, reason="manifest.json absent ou invalide"
        )

    airplane_root = root / "SimObjects" / "Airplanes"
    try:
        configs = list(airplane_root.glob("*/aircraft.cfg"))[: MAX_CONFIG_FILES + 1]
    except OSError:
        configs = []
    if not configs:
        return FsltlInstallation(
            FsltlStatus.INCOMPLETE, root, version, "aucun aircraft.cfg"
        )
    if len(configs) > MAX_CONFIG_FILES:
        return FsltlInstallation(
            FsltlStatus.INCOMPLETE, root, version, "trop de fichiers aircraft.cfg"
        )
    vmr = root / "FSLTL_Rules.vmr"
    return FsltlInstallation(
        FsltlStatus.DETECTED,
        root,
        version,
        config_count=len(configs),
        vmr_path=vmr if vmr.is_file() and not vmr.is_symlink() else None,
    )


def _read_text(path: Path) -> str | None:
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


def parse_aircraft_config(path: Path) -> list[FsltlModel]:
    """Extrait chaque titre FLTSIM avec les ICAO réellement déclarés."""
    text = _read_text(path)
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

    found: list[FsltlModel] = []
    for block in variations:
        title = block.get("title", "").strip()
        aircraft_type = block.get(
            "icao_type_designator", common.get("icao_type_designator", "")
        ).strip().upper()
        airline = block.get("icao_airline", common.get("icao_airline", "")).strip().upper()
        if title and aircraft_type:
            found.append(FsltlModel(title, aircraft_type, airline, path))
    return found


def parse_vmr(path: Path) -> list[VmrRule]:
    """Lit le VMR en streaming, sans DTD, entité externe ni fichier démesuré."""
    try:
        size = path.stat().st_size
        if path.is_symlink():
            LOGGER.warning("VMR FSLTL ignoré : lien symbolique")
            return []
        with path.open("rb") as stream:
            prefix = stream.read(4096)
    except OSError as exc:
        LOGGER.warning("VMR FSLTL illisible : %s", exc)
        return []
    if size > MAX_VMR_BYTES:
        LOGGER.warning("VMR FSLTL ignoré : %s octets", size)
        return []
    upper = prefix.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        LOGGER.warning("VMR FSLTL refusé : DTD ou entité interdite")
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
        LOGGER.warning("VMR FSLTL invalide : %s", exc)
        return []
    return rules


class FsltlModelIndex:
    """Index construit une fois, avec résultats explicables et déterministes."""

    def __init__(self, installation: FsltlInstallation) -> None:
        self.installation = installation
        self.models: list[FsltlModel] = []
        self.rules: list[VmrRule] = []
        self._titles: dict[str, FsltlModel] = {}
        self._exact: dict[tuple[str, str], list[VmrRule]] = defaultdict(list)
        self._type: dict[str, list[VmrRule]] = defaultdict(list)
        self._models: dict[tuple[str, str], list[FsltlModel]] = defaultdict(list)
        if installation.status is FsltlStatus.DETECTED and installation.root:
            self._build()

    def _build(self) -> None:
        root = self.installation.root / "SimObjects" / "Airplanes"  # type: ignore[union-attr]
        for config in sorted(root.glob("*/aircraft.cfg"))[:MAX_CONFIG_FILES]:
            for model in parse_aircraft_config(config):
                key = model.title.casefold()
                if key not in self._titles:
                    self._titles[key] = model
                    self.models.append(model)
                    self._models[(model.aircraft_type, model.airline_icao)].append(model)
        if self.installation.vmr_path:
            self.rules = parse_vmr(self.installation.vmr_path)
        for rule in self.rules:
            if rule.callsign_prefix:
                self._exact[(rule.aircraft_type, rule.callsign_prefix)].append(rule)
            else:
                self._type[rule.aircraft_type].append(rule)
        LOGGER.info(
            "FSLTL détecté (%s), modèles indexés : %d, règles VMR : %d",
            self.installation.version or "version inconnue", len(self.models), len(self.rules),
        )

    def _from_rule(self, rule: VmrRule, kind: MatchKind, level: int) -> ResolvedAircraftModel | None:
        for title in rule.model_titles:
            model = self._titles.get(title.casefold())
            if model:
                return ResolvedAircraftModel(
                    model.title, "FSLTL", kind, level,
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
                    direct[0].title, "FSLTL", MatchKind.EXACT, 0,
                    "aircraft + airline exact match", "aircraft.cfg",
                )
        for rule in self._type.get(aircraft_type, ()):
            result = self._from_rule(rule, MatchKind.AIRCRAFT, 1)
            if result:
                return result
        generic = self._models.get((aircraft_type, "ZZZZ"), ()) or self._models.get((aircraft_type, ""), ())
        if generic:
            return ResolvedAircraftModel(
                generic[0].title, "FSLTL", MatchKind.AIRCRAFT, 1,
                "generic aircraft match", "aircraft.cfg",
            )
        return self._msfs_fallback(msfs_fallback_titles)

    def generic_fallback(
        self, aircraft: TrafficAircraft
    ) -> ResolvedAircraftModel | None:
        """Modèle visible mais neutre quand l'ADS-B ne donne aucun type.

        Un indicatif de compagnie ou une vitesse élevée désigne probablement
        un avion de transport ; sinon le C172 générique évite de transformer
        un appareil léger en monocouloir. Le modèle exact le remplacera dès
        que le registre ICAO24 aura répondu.
        """
        commercial = bool((aircraft.airline_icao or "").strip()) or (
            aircraft.ground_speed_kt is not None
            and aircraft.ground_speed_kt >= 160.0
        )
        preferred = ("A320", "B738", "B737") if commercial else (
            "C172", "A320", "B738"
        )
        for aircraft_type in preferred:
            candidates = (
                self._models.get((aircraft_type, "ZZZZ"), ())
                or self._models.get((aircraft_type, ""), ())
            )
            if candidates:
                return ResolvedAircraftModel(
                    candidates[0].title,
                    "FSLTL",
                    MatchKind.FAMILY,
                    2,
                    "generic real-traffic fallback",
                    "aircraft.cfg",
                )
        return None

    @staticmethod
    def _msfs_fallback(titles: Iterable[str]) -> ResolvedAircraftModel | None:
        title = next((str(item).strip() for item in titles if str(item).strip()), "")
        return ResolvedAircraftModel(
            title, "MSFS", MatchKind.MSFS, 3, "FSLTL match unavailable"
        ) if title else None
