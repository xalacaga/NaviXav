"""Carnet de vol local, conservé dans le dossier de données de NaviXav.

Le carnet vivait dans le stockage du WebView : une réinstallation ou un
nettoyage de WebView2 l'effaçait sans prévenir, et une tablette connectée en
réseau local en voyait un autre, vide. Il est désormais tenu par le service,
dans `logbook.json`, et seule la fenêtre du PC l'écrit.

Les entrées restent celles que l'interface compose : le service les conserve,
les compte et les exporte, sans en réinterpréter le contenu. Aucune donnée ne
quitte la machine.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import threading
from collections import Counter
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

FORMAT_VERSION = 1
MAX_ENTRIES = 2000
TOP_COUNT = 5

CSV_COLUMNS = (
    "ended_at",
    "departure",
    "arrival",
    "callsign",
    "aircraft",
    "duration_minutes",
    "distance_nm",
    "max_altitude_ft",
    "landing_airport",
    "landing_runway",
    "touchdown_rate_fpm",
    "landing_score",
    "threshold_distance_m",
    "centerline_offset_m",
    "bounces",
)


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _clean(entries: Any) -> list[dict[str, Any]]:
    """Ne garde que des entrées identifiées, une seule fois chacune."""
    if not isinstance(entries, list):
        return []
    seen: set[str] = set()
    cleaned: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            continue
        seen.add(identifier)
        cleaned.append(entry)
    return cleaned


def _sorted(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda entry: str(entry.get("ended_at") or ""), reverse=True)


def aircraft_name(entry: dict[str, Any]) -> str:
    landing = entry.get("landing") if isinstance(entry.get("landing"), dict) else {}
    return str(entry.get("aircraft") or landing.get("aircraft") or "").strip()


class LogbookStore:
    """Lecture et écriture atomiques du carnet, partagées entre les requêtes."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._entries: list[dict[str, Any]] | None = None

    # ------------------------------------------------------------------ #

    def _load(self) -> list[dict[str, Any]]:
        if self._entries is not None:
            return self._entries
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            payload = {}
        except (OSError, ValueError) as exc:
            # Un fichier illisible est mis de côté plutôt qu'écrasé : il reste
            # récupérable à la main.
            LOGGER.warning("Carnet de vol illisible, mis de côté (%s)", exc)
            try:
                self.path.replace(self.path.with_suffix(".corrupt.json"))
            except OSError:
                pass
            payload = {}
        entries = payload.get("entries") if isinstance(payload, dict) else None
        self._entries = _sorted(_clean(entries))[:MAX_ENTRIES]
        return self._entries

    def _save(self, entries: list[dict[str, Any]]) -> None:
        entries = _sorted(_clean(entries))[:MAX_ENTRIES]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"version": FORMAT_VERSION, "entries": entries},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        os.replace(temporary, self.path)
        self._entries = entries

    # ------------------------------------------------------------------ #

    def entries(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._load())

    def replace(self, entries: Any) -> list[dict[str, Any]]:
        """Remplace tout le carnet par celui que tient la fenêtre du PC."""
        with self._lock:
            self._save(_clean(entries))
            return list(self._entries or [])

    def merge(self, entries: Any) -> list[dict[str, Any]]:
        """Ajoute des vols venus d'ailleurs ; une entrée connue garde sa version."""
        with self._lock:
            current = self._load()
            known = {entry["id"] for entry in current}
            added = [entry for entry in _clean(entries) if entry["id"] not in known]
            if added:
                self._save(current + added)
            return list(self._entries or [])

    def clear(self) -> None:
        with self._lock:
            self._save([])

    # ------------------------------------------------------------------ #

    def stats(self) -> dict[str, Any]:
        return logbook_stats(self.entries())

    def to_csv(self) -> str:
        return logbook_csv(self.entries())


def logbook_stats(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Totaux du carnet, atterrissages et habitudes du pilote."""
    duration = sum(_number(entry.get("duration_seconds")) or 0 for entry in entries)
    distance = sum(_number(entry.get("distance_nm")) or 0 for entry in entries)

    landings = [
        entry["landing"] for entry in entries
        if isinstance(entry.get("landing"), dict)
        and _number(entry["landing"].get("rate_fpm")) is not None
    ]
    best = None
    if landings:
        best = max(
            landings,
            key=lambda landing: (
                _number(landing.get("score")) or 0,
                -(_number(landing.get("rate_fpm")) or 0),
            ),
        )
    scores = [_number(landing.get("score")) for landing in landings]
    scores = [score for score in scores if score is not None]

    aircraft: dict[str, dict[str, Any]] = {}
    for entry in entries:
        name = aircraft_name(entry)
        if not name:
            continue
        row = aircraft.setdefault(name, {"name": name, "flights": 0, "duration_seconds": 0.0})
        row["flights"] += 1
        row["duration_seconds"] += _number(entry.get("duration_seconds")) or 0

    airports: Counter[str] = Counter()
    for entry in entries:
        for key in ("departure", "arrival"):
            icao = str(entry.get(key) or "").strip().upper()
            if icao and icao != "----":
                airports[icao] += 1

    return {
        "flights": len(entries),
        "total_duration_seconds": round(duration),
        "total_distance_nm": round(distance, 1),
        "landings": {
            "count": len(landings),
            "average_rate_fpm": (
                round(sum(_number(l.get("rate_fpm")) or 0 for l in landings) / len(landings))
                if landings else None
            ),
            "average_score": round(sum(scores) / len(scores)) if scores else None,
            "best": {
                key: best.get(key)
                for key in ("rate_fpm", "score", "grade", "airport", "runway", "touched_down_at")
            } if best else None,
        },
        "aircraft": sorted(
            aircraft.values(),
            key=lambda row: (-row["flights"], -row["duration_seconds"], row["name"]),
        )[:TOP_COUNT],
        "airports": [
            {"icao": icao, "visits": visits}
            for icao, visits in sorted(airports.items(), key=lambda item: (-item[1], item[0]))[:TOP_COUNT]
        ],
    }


def logbook_csv(entries: list[dict[str, Any]]) -> str:
    """Export tableur : une ligne par vol, en unités aéronautiques."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)

    def cell(value: Any, digits: int | None = None) -> str:
        number = _number(value)
        if digits is not None and number is not None:
            return f"{number:.{digits}f}"
        return "" if value is None else str(value)

    for entry in entries:
        landing = entry.get("landing") if isinstance(entry.get("landing"), dict) else {}
        duration = _number(entry.get("duration_seconds"))
        writer.writerow((
            cell(entry.get("ended_at")),
            cell(entry.get("departure")),
            cell(entry.get("arrival")),
            cell(entry.get("callsign")),
            aircraft_name(entry),
            cell(duration / 60 if duration is not None else None, 0),
            cell(entry.get("distance_nm"), 1),
            cell(entry.get("max_altitude_ft"), 0),
            cell(landing.get("airport")),
            cell(landing.get("runway")),
            cell(landing.get("rate_fpm"), 0),
            cell(landing.get("score"), 0),
            cell(landing.get("distance_from_threshold_m"), 0),
            cell(landing.get("centerline_offset_m"), 1),
            cell(landing.get("bounces"), 0),
        ))
    # Le BOM permet à Excel de reconnaître l'UTF-8 des indicatifs et des noms.
    return "﻿" + output.getvalue()
