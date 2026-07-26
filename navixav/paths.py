"""Chemins de ressources et de données pour le développement et l'exécutable."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Indique si NaviXav s'exécute depuis le paquet PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """Racine en lecture seule des fichiers livrés avec NaviXav."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle)
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def user_data_dir() -> Path:
    """Dossier persistant et inscriptible de l'utilisateur courant."""
    override = os.getenv("NAVIXAV_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    if not is_frozen():
        return resource_root() / "data"
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / "NaviXav"


def user_data_path(*parts: str) -> Path:
    return user_data_dir().joinpath(*parts)
