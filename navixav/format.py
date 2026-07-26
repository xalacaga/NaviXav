"""Mise en forme des grandeurs opérationnelles."""

from __future__ import annotations

from datetime import datetime


def mass(value: int | None, unit: str) -> str | None:
    """Masse ou quantité de carburant, avec séparateur de milliers."""
    if value is None:
        return None
    return f"{value:,}".replace(",", " ") + (f" {unit}" if unit else "")


def duration(seconds: int | None) -> str | None:
    """Durée en heures et minutes, format MCDU (« 1h12 »)."""
    if not seconds:
        return None
    hours, remainder = divmod(int(seconds), 3600)
    minutes = remainder // 60
    return f"{hours}h{minutes:02d}" if hours else f"{minutes} min"


def clock(moment: datetime | None) -> str | None:
    """Heure UTC au format HHMMZ."""
    if moment is None:
        return None
    return moment.strftime("%H%MZ")


def flight_level(altitude_ft: int | None) -> str | None:
    if not altitude_ft:
        return None
    if altitude_ft >= 10000:
        return f"FL{altitude_ft // 100:03d}"
    return f"{altitude_ft} ft"


def distance(nautical_miles: int | None) -> str | None:
    if nautical_miles is None:
        return None
    return f"{nautical_miles} NM"


def ratio(value: int | None, maximum: int | None, unit: str) -> str | None:
    """Valeur rapportée à son maximum, avec la marge restante.

    Rend immédiatement lisible une masse proche des limites.
    """
    formatted = mass(value, unit)
    if formatted is None:
        return None
    if maximum is None or value is None:
        return formatted
    margin = maximum - value
    sign = "-" if margin < 0 else ""
    return f"{formatted}  (max {mass(maximum, unit)}, marge {sign}{mass(abs(margin), unit)})"
