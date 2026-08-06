"""Lecture du journal des versions livré avec l'application.

`CHANGELOG.md` est l'histoire du dépôt : une entrée par version publiée, depuis
le début du suivi. Le fichier est écrit par `scripts/prepare_release.ps1` et
embarqué dans la distribution, si bien que l'application décrit toujours son
propre passé, sans réseau.

Le texte des puces reste en anglais : il n'est pas réécrit à chaque traduction
de l'interface, et réécrire trente-six versions passées n'aurait pas de sens.
Seuls les intitulés de rubrique sont traduits, à partir de `kind`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from navixav.paths import resource_path

# « ## [1.4.9] - 2026-08-05 ». Les rubriques de 1.4.8 et 1.4.9 ont été écrites
# au même niveau que la version : le niveau ne distingue donc rien, seul ce
# motif identifie une version.
VERSION_HEADING = re.compile(r"^#{2,3}\s*\[(?P<version>[^\]]+)\]\s*-\s*(?P<date>.+?)\s*$")
SECTION_HEADING = re.compile(r"^#{2,3}\s+(?P<title>.+?)\s*$")
ITEM = re.compile(r"^[-*]\s+(?P<text>.+?)\s*$")


@dataclass
class Section:
    """Une rubrique d'une version : ajouts, corrections, changements."""

    title: str
    items: list[str] = field(default_factory=list)

    @property
    def kind(self) -> str:
        """Identifiant stable pour traduire l'intitulé côté interface."""
        return re.sub(r"[^a-z0-9]+", "_", self.title.strip().lower()).strip("_")

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "title": self.title, "items": list(self.items)}


@dataclass
class Release:
    version: str
    date: str
    sections: list[Section] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "date": self.date,
            "sections": [section.to_dict() for section in self.sections],
        }


def parse_changelog(text: str) -> list[Release]:
    """Découpe le journal en versions, puis en rubriques.

    Une ligne libre — un paragraphe sans puce, comme il en traîne dans les
    premières versions — vaut une puce : elle décrit un changement, elle a été
    écrite pour être lue.
    """
    releases: list[Release] = []
    section: Section | None = None
    after_blank = True

    for raw in text.splitlines():
        line = raw.rstrip()
        version = VERSION_HEADING.match(line)
        if version:
            releases.append(
                Release(version.group("version").strip(), version.group("date").strip())
            )
            section = None
            continue

        if not releases:
            # Tout ce qui précède la première version est le titre du fichier.
            continue

        heading = SECTION_HEADING.match(line)
        if heading:
            section = Section(heading.group("title"))
            releases[-1].sections.append(section)
            continue

        if not line.strip():
            after_blank = True
            continue

        if section is None:
            section = Section("")
            releases[-1].sections.append(section)

        item = ITEM.match(line)
        if item:
            section.items.append(item.group("text"))
        elif section.items and not after_blank:
            # Suite d'une puce repliée sur la ligne suivante. Une ligne isolée
            # après une ligne vide est un paragraphe à part, pas une suite.
            section.items[-1] = f"{section.items[-1]} {line.strip()}"
        else:
            section.items.append(line.strip())
        after_blank = False

    for release in releases:
        release.sections = [s for s in release.sections if s.items]
    return [release for release in releases if release.sections]


def changelog_path() -> Path:
    return resource_path("CHANGELOG.md")


def load_changelog() -> list[dict[str, object]]:
    """Journal prêt pour l'interface, vide si le fichier n'est pas livré."""
    path = changelog_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    return [release.to_dict() for release in parse_changelog(text)]
