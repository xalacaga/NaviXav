"""Détection et model matching FSLTL, sans installation ni simulateur."""

from pathlib import Path

from navixav.traffic.base import MatchKind, TrafficAircraft
from navixav.traffic.fsltl import (
    FsltlModelIndex,
    FsltlStatus,
    detect_fsltl,
    parse_aircraft_config,
    parse_vmr,
)


def _package(tmp_path: Path, *, vmr: str | None = None) -> Path:
    community = tmp_path / "Community"
    root = community / "fsltl-traffic-base"
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(
        '{"title":"FSLTL Traffic Base","package_version":"1.2.3"}',
        encoding="utf-8",
    )
    planes = root / "SimObjects" / "Airplanes"
    (planes / "FSLTL_A320").mkdir(parents=True)
    (planes / "FSLTL_A320" / "aircraft.cfg").write_text(
        """
[GENERAL]
icao_type_designator = "A320"
[FLTSIM.0]
title = "FSLTL_A320_ZZZZ"
icao_airline = "ZZZZ"
[FLTSIM.1]
title = "FSLTL_A320_AFR"
icao_airline = "AFR"
""",
        encoding="utf-8",
    )
    if vmr is not None:
        (root / "FSLTL_Rules.vmr").write_text(vmr, encoding="utf-8")
    return community


def _aircraft(kind: str | None = "A320", airline: str | None = "AFR") -> TrafficAircraft:
    return TrafficAircraft(
        uid="AFR123", callsign="AFR123", aircraft_type=kind,
        airline_icao=airline, latitude=48.0, longitude=2.0,
    )


def test_detection_distinguishes_absent_incomplete_and_detected(tmp_path):
    assert detect_fsltl([tmp_path]).status is FsltlStatus.NOT_DETECTED
    incomplete = tmp_path / "Community" / "fsltl-traffic-base"
    incomplete.mkdir(parents=True)
    assert detect_fsltl([tmp_path / "Community"]).status is FsltlStatus.INCOMPLETE
    community = _package(tmp_path / "complete")
    found = detect_fsltl([community])
    assert found.status is FsltlStatus.DETECTED
    assert found.version == "1.2.3"
    assert found.config_count == 1


def test_manual_path_accepts_the_package_or_its_community_folder(tmp_path):
    community = _package(tmp_path)
    package = community / "fsltl-traffic-base"

    assert detect_fsltl(explicit_path=package).status is FsltlStatus.DETECTED
    assert detect_fsltl(explicit_path=community).root == package
    assert detect_fsltl(explicit_path=tmp_path / "missing").status is FsltlStatus.NOT_DETECTED


def test_aircraft_cfg_keeps_every_variation_and_missing_values(tmp_path):
    community = _package(tmp_path)
    path = next(community.glob("*/SimObjects/Airplanes/*/aircraft.cfg"))
    models = parse_aircraft_config(path)
    assert [(m.title, m.aircraft_type, m.airline_icao) for m in models] == [
        ("FSLTL_A320_ZZZZ", "A320", "ZZZZ"),
        ("FSLTL_A320_AFR", "A320", "AFR"),
    ]


def test_invalid_or_unsafe_vmr_is_ignored(tmp_path):
    malformed = tmp_path / "bad.vmr"
    malformed.write_text("<ModelMatchRuleSet><broken>", encoding="utf-8")
    assert parse_vmr(malformed) == []
    unsafe = tmp_path / "unsafe.vmr"
    unsafe.write_text(
        '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///secret">]><ModelMatchRuleSet/>',
        encoding="utf-8",
    )
    assert parse_vmr(unsafe) == []


def test_exact_vmr_then_generic_aircraft_fallback(tmp_path):
    community = _package(
        tmp_path,
        vmr="""<ModelMatchRuleSet>
          <ModelMatchRule TypeCode="A320" CallsignPrefix="AFR"
            ModelName="missing//FSLTL_A320_AFR" />
          <ModelMatchRule TypeCode="A320" ModelName="FSLTL_A320_ZZZZ" />
        </ModelMatchRuleSet>""",
    )
    index = FsltlModelIndex(detect_fsltl([community]))
    exact = index.match(_aircraft())
    generic = index.match(_aircraft(airline="XYZ"))
    assert exact.title == "FSLTL_A320_AFR"
    assert exact.match_kind is MatchKind.EXACT
    assert generic.title == "FSLTL_A320_ZZZZ"
    assert generic.match_kind is MatchKind.AIRCRAFT


def test_unknown_aircraft_uses_only_an_explicit_msfs_fallback(tmp_path):
    community = _package(tmp_path)
    index = FsltlModelIndex(detect_fsltl([community]))
    assert index.match(_aircraft("ZZZZ")) is None
    fallback = index.match(_aircraft("ZZZZ"), ["Generic Twin Engine"])
    assert fallback.provider == "MSFS"
    assert fallback.fallback_level == 3


def test_real_traffic_without_a_type_gets_a_safe_generic_fsltl_model(tmp_path):
    index = FsltlModelIndex(detect_fsltl([_package(tmp_path)]))

    airliner = index.generic_fallback(_aircraft("", airline="AFR"))
    light = index.generic_fallback(_aircraft("", airline=""))

    assert airliner.title == "FSLTL_A320_ZZZZ"
    assert airliner.match_kind is MatchKind.FAMILY
    assert light.title == "FSLTL_A320_ZZZZ"
