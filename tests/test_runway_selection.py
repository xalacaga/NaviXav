from __future__ import annotations

from navixav.models import WindInfo
from navixav.navdata.base import Runway
from navixav.planner.runway import score_runways


def _runway(name: str, heading: float, length: float, ils: str | None = None) -> Runway:
    return Runway(
        name=name,
        heading_true_deg=heading,
        length_ft=length,
        width_ft=150.0,
        surface="asphalte",
        ils_ident=ils,
        is_landing=True,
        is_takeoff=True,
        lat=0.0,
        lon=0.0,
    )


LFBO_RUNWAYS = [
    _runway("14L", 143.0, 9925, "TG"),
    _runway("14R", 143.0, 11493, "TBS"),
    _runway("32L", 323.0, 11493, "TBN"),
    _runway("32R", 323.0, 9925, "TD"),
]


def test_wind_picks_the_right_direction():
    scores = score_runways(
        LFBO_RUNWAYS, WindInfo(direction_deg=330, speed_kt=8), for_landing=True
    )
    assert scores[0].runway.name.startswith("32")
    assert scores[0].headwind_kt > 7


def test_length_alone_favours_the_longer_parallel():
    scores = score_runways(
        LFBO_RUNWAYS, WindInfo(direction_deg=330, speed_kt=8), for_landing=True
    )
    assert scores[0].runway.name == "32L"


def test_preference_breaks_the_tie_between_parallels():
    scores = score_runways(
        LFBO_RUNWAYS,
        WindInfo(direction_deg=330, speed_kt=8),
        for_landing=True,
        preferred=["32R", "14L"],
    )
    assert scores[0].runway.name == "32R"
    assert scores[0].preferred


def test_preference_never_beats_a_bad_wind():
    """Une préférence ne doit pas retenir une piste à fort vent arrière."""
    scores = score_runways(
        LFBO_RUNWAYS,
        WindInfo(direction_deg=140, speed_kt=25),
        for_landing=True,
        preferred=["32R"],
    )
    assert scores[0].runway.name.startswith("14")


def test_tailwind_limit_disqualifies():
    scores = score_runways(
        LFBO_RUNWAYS,
        WindInfo(direction_deg=140, speed_kt=25),
        for_landing=True,
        max_tailwind_kt=10,
    )
    disqualified = {s.runway.name for s in scores if s.disqualified}
    assert {"32L", "32R"} <= disqualified


def test_gusts_are_used_for_the_computation():
    steady = score_runways(
        LFBO_RUNWAYS, WindInfo(direction_deg=323, speed_kt=10), for_landing=True
    )
    gusty = score_runways(
        LFBO_RUNWAYS,
        WindInfo(direction_deg=323, speed_kt=10, gust_kt=30),
        for_landing=True,
    )
    assert gusty[0].headwind_kt > steady[0].headwind_kt


def test_calm_wind_falls_back_to_length():
    scores = score_runways(
        LFBO_RUNWAYS, WindInfo(speed_kt=0), for_landing=True
    )
    assert scores[0].runway.length_ft == 11493
    assert all(s.headwind_kt == 0 for s in scores)


def test_minimum_length_filter():
    scores = score_runways(
        LFBO_RUNWAYS,
        WindInfo(direction_deg=330, speed_kt=8),
        for_landing=True,
        min_length_ft=11000,
    )
    short = {s.runway.name for s in scores if s.disqualified}
    assert short == {"14L", "32R"}
