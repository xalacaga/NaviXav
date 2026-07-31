from __future__ import annotations

import json
from pathlib import Path

import pytest

from navixav.config import Settings
from navixav.navdata.msfs import MsfsProvider
from navixav.simbrief.parser import parse_ofp

DATA_DIR = Path(__file__).parent / "data"

# Base NaviXav de référence : LFST, LFBO et LFPO extraits de MSFS 2024, avec
# leurs repères et installations déjà résolus. Elle rend la suite de tests
# indépendante du simulateur.
TEST_STORE = DATA_DIR / "navdata_test.sqlite"


@pytest.fixture(scope="session")
def ofp_raw() -> dict:
    return json.loads((DATA_DIR / "ofp_lfst_lfbo.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def ofp(ofp_raw: dict):
    return parse_ofp(ofp_raw)


@pytest.fixture(scope="session")
def settings() -> Settings:
    # METAR pris dans l'OFP : les tests ne doivent pas dépendre du réseau.
    return Settings(metar_source="simbrief")


@pytest.fixture(scope="session")
def provider():
    """Base de référence, en lecture seule et sans accès au simulateur."""
    if not TEST_STORE.is_file():
        pytest.skip(
            "base de test absente : « navixav import LFST LFBO LFPO "
            f"--store {TEST_STORE} » avec le simulateur ouvert"
        )
    instance = MsfsProvider(TEST_STORE, allow_fetch=False)
    yield instance
    instance.close()


# La géométrie du sol et l'exigence RNP viennent désormais de la même base :
# ces alias existent pour garder les tests lisibles là où l'intention porte
# sur l'une ou l'autre de ces capacités.
@pytest.fixture(scope="session")
def ground_provider(provider):
    if not provider.has_ground_geometry:
        pytest.skip("la base de test ne contient pas la géométrie du sol")
    return provider


@pytest.fixture(scope="session")
def named_ground_provider(ground_provider):
    """Base dont les voies de circulation portent leur nom.

    La base de référence a été constituée avant que NaviXav ne demande le bloc
    des noms au simulateur ; tant qu'elle n'a pas été refaite, les tests qui en
    dépendent s'ignorent plutôt que d'échouer sur une donnée absente.
    """
    if not ground_provider.has_taxi_names:
        pytest.skip(
            "base de test sans nom de voie : refaire « navixav import LFST "
            "LFBO LFPO --store tests/data/navdata_test.sqlite » avec le "
            "simulateur ouvert"
        )
    return ground_provider


@pytest.fixture(scope="session")
def rnp_provider(provider):
    if not provider.supports_rnp_flag:
        pytest.skip("la base de test ne renseigne pas l'exigence RNP")
    return provider
