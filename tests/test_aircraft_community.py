"""Inventaire des avions installés et amorçage de leurs procédures.

Tout se fait sur un faux dossier Community construit ici : le simulateur peut
être installé n'importe où, et la suite de tests ne doit dépendre ni de sa
présence ni de son emplacement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from navixav.aircraft import AircraftMatcher
from navixav.aircraft.community import (
    InstalledAircraft,
    community_folders,
    packages_paths,
    scan,
    survey,
)
from navixav.aircraft.scaffold import (
    build_entry,
    derive_patterns,
    identifier_for,
    infer_check,
    infer_systems,
    phase_of,
    write_entry,
)

DB_ROOT = Path(__file__).resolve().parent.parent / "aircraft_db"

CHECKLIST = """<?xml version="1.0" encoding="Windows-1252"?>
<SimBase.Document Type="Checklist" version="1,0">
  <Checklist.Checklist>
    <Step ChecklistStepId="PREFLIGHT_GATE">
      <Page SubjectTT="Before Starting Engine">
        <Checkpoint><CheckpointDesc SubjectTT="Parking Brake" ExpectationTT="Set"/></Checkpoint>
        <Checkpoint><CheckpointDesc SubjectTT="Preflight Inspection" ExpectationTT="Complete"/></Checkpoint>
      </Page>
      <Page SubjectTT="After Takeoff">
        <Checkpoint><CheckpointDesc SubjectTT="Landing Gear" ExpectationTT="Up"/></Checkpoint>
        <Checkpoint><CheckpointDesc SubjectTT="Wing Flaps" ExpectationTT="Up"/></Checkpoint>
        <Checkpoint><CheckpointDesc SubjectTT="Strobe Lights" ExpectationTT="On"/></Checkpoint>
        <Checkpoint><CheckpointDesc SubjectTT="Cowl Flaps" ExpectationTT="As Required"/></Checkpoint>
      </Page>
    </Step>
  </Checklist.Checklist>
</SimBase.Document>
"""


def make_package(
    community: Path,
    package: str,
    folder: str,
    *,
    titles: list[str],
    manufacturer: str,
    ui_type: str,
    icao: str,
    engines: int = 1,
    engine_type: int = 0,
    checklist: str | None = None,
) -> Path:
    directory = community / package / "SimObjects" / "Airplanes" / folder
    directory.mkdir(parents=True)
    blocks = [
        "[GENERAL]",
        f'icao_type_designator = "{icao}"',
        "",
        "[PISTON_ENGINE]",
        f"number_of_engines = {engines}",
        f"engine_type = {engine_type}",
        "",
    ]
    for index, title in enumerate(titles):
        blocks += [
            f"[FLTSIM.{index}]",
            f'title = "{title}" ; nom de la livrée',
            f'ui_manufacturer = "{manufacturer}"',
            f'ui_type = "{ui_type}"',
            "",
        ]
    (directory / "aircraft.cfg").write_text("\n".join(blocks), encoding="cp1252")
    if checklist is not None:
        (directory / "Checklist").mkdir()
        (directory / "Checklist" / "Aircraft_Checklist.xml").write_text(
            checklist, encoding="cp1252"
        )
    return directory


@pytest.fixture
def community(tmp_path: Path) -> Path:
    folder = tmp_path / "MSFS" / "Community"
    folder.mkdir(parents=True)
    make_package(
        folder, "vendor-aircraft-widget", "vendor-widget",
        titles=["Widget Aviation Widget 500 White", "Widget Aviation Widget 500 Blue"],
        manufacturer="Widget Aviation", ui_type="Widget 500", icao="WI50",
        engines=2, engine_type=5, checklist=CHECKLIST,
    )
    make_package(
        folder, "vendor-aircraft-sprocket", "vendor-sprocket",
        titles=["Sprocket Sprocket 100"],
        manufacturer="Sprocket", ui_type="Sprocket 100", icao="SP10",
    )
    # Le C172 est déjà dans la base livrée : il doit ressortir comme couvert.
    make_package(
        folder, "vendor-aircraft-c172", "vendor-c172",
        titles=["Cessna 172 Skyhawk G1000"],
        manufacturer="Cessna", ui_type="172 Skyhawk", icao="C172",
    )
    return folder


# --------------------------------------------------------------------- #
# Localisation


def test_le_dossier_explicite_l_emporte(community: Path):
    assert community_folders([community]) == [community]


def test_un_parent_est_accepte_a_la_place_du_dossier_community(community: Path):
    """L'utilisateur donnera souvent la racine du simulateur, pas Community."""
    assert community_folders([community.parent]) == [community]


def test_un_chemin_faux_est_ignore_sans_exception(tmp_path: Path):
    assert community_folders([tmp_path / "nulle-part"]) == []


def test_le_chemin_est_lu_dans_user_cfg(tmp_path: Path):
    simulator = tmp_path / "Simulateur"
    (simulator / "Community").mkdir(parents=True)
    config = tmp_path / "UserCfg.opt"
    config.write_text(
        'SomeOtherKey 1\nInstalledPackagesPath "%s"\n' % simulator, encoding="utf-8"
    )
    assert packages_paths([config]) == [simulator]
    assert community_folders(None, [config]) == [simulator / "Community"]


def test_les_deux_dossiers_community_de_msfs_2024_sont_retenus(tmp_path: Path):
    simulator = tmp_path / "MSFS2024"
    for name in ("Community", "Community2024", "Official2024"):
        (simulator / name).mkdir(parents=True)
    config = tmp_path / "UserCfg.opt"
    config.write_text('InstalledPackagesPath "%s"\n' % simulator, encoding="utf-8")
    trouves = [f.name for f in community_folders(None, [config])]
    assert trouves == ["Community", "Community2024"]


# --------------------------------------------------------------------- #
# Inventaire


def test_recense_les_appareils(community: Path):
    avions = scan([community])
    assert [a.model for a in avions] == ["172 Skyhawk", "Sprocket 100", "Widget 500"]


def test_les_livrees_sont_fusionnees_en_un_seul_appareil(community: Path):
    widget = next(a for a in scan([community]) if a.model == "Widget 500")
    assert widget.titles == (
        "Widget Aviation Widget 500 White",
        "Widget Aviation Widget 500 Blue",
    )
    assert widget.engine_count == 2
    assert widget.engine_type == "turboprop"
    assert widget.checklist is not None


def test_la_survey_separe_le_couvert_du_reste(community: Path):
    report = survey(AircraftMatcher(DB_ROOT), [community])
    assert report.total == 3
    assert [i for _, i, _ in report.covered] == ["cessna/c172"]
    assert sorted(a.model for a in report.missing) == ["Sprocket 100", "Widget 500"]
    assert report.to_dict()["covered"][0]["maturity"] == "authored"


# --------------------------------------------------------------------- #
# Déductions


@pytest.mark.parametrize(
    ("titre", "phase"),
    [
        ("Before Starting Engine", "before_start"),
        ("After Takeoff", "after_takeoff"),
        ("Before Takeoff", "before_takeoff"),
        ("Takeoff", "takeoff"),
        ("After Landing", "after_landing"),
        ("Before Landing", "approach"),
        ("Securing Aircraft", "shutdown"),
        ("Quelque chose d'inattendu", "preflight"),
    ],
)
def test_la_phase_est_deduite_de_l_intitule(titre: str, phase: str):
    assert phase_of(titre) == phase


@pytest.mark.parametrize(
    ("titre", "attendu", "check"),
    [
        ("Parking Brake", "Set", {"property": "configuration.parking_brake", "is": True}),
        ("Parking Brake", "Release", {"property": "configuration.parking_brake", "is": False}),
        ("Wing Flaps", "Up", {"property": "configuration.flaps_handle_index", "is": 0}),
        ("Strobe Lights", "On", {"property": "configuration.lights.strobe", "is": True}),
        ("Beacon", "Off", {"property": "configuration.lights.beacon", "is": False}),
        ("Autopilot", "Disengaged", {"property": "configuration.autopilot_master", "is": False}),
    ],
)
def test_les_etapes_evidentes_deviennent_automatiques(titre, attendu, check):
    systems = dict.fromkeys(
        ["flaps", "autopilot", "retractable_gear", "spoilers", "anti_ice"], True
    )
    inferred = infer_check(titre, attendu, systems)
    assert inferred is not None
    assert inferred[0] == check


@pytest.mark.parametrize(
    ("titre", "attendu"),
    [
        ("Wing Flaps", "As Required"),
        ("Flaps", "Set for takeoff"),
        ("Cowl Flaps", "Open"),
        ("Mixture", "Rich"),
        ("Emergency Gear Handle", "Stowed"),
    ],
)
def test_le_doute_reste_manuel(titre: str, attendu: str):
    """Une étape qui se coche seule à tort coûte plus qu'un clic de trop."""
    systems = dict.fromkeys(["flaps", "retractable_gear"], True)
    assert infer_check(titre, attendu, systems) is None


def test_aucune_verification_sur_un_systeme_absent():
    sans_train = {"flaps": True, "retractable_gear": False}
    assert infer_check("Landing Gear", "Down", sans_train) is None


def test_le_train_rentrant_est_suppose_absent():
    """Le doute penche du côté silencieux : une étape qui disparaît, pas une
    étape qui ne se coche jamais."""
    avion = InstalledAircraft(
        package="p", directory=Path("."), titles=("x",), engine_type="turbofan", engine_count=2
    )
    assert infer_systems(avion)["retractable_gear"] is False
    assert infer_systems(avion)["pressurisation"] is True


def test_les_motifs_viennent_des_titres_reels():
    avion = InstalledAircraft(
        package="p", directory=Path("."),
        titles=("Widget Aviation Widget 500 White",),
        manufacturer="Widget Aviation", model="Widget 500",
    )
    assert derive_patterns(avion) == ["widget aviation widget 500", "widget 500"]


def test_un_motif_qui_ne_reconnait_aucun_titre_est_ecarte():
    avion = InstalledAircraft(
        package="p", directory=Path("."), titles=("FNX320 IAE",),
        manufacturer="Fenix", model="A320neo",
    )
    # Ni « fenix a320neo » ni « a320neo » n'apparaissent : repli sur le titre.
    assert derive_patterns(avion) == ["fnx320 iae"]


# --------------------------------------------------------------------- #
# Écriture


def test_le_canevas_est_construit_depuis_la_checklist_de_l_appareil(community: Path):
    widget = next(a for a in scan([community]) if a.model == "Widget 500")
    entry = build_entry(widget, identifier_for(widget))

    procedures = entry["procedures"]["procedures"]
    assert [p["phase"] for p in procedures] == ["before_start", "after_takeoff"]

    etapes = {s["id"]: s for p in procedures for s in p["steps"]}
    assert etapes["parking_brake"]["mode"] == "auto"
    assert etapes["preflight_inspection"]["mode"] == "manual"
    assert etapes["strobe_lights"]["mode"] == "auto"
    # Le train est supposé absent : l'étape reste à confirmer à la main.
    assert etapes["landing_gear"]["mode"] == "manual"
    assert etapes["cowl_flaps"]["mode"] == "manual"

    assert entry["metadata"]["maturity"] == "draft"
    assert entry["metadata"]["propulsion"] == "turboprop"
    assert entry["limitations"]["speeds"] == {}


def test_ecrit_une_famille_valide_dans_la_base_utilisateur(community: Path, tmp_path: Path):
    user = tmp_path / "base-utilisateur"
    widget = next(a for a in scan([community]) if a.model == "Widget 500")
    directory = write_entry(widget, user)

    assert directory == user / "aircraft" / "widget_aviation" / "widget_500"
    for name in ("metadata", "systems", "procedures", "limitations", "mapping"):
        assert (directory / f"{name}.json").is_file()

    # Le canevas doit être détectable immédiatement, sans retouche.
    matcher = AircraftMatcher(DB_ROOT, user_root=user)
    match = matcher.match("Widget Aviation Widget 500 White")
    assert match is not None
    assert match.entry.user_supplied is True
    assert match.entry.maturity == "draft"


def test_le_canevas_ecrit_passe_le_validateur(community: Path, tmp_path: Path):
    """Un canevas invalide serait pire qu'aucun canevas."""
    import importlib.util
    import sys

    user = tmp_path / "base-utilisateur"
    (user / "schema").mkdir(parents=True)
    (user / "schema" / "properties.json").write_text(
        (DB_ROOT / "schema" / "properties.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (user / "VERSION.json").write_text(
        json.dumps({"version": "2026.08.08", "schema_version": 1}), encoding="utf-8"
    )
    for aircraft in scan([community]):
        if aircraft.model != "172 Skyhawk":
            write_entry(aircraft, user)

    spec = importlib.util.spec_from_file_location(
        "validate_for_user_db", DB_ROOT / "tools" / "validate.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.validate_database(user) == []


def test_refuse_d_ecraser_un_avion_deja_amorce(community: Path, tmp_path: Path):
    user = tmp_path / "base-utilisateur"
    widget = next(a for a in scan([community]) if a.model == "Widget 500")
    write_entry(widget, user)
    with pytest.raises(FileExistsError):
        write_entry(widget, user)
