"""Choix du jeu de modèles : un seul jeu injecte, l'autre reste visible."""

from pathlib import Path

from navixav.traffic.aig import AigModelIndex
from navixav.traffic.base import InstallationStatus, TrafficAircraft
from navixav.traffic.fsltl import FsltlModelIndex
from navixav.traffic.selection import build_index, detect_models, normalise_choice


def _fsltl(community: Path) -> Path:
    root = community / "fsltl-traffic-base"
    planes = root / "SimObjects" / "Airplanes" / "FSLTL_A320"
    planes.mkdir(parents=True)
    (root / "manifest.json").write_text(
        '{"title":"FSLTL Traffic Base","package_version":"1.2.3"}', encoding="utf-8"
    )
    (planes / "aircraft.cfg").write_text(
        '[GENERAL]\nicao_type_designator = "A320"\n'
        '[FLTSIM.0]\ntitle = "FSLTL_A320_AFR"\nicao_airline = "AFR"\n',
        encoding="utf-8",
    )
    return community


def _aig(community: Path) -> Path:
    root = community / "aig-aitraffic-oci"
    planes = root / "SimObjects" / "Airplanes" / "AIGAIM_AFR_A320"
    planes.mkdir(parents=True)
    (root / "manifest.json").write_text(
        '{"title":"AIGAIM AI Traffic","package_version":"0.1.0"}', encoding="utf-8"
    )
    (planes / "aircraft.cfg").write_text(
        '[General]\nicao_type_designator = "A320"\n'
        '[fltsim.0]\ntitle = "AIGAIM_Air France Airbus A320-200"\n'
        'icao_airline = "AFR"\n',
        encoding="utf-8",
    )
    return community


def _aircraft() -> TrafficAircraft:
    return TrafficAircraft(
        uid="AFR1", callsign="AFR1", aircraft_type="A320",
        airline_icao="AFR", latitude=48.0, longitude=2.0,
    )


def test_an_unknown_choice_falls_back_to_the_installed_default():
    assert normalise_choice("AIG") == "aig"
    assert normalise_choice("navigraph") == "fsltl"
    # Les deux jeux à la fois n'existent pas : un vol, une bibliothèque.
    assert normalise_choice("both") == "fsltl"
    assert normalise_choice("") == "fsltl"


def test_both_sets_are_always_reported_but_only_the_choice_injects(tmp_path):
    community = _fsltl(tmp_path / "Community")

    setup = detect_models("aig", [community])
    # AIG n'est pas installé : le choix ne peut pas injecter…
    assert setup.status is InstallationStatus.NOT_DETECTED
    assert setup.reason == "modèles AIG absents"
    # … mais l'interface voit tout de même le jeu présent sur le disque.
    assert setup.to_dict()["sets"]["fsltl"]["detected"] is True

    chosen = detect_models("fsltl", [community])
    assert chosen.status is InstallationStatus.DETECTED
    assert chosen.version == "FSLTL 1.2.3"


def test_only_the_chosen_set_is_ever_indexed(tmp_path):
    """Les deux paquets sont là : un seul doit répondre."""
    community = tmp_path / "Community"
    community.mkdir()
    _fsltl(community)
    _aig(community)

    fsltl = build_index(detect_models("fsltl", [community]))
    assert isinstance(fsltl, FsltlModelIndex)
    assert fsltl.match(_aircraft()).title == "FSLTL_A320_AFR"

    aig = build_index(detect_models("aig", [community]))
    assert isinstance(aig, AigModelIndex)
    assert aig.match(_aircraft()).title == "AIGAIM_Air France Airbus A320-200"

    # Aucun index ne connaît les titres de l'autre.
    assert all("AIGAIM" not in model.title for model in fsltl.models)
    assert all("FSLTL" not in model.title for model in aig.models)
