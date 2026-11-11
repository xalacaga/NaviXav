"""Présence de GSX Pro sur la machine.

Le module Escale n'a de sens qu'avec GSX Pro : sans lui, l'onglet reste
masqué. L'installateur de FSDreamTeam laisse deux traces stables, vérifiées
sur une installation réelle : le dossier de données de GSX pour MSFS dans
`%APPDATA%\\Virtuali\\GSX\\MSFS`, et le manifeste « GSX Pro *.lw.xml » de son
gestionnaire d'extensions. L'une ou l'autre suffit ; rien n'est lu au-delà de
leur existence.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_ADDON_MANAGER_DIRS = (
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Addon Manager",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Addon Manager",
)


def gsx_installed(
    appdata: str | None = None,
    addon_manager_dirs: tuple[Path, ...] = _ADDON_MANAGER_DIRS,
) -> bool:
    """Vrai si GSX Pro pour MSFS est installé sur cette machine."""
    root = appdata if appdata is not None else os.environ.get("APPDATA", "")
    if root and (Path(root) / "Virtuali" / "GSX" / "MSFS").is_dir():
        return True
    for folder in addon_manager_dirs:
        try:
            if any(folder.glob("GSX Pro*.lw.xml")):
                return True
        except OSError:
            continue
    return False


@lru_cache(maxsize=1)
def gsx_installed_cached() -> bool:
    """Même réponse, calculée une fois par lancement : une installation ne
    change pas pendant une session."""
    return gsx_installed()
