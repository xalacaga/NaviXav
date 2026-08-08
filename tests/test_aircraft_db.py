"""Contrôles de la NaviXav Aircraft Database.

Le test central est `test_vocabulaire_aligne_sur_le_moteur` : il attache le
vocabulaire de la base aux dataclasses de `navixav.live.base`. Renommer un
attribut du moteur sans mettre `schema/properties.json` à jour fait échouer la
suite, ce qui est le seul garde-fou possible entre deux dépôts destinés à être
séparés.
"""

from __future__ import annotations

import importlib.util
import io
import json
import shutil
import sys
from pathlib import Path

import pytest

from navixav.live.base import AircraftConfiguration, AircraftState

DB_ROOT = Path(__file__).resolve().parent.parent / "aircraft_db"


def _load_tool(name: str):
    path = DB_ROOT / "tools" / f"{name}.py"
    # La base est du code étranger au paquet navixav : elle est chargée par son
    # chemin, comme le fera le dépôt séparé.
    spec = importlib.util.spec_from_file_location(f"aircraft_db_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # `@dataclass` résout ses annotations via `sys.modules[cls.__module__]` :
    # sans cet enregistrement préalable, l'import échoue sur un module chargé
    # par son chemin.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validate = _load_tool("validate")
coverage = _load_tool("coverage")


@pytest.fixture(scope="module")
def vocabulary() -> dict:
    return json.loads((DB_ROOT / "schema" / "properties.json").read_text(encoding="utf-8"))


def test_base_conforme():
    assert validate.validate_database(DB_ROOT) == []


def test_vocabulaire_aligne_sur_le_moteur(vocabulary):
    owners = {
        "AircraftState": AircraftState,
        "AircraftConfiguration": AircraftConfiguration,
    }

    for name, spec in vocabulary["properties"].items():
        source = spec["source"]
        owner, _, attribute = source.partition(".")
        assert owner in owners, f"{name} : classe inconnue « {owner} »"

        # Les propriétés de lampes visent une entrée du dictionnaire `lights`.
        attribute = attribute.partition("[")[0]
        fields = owners[owner].__dataclass_fields__
        assert attribute in fields, f"{name} : « {source} » n'existe plus dans le moteur"


def test_c172_sans_train_rentrant(vocabulary):
    systems = json.loads(
        (DB_ROOT / "aircraft" / "cessna" / "c172" / "systems.json").read_text(encoding="utf-8")
    )["systems"]
    assert systems["retractable_gear"] is False


def test_etapes_auto_portent_un_check():
    procedures = json.loads(
        (DB_ROOT / "aircraft" / "cessna" / "c172" / "procedures.json").read_text(encoding="utf-8")
    )["procedures"]
    steps = [step for procedure in procedures for step in procedure["steps"]]
    assert steps, "aucune étape chargée"
    for step in steps:
        if step["mode"] == "auto":
            assert "check" in step, f"{step['id']} : étape auto sans check"
        else:
            assert "check" not in step, f"{step['id']} : étape non auto avec un check"


def test_groupes_du_before_takeoff():
    """Le regroupement est une respiration visuelle, sans ordre imposé.

    Le test fixe l'intention du C172 : la montée en puissance, la configuration
    et l'alignement forment trois blocs distincts dans le module Procedures.
    """
    procedures = json.loads(
        (DB_ROOT / "aircraft" / "cessna" / "c172" / "procedures.json").read_text(encoding="utf-8")
    )["procedures"]
    before_takeoff = next(p for p in procedures if p["id"] == "before_takeoff")
    groups = [step.get("group") for step in before_takeoff["steps"]]
    assert set(groups) == {None, "runup", "configuration", "line_up"}


@pytest.fixture
def broken_db(tmp_path: Path) -> Path:
    root = tmp_path / "aircraft_db"
    shutil.copytree(DB_ROOT, root)
    return root


def _rewrite(path: Path, mutate) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_refuse_une_propriete_hors_vocabulaire(broken_db: Path):
    procedures = broken_db / "aircraft" / "cessna" / "c172" / "procedures.json"

    def mutate(data):
        data["procedures"][0]["steps"][3]["check"] = {
            "property": "configuration.brake_parking_position",
            "is": True,
        }

    _rewrite(procedures, mutate)
    errors = validate.validate_database(broken_db)
    assert any("hors vocabulaire" in error for error in errors), errors


def test_refuse_une_verification_sur_un_systeme_absent(broken_db: Path):
    """Un contrôle de train sur un C172 doit être rejeté par la base.

    C'est la classe d'erreur que le format existe pour empêcher : une étape qui
    ne se cocherait jamais, sur un avion qui n'a pas le système.
    """
    procedures = broken_db / "aircraft" / "cessna" / "c172" / "procedures.json"

    def mutate(data):
        data["procedures"][0]["steps"].append(
            {
                "id": "gear_down",
                "title": "LANDING GEAR",
                "expected": "DOWN",
                "mode": "auto",
                "check": {"property": "configuration.gear_handle_down", "is": True},
            }
        )

    _rewrite(procedures, mutate)
    errors = validate.validate_database(broken_db)
    assert any("retractable_gear" in error for error in errors), errors


def test_refuse_un_comparateur_incoherent(broken_db: Path):
    procedures = broken_db / "aircraft" / "cessna" / "c172" / "procedures.json"

    def mutate(data):
        data["procedures"][0]["steps"][3]["check"] = {
            "property": "configuration.parking_brake",
            "at_least": 1,
        }

    _rewrite(procedures, mutate)
    errors = validate.validate_database(broken_db)
    assert any("booléen" in error for error in errors), errors


def test_refuse_une_phase_inconnue(broken_db: Path):
    procedures = broken_db / "aircraft" / "cessna" / "c172" / "procedures.json"

    def mutate(data):
        data["procedures"][0]["phase"] = "avant_le_demarrage"

    _rewrite(procedures, mutate)
    errors = validate.validate_database(broken_db)
    assert any("phase inconnue" in error for error in errors), errors


def test_refuse_un_groupe_vide(broken_db: Path):
    procedures = broken_db / "aircraft" / "cessna" / "c172" / "procedures.json"

    def mutate(data):
        data["procedures"][0]["steps"][0]["group"] = ""

    _rewrite(procedures, mutate)
    errors = validate.validate_database(broken_db)
    assert any("`group`" in error for error in errors), errors


def test_refuse_un_motif_de_detection_capitalise(broken_db: Path):
    metadata = broken_db / "aircraft" / "cessna" / "c172" / "metadata.json"

    def mutate(data):
        data["match"]["title_contains"] = ["Cessna 172"]

    _rewrite(metadata, mutate)
    errors = validate.validate_database(broken_db)
    assert any("minuscules" in error for error in errors), errors


# --------------------------------------------------------------------- #
# tools/coverage.py
#
# Les sources d'exemple sont fabriquées ici, jamais versionnées : les
# checklists publiées sont sous GPL et la base sous Apache-2.0. L'outil les lit
# depuis leur propre clone, et ces tests reproduisent seulement leur format.


def _run_coverage(*arguments: str) -> int:
    return coverage.main(["coverage.py", *arguments])


def _multicrew(path: Path, items: list[tuple[str, str]]) -> Path:
    path.write_text(
        json.dumps(
            {
                "aircraft": "C172",
                "checklists": [
                    {
                        "name": "BEFORE TAKEOFF",
                        "items": [
                            {"checkpoint": title, "value": value, "role": "pf"}
                            for title, value in items
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_coverage_ne_signale_rien_quand_la_base_couvre_la_source(tmp_path, capsys):
    source = _multicrew(
        tmp_path / "c172.json",
        [("PARKING BRAKE", "SET"), ("WING FLAPS", "UP"), ("MIXTURE", "RICH")],
    )
    assert _run_coverage("cessna/c172", "--source", str(source)) == 0
    assert "Aucune étape manquante" in capsys.readouterr().out


def test_coverage_signale_une_etape_absente(tmp_path, capsys):
    source = _multicrew(
        tmp_path / "c172.json",
        [("PARKING BRAKE", "SET"), ("OXYGEN MASKS", "CHECKED")],
    )
    assert _run_coverage("cessna/c172", "--source", str(source), "--strict") == 1
    out = capsys.readouterr().out
    assert "OXYGEN MASKS" in out
    assert "PARKING BRAKE" not in out.split("manquant", 1)[1]


def test_coverage_lit_le_xml_flightgear(tmp_path, capsys):
    source = tmp_path / "checklists.xml"
    # Les items sont rangés sous <page>, disposition que l'outil doit traverser.
    source.write_text(
        """<?xml version="1.0"?>
<PropertyList>
  <checklist>
    <title>Before Takeoff</title>
    <page>
      <item><name>Parking brake</name><value>Set</value></item>
      <item><name>Oxygen masks</name><value>Checked</value></item>
    </page>
  </checklist>
</PropertyList>
""",
        encoding="utf-8",
    )
    assert _run_coverage("cessna/c172", "--source", str(source), "--strict") == 1
    assert "Oxygen masks" in capsys.readouterr().out


def test_coverage_refuse_une_source_versionnee_dans_la_base(capsys):
    """Garde-fou de licence : une source GPL ne s'installe pas dans la base."""
    interne = DB_ROOT / "VERSION.json"
    assert _run_coverage("cessna/c172", "--source", str(interne)) == 2
    assert "Refus" in capsys.readouterr().err


def test_coverage_refuse_un_format_inconnu(tmp_path, capsys):
    source = tmp_path / "checklist.txt"
    source.write_text("PARKING BRAKE ... SET", encoding="utf-8")
    assert _run_coverage("cessna/c172", "--source", str(source)) == 2
    assert "format inconnu" in capsys.readouterr().err


def test_coverage_ecrit_sur_une_console_cp1252(tmp_path, monkeypatch):
    """Le rapport doit passer sur une console Windows par défaut.

    `capsys` remplace la sortie par un flux tolérant et masque le problème :
    ce test reproduit le cp1252 réel, où « → » et « ✓ » ne sont pas encodables.
    """
    source = _multicrew(tmp_path / "c172.json", [("PARKING BRAKE", "SET")])
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", stream)

    assert _run_coverage("cessna/c172", "--source", str(source)) == 0
    assert stream.encoding.lower() in {"utf-8", "utf8"}


# --------------------------------------------------------------------- #
# Sources de remplacement déclarées par une variante


def _a320_mapping(root: Path) -> Path:
    return root / "aircraft" / "airbus" / "a320" / "mapping.json"


def _fenix_override(data: dict) -> dict:
    variant = next(v for v in data["variants"] if v["id"] == "fenix")
    return variant["overrides"]


def test_refuse_un_as_incompatible_avec_la_propriete(broken_db: Path):
    """`parking_brake` est booléen : aucune conversion numérique n'a de sens."""
    path = _a320_mapping(broken_db)

    def mutate(data):
        _fenix_override(data)["configuration.parking_brake"]["as"] = "number"

    _rewrite(path, mutate)
    errors = validate.validate_database(broken_db)
    assert any("`as` ne peut pas valoir number" in error for error in errors), errors


def test_refuse_un_seuil_sur_une_conversion_numerique(broken_db: Path):
    path = _a320_mapping(broken_db)

    def mutate(data):
        _fenix_override(data)["configuration.spoilers_handle_pct"]["below"] = 0.5

    _rewrite(path, mutate)
    errors = validate.validate_database(broken_db)
    assert any("ne s'applique qu'à un booléen" in error for error in errors), errors


def test_refuse_une_mise_a_l_echelle_sur_un_booleen(broken_db: Path):
    path = _a320_mapping(broken_db)

    def mutate(data):
        _fenix_override(data)["configuration.spoilers_armed"]["scale"] = 2.0

    _rewrite(path, mutate)
    errors = validate.validate_database(broken_db)
    assert any("n'a pas de sens sur un booléen" in error for error in errors), errors


def test_refuse_un_override_sans_lvar(broken_db: Path):
    path = _a320_mapping(broken_db)

    def mutate(data):
        del _fenix_override(data)["configuration.parking_brake"]["lvar"]

    _rewrite(path, mutate)
    errors = validate.validate_database(broken_db)
    assert any("`lvar` manquant" in error for error in errors), errors


def test_refuse_below_et_above_ensemble(broken_db: Path):
    path = _a320_mapping(broken_db)

    def mutate(data):
        _fenix_override(data)["configuration.spoilers_armed"]["above"] = 2.0

    _rewrite(path, mutate)
    errors = validate.validate_database(broken_db)
    assert any("s'excluent" in error for error in errors), errors


def test_chaque_avion_declare_tous_les_systemes():
    """Un système omis vaudrait absent par défaut : la base doit être explicite."""
    vocabulary = json.loads(
        (DB_ROOT / "schema" / "properties.json").read_text(encoding="utf-8")
    )
    expected = set(vocabulary["systems"])
    for metadata in sorted((DB_ROOT / "aircraft").glob("*/*/metadata.json")):
        systems = json.loads(
            (metadata.parent / "systems.json").read_text(encoding="utf-8")
        )["systems"]
        assert set(systems) == expected, metadata.parent.name


def test_coverage_lit_le_xml_msfs(tmp_path, capsys):
    """Format natif du simulateur : `<Page>` nomme la checklist, `<CheckpointDesc>` l'étape."""
    source = tmp_path / "C172_Checklist.xml"
    source.write_text(
        """<?xml version="1.0" encoding="Windows-1252"?>
<SimBase.Document Type="Checklist" version="1,0">
  <Checklist.Checklist>
    <Step ChecklistStepId="PREFLIGHT_GATE">
      <Page SubjectTT="Before Takeoff">
        <Checkpoint>
          <CheckpointDesc SubjectTT="Parking Brake" ExpectationTT="Set"/>
          <Instrument Id="LANDING_GEAR_SWITCH_PARKINGBRAKE"/>
        </Checkpoint>
        <Checkpoint>
          <CheckpointDesc SubjectTT="Cowl Flaps" ExpectationTT="Open"/>
        </Checkpoint>
      </Page>
    </Step>
  </Checklist.Checklist>
</SimBase.Document>
""",
        encoding="cp1252",
    )
    assert _run_coverage("cessna/c172", "--source", str(source), "--strict") == 1
    out = capsys.readouterr().out
    assert "Cowl Flaps" in out
    # « Parking Brake » est couvert : seule l'étape absente doit être signalée.
    assert "manquant   Parking Brake" not in out


def test_coverage_refuse_une_racine_xml_inconnue(tmp_path, capsys):
    source = tmp_path / "autre.xml"
    source.write_text("<?xml version='1.0'?><Autre><x/></Autre>", encoding="utf-8")
    assert _run_coverage("cessna/c172", "--source", str(source)) == 2
    assert "racine XML inconnue" in capsys.readouterr().err


def test_refuse_une_maturite_inconnue(broken_db: Path):
    path = broken_db / "aircraft" / "cessna" / "c172" / "metadata.json"

    def mutate(data):
        data["maturity"] = "verified"

    _rewrite(path, mutate)
    errors = validate.validate_database(broken_db)
    assert any("`maturity`" in error for error in errors), errors


def test_aucun_canevas_ne_pretend_avoir_des_limitations():
    """Une V-speed fausse est pire qu'une V-speed absente.

    Les canevas de classe ne devinent aucune limitation : leur `speeds` est
    vide, et c'est le comportement voulu tant que personne n'a ouvert le manuel.
    """
    for metadata in sorted((DB_ROOT / "aircraft").glob("*/*/metadata.json")):
        data = json.loads(metadata.read_text(encoding="utf-8"))
        if data.get("maturity") != "draft":
            continue
        speeds = json.loads(
            (metadata.parent / "limitations.json").read_text(encoding="utf-8")
        )["speeds"]
        assert speeds == {}, f"{data['id']} : un canevas ne doit pas inventer de vitesses"
