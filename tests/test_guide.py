"""Guide d'utilisation : chargé par la page, complet dans les huit langues."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parent.parent / "navixav" / "web" / "static"
GUIDE = (STATIC / "guide.js").read_text(encoding="utf-8")
I18N = (STATIC / "i18n.js").read_text(encoding="utf-8")
LANGUAGES = ["fr", "en", "de", "es", "it", "pt", "nl", "pl"]


def blocks() -> dict[str, str]:
    """Texte de chaque langue, de « TEXT.xx = { » à la langue suivante."""
    marks = list(re.finditer(r"^  TEXT\.(\w\w) = \{", GUIDE, flags=re.M))
    return {
        mark.group(1): GUIDE[mark.end(): marks[index + 1].start() if index + 1 < len(marks) else len(GUIDE)]
        for index, mark in enumerate(marks)
    }


def item_ids(block: str) -> list[str]:
    return re.findall(r"^ {10}(\w+): \[", block, flags=re.M)


def test_the_page_loads_the_guide_before_the_application():
    """Sans ce script, le guide s'ouvrait vide : GUIDE n'existait pas."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    guide = html.find("/static/guide.js")
    application = html.find("/static/app.js")
    assert guide != -1
    assert guide < application


def test_every_language_is_written():
    assert sorted(blocks()) == sorted(LANGUAGES)


@pytest.mark.parametrize("language", LANGUAGES[1:])
def test_every_language_has_the_same_entries_as_french(language):
    reference = item_ids(blocks()["fr"])
    assert item_ids(blocks()[language]) == reference


def test_every_interface_label_quoted_by_the_guide_exists():
    """« {tower_toggle} » est remplacé par le libellé de l'interface."""
    # Les clés s'écrivent avec ou sans guillemets selon le bloc de traductions.
    keys = set(re.findall(r'^\s+"?(\w+)"?:', I18N, flags=re.M)) | set(re.findall(r'[{,]\s*"?(\w+)"?: ', I18N))
    quoted = set(re.findall(r"\{(\w+)\}", GUIDE))
    assert quoted - keys == set()
