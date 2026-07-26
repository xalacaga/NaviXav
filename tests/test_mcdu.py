"""La fiche MCDU doit parler Airbus, pas Navigraph.

Le point critique est le couple VIA / TRANS de la page ARRIVAL : ce sont deux
transitions différentes, aux deux extrémités de la STAR.
"""

from __future__ import annotations

from rich.console import Console

from navixav.mcdu import render_mcdu_card
from navixav.planner.engine import CompletionEngine, PlannerOverrides
from navixav.preferences import AirportPreferences


def _card(provider, settings, ofp, overrides=None) -> str:
    plan = CompletionEngine(provider, settings, AirportPreferences.load()).complete(
        ofp, overrides
    )
    console = Console(width=100, record=True, force_terminal=False)
    render_mcdu_card(plan, console)
    return console.export_text()


def _content(card: str) -> list[str]:
    """Lignes de la fiche, débarrassées des bordures du panneau."""
    return [line.strip("│ ").rstrip() for line in card.splitlines()]


def _field(card: str, name: str) -> str:
    """Ligne d'un champ MCDU. Lève une erreur explicite si absente."""
    matches = [line for line in _content(card) if line.startswith(f"{name} ")]
    assert matches, f"champ « {name} » absent de la fiche :\n{card}"
    return matches[0]


def test_departure_page_lists_runway_sid_and_transition(provider, settings, ofp):
    card = _card(provider, settings, ofp)
    assert "F-PLN › DEPARTURE" in card
    assert "05" in _field(card, "RWY")
    assert "EPIK8M" in _field(card, "SID")
    trans = next(l for l in _content(card) if "sortie de la SID" in l)
    assert "EPIKO" in trans


def test_via_is_the_approach_transition(provider, settings, ofp):
    via = _field(_card(provider, settings, ofp), "VIA")
    assert "ADIMO" in via
    assert "APPROCHE" in via


def test_trans_on_arrival_is_the_star_entry(provider, settings, ofp):
    card = _card(provider, settings, ofp)
    trans = next(l for l in _content(card) if "transition d'entrée de STAR" in l)
    assert "AFRIC" in trans


def test_via_and_trans_are_two_different_transitions(provider, settings, ofp):
    """Le piège Airbus : VIA et TRANS sont aux deux bouts de la STAR."""
    card = _card(provider, settings, ofp)
    assert "ADIMO" in _field(card, "VIA")
    assert "ADIMO" not in next(
        l for l in _content(card) if "transition d'entrée de STAR" in l
    )


def test_appr_carries_the_full_approach_name(provider, settings, ofp):
    assert "ILS Z RWY 32R" in _field(_card(provider, settings, ofp), "APPR")


def test_init_page_has_route_basics(provider, settings, ofp):
    card = _card(provider, settings, ofp)
    assert "LFST/LFBO" in card
    assert "LFBP" in card       # dégagement
    assert "FL340" in card      # niveau de croisière


def test_ils_frequency_is_shown(provider, settings, ofp):
    assert "108.35" in _card(provider, settings, ofp)


def test_uncertain_items_are_flagged_for_atis_check(provider, settings, ofp):
    """La piste d'arrivée sort d'un départage : elle doit être signalée."""
    card = _card(provider, settings, ofp)
    assert "À confirmer à l'ATIS" in card
    assert "piste arrivée" in card


def test_forced_values_are_not_flagged(provider, settings, ofp):
    card = _card(
        provider,
        settings,
        ofp,
        PlannerOverrides(arrival_runway="32R", approach="ILS Z RWY 32R"),
    )
    assert "piste arrivée" not in card


def test_field_labels_never_wrap(provider, settings, ofp):
    """« TRANS ALT » et « TRANS LVL » doivent tenir sur une ligne."""
    card = _card(provider, settings, ofp)
    assert "7000" in _field(card, "TRANS ALT")
    assert not any(line == "ALT" for line in _content(card))
