from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from navixav.constraints import procedure_path
from navixav.geo import distance_nm
from navixav.navdata.base import ProcedureKind, expand_arinc_runways, normalise_runway
from navixav.navdata.msfs import MsfsProvider

# Position réelle du point de report « CF02 » de la base MSFS : un repère corse,
# à 430 NM de l'axe de la 02 d'Orly, dont l'approche porte pourtant ce nom.
CORSICA_CF02 = (41.717347, 8.674186)


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


# --------------------------------------------------------------------------- #
# Repères de seuil de piste
#
# « RW18L » n'est pas un point de report mondial : c'est le seuil de la piste
# 18L du terrain qui publie la procédure. Une recherche de waypoint plaçait la
# 18L de Madrid à Antalya, et un rattachement approximatif la plaçait à
# Toulouse dès qu'un autre terrain possédait une piste homonyme.
# --------------------------------------------------------------------------- #


def test_runway_fix_resolves_to_its_own_airport(provider):
    for icao in ("LFST", "LFBO"):
        runways = {r.name: (r.lat, r.lon) for r in provider.runways(icao)}
        for name, expected in runways.items():
            assert provider.fix_position(f"RW{name}", icao) == expected


def test_runway_fix_never_borrows_another_airport(provider):
    madrid_like = {r.name for r in provider.runways("LFBO")}
    strasbourg = {r.name for r in provider.runways("LFST")}
    shared = madrid_like & strasbourg
    for name in shared:
        toulouse = provider.fix_position(f"RW{name}", "LFBO")
        entzheim = provider.fix_position(f"RW{name}", "LFST")
        assert toulouse != entzheim


def test_ambiguous_runway_fix_is_refused_without_an_airport(provider):
    """Sans terrain fourni, mieux vaut aucune position qu'une position fausse."""
    counts: dict[str, set[str]] = {}
    for icao in ("LFST", "LFBO", "LFPO"):
        for runway in provider.runways(icao):
            counts.setdefault(runway.name, set()).add(icao)
    ambiguous = [name for name, airports in counts.items() if len(airports) > 1]
    for name in ambiguous:
        assert provider.fix_position(f"RW{name}") is None


def test_runway_fix_is_never_looked_up_as_a_waypoint(provider):
    """Le repère de seuil ne doit jamais atteindre la table des waypoints."""
    stored = {
        row[0]
        for row in provider._conn.execute(  # noqa: SLF001 - vérification du cache
            "SELECT ident FROM waypoint WHERE ident GLOB 'RW[0-9]*'"
        )
    }
    assert not stored


# --------------------------------------------------------------------------- #
# Repères d'interception de l'axe final et homonymes lointains
#
# « CF02 » désigne le point où l'approche de la 02 rejoint l'axe : la procédure
# le construit, la base mondiale n'en publie pas. MSFS connaît pourtant un vrai
# point de report du même nom en Corse, et le tracé de la finale d'Orly y
# filait tout droit avant d'en revenir.
# --------------------------------------------------------------------------- #


@pytest.fixture
def polluted_provider(tmp_path: Path, provider):
    """Base de test dont la table des waypoints contient le « CF02 » corse."""
    target = tmp_path / "navdata.sqlite"
    shutil.copyfile(provider._path, target)  # noqa: SLF001 - copie de la base
    instance = MsfsProvider(target, allow_fetch=False)
    with instance._conn:  # noqa: SLF001 - pollution volontaire, après la purge
        instance._conn.execute(  # noqa: SLF001
            "INSERT OR REPLACE INTO waypoint (ident, region, lat, lon) "
            "VALUES ('CF02', 'LF', ?, ?)",
            CORSICA_CF02,
        )
    yield instance
    instance.close()


def test_intercept_fix_never_lands_on_another_airport(polluted_provider):
    """« CF02 » cité par Orly ne peut pas être le « CF02 » corse."""
    assert polluted_provider.fix_position("CF02", "LFPO") is None
    assert polluted_provider.fix_position("CF32R", "LFBO") is None


def test_an_axis_fix_is_refused_even_from_a_neighbouring_airport(polluted_provider):
    """Le piège suivant : l'homonyme du terrain voisin, pas de l'autre bout du monde."""
    with polluted_provider._conn:  # noqa: SLF001 - pollution volontaire
        # « CI24 » publié à Lyon, à 210 NM d'Orly, dont la 24 porte le même nom.
        polluted_provider._conn.execute(  # noqa: SLF001
            "INSERT OR REPLACE INTO waypoint (ident, region, lat, lon) "
            "VALUES ('CI24', 'LF', 45.72, 5.08)"
        )
    assert "24" in polluted_provider._runway_names("LFPO")  # noqa: SLF001
    assert polluted_provider.fix_position("CI24", "LFPO") is None


def test_a_published_fix_named_after_a_runway_is_kept(polluted_provider):
    """« MD18L » à Madrid a la forme d'un repère d'axe, mais il est publié.

    C'est la distance au terrain qui tranche, jamais le préfixe : une liste de
    préfixes aurait écarté ce point réel avec les repères construits.
    """
    with polluted_provider._conn:  # noqa: SLF001 - repère réel, à 20 NM d'Orly
        polluted_provider._conn.execute(  # noqa: SLF001
            "INSERT OR REPLACE INTO waypoint (ident, region, lat, lon) "
            "VALUES ('PO02', 'LF', 49.05, 2.45)"
        )
    assert polluted_provider.fix_position("PO02", "LFPO") == (49.05, 2.45)


def test_approach_path_stays_around_its_airport(polluted_provider):
    """Aucun point de la finale d'Orly ne doit sortir de la région parisienne."""
    def lookup(ident: str):
        return polluted_provider.fix_position(ident, "LFPO")

    orly = polluted_provider.airport("LFPO")
    approaches = polluted_provider.procedures("LFPO", ProcedureKind.APPROACH)
    for approach in approaches:
        for point in procedure_path(approach, position_lookup=lookup):
            assert distance_nm(orly.lat, orly.lon, point["lat"], point["lon"]) < 300


def test_a_distant_homonym_is_refused_in_a_procedure(polluted_provider):
    """Un repère de procédure à 400 NM du terrain est un homonyme, pas le bon."""
    with polluted_provider._conn:  # noqa: SLF001 - pollution volontaire
        polluted_provider._conn.execute(  # noqa: SLF001
            "INSERT OR REPLACE INTO waypoint (ident, region, lat, lon) "
            "VALUES ('LOINT', 'LI', ?, ?)",
            CORSICA_CF02,
        )
    assert polluted_provider.fix_position("LOINT", "LFPO") is None
    # Sans terrain de rattachement, la position reste exploitable : c'est au
    # tracé en route de juger, sur la route entière.
    assert polluted_provider.fix_position("LOINT") is not None


def test_the_nearest_homonym_wins(polluted_provider):
    """Deux repères du même nom : celui du voisinage l'emporte."""
    with polluted_provider._conn:  # noqa: SLF001 - pollution volontaire
        polluted_provider._conn.executemany(  # noqa: SLF001
            "INSERT OR REPLACE INTO waypoint (ident, region, lat, lon) "
            "VALUES ('DOUBL', ?, ?, ?)",
            [("LF", 48.9, 2.5), ("NZ", -41.0, 174.0)],
        )
    assert polluted_provider.fix_position("DOUBL", "LFPO") == (48.9, 2.5)
    assert polluted_provider.fix_position("DOUBL", near=(48.7, 2.4)) == (48.9, 2.5)
    assert polluted_provider.fix_position("DOUBL", near=(-41.2, 174.5)) == (-41.0, 174.0)


def test_pseudo_fixes_are_purged_from_an_existing_store(tmp_path: Path, provider):
    """Une base déjà polluée se nettoie à l'ouverture."""
    target = tmp_path / "navdata.sqlite"
    shutil.copyfile(provider._path, target)  # noqa: SLF001 - copie de la base
    connection = sqlite3.connect(target)
    with connection:
        connection.execute(
            "INSERT OR REPLACE INTO waypoint (ident, region, lat, lon) "
            "VALUES ('CF02', 'LF', ?, ?)",
            CORSICA_CF02,
        )
    connection.close()

    with MsfsProvider(target, allow_fetch=False) as reopened:
        remaining = reopened._conn.execute(  # noqa: SLF001 - vérification du cache
            "SELECT COUNT(*) FROM waypoint WHERE ident GLOB 'CF[0-9]*'"
        ).fetchone()[0]
    assert remaining == 0
