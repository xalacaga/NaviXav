"""Extraction des données de navigation directement depuis MSFS.

Passe par l'API Facilities de SimConnect : aucune application tierce, aucun
abonnement. Les définitions de champs de `fields.py` ont été établies par
sondage contre MSFS 2024, pas déduites d'une documentation.
"""

from __future__ import annotations

from navixav.msfs.client import SimConnectClient, SimConnectError
from navixav.msfs.extract import extract_airport

__all__ = ["SimConnectClient", "SimConnectError", "extract_airport"]
