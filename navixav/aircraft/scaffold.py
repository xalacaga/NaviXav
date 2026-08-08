"""Génération d'une famille d'avion dans la base de l'utilisateur.

Partir d'une page blanche décourage. Ce module produit un dossier complet et
valide à partir de ce que le simulateur sait déjà de l'appareil : son
`aircraft.cfg` donne l'identité et les motifs de détection, et sa checklist
native — quand il en livre une — donne les procédures.

Deux garde-fous tiennent tout le reste :

* l'écriture ne vise que la base de l'utilisateur, jamais celle livrée. Une
  checklist d'addon est du contenu payant : elle est convertie sur la machine
  de celui qui a acheté l'appareil, pour son usage, et ne part nulle part.
* le résultat est un **canevas** (`maturity: "draft"`). Il est valide, il n'est
  pas relu. Les vérifications automatiques ne sont posées que là où l'intention
  est certaine, et tout le reste attend une confirmation du pilote.
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Any

from navixav.aircraft.community import InstalledAircraft
from navixav.aircraft.matcher import user_database_root

logger = logging.getLogger(__name__)

ALL_SYSTEMS = (
    "retractable_gear", "flaps", "spoilers", "autopilot", "autothrottle", "anti_ice",
    "pressurisation", "apu", "irs", "fadec", "tcas", "weather_radar", "lnav", "vnav",
    "autobrake", "electrical", "hydraulic", "pneumatic", "fuel",
)

CATEGORIES = {
    ("piston", 1): "single_piston",
    ("piston", 2): "twin_piston",
    ("turboprop", 1): "single_turboprop",
    ("turboprop", 2): "twin_turboprop",
    ("turbofan", 1): "single_turbofan",
    ("turbofan", 2): "light_jet",
    ("turbofan", 4): "widebody_jet",
}

# Ordre décroissant de précision : « after takeoff » doit gagner sur « takeoff ».
PHASES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("cold and dark", "cold & dark"), "cold_and_dark"),
    (("before starting", "before start", "prestart", "pre-start"), "before_start"),
    (("after takeoff", "after take-off"), "after_takeoff"),
    (("before takeoff", "before take-off", "line up", "lineup", "run-up", "run up"), "before_takeoff"),
    (("after landing",), "after_landing"),
    (("before landing", "approach", "descent preparation"), "approach"),
    (("after start", "before taxi"), "after_start"),
    (("preflight", "preliminary", "pre-flight", "cockpit preparation"), "preflight"),
    (("engine start", "starting engine", "start"), "start"),
    (("taxi",), "taxi"),
    (("takeoff", "take-off"), "takeoff"),
    (("climb",), "climb"),
    (("cruise",), "cruise"),
    (("descent", "descend"), "descent"),
    (("landing",), "landing"),
    (("shutdown", "shut down", "securing", "secure", "parking", "post flight"), "shutdown"),
)

_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text: str, fallback: str = "step") -> str:
    cleaned = _SLUG.sub("_", text.lower()).strip("_")
    return cleaned or fallback


def phase_of(title: str) -> str:
    """Phase de vol correspondant à un intitulé de checklist."""
    lowered = title.lower()
    for keywords, phase in PHASES:
        if any(keyword in lowered for keyword in keywords):
            return phase
    return "preflight"


def _light(name: str, expected: str) -> dict[str, Any] | None:
    on = any(word in expected for word in ("on", "bright"))
    off = "off" in expected
    if on == off:
        return None
    return {"property": f"configuration.lights.{name}", "is": on}


def infer_check(title: str, expected: str, systems: dict[str, bool]) -> tuple[dict, str | None] | None:
    """Vérification automatique déduite d'une étape, ou None si incertaine.

    Le doute vaut toujours `manual`. Une étape confirmée à la main coûte un
    clic ; une étape qui se coche seule à tort coûte la confiance dans l'outil.
    """
    t, e = title.lower(), expected.lower()

    def has(system: str) -> bool:
        return systems.get(system, False) is True

    if "parking brake" in t or "park brake" in t:
        released = any(word in e for word in ("release", "off", "released"))
        return {"property": "configuration.parking_brake", "is": not released}, None

    if "gear" in t and "emergency" not in t and "crank" not in t:
        if not has("retractable_gear"):
            return None
        if any(word in e for word in ("up", "retract")):
            return {"property": "configuration.gear_handle_down", "is": False}, "retractable_gear"
        if "down" in e:
            return {
                "all_of": [
                    {"property": "configuration.gear_handle_down", "is": True},
                    {"property": "configuration.gear_extended_pct", "at_least": 99},
                ]
            }, "retractable_gear"
        return None

    if "flap" in t and has("flaps"):
        # Seule la position rentrée est sans ambiguïté : « as required », « set »
        # ou un cran chiffré dépendent des performances du jour.
        if any(word in e for word in ("up", "retract", "0")):
            return {"property": "configuration.flaps_handle_index", "is": 0}, "flaps"
        return None

    if ("speed brake" in t or "speedbrake" in t or "spoiler" in t) and has("spoilers"):
        if "arm" in e:
            return {"property": "configuration.spoilers_armed", "is": True}, "spoilers"
        if any(word in e for word in ("retract", "down", "closed", "stowed")):
            return {"property": "configuration.spoilers_handle_pct", "at_most": 1}, "spoilers"
        return None

    if "autopilot" in t and has("autopilot"):
        if any(word in e for word in ("off", "diseng", "disconnect")):
            return {"property": "configuration.autopilot_master", "is": False}, "autopilot"
        return None

    if ("anti-ice" in t or "anti ice" in t) and has("anti_ice") and "off" in e:
        return {"property": "configuration.engine_anti_ice", "is": False}, "anti_ice"

    for keywords, name in (
        (("strobe",), "strobe"),
        (("beacon", "anti-collision", "anticollision"), "beacon"),
        (("landing light",), "landing"),
        (("taxi light",), "taxi"),
        (("navigation light", "nav light", "position light"), "nav"),
        (("wing light", "wing inspection"), "wing"),
        (("logo light",), "logo"),
    ):
        if any(keyword in t for keyword in keywords):
            check = _light(name, e)
            return (check, None) if check else None

    return None


def read_msfs_checklist(path: Path) -> list[tuple[str, list[tuple[str, str]]]]:
    """Pages d'une checklist native MSFS : (intitulé, [(étape, attendu)])."""
    root = ElementTree.parse(path).getroot()
    pages = []
    for page in root.iter("Page"):
        items = []
        for checkpoint in page.iter("CheckpointDesc"):
            subject = checkpoint.get("SubjectTT")
            if subject:
                items.append((subject.strip(), (checkpoint.get("ExpectationTT") or "").strip()))
        if items:
            pages.append(((page.get("SubjectTT") or "CHECKLIST").strip(), items))
    return pages


def _unique(identifier: str, seen: set[str]) -> str:
    candidate, index = identifier, 2
    while candidate in seen:
        candidate, index = f"{identifier}_{index}", index + 1
    seen.add(candidate)
    return candidate


def procedures_from_checklist(
    pages: list[tuple[str, list[tuple[str, str]]]], systems: dict[str, bool]
) -> list[dict[str, Any]]:
    """Convertit une checklist du simulateur en procédures de la base."""
    procedures = []
    used: set[str] = set()
    for title, items in pages:
        steps = []
        step_ids: set[str] = set()
        for subject, expected in items:
            step: dict[str, Any] = {
                "id": _unique(slug(subject), step_ids),
                "title": subject.upper(),
                "expected": expected.upper(),
                "mode": "manual",
            }
            inferred = infer_check(subject, expected, systems)
            if inferred is not None:
                check, required = inferred
                step["mode"] = "auto"
                step["check"] = check
                if required:
                    step["requires_system"] = required
            steps.append(step)
        procedures.append(
            {
                "id": _unique(slug(title, "checklist"), used),
                "phase": phase_of(title),
                "kind": "normal",
                "title": title.upper(),
                "steps": steps,
            }
        )
    return procedures


def derive_patterns(aircraft: InstalledAircraft) -> list[str]:
    """Motifs de détection, vérifiés contre les titres réels de l'appareil.

    Un motif qui ne reconnaît aucun titre installé serait un motif mort : seuls
    ceux qui matchent vraiment sont retenus.
    """
    titles = [title.lower() for title in aircraft.titles]
    proposals = [
        f"{aircraft.manufacturer} {aircraft.model}".strip().lower(),
        aircraft.model.strip().lower(),
    ]
    patterns = [p for p in dict.fromkeys(proposals) if p and any(p in t for t in titles)]
    if patterns:
        return patterns
    # Aucun champ ne se retrouve dans les titres : le début du premier titre
    # reste le meilleur repère disponible.
    words = titles[0].split() if titles else []
    return [" ".join(words[:2])] if words else []


def infer_systems(aircraft: InstalledAircraft) -> dict[str, bool]:
    """Systèmes déduits du type d'appareil, prudemment.

    `retractable_gear` est déclaré absent par défaut, et ce n'est pas de la
    paresse : un train déclaré absent à tort fait seulement disparaître des
    étapes, alors qu'un train déclaré présent à tort produit une étape qui ne
    se coche jamais. Le doute penche du côté silencieux.
    """
    engine = aircraft.engine_type
    jet = engine in {"turbofan", "turboprop", "turbine"}
    systems = dict.fromkeys(ALL_SYSTEMS, False)
    systems.update(
        {
            "flaps": True,
            "electrical": True,
            "fuel": True,
            "autopilot": True,
            "hydraulic": jet,
            "pneumatic": jet,
            "pressurisation": engine == "turbofan" and aircraft.engine_count >= 2,
            "anti_ice": jet,
            "fadec": engine == "turbofan",
        }
    )
    return systems


def build_entry(aircraft: InstalledAircraft, identifier: str) -> dict[str, dict[str, Any]]:
    """Les cinq fichiers d'une famille, prêts à être écrits."""
    systems = infer_systems(aircraft)
    patterns = derive_patterns(aircraft)

    pages: list[tuple[str, list[tuple[str, str]]]] = []
    if aircraft.checklist is not None:
        try:
            pages = read_msfs_checklist(aircraft.checklist)
        except (OSError, ElementTree.ParseError) as exc:
            logger.info("Checklist illisible pour %s (%s)", aircraft.label, exc)

    if pages:
        procedures = procedures_from_checklist(pages, systems)
        origin = (
            "Converti depuis la checklist livrée avec l'appareil installé, sur cette machine "
            "et pour cet usage. Rien n'est publié ni redistribué."
        )
    else:
        procedures = [
            {
                "id": "before_takeoff",
                "phase": "before_takeoff",
                "kind": "normal",
                "title": "BEFORE TAKEOFF",
                "steps": [
                    {
                        "id": "parking_brake",
                        "title": "PARKING BRAKE",
                        "expected": "SET",
                        "mode": "auto",
                        "check": {"property": "configuration.parking_brake", "is": True},
                    },
                    {
                        "id": "flight_controls",
                        "title": "FLIGHT CONTROLS",
                        "expected": "FREE AND CORRECT",
                        "mode": "manual",
                    },
                ],
            }
        ]
        origin = (
            "L'appareil ne livre pas de checklist : ce squelette est à compléter depuis son "
            "manuel."
        )

    return {
        "metadata": {
            "id": identifier,
            "manufacturer": aircraft.manufacturer or "Inconnu",
            "family": aircraft.model or aircraft.label,
            "model": aircraft.model or aircraft.label,
            "icao_type": aircraft.icao,
            "category": CATEGORIES.get(
                (aircraft.engine_type, aircraft.engine_count), "unknown"),
            "engine_count": aircraft.engine_count,
            "propulsion": aircraft.engine_type or "unknown",
            "crew": 1,
            "certification": "n/a",
            "maturity": "draft",
            "source": origin,
            "note": (
                "Généré par NaviXav depuis « " + aircraft.package + " ». "
                "Relis les systèmes déclarés : le train rentrant est supposé absent tant que "
                "personne ne l'a confirmé."
            ),
            "match": {"title_contains": patterns, "priority": 50},
        },
        "systems": {"systems": systems},
        "procedures": {"source": origin, "procedures": procedures},
        "limitations": {
            "source": "Non renseigné.",
            "note": "Aucune limitation relevée. Une V-speed fausse est pire qu'une absente.",
            "speeds": {},
        },
        "mapping": {
            "default_variant": "default",
            "variants": [
                {
                    "id": "default",
                    "label": aircraft.package,
                    "match": {"title_contains": patterns},
                    "systems": {},
                    "overrides": {},
                }
            ],
        },
    }


def identifier_for(aircraft: InstalledAircraft) -> str:
    """Chemin `<constructeur>/<famille>` de l'appareil dans la base."""
    manufacturer = slug(aircraft.manufacturer, "inconnu")
    family = slug(aircraft.model or aircraft.label, "avion")
    return f"{manufacturer}/{family}"


def write_entry(aircraft: InstalledAircraft, root: Path | None = None) -> Path:
    """Écrit la famille dans la base de l'utilisateur et rend son dossier.

    Un dossier existant est refusé : cette fonction amorce un avion, elle
    n'écrase jamais un travail de relecture déjà fait.
    """
    base = root if root is not None else user_database_root()
    identifier = identifier_for(aircraft)
    directory = base / "aircraft" / identifier
    if directory.exists():
        raise FileExistsError(f"« {identifier} » existe déjà : {directory}")

    entry = build_entry(aircraft, identifier)
    if not entry["metadata"]["match"]["title_contains"]:
        raise ValueError(f"Aucun motif de détection possible pour « {aircraft.label} »")

    directory.mkdir(parents=True)
    for name, payload in entry.items():
        path = directory / f"{name}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return directory
