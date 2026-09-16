"""Écran de MCDU/CDU sous une forme commune à tous les connecteurs.

Chaque connecteur (Fenix, FlyByWire, PMDG) reçoit l'écran dans son propre
format ; l'interface, elle, n'en connaît qu'un : un titre, des lignes et un
bloc-notes, chacun en segments ``{text, color, size}``. Les couleurs sont
celles des MCDU Airbus et CDU Boeing : white, green, cyan, magenta, amber,
yellow, red, grey (inopérant).
"""

from __future__ import annotations

from typing import Any

COLUMNS = 24

Segment = dict[str, str]


def segment(text: str, color: str = "white", size: str = "large") -> Segment:
    return {"text": text, "color": color, "size": size}


def screen(title: list[Segment], lines: list[list[Segment]], scratchpad: list[Segment]) -> dict[str, Any]:
    return {"title": title, "lines": lines, "scratchpad": scratchpad}


def width(segments: list[Segment]) -> int:
    return sum(len(item["text"]) for item in segments)


def compose(left: list[Segment], right: list[Segment], center: list[Segment] | None = None) -> list[Segment]:
    """Aligne trois textes sur une ligne de 24 colonnes : gauche, droite, centre.

    Le texte centré est posé par-dessus l'espace laissé libre ; s'il chevauche
    la gauche ou la droite, la gauche et la droite gagnent, comme sur l'écran.
    """
    left = list(left)
    right = list(right)
    center = list(center or [])
    free = COLUMNS - width(left) - width(right)
    if center and width(center) <= free:
        before = (COLUMNS - width(center)) // 2 - width(left)
        after = free - width(center) - before
        return left + [segment(" " * max(0, before))] + center + [segment(" " * max(0, after))] + right
    return left + [segment(" " * max(0, free))] + right
