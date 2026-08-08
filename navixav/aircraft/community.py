"""Inventaire des appareils installés par l'utilisateur.

Personne ne peut deviner ce qu'un utilisateur a installé, ni où. Ce module va
donc le lire : il localise le dossier des paquets du simulateur, y recense les
appareils, et dit lesquels la base d'avions couvre déjà.

Le chemin n'est jamais supposé. Il est lu dans `UserCfg.opt`, que MSFS écrit à
un endroit connu quelle que soit la version et la boutique, et il peut de toute
façon être imposé par les réglages : un utilisateur a le droit d'avoir installé
son simulateur où il veut.

Rien n'est écrit ici. Ce module lit, il ne produit que des constats.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# `InstalledPackagesPath "D:\MSFS2024"`, tel que MSFS l'écrit.
_PACKAGES_PATH = re.compile(r'^\s*InstalledPackagesPath\s+"(?P<path>[^"]+)"', re.MULTILINE)

# aircraft.cfg n'est pas un vrai fichier INI : les sections `[FLTSIM.n]` se
# répètent et `configparser` s'y refuse. Une lecture ligne à ligne suffit.
_ENTRY = re.compile(r'^\s*(?P<key>[A-Za-z_0-9]+)\s*=\s*(?P<value>.*?)\s*(?:;.*)?$')

# `engine_type` de MSFS. 2 et 4 ne concernent aucun appareil suivi par NaviXav.
_ENGINE_TYPES = {0: "piston", 1: "turbofan", 3: "turbine", 5: "turboprop"}

_INTERESTING = frozenset(
    {
        "title",
        "ui_manufacturer",
        "ui_type",
        "ui_variation",
        "icao_type_designator",
        "number_of_engines",
        "engine_type",
        "isairtraffic",
        "base_container",
    }
)

_SECTION = re.compile(r"^\s*\[(?P<name>[^\]]+)\]")


def _environment_path(variable: str, *parts: str) -> Path | None:
    root = os.getenv(variable, "").strip()
    return Path(root).joinpath(*parts) if root else None


def user_config_candidates() -> list[Path]:
    """Emplacements connus de `UserCfg.opt`, boutique et version confondues."""
    candidates = [
        _environment_path(
            "LOCALAPPDATA", "Packages",
            "Microsoft.FlightSimulator_8wekyb3d8bbwe", "LocalCache", "UserCfg.opt"),
        _environment_path(
            "LOCALAPPDATA", "Packages",
            "Microsoft.Limitless_8wekyb3d8bbwe", "LocalCache", "UserCfg.opt"),
        _environment_path("APPDATA", "Microsoft Flight Simulator", "UserCfg.opt"),
        _environment_path("APPDATA", "Microsoft Flight Simulator 2024", "UserCfg.opt"),
    ]
    return [path for path in candidates if path is not None]


def packages_paths(candidates: Iterable[Path] | None = None) -> list[Path]:
    """Dossiers de paquets déclarés par les `UserCfg.opt` présents."""
    found: list[Path] = []
    for config in candidates if candidates is not None else user_config_candidates():
        try:
            text = config.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = _PACKAGES_PATH.search(text)
        if not match:
            continue
        path = Path(match.group("path"))
        if path.is_dir() and path not in found:
            found.append(path)
    return found


def community_folders(
    explicit: Iterable[Path] | None = None,
    candidates: Iterable[Path] | None = None,
) -> list[Path]:
    """Dossiers Community à examiner.

    Un chemin donné par l'utilisateur l'emporte sur toute détection : c'est le
    seul recours quand le simulateur est installé hors des chemins connus. Il
    est accepté qu'il désigne le dossier Community lui-même ou son parent.

    Sans chemin explicite, tous les `Community*` des dossiers de paquets sont
    retenus — MSFS 2024 en installe deux, un par version du contenu.
    """
    if explicit is not None:
        folders = []
        for path in explicit:
            path = Path(path).expanduser()
            if not path.is_dir():
                logger.info("Dossier Community introuvable : %s", path)
                continue
            folders.extend([path] if path.name.lower().startswith("community")
                           else _community_children(path))
        return folders

    folders: list[Path] = []
    for packages in packages_paths(candidates):
        folders.extend(_community_children(packages))
    return folders


def _community_children(parent: Path) -> list[Path]:
    try:
        children = sorted(parent.iterdir())
    except OSError:
        return []
    return [c for c in children if c.is_dir() and c.name.lower().startswith("community")]


@dataclass(frozen=True)
class InstalledAircraft:
    """Un appareil installé, tel que son `aircraft.cfg` le décrit."""

    package: str
    directory: Path
    titles: tuple[str, ...] = ()
    manufacturer: str = ""
    model: str = ""
    icao: str = ""
    engine_count: int = 0
    engine_type: str = ""
    checklist: Path | None = None
    # Un paquet de livrée seule ne décrit aucun appareil : il ajoute des titres
    # à un avion installé ailleurs, et n'a donc ni moteur ni performances.
    livery_only: bool = False

    @property
    def key(self) -> tuple[str, str, str]:
        """Identité d'un modèle, livrées confondues.

        Un paquet de trafic embarque des centaines de décorations du même
        appareil : sans ce regroupement, l'inventaire serait illisible.
        """
        return (self.manufacturer.lower(), self.model.lower(), self.icao.upper())

    @property
    def label(self) -> str:
        # « Cessna 208B Grand Caravan EX » nomme déjà son constructeur : le
        # préfixer donnerait « Cessna Cessna 208B ».
        if self.model and self.model.lower().startswith(self.manufacturer.lower()):
            return self.model
        parts = [p for p in (self.manufacturer, self.model) if p]
        return " ".join(parts) or (self.titles[0] if self.titles else self.directory.name)


def _read_config(path: Path) -> dict[str, list[str]]:
    """Valeurs qui nous intéressent, toutes occurrences gardées."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = path.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except OSError:
            return {}
    else:
        return {}

    values: dict[str, list[str]] = {}
    current: dict[str, str] | None = None
    variations: list[dict[str, str]] = []

    for line in text.splitlines():
        section = _SECTION.match(line)
        if section:
            # Chaque `[FLTSIM.n]` décrit une livrée, avec son propre drapeau de
            # trafic : le tri se fait par bloc, pas par fichier.
            if section.group("name").lower().startswith("fltsim"):
                current = {}
                variations.append(current)
            else:
                current = None
            continue

        match = _ENTRY.match(line)
        if not match:
            continue
        key = match.group("key").lower()
        if key not in _INTERESTING:
            continue
        value = match.group("value").strip().strip('"').strip()
        # « TT:AIRCRAFT.UI_MANUFACTURER » est une clé de traduction que le
        # simulateur résout à l'affichage. Non résolue, elle ne nomme rien.
        if not value or value.upper().startswith("TT:"):
            continue
        values.setdefault(key, []).append(value)
        if current is not None:
            current[key] = value

    values["__variations__"] = variations  # type: ignore[assignment]
    return values


def _first(values: dict[str, list[str]], key: str, default: str = "") -> str:
    found = values.get(key)
    return found[0] if found else default


def _checklist_beside(directory: Path) -> Path | None:
    folder = directory / "Checklist"
    if not folder.is_dir():
        return None
    files = sorted(folder.glob("*.xml"))
    return files[0] if files else None


def read_aircraft(directory: Path, package: str) -> InstalledAircraft | None:
    """Lit un dossier `SimObjects/Airplanes/<x>`, ou None s'il n'apprend rien."""
    values = _read_config(directory / "aircraft.cfg")
    variations: list[dict[str, str]] = values.pop("__variations__", [])  # type: ignore[assignment]

    # Les paquets de trafic embarquent des milliers de livrées que personne ne
    # pilote : elles portent `isAirTraffic = 1` et n'ont rien à faire dans un
    # inventaire d'appareils. Un appareil dont toutes les livrées sont du
    # trafic disparaît entièrement.
    flyable = [
        block["title"]
        for block in variations
        if block.get("title") and block.get("isairtraffic", "0").strip() != "1"
    ]
    titles = tuple(dict.fromkeys(flyable or ()))
    if not titles and not variations:
        titles = tuple(dict.fromkeys(values.get("title", ())))
    if not titles:
        return None

    try:
        engine_count = int(float(_first(values, "number_of_engines", "0")))
    except ValueError:
        engine_count = 0
    try:
        engine_type = _ENGINE_TYPES.get(int(float(_first(values, "engine_type", "-1"))), "")
    except ValueError:
        engine_type = ""

    manufacturer = _first(values, "ui_manufacturer")
    model = _first(values, "ui_type")
    if not manufacturer and model:
        # « Cessna 208B Grand Caravan EX » sans constructeur déclaré : le
        # premier mot du modèle vaut mieux que « inconnu » dans un chemin.
        manufacturer = model.split()[0]

    return InstalledAircraft(
        package=package,
        directory=directory,
        titles=titles,
        livery_only=bool(_first(values, "base_container")),
        manufacturer=manufacturer,
        model=model,
        icao=_first(values, "icao_type_designator").upper(),
        engine_count=engine_count,
        engine_type=engine_type,
        checklist=_checklist_beside(directory),
    )


def scan(folders: Iterable[Path]) -> list[InstalledAircraft]:
    """Appareils installés dans les dossiers donnés, un par modèle.

    Les décorations sont fusionnées : le premier dossier rencontré fournit les
    métadonnées, et les titres de tous les autres viennent s'y ajouter, parce
    que ce sont eux que le simulateur publiera.
    """
    merged: dict[tuple[str, str, str], InstalledAircraft] = {}
    for folder in folders:
        for config in sorted(folder.glob("*/SimObjects/Airplanes/*/aircraft.cfg")):
            package = config.relative_to(folder).parts[0]
            aircraft = read_aircraft(config.parent, package)
            if aircraft is None:
                continue
            previous = merged.get(aircraft.key)
            if previous is None:
                merged[aircraft.key] = aircraft
                continue
            titles = tuple(dict.fromkeys(previous.titles + aircraft.titles))
            merged[aircraft.key] = replace_titles(
                previous, titles, previous.checklist or aircraft.checklist
            )
    return sorted(merged.values(), key=lambda a: a.label.lower())


def replace_titles(
    aircraft: InstalledAircraft, titles: tuple[str, ...], checklist: Path | None
) -> InstalledAircraft:
    return InstalledAircraft(
        package=aircraft.package,
        directory=aircraft.directory,
        titles=titles,
        manufacturer=aircraft.manufacturer,
        model=aircraft.model,
        icao=aircraft.icao,
        engine_count=aircraft.engine_count,
        engine_type=aircraft.engine_type,
        checklist=checklist,
        livery_only=aircraft.livery_only,
    )


@dataclass
class Survey:
    """Ce que l'inventaire a trouvé, face à la base d'avions."""

    folders: list[Path] = field(default_factory=list)
    covered: list[tuple[InstalledAircraft, str, str]] = field(default_factory=list)
    missing: list[InstalledAircraft] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.covered) + len(self.missing)

    def to_dict(self) -> dict[str, object]:
        return {
            "folders": [str(f) for f in self.folders],
            "total": self.total,
            "covered": [
                {"label": a.label, "icao": a.icao, "aircraft": i, "maturity": m}
                for a, i, m in self.covered
            ],
            "missing": [
                {
                    "label": a.label,
                    "icao": a.icao,
                    "package": a.package,
                    "engines": a.engine_count,
                    "engine_type": a.engine_type,
                    "has_checklist": a.checklist is not None,
                    "livery_only": a.livery_only,
                }
                for a in self.missing
            ],
        }


def survey(matcher, folders: Iterable[Path]) -> Survey:
    """Confronte les appareils installés à ce que la base sait déjà faire.

    `matcher` est un `AircraftMatcher` ; il n'est pas importé ici pour que ce
    module reste purement descriptif et testable sans base.
    """
    folders = list(folders)
    result = Survey(folders=folders)
    for aircraft in scan(folders):
        match = _consensus(matcher, aircraft.titles)
        if match is None:
            result.missing.append(aircraft)
        else:
            result.covered.append((aircraft, match.entry.id, match.entry.maturity))
    return result


def _consensus(matcher, titles: Iterable[str]):
    """Famille sur laquelle la majorité des livrées s'accorde.

    Retenir la première livrée qui matche laisserait une décoration isolée
    décider pour tout un modèle : une compagnie fictive nommée « Skyhawk » sur
    un A330 suffirait à le faire passer pour un Cessna 172.
    """
    matches: dict[str, tuple[int, Any]] = {}
    for title in titles:
        match = matcher.match(title)
        if match is None:
            continue
        count, kept = matches.get(match.entry.id, (0, match))
        matches[match.entry.id] = (count + 1, kept)
    if not matches:
        return None
    return max(matches.values(), key=lambda item: item[0])[1]
