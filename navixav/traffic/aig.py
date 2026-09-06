"""Détection et indexation strictement read-only des modèles AIG (OCI).

AIG se distribue autrement que FSLTL : AI Manager pose les modèles dans
`Community\\aig-aitraffic-oci`, et deux paquets frères — `modelbehavior` et
`effects` — portent les bibliothèques dont ces modèles dépendent. Le trio est
posé par l'installateur d'AIG ; NaviXav le lit et n'y touche jamais.

Deux propriétés du paquet commandent le code : le `aig.vmr` livré à la racine
ne contient qu'une poignée de règles, l'essentiel du matching venant des
`aircraft.cfg` ; et AIG n'a pas de convention de modèle générique équivalente
au `ZZZZ` de FSLTL. `AigModelIndex` n'expose donc pas de `generic_fallback` :
un appareil ADS-B sans type reste sur la carte plutôt que de prendre au hasard
la silhouette d'un jet d'affaires.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from navixav.aircraft.community import community_folders
from navixav.traffic.base import InstallationStatus
from navixav.traffic.simobjects import SimObjectModelIndex

LOGGER = logging.getLogger(__name__)

# L'OCI livre aujourd'hui un dossier unique. Le préfixe plutôt que l'égalité
# couvre l'installation scindée par compagnies qu'AI Manager sait aussi
# produire, sans jamais happer les deux paquets de bibliothèques, qui ne
# commencent pas par `aig-aitraffic-oci`.
PACKAGE_PREFIX = "aig-aitraffic-oci"
COMPANION_PACKAGES = ("aig-aitraffic-modelbehavior", "aig-aitraffic-effects")
AIG_DOWNLOAD_URL = "https://www.alpha-india.net/"
# Une installation OCI complète dépasse de loin le catalogue FSLTL : la borne
# reste une borne, pas une limite atteinte en usage normal.
MAX_CONFIG_FILES = 20000
MAX_VMR_FILES = 3


@dataclass(frozen=True)
class AigInstallation:
    status: InstallationStatus
    roots: tuple[Path, ...] = ()
    version: str = ""
    reason: str = ""
    config_count: int = 0
    vmr_paths: tuple[Path, ...] = ()
    missing_companions: tuple[str, ...] = ()

    @property
    def root(self) -> Path | None:
        return self.roots[0] if self.roots else None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "detected": self.status is InstallationStatus.DETECTED,
            "version": self.version,
            "reason": self.reason,
            "models": self.config_count,
            "vmr": bool(self.vmr_paths),
            "packages": len(self.roots),
            "companions": list(self.missing_companions),
        }


def _package_children(folder: Path) -> Iterator[Path]:
    try:
        for child in sorted(folder.iterdir()):
            if (
                child.is_dir()
                and not child.is_symlink()
                and child.name.casefold().startswith(PACKAGE_PREFIX)
            ):
                yield child
    except OSError:
        return


def _missing_companions(root: Path) -> tuple[str, ...]:
    """Bibliothèques attendues à côté des modèles, jamais indexées.

    Leur absence n'empêche pas un appareil d'apparaître, mais le prive de ses
    animations et de ses effets. Mieux vaut le dire que laisser croire à un
    paquet abîmé.
    """
    parent = root.parent
    return tuple(
        name for name in COMPANION_PACKAGES if not (parent / name).is_dir()
    )


def _vmr_files(root: Path) -> tuple[Path, ...]:
    """Règles VMR posées à la racine du paquet, quel que soit leur nom.

    AIG livre `aig.vmr`, les packs miroirs nomment parfois le leur autrement.
    Ramasser la racine évite un réglage de plus pour un fichier d'appoint.
    """
    try:
        found = [
            path for path in sorted(root.glob("*.vmr"))
            if path.is_file() and not path.is_symlink()
        ]
    except OSError:
        return ()
    return tuple(found[:MAX_VMR_FILES])


def detect_aig(
    folders: Iterable[Path] | None = None,
    *,
    explicit_path: Path | None = None,
) -> AigInstallation:
    """Localise les paquets et distingue absence, paquet incomplet et utilisable."""
    if explicit_path is not None:
        selected = Path(explicit_path).expanduser()
        if selected.is_symlink():
            return AigInstallation(
                InstallationStatus.NOT_DETECTED,
                reason="chemin AIG manuel invalide",
            )
        if selected.is_dir() and selected.name.casefold().startswith(PACKAGE_PREFIX):
            candidates = [selected]
        else:
            candidates = list(_package_children(selected)) if selected.is_dir() else []
        if not candidates:
            return AigInstallation(
                InstallationStatus.NOT_DETECTED,
                reason="modèles AIG absents du chemin manuel",
            )
    else:
        roots = list(folders) if folders is not None else community_folders()
        candidates = [
            child for folder in roots for child in _package_children(Path(folder))
        ]
    if not candidates:
        return AigInstallation(
            InstallationStatus.NOT_DETECTED, reason="modèles AIG absents"
        )

    version = ""
    try:
        raw = json.loads((candidates[0] / "manifest.json").read_text(encoding="utf-8-sig"))
        if isinstance(raw, dict):
            version = str(raw.get("package_version") or "")[:64]
    except (OSError, ValueError):
        return AigInstallation(
            InstallationStatus.INCOMPLETE,
            tuple(candidates),
            reason="manifest.json absent ou invalide",
        )

    configs = 0
    for root in candidates:
        try:
            configs += len(
                list((root / "SimObjects" / "Airplanes").glob("*/aircraft.cfg"))
            )
        except OSError:
            continue
        if configs > MAX_CONFIG_FILES:
            return AigInstallation(
                InstallationStatus.INCOMPLETE,
                tuple(candidates),
                version,
                "trop de fichiers aircraft.cfg",
            )
    if not configs:
        # Le paquet existe mais AI Manager n'y a encore écrit aucune
        # configuration : c'est le cas d'une OCI installée sans compagnie.
        return AigInstallation(
            InstallationStatus.INCOMPLETE,
            tuple(candidates),
            version,
            "aucun aircraft.cfg",
        )

    vmr_paths = tuple(path for root in candidates for path in _vmr_files(root))
    return AigInstallation(
        InstallationStatus.DETECTED,
        tuple(candidates),
        version,
        config_count=configs,
        vmr_paths=vmr_paths[:MAX_VMR_FILES],
        missing_companions=_missing_companions(candidates[0]),
    )


class AigModelIndex(SimObjectModelIndex):
    """Index AIG : les `aircraft.cfg` des paquets OCI et leurs règles VMR."""

    provider = "AIG"
    unavailable_reason = "AIG match unavailable"

    def __init__(self, installation: AigInstallation) -> None:
        super().__init__()
        self.installation = installation
        if installation.status is InstallationStatus.DETECTED and installation.roots:
            self._index(
                installation.roots,
                installation.vmr_paths,
                max_config_files=MAX_CONFIG_FILES,
            )
            LOGGER.info(
                "AIG détecté (%s), paquets : %d, modèles indexés : %d, règles VMR : %d",
                installation.version or "version inconnue",
                len(installation.roots),
                len(self.models),
                len(self.rules),
            )
            if installation.missing_companions:
                LOGGER.warning(
                    "Bibliothèques AIG manquantes : %s",
                    ", ".join(installation.missing_companions),
                )
