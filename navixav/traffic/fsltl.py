"""Détection et indexation strictement read-only de FSLTL Base Models."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from navixav.aircraft.community import community_folders
from navixav.traffic.base import (
    InstallationStatus,
    MatchKind,
    ResolvedAircraftModel,
    TrafficAircraft,
)
from navixav.traffic.simobjects import (
    MAX_CONFIG_BYTES,
    MAX_VALUE_LENGTH,
    MAX_VMR_BYTES,
    SimObjectModel,
    SimObjectModelIndex,
    VmrRule,
    parse_aircraft_config,
    parse_vmr,
)

LOGGER = logging.getLogger(__name__)

PACKAGE_NAME = "fsltl-traffic-base"
FSLTL_DOWNLOAD_URL = "https://flybywiresim.com/downloads/"
MAX_CONFIG_FILES = 5000

# Le statut ne dit rien de FSLTL en particulier : il vaut pour n'importe quel
# jeu de modèles. Le nom historique reste, il est écrit dans tout le module.
FsltlStatus = InstallationStatus
# Les modèles lus dans un `aircraft.cfg` n'ont rien de propre à FSLTL non plus.
FsltlModel = SimObjectModel

__all__ = [
    "FSLTL_DOWNLOAD_URL",
    "MAX_CONFIG_BYTES",
    "MAX_CONFIG_FILES",
    "MAX_VALUE_LENGTH",
    "MAX_VMR_BYTES",
    "PACKAGE_NAME",
    "FsltlInstallation",
    "FsltlModel",
    "FsltlModelIndex",
    "FsltlStatus",
    "VmrRule",
    "detect_fsltl",
    "parse_aircraft_config",
    "parse_vmr",
]


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


class FsltlModelIndex(SimObjectModelIndex):
    """Index FSLTL : les `aircraft.cfg` du paquet et ses règles VMR."""

    provider = "FSLTL"
    unavailable_reason = "FSLTL match unavailable"

    def __init__(self, installation: FsltlInstallation) -> None:
        super().__init__()
        self.installation = installation
        if installation.status is FsltlStatus.DETECTED and installation.root:
            self._index(
                [installation.root],
                [installation.vmr_path] if installation.vmr_path else [],
                max_config_files=MAX_CONFIG_FILES,
            )
            LOGGER.info(
                "FSLTL détecté (%s), modèles indexés : %d, règles VMR : %d",
                installation.version or "version inconnue",
                len(self.models),
                len(self.rules),
            )

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
                    self.provider,
                    MatchKind.FAMILY,
                    2,
                    "generic real-traffic fallback",
                    "aircraft.cfg",
                )
        return None
