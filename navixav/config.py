"""Configuration de NaviXav, initialisée par l'environnement et l'interface."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_APPROACH_PREFERENCE = (
    "ILS",
    "GLS",
    "LOC",
    "RNAV",
    "VORDME",
    "VOR",
    "NDBDME",
    "NDB",
    "TACAN",
    "VISUAL",
)

USER_SETTINGS_FILE = Path(__file__).resolve().parent.parent / "data" / "user_settings.json"


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "oui", "on"}:
        return True
    if raw in {"0", "false", "no", "non", "off"}:
        return False
    return default


def default_navdata_store() -> Path:
    """Emplacement de la base NaviXav, alimentée depuis MSFS."""
    return Path(__file__).resolve().parent.parent / "data" / "navixav.sqlite"


@dataclass(frozen=True)
class Settings:
    simbrief_pilot_id: str = ""
    simbrief_username: str = ""
    # Chemin de la base NaviXav ; None = emplacement par défaut.
    navdata_store: Path | None = None
    metar_source: str = "simbrief"
    approach_preference: tuple[str, ...] = field(default=DEFAULT_APPROACH_PREFERENCE)
    max_tailwind_kt: int = 10
    max_crosswind_kt: int = 35
    min_runway_length_ft: int = 0
    airport_preferences_path: Path | None = None
    # Qualification RNP de l'avion : conditionne l'accès aux approches dont
    # l'approche interrompue est de type RNAV (ILS Z à LFBO, par exemple).
    aircraft_rnp_capable: bool = True

    @classmethod
    def load(cls, env_file: Path | str | None = None) -> "Settings":
        load_dotenv(dotenv_path=env_file, override=False)

        raw_store = _env("NAVDATA_STORE")

        raw_pref = _env("APPROACH_PREFERENCE")
        preference = (
            tuple(p.strip().upper() for p in raw_pref.split(",") if p.strip())
            if raw_pref
            else DEFAULT_APPROACH_PREFERENCE
        )

        return cls(
            simbrief_pilot_id=_env("SIMBRIEF_PILOT_ID"),
            simbrief_username=_env("SIMBRIEF_USERNAME"),
            navdata_store=Path(raw_store).expanduser() if raw_store else None,
            metar_source=_env("METAR_SOURCE", "simbrief").lower(),
            approach_preference=preference,
            max_tailwind_kt=_env_int("MAX_TAILWIND_KT", 10),
            max_crosswind_kt=_env_int("MAX_CROSSWIND_KT", 35),
            min_runway_length_ft=_env_int("MIN_RUNWAY_LENGTH_FT", 0),
            airport_preferences_path=(
                Path(_env("AIRPORT_PREFERENCES")).expanduser()
                if _env("AIRPORT_PREFERENCES")
                else None
            ),
            aircraft_rnp_capable=_env_bool("AIRCRAFT_RNP_CAPABLE", True),
        )

    def describe_simbrief_target(self) -> str:
        if self.simbrief_pilot_id:
            return f"userid={self.simbrief_pilot_id}"
        if self.simbrief_username:
            return f"username={self.simbrief_username}"
        return "(non configuré)"

    def with_user_values(self, values: dict[str, object]) -> "Settings":
        """Retourne une configuration validée avec les valeurs de l'interface."""
        raw_preference = values.get("approach_preference", self.approach_preference)
        if isinstance(raw_preference, str):
            preference = tuple(
                item.strip().upper()
                for item in raw_preference.split(",")
                if item.strip()
            )
        elif isinstance(raw_preference, (list, tuple)):
            preference = tuple(
                str(item).strip().upper()
                for item in raw_preference
                if str(item).strip()
            )
        else:
            preference = self.approach_preference

        raw_store = str(values.get("navdata_store", "") or "").strip()
        return Settings(
            simbrief_pilot_id=str(values.get("simbrief_pilot_id", "") or "").strip(),
            simbrief_username=str(values.get("simbrief_username", "") or "").strip(),
            navdata_store=Path(raw_store).expanduser() if raw_store else self.navdata_store,
            metar_source=str(values.get("metar_source", self.metar_source) or "simbrief")
            .strip()
            .lower(),
            approach_preference=preference or DEFAULT_APPROACH_PREFERENCE,
            max_tailwind_kt=int(values.get("max_tailwind_kt", self.max_tailwind_kt)),
            max_crosswind_kt=int(values.get("max_crosswind_kt", self.max_crosswind_kt)),
            min_runway_length_ft=int(
                values.get("min_runway_length_ft", self.min_runway_length_ft)
            ),
            airport_preferences_path=self.airport_preferences_path,
            aircraft_rnp_capable=bool(
                values.get("aircraft_rnp_capable", self.aircraft_rnp_capable)
            ),
        )

    def user_values(self) -> dict[str, object]:
        return {
            "simbrief_pilot_id": self.simbrief_pilot_id,
            "simbrief_username": self.simbrief_username,
            "navdata_store": str(self.navdata_store) if self.navdata_store else "",
            "metar_source": self.metar_source,
            "approach_preference": list(self.approach_preference),
            "max_tailwind_kt": self.max_tailwind_kt,
            "max_crosswind_kt": self.max_crosswind_kt,
            "min_runway_length_ft": self.min_runway_length_ft,
            "aircraft_rnp_capable": self.aircraft_rnp_capable,
        }


def load_user_settings(base: Settings, path: Path = USER_SETTINGS_FILE) -> Settings:
    if not path.is_file():
        return base
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
        return base.with_user_values(values) if isinstance(values, dict) else base
    except (OSError, ValueError, TypeError):
        return base


def save_user_settings(settings: Settings, path: Path = USER_SETTINGS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(settings.user_values(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
