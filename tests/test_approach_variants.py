"""Choix entre deux variantes d'une même approche (ILS Y / ILS Z).

La lettre X/Y/Z n'est qu'un identifiant attribué à rebours depuis Z ; elle ne
porte aucune notion de priorité. Le choix doit donc reposer uniquement sur la
structure de la procédure :

    LFBO ILS Z RWY 32R : entrée IO32R (IAF), 5 transitions, remise de gaz RNAV
                         -> RNP 1 requis
    LFBO ILS Y RWY 32R : entrée CF32R (repère d'interception), aucune transition,
                         remise de gaz conventionnelle -> aucune exigence RNP
"""

from __future__ import annotations

from navixav.models import Confidence
from navixav.navdata.base import ProcedureKind
from navixav.planner.engine import CompletionEngine, PlannerOverrides
from navixav.preferences import AirportPreferences


def _plan(provider, settings, ofp, overrides=None):
    engine = CompletionEngine(provider, settings, AirportPreferences.load())
    return engine.complete(ofp, overrides)


def _approach(source, name: str):
    return next(
        p
        for p in source.procedures("LFBO", ProcedureKind.APPROACH)
        if p.display_name == name
    )


# --------------------------------------------------------------------------- #
# Ce que la base dit réellement des deux variantes
# --------------------------------------------------------------------------- #


def test_z_variant_is_the_published_arrival(provider):
    ils_z = _approach(provider, "ILS Z RWY 32R")
    assert ils_z.has_published_transitions
    assert "ADIMO" in ils_z.transition_idents()
    assert not ils_z.is_vectors_entry


def test_y_variant_is_the_radar_vectored_one(provider):
    ils_y = _approach(provider, "ILS Y RWY 32R")
    assert not ils_y.has_published_transitions
    assert ils_y.entry_fix == "CF32R"
    assert ils_y.has_artificial_entry
    assert ils_y.is_vectors_entry
    assert not ils_y.requires_rnp


# --------------------------------------------------------------------------- #
# Décision du moteur
# --------------------------------------------------------------------------- #


def test_star_connection_selects_the_published_variant(provider, settings, ofp):
    """AFRI8N finit à ADIMO, que seule la variante Z publie."""
    plan = _plan(provider, settings, ofp)
    assert plan.arrival.approach.value == "ILS Z RWY 32R"
    assert plan.arrival.approach_transition.value == "ADIMO"
    assert plan.arrival.approach.confidence is Confidence.HIGH


def test_non_rnp_aircraft_falls_back_to_the_other_variant(rnp_provider, settings, ofp):
    """Sans qualification RNP, Z est inutilisable malgré le raccord STAR.

    Le critère n'existe que sur une base qui publie l'exigence RNP : les
    données du simulateur ne la portent pas, ce que le moteur signale par un
    avertissement plutôt qu'en filtrant à vide (voir test_navdata_capabilities).
    """
    plan = _plan(rnp_provider, settings, ofp, PlannerOverrides(rnp_capable=False))
    assert plan.arrival.approach.value == "ILS Y RWY 32R"
    assert plan.arrival.approach_transition.value == "VECTORS"
    assert any("RNP" in w for w in plan.warnings)
    alternatives = {
        item["value"]: item for item in plan.arrival.approach.alternatives
    }
    assert alternatives["ILS Z RWY 32R"]["disqualified"] is True


def test_rnp_requirement_is_published_on_the_z_variant(rnp_provider):
    assert _approach(rnp_provider, "ILS Z RWY 32R").requires_rnp
    assert not _approach(rnp_provider, "ILS Y RWY 32R").requires_rnp


def test_without_a_star_the_vectors_variant_wins(provider, settings):
    """Aucun point de sortie de STAR : on sera vectoré vers l'axe.

    La règle est testée directement sur le classement : la construire depuis un
    OFP demanderait une destination sans STAR exploitable, ce que l'exemple de
    référence ne permet pas.
    """
    engine = CompletionEngine(provider, settings, AirportPreferences.load())
    approach, transition = engine._choose_approach(
        approaches=provider.procedures("LFBO", ProcedureKind.APPROACH),
        runway_name="32R",
        link_fix=None,
        via_star=False,
        forced_name=None,
        forced_transition=None,
        prefer_ils=True,
        rnp_capable=True,
    )
    assert approach.value == "ILS Y RWY 32R"
    assert transition.value == "VECTORS"


def test_letter_is_never_used_as_a_tiebreaker(rnp_provider, settings, ofp):
    """Le choix doit changer avec la structure, jamais avec l'ordre des lettres."""
    with_star = _plan(rnp_provider, settings, ofp).arrival.approach.value
    without_rnp = _plan(
        rnp_provider, settings, ofp, PlannerOverrides(rnp_capable=False)
    ).arrival.approach.value
    # Deux structures différentes, deux lettres différentes : la lettre suit,
    # elle ne décide pas.
    assert with_star != without_rnp
    assert {with_star, without_rnp} == {"ILS Z RWY 32R", "ILS Y RWY 32R"}


def test_reason_explains_the_structural_choice(provider, settings, ofp):
    """La justification cite le maillon retenu, quelle que soit la base."""
    plan = _plan(provider, settings, ofp)
    assert "ADIMO" in plan.arrival.approach.reason
    assert "ILS" in plan.arrival.approach.reason


def test_alternatives_describe_each_variant_role(provider, settings, ofp):
    plan = _plan(provider, settings, ofp)
    roles = {a["value"]: a for a in plan.arrival.approach.alternatives}
    assert roles["ILS Y RWY 32R"]["role"] == "variante guidage radar"
    assert roles["ILS Y RWY 32R"]["connects_to_star"] is False
    assert roles["RNAV RWY 32R"]["connects_to_star"] is True


def test_forced_approach_still_wins(provider, settings, ofp):
    plan = _plan(provider, settings, ofp, PlannerOverrides(approach="ILS Y RWY 32R"))
    assert plan.arrival.approach.value == "ILS Y RWY 32R"
    assert plan.arrival.approach.source == "utilisateur"
