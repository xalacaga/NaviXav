"""Configurations préférentielles de pistes, par aéroport.

Le vent et la longueur ne suffisent pas à reproduire la réalité : beaucoup de
plateformes imposent une répartition (LFBO utilise 32R/14L à l'arrivée et
32L/14R au départ, indépendamment de la longueur). Ces règles ne figurent dans
aucun cycle AIRAC ; elles sont donc déclarées ici, et n'interviennent qu'en
départage — jamais pour retenir une piste hors limites de vent.

Format du fichier JSON :

    {
      "LFBO": {
        "arrival":   ["32R", "14L"],
        "departure": ["32L", "14R"],
        "note": "répartition arrivées / départs"
      }
    }
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

DEFAULT_PREFERENCES_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "airport_preferences.json"
)


@dataclass
class AirportPreference:
    arrival: tuple[str, ...] = ()
    departure: tuple[str, ...] = ()
    note: str = ""


@dataclass
class AirportPreferences:
    entries: dict[str, AirportPreference] = field(default_factory=dict)
    source: Path | None = None

    @classmethod
    def load(cls, path: Path | str | None = None) -> "AirportPreferences":
        target = Path(path) if path else DEFAULT_PREFERENCES_FILE
        if not target.is_file():
            return cls()
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()

        entries: dict[str, AirportPreference] = {}
        for icao, value in raw.items():
            if not isinstance(value, dict):
                continue
            entries[icao.strip().upper()] = AirportPreference(
                arrival=_tuple_of(value.get("arrival")),
                departure=_tuple_of(value.get("departure")),
                note=str(value.get("note", "")),
            )
        return cls(entries=entries, source=target)

    def for_airport(self, icao: str) -> AirportPreference | None:
        return self.entries.get(icao.strip().upper())

    def runways(self, icao: str, for_landing: bool) -> tuple[str, ...]:
        entry = self.for_airport(icao)
        if entry is None:
            return ()
        return entry.arrival if for_landing else entry.departure

    def note(self, icao: str) -> str:
        entry = self.for_airport(icao)
        return entry.note if entry else ""


def _tuple_of(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item).strip().upper() for item in value if str(item).strip())
