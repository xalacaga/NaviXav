"""Détection de l'appareil chargé, face à la base livrée.

Les titres utilisés sont ceux que publie le simulateur. Le reste des cas —
priorité, base absente, dossier illisible — s'appuie sur une base fabriquée
dans un dossier temporaire, pour que ces tests ne dépendent pas du contenu
présent de `aircraft_db/`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from navixav.aircraft import AircraftMatcher
from navixav.aircraft.matcher import database_root, load_entries

DB_ROOT = Path(__file__).resolve().parent.parent / "aircraft_db"


@pytest.fixture(scope="module")
def matcher() -> AircraftMatcher:
    return AircraftMatcher(DB_ROOT)


def test_racine_par_defaut_pointe_sur_la_base_livree():
    assert database_root().name == "aircraft_db"


def test_reconnait_le_c172(matcher: AircraftMatcher):
    match = matcher.match("Cessna 172 Skyhawk G1000")
    assert match is not None
    assert match.entry.id == "cessna/c172"
    assert match.entry.manufacturer == "Cessna"


@pytest.mark.parametrize(
    ("title", "variant"),
    [
        ("Cessna 172 Skyhawk G1000", "asobo_g1000"),
        ("Cessna Skyhawk G1000 NXi", "asobo_g1000"),
        ("Cessna 172 Skyhawk (Steam Gauges)", "asobo_classic"),
        ("Asobo C172", "asobo"),
    ],
)
def test_distingue_les_variantes(matcher: AircraftMatcher, title: str, variant: str):
    match = matcher.match(title)
    assert match is not None
    assert match.variant is not None
    assert match.variant.id == variant


def test_la_variante_corrige_les_systemes_de_la_famille(matcher: AircraftMatcher):
    """`systems.json` déclare `vnav` absent ; la variante G1000 le rétablit."""
    classique = matcher.match("Cessna 172 Skyhawk (Steam Gauges)")
    g1000 = matcher.match("Cessna 172 Skyhawk G1000")
    assert classique is not None and g1000 is not None
    assert classique.has("vnav") is False
    assert g1000.has("vnav") is True


def test_un_systeme_non_declare_vaut_absent(matcher: AircraftMatcher):
    match = matcher.match("Cessna 172 Skyhawk G1000")
    assert match is not None
    assert match.has("retractable_gear") is False
    assert match.has("pressurisation") is False
    assert match.has("thermonucleaire") is False


def test_titre_inconnu(matcher: AircraftMatcher):
    # Volontairement hors de la feuille de route : un appareil qui y figure
    # ferait échouer ce test le jour où il rejoint la base.
    assert matcher.match("Supermarine Spitfire Mk IX") is None


@pytest.mark.parametrize(
    ("title", "aircraft", "variant"),
    [
        ("Diamond DA62", "diamond/da62", "asobo"),
        ("Beechcraft King Air 350i", "beechcraft/king_air_350", "asobo"),
        ("Beechcraft King Air 350i G1000 NXi", "beechcraft/king_air_350", "asobo_g1000"),
        ("Airbus A320neo", "airbus/a320", "asobo"),
        ("Fenix A320 IAE", "airbus/a320", "fenix"),
        ("FlyByWire A32NX", "airbus/a320", "flybywire"),
        ("iniBuilds A321neo", "airbus/a320", "inibuilds"),
        ("Daher TBM 930", "daher/tbm930", "asobo"),
        ("Cirrus SF50 Vision Jet G2", "cirrus/sf50", "asobo"),
        ("Cessna Citation CJ4", "cessna/citation_cj4", "asobo"),
        ("Boeing 737-800", "boeing/b737", "asobo"),
        # Titre relevé dans le dossier Community de l'utilisateur.
        ("PMDG 737-900 PMDG House (N739BW | 2022)", "boeing/b737", "pmdg"),
    ],
)
def test_reconnait_les_familles_de_la_base(
    matcher: AircraftMatcher, title: str, aircraft: str, variant: str
):
    match = matcher.match(title)
    assert match is not None
    assert match.entry.id == aircraft
    assert match.variant is not None
    assert match.variant.id == variant


def test_le_da62_a_un_train_rentrant_contrairement_au_c172(matcher: AircraftMatcher):
    """La même vérification de train est légitime ici et rejetée sur le C172."""
    da62 = matcher.match("Diamond DA62")
    c172 = matcher.match("Cessna 172 Skyhawk G1000")
    assert da62 is not None and c172 is not None
    assert da62.has("retractable_gear") is True
    assert c172.has("retractable_gear") is False


def test_le_mapping_fenix_reproduit_le_code_existant(matcher: AircraftMatcher):
    """Les overrides Fenix sont la spécification du lot « mapping dynamique ».

    Ils décrivent en données ce que `navixav/live/simconnect.py` porte
    aujourd'hui en dur ; ce test fige la correspondance des LVar.
    """
    match = matcher.match("Fenix A320 IAE")
    assert match is not None and match.variant is not None
    overrides = match.variant.overrides
    assert overrides["configuration.flaps_handle_index"]["lvar"] == "S_FC_FLAPS"
    assert overrides["configuration.parking_brake"]["lvar"] == "S_MIP_PARKING_BRAKE"
    assert overrides["configuration.spoilers_armed"] == {
        "lvar": "A_FC_SPEEDBRAKE",
        "as": "boolean",
        "below": 0.5,
    }


@pytest.mark.parametrize("title", ["", "   "])
def test_titre_vide(matcher: AircraftMatcher, title: str):
    assert matcher.match(title) is None


def test_serialisation(matcher: AircraftMatcher):
    match = matcher.match("Cessna 172 Skyhawk G1000")
    assert match is not None
    payload = match.to_dict()
    assert payload["id"] == "cessna/c172"
    assert payload["variant"] == "asobo_g1000"
    assert payload["systems"]["retractable_gear"] is False


# --------------------------------------------------------------------- #
# Base fabriquée


def _write_aircraft(
    root: Path,
    identifier: str,
    *,
    patterns: list[str],
    priority: int,
    variants: list[dict] | None = None,
) -> Path:
    directory = root / "aircraft" / identifier
    directory.mkdir(parents=True)
    (directory / "metadata.json").write_text(
        json.dumps(
            {
                "id": identifier,
                "manufacturer": "Essai",
                "family": identifier,
                "model": identifier,
                "match": {"title_contains": patterns, "priority": priority},
            }
        ),
        encoding="utf-8",
    )
    (directory / "systems.json").write_text(
        json.dumps({"systems": {"flaps": True}}), encoding="utf-8"
    )
    (directory / "mapping.json").write_text(
        json.dumps({"variants": variants or []}), encoding="utf-8"
    )
    return directory


def test_la_priorite_departage_deux_familles(tmp_path: Path):
    _write_aircraft(tmp_path, "essai/generique", patterns=["boeing"], priority=1)
    _write_aircraft(tmp_path, "essai/precis", patterns=["boeing"], priority=20)

    match = AircraftMatcher(tmp_path).match("Boeing 737")
    assert match is not None
    assert match.entry.id == "essai/precis"


def test_a_priorite_egale_le_motif_le_plus_long_gagne(tmp_path: Path):
    _write_aircraft(tmp_path, "essai/court", patterns=["737"], priority=10)
    _write_aircraft(tmp_path, "essai/long", patterns=["boeing 737"], priority=10)

    match = AircraftMatcher(tmp_path).match("Boeing 737-800")
    assert match is not None
    assert match.entry.id == "essai/long"


def test_sans_variante_reconnue_la_variante_par_defaut_est_retenue(tmp_path: Path):
    """Aucune variante ne reconnaît le titre : celle déclarée par défaut sert."""
    directory = _write_aircraft(tmp_path, "essai/avion", patterns=["avion"], priority=10)
    (directory / "mapping.json").write_text(
        json.dumps(
            {
                "default_variant": "standard",
                "variants": [
                    {"id": "precise", "label": "Précise", "match": {"title_contains": ["addon"]}},
                    {"id": "standard", "label": "Standard", "match": {"title_contains": ["autre"]}},
                ],
            }
        ),
        encoding="utf-8",
    )

    match = AircraftMatcher(tmp_path).match("Avion générique")
    assert match is not None
    assert match.variant is not None
    assert match.variant.id == "standard"


def test_sans_variante_ni_defaut_la_famille_suffit(tmp_path: Path):
    """Le défaut nommé est validé par `validate.py` ; ici il est simplement absent."""
    _write_aircraft(tmp_path, "essai/avion", patterns=["avion"], priority=10)

    match = AircraftMatcher(tmp_path).match("Avion générique")
    assert match is not None
    assert match.variant is None
    assert match.has("flaps") is True


def test_base_absente(tmp_path: Path, caplog):
    assert load_entries(tmp_path / "nulle-part") == []
    assert AircraftMatcher(tmp_path / "nulle-part").match("Cessna 172") is None


def test_un_dossier_illisible_est_ignore_sans_exception(tmp_path: Path, caplog):
    """Une base livrée est faillible : elle ne doit jamais couper le suivi."""
    _write_aircraft(tmp_path, "essai/valide", patterns=["cessna"], priority=10)
    casse = tmp_path / "aircraft" / "essai" / "casse"
    casse.mkdir(parents=True)
    (casse / "metadata.json").write_text("{ ceci n'est pas du JSON", encoding="utf-8")

    entries = load_entries(tmp_path)
    assert [entry.id for entry in entries] == ["essai/valide"]


def test_un_avion_sans_motif_est_ignore(tmp_path: Path):
    directory = _write_aircraft(tmp_path, "essai/muet", patterns=["x"], priority=10)
    (directory / "metadata.json").write_text(
        json.dumps({"id": "essai/muet", "match": {"priority": 10}}), encoding="utf-8"
    )
    assert load_entries(tmp_path) == []


def test_aucune_famille_ne_capture_le_titre_d_une_autre(matcher: AircraftMatcher):
    """Deux familles ne doivent pas se disputer un même appareil.

    Les motifs sont libres, donc rien n'empêche « c172 » et « citation » de se
    recouvrir un jour. Ce test échoue le jour où cela arrive.
    """
    titres = {
        "cessna/c172": "Cessna 172 Skyhawk G1000",
        "cessna/citation_cj4": "Cessna Citation CJ4",
        "diamond/da62": "Diamond DA62",
        "beechcraft/king_air_350": "Beechcraft King Air 350i",
        "daher/tbm930": "Daher TBM 930",
        "cirrus/sf50": "Cirrus SF50 Vision Jet G2",
        "airbus/a320": "Airbus A320neo",
        "boeing/b737": "Boeing 737-800",
    }
    for attendu, titre in titres.items():
        match = matcher.match(titre)
        assert match is not None, titre
        assert match.entry.id == attendu, f"« {titre} » capturé par {match.entry.id}"


def test_la_flotte_est_complete(matcher: AircraftMatcher):
    """Toutes les familles de la base sont chargeables et détectables."""
    identifiants = {entry.id for entry in matcher.entries}
    assert len(identifiants) == 30
    assert "cessna/c172" in identifiants
    assert "boeing/b777" in identifiants


def test_les_familles_ecrites_a_la_main_sont_marquees(matcher: AircraftMatcher):
    """`maturity` distingue une procédure lue dans un manuel d'un canevas.

    Un pilote a le droit de savoir ce qu'il lit : l'interface doit pouvoir le
    dire, donc l'information voyage jusqu'à `to_dict`.
    """
    authored = {e.id for e in matcher.entries if e.maturity == "authored"}
    assert authored == {
        "airbus/a320", "beechcraft/king_air_350", "boeing/b737", "cessna/c172",
        "cessna/citation_cj4", "cirrus/sf50", "daher/tbm930", "diamond/da62",
    }
    assert all(e.maturity in {"draft", "authored"} for e in matcher.entries)
    assert matcher.match("Cessna 172 Skyhawk G1000").to_dict()["maturity"] == "authored"
    assert matcher.match("A2A Aerostar 600").to_dict()["maturity"] == "draft"


@pytest.mark.parametrize(
    ("titre", "attendu"),
    [
        ("Cessna 172 Skyhawk G1000", "cessna/c172"),
        ("Cessna Citation CJ4", "cessna/citation_cj4"),
        ("Flysimware Cessna 414AW Chancellor", "cessna/c414"),
        ("Diamond DA62", "diamond/da62"),
        ("COWS DA42-VI White", "diamond/da42"),
        ("Beechcraft King Air 350i", "beechcraft/king_air_350"),
        ("Black Square Baron 58", "beechcraft/baron58"),
        ("Black Square Bonanza A36", "beechcraft/bonanza36"),
        ("Black Square Piston Duke B60", "beechcraft/duke_b60"),
        ("Black Square Turbine Duke", "beechcraft/duke_turbine"),
        ("Flysimware Sierra 200 C24R", "beechcraft/sierra_c24r"),
        ("A2A Aerostar 600", "piper/aerostar600"),
        ("A2A PA-24 Comanche 250", "piper/pa24"),
        ("Black Box BN-2B Islander", "brittennorman/bn2"),
        ("Milviz PC-6 Porter Giraffe", "pilatus/pc6"),
        ("SimWorks Studios Pilatus PC-12/47", "pilatus/pc12"),
        ("Daher TBM 930", "daher/tbm930"),
        ("Cirrus SF50 Vision Jet G2", "cirrus/sf50"),
        ("Flysimware Learjet 35A", "bombardier/learjet35a"),
        ("Airbus A320neo", "airbus/a320"),
        ("Headwind A330-900neo", "airbus/a330"),
        ("iniBuilds A340-300", "airbus/a340"),
        ("iniBuilds A350-900", "airbus/a350"),
        ("FlyByWire A380-842", "airbus/a380"),
        ("Boeing 737-800", "boeing/b737"),
        ("PMDG 777-200ER", "boeing/b777"),
        ("Just Flight F28 Fellowship Mk 4000", "fokker/f28"),
        ("Just Flight Avro RJ85", "bae/avro_rj"),
        ("Aeroplane Heaven P-51D Mustang", "northamerican/p51d"),
        ("FlyingIron Fw 190 A-8", "fockewulf/fw190"),
    ],
)
def test_chaque_famille_capture_son_avion_et_pas_un_autre(
    matcher: AircraftMatcher, titre: str, attendu: str
):
    """Trente familles aux motifs libres : rien n'empêche deux d'entre elles de
    se recouvrir. Ce test échoue le jour où cela arrive."""
    match = matcher.match(titre)
    assert match is not None, titre
    assert match.entry.id == attendu, f"« {titre} » capturé par {match.entry.id}"



def test_la_base_est_livree_avec_l_application():
    """Sans entrée dans le .spec, aucun avion ne serait détecté une fois installé."""
    spec = (DB_ROOT.parent / "NaviXav.spec").read_text(encoding="utf-8")
    assert 'project_root / "aircraft_db" / "aircraft"' in spec
    assert 'project_root / "aircraft_db" / "VERSION.json"' in spec
    # `schema/` et `tools/` servent aux contributeurs : la distribution ne les
    # porte pas, et le moteur ne les lit jamais.
    assert '"aircraft_db" / "schema"' not in spec
    assert '"aircraft_db" / "tools"' not in spec


# --------------------------------------------------------------------- #
# Base de l'utilisateur, superposée à celle livrée


def test_la_base_utilisateur_ajoute_une_famille(tmp_path: Path):
    """Un dossier déposé par l'utilisateur suffit : ni code, ni mise à jour."""
    user = tmp_path / "user"
    _write_aircraft(user, "pilatus/pc6", patterns=["pc-6", "porter"], priority=10)

    matcher = AircraftMatcher(DB_ROOT, user_root=user)
    match = matcher.match("Milviz PC-6 Porter")
    assert match is not None
    assert match.entry.id == "pilatus/pc6"
    assert match.entry.user_supplied is True
    # La base livrée reste entière.
    assert matcher.match("Cessna 172 Skyhawk G1000") is not None


def test_la_base_utilisateur_remplace_une_famille_livree(tmp_path: Path):
    """Corriger un avion livré ne doit pas demander de modifier la base livrée.

    Une mise à jour de NaviXav écraserait la correction ; la superposition la
    préserve.
    """
    user = tmp_path / "user"
    _write_aircraft(user, "cessna/c172", patterns=["c172", "skyhawk"], priority=10)

    matcher = AircraftMatcher(DB_ROOT, user_root=user)
    match = matcher.match("Cessna 172 Skyhawk G1000")
    assert match is not None
    assert match.entry.user_supplied is True
    assert match.entry.manufacturer == "Essai"
    assert match.to_dict()["user_supplied"] is True


def test_la_base_utilisateur_absente_ne_gene_pas(tmp_path: Path):
    matcher = AircraftMatcher(DB_ROOT, user_root=tmp_path / "jamais-creee")
    assert matcher.match("Cessna 172 Skyhawk G1000") is not None


def test_les_racines_par_defaut_sont_la_base_livree_puis_celle_utilisateur():
    from navixav.aircraft.matcher import database_roots, user_database_root

    roots = database_roots()
    assert roots[0] == database_root()
    assert roots[1] == user_database_root()
    assert user_database_root().name == "aircraft_db"
