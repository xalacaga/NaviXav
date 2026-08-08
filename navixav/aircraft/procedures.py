"""Procédures de l'appareil chargé, évaluées sans inventer de résultat.

La base décrit des propriétés métier, jamais des SimVars. Ce module relie ces
propriétés à ``AircraftState`` et applique une logique à trois valeurs : vrai,
faux ou inconnu. Une donnée absente reste inconnue et l'interface laisse alors
le pilote confirmer l'étape lui-même.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from navixav.aircraft.matcher import AircraftMatch
from navixav.live.base import AircraftState

LOGGER = logging.getLogger(__name__)

PHASE_ORDER = (
    "before_start",
    "start",
    "after_start",
    "taxi",
    "before_takeoff",
    "takeoff",
    "after_takeoff",
    "climb",
    "cruise",
    "descent",
    "approach",
    "landing",
    "after_landing",
    "shutdown",
)


@lru_cache(maxsize=128)
def _read_procedures(path: str, modified_ns: int) -> dict[str, Any]:
    del modified_ns  # La date fait partie de la clé et invalide seule le cache.
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _procedure_document(match: AircraftMatch) -> dict[str, Any] | None:
    path = match.entry.directory / "procedures.json"
    try:
        return _read_procedures(str(path), path.stat().st_mtime_ns)
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        LOGGER.warning(
            "Procédures avion indisponibles pour %s : %s",
            match.entry.id,
            exc,
        )
        return None


def _property_value(state: AircraftState | None, path: str) -> Any:
    if state is None:
        return None
    if path.startswith("state."):
        value: Any = state
        parts = path.split(".")[1:]
    elif path.startswith("configuration."):
        value = state.configuration
        parts = path.split(".")[1:]
    else:
        return None
    for part in parts:
        if value is None:
            return None
        value = value.get(part) if isinstance(value, dict) else getattr(value, part, None)
    return value


def evaluate_condition(
    condition: Any, state: AircraftState | None
) -> bool | None:
    """Évalue une condition avec propagation stricte de l'inconnu."""
    if not isinstance(condition, dict):
        return None
    if "all_of" in condition:
        results = [evaluate_condition(item, state) for item in condition["all_of"]]
        if any(result is False for result in results):
            return False
        return None if any(result is None for result in results) else True
    if "any_of" in condition:
        results = [evaluate_condition(item, state) for item in condition["any_of"]]
        if any(result is True for result in results):
            return True
        return None if any(result is None for result in results) else False
    if "not" in condition:
        result = evaluate_condition(condition["not"], state)
        return None if result is None else not result

    value = _property_value(state, str(condition.get("property", "")))
    if value is None:
        return None
    try:
        if "is" in condition:
            return value == condition["is"]
        if "at_least" in condition:
            return value >= condition["at_least"]
        if "at_most" in condition:
            return value <= condition["at_most"]
        if "between" in condition:
            low, high = condition["between"]
            return low <= value <= high
        if "one_of" in condition:
            return value in condition["one_of"]
    except (TypeError, ValueError):
        return None
    return None


def _step_payload(
    step: dict[str, Any], state: AircraftState | None
) -> dict[str, Any]:
    mode = str(step.get("mode", "manual"))
    automatic = evaluate_condition(step.get("check"), state) if mode == "auto" else None
    if mode == "auto":
        status = "complete" if automatic is True else "unknown" if automatic is None else "pending"
    else:
        status = mode
    return {
        key: step[key]
        for key in ("id", "group", "title", "expected", "mode", "note")
        if key in step
    } | {"status": status}


def procedure_payload(
    match: AircraftMatch | None,
    state: AircraftState | None = None,
) -> dict[str, Any]:
    """Rend la procédure normale filtrée pour l'appareil et son état réel."""
    if match is None:
        return {"available": False, "reason": "aircraft_not_covered", "phases": []}
    document = _procedure_document(match)
    if document is None:
        return {
            "available": False,
            "reason": "procedures_unavailable",
            "aircraft": match.to_dict(),
            "phases": [],
        }

    systems = match.systems
    procedures = []
    for raw in document.get("procedures", []):
        if not isinstance(raw, dict) or raw.get("kind", "normal") != "normal":
            continue
        steps = [
            _step_payload(step, state)
            for step in raw.get("steps", [])
            if isinstance(step, dict)
            and (
                not step.get("requires_system")
                or systems.get(str(step["requires_system"])) is True
            )
        ]
        procedures.append(
            {
                "id": str(raw.get("id", raw.get("phase", ""))),
                "phase": str(raw.get("phase", "")),
                "title": str(raw.get("title", "")),
                "steps": steps,
            }
        )
    order = {phase: index for index, phase in enumerate(PHASE_ORDER)}
    procedures.sort(key=lambda item: order.get(item["phase"], len(order)))
    return {
        "available": bool(procedures),
        "reason": "" if procedures else "procedures_unavailable",
        "aircraft": match.to_dict(),
        "source": str(document.get("source", "")),
        "phases": procedures,
    }
