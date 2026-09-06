"""Détection et model matching AIG, sans installation ni simulateur."""

from pathlib import Path

from navixav.traffic.aig import AigModelIndex, detect_aig
from navixav.traffic.base import (
    GenericFallbackIndex,
    InstallationStatus,
    MatchKind,
    TrafficAircraft,
)

# La forme réelle d'un `aircraft.cfg` AIG : un seul `icao_type_designator`
# dans `[General]` couvre toutes les livrées, chacune n'apportant que son
# titre et sa compagnie.
CONFIG = """
[VERSION]
major = 1
[General]
icao_type_designator = "E55P"
atc_type = "$$:Embraer"
[fltsim.0]
title = "AIGAIM_NetJets Embraer Phenom 300E - N418QS"
icao_airline = "EJA"
[fltsim.1]
title = "AIGAIM_Flexjet Embraer Phenom 300 - N300FX"
icao_airline = "LXJ"
[fltsim.2]
title = "AIGAIM_Private Embraer Phenom 300"
"""


def _package(
    tmp_path: Path,
    *,
    name: str = "aig-aitraffic-oci",
    vmr: str | None = None,
    companions: bool = True,
    config: str | None = CONFIG,
) -> Path:
    community = tmp_path / "Community"
    root = community / name
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(
        '{"title":"AIGAIM AI Traffic","package_version":"0.1.0"}', encoding="utf-8"
    )
    planes = root / "SimObjects" / "Airplanes"
    folder = planes / f"AIGAIM_{name}_E55P"
    folder.mkdir(parents=True)
    if config is not None:
        (folder / "aircraft.cfg").write_text(config, encoding="utf-8")
    if vmr is not None:
        (root / "aig.vmr").write_text(vmr, encoding="utf-8")
    if companions:
        for companion in ("aig-aitraffic-modelbehavior", "aig-aitraffic-effects"):
            (community / companion).mkdir(exist_ok=True)
    return community


def _aircraft(kind: str | None = "E55P", airline: str | None = "EJA") -> TrafficAircraft:
    return TrafficAircraft(
        uid="EJA1", callsign="EJA1", aircraft_type=kind,
        airline_icao=airline, latitude=48.0, longitude=2.0,
    )


def test_detection_distinguishes_absent_incomplete_and_detected(tmp_path):
    assert detect_aig([tmp_path]).status is InstallationStatus.NOT_DETECTED

    community = _package(tmp_path, config=None)
    # Le paquet est là, mais AI Manager n'y a écrit aucune configuration.
    incomplete = detect_aig([community])
    assert incomplete.status is InstallationStatus.INCOMPLETE
    assert incomplete.reason == "aucun aircraft.cfg"

    (community / "aig-aitraffic-oci" / "SimObjects" / "Airplanes"
     / "AIGAIM_aig-aitraffic-oci_E55P" / "aircraft.cfg").write_text(
        CONFIG, encoding="utf-8"
    )
    found = detect_aig([community])
    assert found.status is InstallationStatus.DETECTED
    assert found.version == "0.1.0"
    assert found.config_count == 1


def test_manual_path_accepts_the_package_or_its_community_folder(tmp_path):
    community = _package(tmp_path)
    package = community / "aig-aitraffic-oci"
    assert detect_aig(explicit_path=package).status is InstallationStatus.DETECTED
    assert detect_aig(explicit_path=community).status is InstallationStatus.DETECTED
    assert detect_aig(
        explicit_path=tmp_path / "missing"
    ).status is InstallationStatus.NOT_DETECTED


def test_missing_libraries_are_reported_without_blocking_the_injection(tmp_path):
    community = _package(tmp_path, companions=False)
    installation = detect_aig([community])
    assert installation.status is InstallationStatus.DETECTED
    assert installation.missing_companions == (
        "aig-aitraffic-modelbehavior", "aig-aitraffic-effects"
    )
    assert installation.to_dict()["companions"] == [
        "aig-aitraffic-modelbehavior", "aig-aitraffic-effects"
    ]


def test_several_oci_packages_are_merged_and_libraries_are_never_indexed(tmp_path):
    community = _package(tmp_path)
    _package(tmp_path, name="aig-aitraffic-oci-cargo", companions=False)
    installation = detect_aig([community])
    assert len(installation.roots) == 2
    assert installation.config_count == 2
    assert all("oci" in root.name for root in installation.roots)


def test_the_general_section_type_covers_every_livery(tmp_path):
    index = AigModelIndex(detect_aig([_package(tmp_path)]))
    assert len(index.models) == 3
    assert {model.aircraft_type for model in index.models} == {"E55P"}

    exact = index.match(_aircraft())
    assert exact.title == "AIGAIM_NetJets Embraer Phenom 300E - N418QS"
    assert exact.provider == "AIG"
    assert exact.match_kind is MatchKind.EXACT

    # La livrée sans compagnie sert de générique pour le type.
    generic = index.match(_aircraft(airline="AFR"))
    assert generic.title == "AIGAIM_Private Embraer Phenom 300"
    assert generic.match_kind is MatchKind.AIRCRAFT


def test_a_root_vmr_is_read_whatever_its_name(tmp_path):
    community = _package(
        tmp_path,
        vmr=(
            '<?xml version="1.0" encoding="utf-8"?>\n<ModelMatchRuleSet>'
            '<ModelMatchRule CallsignPrefix="LXJ" TypeCode="E55P" '
            'ModelName="AIGAIM_Flexjet Embraer Phenom 300 - N300FX" />'
            "</ModelMatchRuleSet>"
        ),
    )
    (community / "aig-aitraffic-oci" / "aig.vmr").rename(
        community / "aig-aitraffic-oci" / "mirror-pack.vmr"
    )
    installation = detect_aig([community])
    assert len(installation.vmr_paths) == 1

    index = AigModelIndex(installation)
    assert len(index.rules) == 1
    matched = index.match(_aircraft(airline="LXJ"))
    assert matched.title == "AIGAIM_Flexjet Embraer Phenom 300 - N300FX"
    assert matched.source_rule == "VMR E55P + LXJ"


def test_aig_offers_no_generic_model_and_says_so(tmp_path):
    """AIG n'a pas de convention `ZZZZ` : le repli ne doit pas être inventé."""
    index = AigModelIndex(detect_aig([_package(tmp_path)]))
    assert not isinstance(index, GenericFallbackIndex)
    assert index.match(_aircraft(kind=None)) is None
