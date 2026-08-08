"""Couverture d'un avion NADB face à une checklist publiée.

L'outil **compare**, il ne traduit pas. Il lit une source externe restée chez
elle, la rapproche des procédures de la base et dit ce qui manque. Rien n'est
recopié : le rapport sort sur la sortie standard, aucun fichier de la base
n'est écrit.

C'est la raison pour laquelle il survit aux mises à jour amont. Un importeur
casse quand le format change ; un compteur, non — et surtout, aucune source
publiée ne contient les prédicats `check`, les `systems` ni les phases, qui
sont l'essentiel du travail. Seul le texte des étapes est comparable, et c'est
exactement ce que fait cet outil.

    python aircraft_db/tools/coverage.py cessna/c172 --source ~/clones/checklists/c172.json
    python aircraft_db/tools/coverage.py cessna/c172 --source ~/clones/fgaddon/c172p/checklists.xml

    python aircraft_db/tools/coverage.py cessna/c172 --source "D:/MSFS2024/.../C172_Checklist.xml"

Trois formats sont reconnus. Le JSON par son extension, les deux XML par leur
racine :

    .json   aircraft-multi-crew-checklists   { checklists: [ { name, items: [ { checkpoint, value } ] } ] }
    .xml    FlightGear                       <PropertyList><checklist><title><item><name><value>
    .xml    MSFS                             <SimBase.Document><Page SubjectTT><CheckpointDesc>

Le format MSFS est le plus utile en pratique : c'est celui que livrent les
appareils du simulateur, ceux d'Asobo comme les addons. Il se lit depuis le
dossier du simulateur, qui n'est pas la base — la règle du garde-fou vaut là
aussi.

Le rapprochement se fait sur la **ressemblance du texte**, pas sur le sens. Une
étape signalée absente demande une lecture humaine avant d'être ajoutée, et son
contenu doit être écrit depuis le POH, jamais recopié depuis la source.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

DB_ROOT = Path(__file__).resolve().parent.parent

# Au-delà, deux libellés désignent la même étape. Réglé pour tolérer les
# variantes d'écriture (« FUEL SELECTOR » / « FUEL SELECTOR VALVE ») sans
# confondre deux étapes distinctes de la même checklist.
STEP_THRESHOLD = 0.72
PROCEDURE_THRESHOLD = 0.55

_NOISE = re.compile(r"[^A-Z0-9 ]+")
_SPACES = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Réduit un libellé à ce qui est comparable d'une source à l'autre."""
    # Les points de conduite (« FLAPS ....... UP ») sont de la mise en forme.
    return _SPACES.sub(" ", _NOISE.sub(" ", text.upper())).strip()


@dataclass
class Item:
    title: str
    expected: str = ""

    @property
    def key(self) -> str:
        return normalise(self.title)

    def __str__(self) -> str:
        return f"{self.title} — {self.expected}" if self.expected else self.title


@dataclass
class Section:
    title: str
    items: list[Item] = field(default_factory=list)

    @property
    def key(self) -> str:
        return normalise(self.title)


# --------------------------------------------------------------------- #
# Lecture de la base


def read_database(root: Path, aircraft: str) -> list[Section]:
    path = root / "aircraft" / aircraft / "procedures.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    sections = []
    for procedure in data["procedures"]:
        items = [
            Item(step["title"], step.get("expected", ""))
            for step in procedure["steps"]
        ]
        sections.append(Section(procedure["title"], items))
    return sections


# --------------------------------------------------------------------- #
# Lecture des sources externes


def read_multicrew(path: Path) -> list[Section]:
    data = json.loads(path.read_text(encoding="utf-8"))
    checklists = data.get("checklists")
    if not isinstance(checklists, list):
        raise ValueError("JSON multi-crew attendu : clé « checklists » absente")

    sections = []
    for checklist in checklists:
        items = [
            Item(str(item.get("checkpoint", "")), str(item.get("value", "")))
            for item in checklist.get("items", [])
            if item.get("checkpoint")
        ]
        sections.append(Section(str(checklist.get("name", "?")), items))
    return sections


def read_flightgear(root: ElementTree.Element) -> list[Section]:
    sections = []
    for checklist in root.iter("checklist"):
        title = checklist.findtext("title") or "?"
        items = []
        # Les items peuvent être directement sous la checklist ou rangés dans
        # des <page> : `iter` traverse les deux dispositions.
        for element in checklist.iter("item"):
            name = element.findtext("name")
            if not name:
                continue
            values = [value.text.strip() for value in element.findall("value") if value.text]
            items.append(Item(name.strip(), " / ".join(values)))
        sections.append(Section(title.strip(), items))
    return sections


def read_msfs(root: ElementTree.Element) -> list[Section]:
    """Checklist native MSFS, telle que la livrent les avions du simulateur.

    `<Page SubjectTT>` nomme la checklist, `<CheckpointDesc>` porte l'intitulé
    et la réponse attendue. Les `<Instrument Id>` désignent des éléments du
    cockpit propres à l'appareil : ils n'ont pas d'équivalent dans le
    vocabulaire de la base et sont ignorés.
    """
    sections = []
    for page in root.iter("Page"):
        title = page.get("SubjectTT") or "?"
        items = []
        for checkpoint in page.iter("CheckpointDesc"):
            subject = checkpoint.get("SubjectTT")
            if not subject:
                continue
            items.append(Item(subject.strip(), (checkpoint.get("ExpectationTT") or "").strip()))
        sections.append(Section(title.strip(), items))
    return sections


def read_xml(path: Path) -> list[Section]:
    """Distingue les deux formats XML par leur racine, pas par leur extension."""
    root = ElementTree.parse(path).getroot()
    tag = root.tag.rsplit("}", 1)[-1]
    if tag == "PropertyList":
        return read_flightgear(root)
    if tag.startswith("SimBase"):
        return read_msfs(root)
    raise ValueError(f"racine XML inconnue « {tag} » : attendu PropertyList ou SimBase.Document")


READERS = {".json": read_multicrew, ".xml": read_xml}


def read_source(path: Path) -> list[Section]:
    reader = READERS.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"format inconnu « {path.suffix} » : attendu .json ou .xml")
    return reader(path)


# --------------------------------------------------------------------- #
# Rapprochement


def best_match(needle: str, haystack: list[str]) -> tuple[int, float]:
    """Indice et score du meilleur candidat, (-1, 0.0) si `haystack` est vide."""
    best_index, best_score = -1, 0.0
    for index, candidate in enumerate(haystack):
        score = SequenceMatcher(None, needle, candidate).ratio()
        if score > best_score:
            best_index, best_score = index, score
    return best_index, best_score


def missing_items(source: Section, targets: list[Section]) -> list[Item]:
    """Étapes de `source` qu'aucune section de `targets` ne couvre."""
    keys = [item.key for section in targets for item in section.items]
    absent = []
    for item in source.items:
        _, score = best_match(item.key, keys)
        if score < STEP_THRESHOLD:
            absent.append(item)
    return absent


def report(aircraft: str, database: list[Section], source: list[Section]) -> int:
    """Écrit le rapport, renvoie le nombre d'étapes signalées absentes."""
    database_titles = [section.key for section in database]
    total_missing = 0

    print(f"Couverture de {aircraft}")
    print(f"  base   : {len(database)} procédures, {sum(len(s.items) for s in database)} étapes")
    print(f"  source : {len(source)} checklists, {sum(len(s.items) for s in source)} items")
    print()

    for section in source:
        index, score = best_match(section.key, database_titles)
        if score >= PROCEDURE_THRESHOLD:
            counterpart = database[index]
            # La comparaison reste globale : une source découpe rarement ses
            # checklists comme la base, et une étape présente ailleurs n'est
            # pas manquante.
            absent = missing_items(section, database)
            header = f"{section.title}  →  {counterpart.title}"
        else:
            absent = missing_items(section, database)
            header = f"{section.title}  →  (aucune procédure correspondante)"

        total_missing += len(absent)
        if absent:
            print(header)
            for item in absent:
                print(f"    manquant   {item}")
            print()
        else:
            print(f"{header}  ✓")

    print()
    if total_missing:
        print(f"{total_missing} étape(s) présentes dans la source et absentes de la base.")
        print("À lire, puis à écrire depuis le POH — pas à recopier depuis la source.")
    else:
        print("Aucune étape manquante.")
    return total_missing


# --------------------------------------------------------------------- #


def use_utf8() -> None:
    """Force la sortie en UTF-8.

    La console Windows est en cp1252 par défaut : le rapport, qui est français
    et contient des flèches, échouerait à l'écriture. `capsys` ne reproduit pas
    cette contrainte, d'où le test dédié.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str]) -> int:
    use_utf8()
    parser = argparse.ArgumentParser(
        description="Compare un avion de la base à une checklist publiée, sans rien copier.",
    )
    parser.add_argument("aircraft", help="chemin de l'avion dans la base, par exemple cessna/c172")
    parser.add_argument("--source", required=True, type=Path, help="fichier .json ou .xml externe")
    parser.add_argument("--root", type=Path, default=DB_ROOT, help="racine de la base")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="sortie non nulle s'il manque au moins une étape",
    )
    arguments = parser.parse_args(argv[1:])

    source_path = arguments.source.expanduser().resolve()
    root = arguments.root.resolve()

    # Garde-fou de licence : les sources publiées sont sous GPL, la base est
    # sous Apache-2.0. Elles se lisent depuis leur clone, elles ne s'installent
    # jamais dans le dépôt.
    if root == source_path or root in source_path.parents:
        print(
            f"Refus : « {source_path} » est dans la base. Les sources externes se lisent "
            "depuis leur propre clone et ne sont jamais versionnées ici.",
            file=sys.stderr,
        )
        return 2

    if not source_path.is_file():
        print(f"Source introuvable : {source_path}", file=sys.stderr)
        return 2
    if not (root / "aircraft" / arguments.aircraft / "procedures.json").is_file():
        print(f"Avion inconnu dans la base : {arguments.aircraft}", file=sys.stderr)
        return 2

    try:
        source = read_source(source_path)
    except (ValueError, ElementTree.ParseError, json.JSONDecodeError) as exc:
        print(f"Source illisible : {exc}", file=sys.stderr)
        return 2

    database = read_database(root, arguments.aircraft)
    missing = report(arguments.aircraft, database, source)
    return 1 if (missing and arguments.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
