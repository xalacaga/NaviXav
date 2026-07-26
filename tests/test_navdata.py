from __future__ import annotations

from navixav.navdata.base import ProcedureKind, expand_arinc_runways, normalise_runway


def test_normalise_runway():
    assert normalise_runway("RW05") == "05"
    assert normalise_runway("5") == "05"
    assert normalise_runway("32r") == "32R"


def test_expand_arinc_both_parallels():
    available = ["14L", "14R", "32L", "32R"]
    assert expand_arinc_runways("RW32B", None, available) == ("32L", "32R")


def test_expand_arinc_single_runway():
    assert expand_arinc_runways("RW05", None, ["05", "23"]) == ("05",)


def test_expand_arinc_all_means_every_runway():
    available = ["05", "23"]
    assert expand_arinc_runways("ALL", None, available) == ("05", "23")


def test_explicit_runway_name_wins():
    available = ["14L", "14R", "32L", "32R"]
    assert expand_arinc_runways("RW32B", "32R", available) == ("32R",)


# --------------------------------------------------------------------------- #
# Tests sur la base réelle (ignorés si aucune base n'est installée)
# --------------------------------------------------------------------------- #


def test_airport_lookup(provider):
    airport = provider.airport("LFBO")
    assert airport is not None
    assert "Blagnac" in airport.name


def test_runways_have_ils(provider):
    runways = {r.name: r for r in provider.runways("LFBO")}
    assert set(runways) == {"14L", "14R", "32L", "32R"}
    assert runways["32R"].has_ils


def test_sid_exit_fix_matches_its_name(provider):
    sids = provider.procedures("LFST", ProcedureKind.SID)
    epik = next(p for p in sids if p.ident == "EPIK8M")
    assert epik.exit_fix == "EPIKO"
    assert epik.serves_runway("05")
    assert not epik.serves_runway("23")


def test_star_entry_and_exit_fixes(provider):
    stars = provider.procedures("LFBO", ProcedureKind.STAR)
    afri = next(p for p in stars if p.ident == "AFRI8N")
    assert afri.entry_fix == "AFRIC"
    assert afri.exit_fix == "ADIMO"
    assert afri.serves_runway("32R")


def test_approach_display_name_and_transitions(provider):
    approaches = provider.procedures("LFBO", ProcedureKind.APPROACH)
    ils = next(p for p in approaches if p.display_name == "ILS Z RWY 32R")
    assert "ADIMO" in ils.transition_idents()


def test_ils_frequency(provider):
    frequency = provider.ils_frequency("LFBO", "32R")
    assert frequency is not None
    assert 108.0 <= frequency <= 112.0


def test_airway_lookup(provider):
    """Une route n'est connue qu'une fois un de ses points résolu.

    Les routes sont découvertes au fil des recherches de repères, et non
    importées en bloc : la base ne contient que ce que les vols ont demandé.
    """
    known = {
        row["airway"]
        for row in provider._conn.execute(  # noqa: SLF001 - vérification du cache
            "SELECT DISTINCT airway FROM airway_segment"
        )
    }
    assert known, "la base de test doit contenir au moins une route"
    assert all(provider.is_airway(name) for name in known)
    assert not provider.is_airway("PASUNEAIRWAY")


def test_fix_position(provider):
    position = provider.fix_position("AFRIC")
    assert position is not None
    latitude, longitude = position
    assert 43 < latitude < 44
    assert 2 < longitude < 4
