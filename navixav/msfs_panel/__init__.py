"""Paquet Communauté du panneau NaviXav, installé seulement sur demande.

Le panneau ajoute une icône dans la barre d'outils de MSFS et interroge le
service local ; il ne fait rien que l'application ne fasse déjà. Il vit dans
`Community`, c'est-à-dire chez l'utilisateur, au milieu de ses propres
paquets : NaviXav ne l'y pose donc jamais de lui-même. L'installateur n'y
touche pas, la mise à jour non plus, et seul un geste explicite dans les
réglages l'écrit ou le retire.

Le retrait ne supprime que le dossier que nous avons écrit, reconnu à son nom
et à son manifeste : rien d'autre dans `Community` ne doit pouvoir disparaître
à cause de nous.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from navixav.aircraft.community import community_folders
from navixav.paths import resource_path

LOGGER = logging.getLogger(__name__)

PACKAGE_NAME = "navixav-toolbar"
PANEL_FILE = "InGamePanels/navixav-toolbar.spb"
# Décalage entre l'époque Unix et celle de Windows, en centaines de
# nanosecondes : `layout.json` date ses fichiers comme le simulateur les date.
FILETIME_EPOCH_OFFSET = 116444736000000000


@dataclass(frozen=True)
class PanelStatus:
    """Ce que l'interface a besoin de savoir avant de proposer le geste."""

    available: bool
    installed: bool
    version: str = ""
    installed_version: str = ""
    path: str = ""
    community: str = ""
    complete: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "installed": self.installed,
            "version": self.version,
            "installed_version": self.installed_version,
            "path": self.path,
            "community": self.community,
            "complete": self.complete,
        }


def bundled_package() -> Path:
    """Dossier du paquet livré avec NaviXav, source de toute installation."""
    return resource_path(f"navixav/msfs_panel/{PACKAGE_NAME}")


def _version_of(package: Path) -> str:
    try:
        raw = json.loads((package / "manifest.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return ""
    return str(raw.get("package_version") or "")[:64] if isinstance(raw, dict) else ""


def _target_community(folders: Iterable[Path] | None = None) -> Path | None:
    """Premier dossier Communauté utilisable, celui que MSFS lit vraiment."""
    candidates = list(folders) if folders is not None else community_folders()
    for folder in candidates:
        path = Path(folder)
        if path.is_dir():
            return path
    return None


def installed_package(folders: Iterable[Path] | None = None) -> Path | None:
    candidates = list(folders) if folders is not None else community_folders()
    for folder in candidates:
        path = Path(folder) / PACKAGE_NAME
        if path.is_dir() and not path.is_symlink():
            return path
    return None


def status(folders: Iterable[Path] | None = None) -> PanelStatus:
    bundled = bundled_package()
    available = (bundled / "manifest.json").is_file()
    # Sans le `.spb` compilé, le paquet se copierait sans jamais apparaître
    # dans la barre d'outils : mieux vaut ne pas proposer le geste.
    complete = available and (bundled / PANEL_FILE).is_file()
    community = _target_community(folders)
    installed = installed_package(folders)
    return PanelStatus(
        available=available,
        installed=installed is not None,
        version=_version_of(bundled) if available else "",
        installed_version=_version_of(installed) if installed else "",
        path=str(installed) if installed else "",
        community=str(community) if community else "",
        complete=complete,
    )


def _write_layout(package: Path) -> None:
    """Décrit le paquet comme le simulateur l'attend, après la copie.

    `layout.json` est écrit ici plutôt que livré figé : il doit refléter les
    tailles et les dates réelles des fichiers posés sur ce disque, et non
    celles de la machine qui a construit la distribution.
    """
    content = []
    for path in sorted(package.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(package).as_posix()
        if relative in {"layout.json", "manifest.json"}:
            continue
        stat = path.stat()
        content.append({
            "path": relative,
            "size": stat.st_size,
            "date": int(stat.st_mtime * 10_000_000) + FILETIME_EPOCH_OFFSET,
        })
    (package / "layout.json").write_text(
        json.dumps({"content": content}, indent=2) + "\n", encoding="utf-8"
    )


def install(folders: Iterable[Path] | None = None) -> Path:
    """Copie le paquet dans Community et rend son emplacement."""
    bundled = bundled_package()
    if not (bundled / "manifest.json").is_file():
        raise FileNotFoundError("Le paquet du panneau MSFS est absent de cette version.")
    if not (bundled / PANEL_FILE).is_file():
        raise FileNotFoundError(
            "Le paquet du panneau MSFS est incomplet : déclaration compilée absente."
        )
    community = _target_community(folders)
    if community is None:
        raise FileNotFoundError("Aucun dossier Communauté MSFS trouvé.")

    target = community / PACKAGE_NAME
    if target.is_symlink():
        raise FileExistsError("Un lien porte déjà ce nom dans Community.")
    if target.exists():
        # Une réinstallation remplace notre propre paquet, jamais un autre :
        # le nom seul ne suffit pas, le manifeste doit être le nôtre.
        if not (target / "manifest.json").is_file():
            raise FileExistsError("Un dossier étranger porte déjà ce nom.")
        shutil.rmtree(target)
    shutil.copytree(bundled, target)
    _write_layout(target)
    LOGGER.info("Panneau MSFS installé dans %s", target)
    return target


def uninstall(folders: Iterable[Path] | None = None) -> bool:
    """Retire le paquet que nous avons écrit, et lui seul."""
    target = installed_package(folders)
    if target is None:
        return False
    if target.name != PACKAGE_NAME or not (target / "manifest.json").is_file():
        raise FileExistsError("Ce dossier n'est pas le paquet du panneau NaviXav.")
    shutil.rmtree(target)
    LOGGER.info("Panneau MSFS retiré de %s", target)
    return True
