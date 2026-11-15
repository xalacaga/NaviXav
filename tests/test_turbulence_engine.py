"""Turbulence ressentie : estimation, rafales de Dryden et écriture dans MSFS."""

from __future__ import annotations

import math
import random
import statistics
import time

import pytest

from navixav.config import Settings
from navixav.msfs.client import SimConnectRefused
from navixav.turbulence import dynamics, model
from navixav.turbulence import terrain as terrain_module
from navixav.turbulence.service import (
    CORE_VARIABLES,
    WRITE_VARIABLES,
    TurbulenceService,
    height_factor,
)

NOW = 1_800_000_000.0


def _conditions(**overrides) -> model.Conditions:
    values = dict(latitude=46.0, longitude=6.0, altitude_ft=35000, height_agl_ft=33000, on_ground=False)
    values.update(overrides)
    return model.Conditions(**values)


def test_edr_levels_follow_icao_thresholds():
    assert model.level(0.05) is None
    assert model.level(0.12) == "LGT"
    assert model.level(0.30) == "MOD"
    assert model.level(0.50) == "SEV"


def test_shear_maps_onto_the_dispatch_risk_thresholds():
    assert model.level(model.shear_to_edr(2.0)) is None
    assert model.level(model.shear_to_edr(4.0)) == "LGT"
    assert model.level(model.shear_to_edr(7.0)) == "MOD"
    assert model.level(model.shear_to_edr(10.0)) == "SEV"


def test_a_nearby_report_at_the_aircraft_level_is_felt_in_full():
    sources = model.Sources(reports=(model.Report(46.05, 6.0, 2, NOW - 600, level_ft=35000),))
    assessment = model.Estimator(seed=1).assess(_conditions(), sources, NOW)
    assert assessment.level == "MOD"
    assert assessment.dominant == "report"


def test_reports_fade_with_distance_level_and_age():
    estimator = model.Estimator(seed=1)
    far = model.Sources(reports=(model.Report(47.0, 6.0, 3, NOW - 600, level_ft=35000),))
    other_level = model.Sources(reports=(model.Report(46.0, 6.0, 3, NOW - 600, level_ft=25000),))
    stale = model.Sources(reports=(model.Report(46.0, 6.0, 3, NOW - 4 * 3600, level_ft=35000),))
    for sources in (far, other_level, stale):
        assert estimator.assess(_conditions(), sources, NOW).edr == 0.0


def test_a_forecast_is_felt_in_patches_not_everywhere():
    sources = model.Sources(forecast=(model.ForecastPoint(46.0, 6.0, 35000, 7.0),))
    estimator = model.Estimator(seed=7)
    felt = [
        estimator.assess(_conditions(latitude=46.0 + i * 0.02), sources, NOW).edr
        for i in range(-20, 21)
    ]
    assert any(value == 0.0 for value in felt)
    assert any(value > model.EDR_MODERATE for value in felt)


def test_a_smooth_report_damps_the_forecast():
    forecast = (model.ForecastPoint(46.0, 6.0, 35000, 9.0),)
    estimator = model.Estimator(seed=3)
    for step in range(200):
        conditions = _conditions(latitude=45.5 + step * 0.005)
        smooth = (model.Report(conditions.latitude, 6.0, 0, NOW - 300, level_ft=35000),)
        alone = estimator.assess(conditions, model.Sources(forecast=forecast), NOW).edr
        if alone > 0.2:
            damped = estimator.assess(
                conditions, model.Sources(forecast=forecast, reports=smooth), NOW
            ).edr
            assert damped == pytest.approx(alone * model.SMOOTH_REPORT_DAMPING)
            return
    pytest.fail("aucune plaque de turbulence traversée")


def test_independent_sources_add_in_energy():
    conditions = _conditions(in_cloud=True, height_agl_ft=1000, wind_speed_kt=40)
    assessment = model.Estimator(seed=1).assess(conditions, model.Sources(), NOW)
    parts = [c.edr for c in assessment.contributions]
    assert {c.source for c in assessment.contributions} == {"cloud", "boundary_layer"}
    assert assessment.edr == pytest.approx(sum(p * p for p in parts) ** 0.5)
    assert assessment.edr < sum(parts)


def test_nothing_is_felt_on_the_ground():
    sources = model.Sources(reports=(model.Report(46.0, 6.0, 3, NOW, level_ft=0),))
    assessment = model.Estimator().assess(_conditions(on_ground=True, altitude_ft=0), sources, NOW)
    assert assessment.edr == 0.0


def test_live_shear_is_measured_only_across_a_level_change():
    shear = model.LiveShear()
    assert shear.update(0.0, 30000, 270, 50) == 0.0
    assert shear.update(10.0, 30100, 270, 80) == 0.0  # 100 ft : trop peu
    assert shear.update(20.0, 31000, 270, 80) == pytest.approx(30.0, rel=0.01)


def test_live_shear_ignores_a_wind_change_in_level_flight():
    shear = model.LiveShear()
    shear.update(0.0, 30000, 270, 50)
    shear.update(100.0, 30000, 270, 90)  # vent changé en palier
    assert shear.update(110.0, 30400, 270, 90) == 0.0


def test_gust_alleviation_matches_the_certification_formula():
    mu = 30.0
    chord = 4.0
    density = 1.0
    wing_loading = mu * density * chord * dynamics.LIFT_SLOPE * dynamics.G / 2
    assert dynamics.gust_alleviation(wing_loading, density, chord) == pytest.approx(0.88 * mu / 35.3)


def test_a_light_aircraft_is_shaken_harder_than_an_airliner():
    sigma_w = dynamics.vertical_gust_sigma(0.3, dynamics.HIGH_ALTITUDE_SCALE_M)
    light = dynamics.Airframe(weight_kg=1100, wing_area_m2=16.2, span_m=11.0)
    airliner = dynamics.Airframe(weight_kg=70000)
    light_n = dynamics.load_factor_sigma(sigma_w, 60, 1.0, light.wing_loading_pa, light.chord_m)
    airliner_n = dynamics.load_factor_sigma(sigma_w, 60, 1.0, airliner.wing_loading_pa, airliner.chord_m)
    assert light_n > 2 * airliner_n


def test_scale_length_follows_the_dryden_altitude_bands():
    assert dynamics.scale_length_m(100) == 100
    assert dynamics.scale_length_m(5000) == pytest.approx(dynamics.HIGH_ALTITUDE_SCALE_M)
    assert dynamics.LOW_ALTITUDE_M < dynamics.scale_length_m(450) < dynamics.HIGH_ALTITUDE_SCALE_M


def test_gusts_are_zero_mean_bounded_and_scale_with_intensity():
    airframe = dynamics.Airframe(weight_kg=60000)

    def run(edr: float, scale: float = 1.0) -> list[float]:
        field = dynamics.GustField(rng=random.Random(4))
        pitches = []
        for _ in range(4000):
            motion = field.step(1 / 30, edr, 450, 33000, 0.38, airframe, scale)
            pitches.append(motion.pitch)
            assert abs(motion.pitch) <= dynamics.MAX_PITCH_ACC
            assert abs(motion.roll) <= dynamics.MAX_ROLL_ACC
            assert abs(motion.yaw) <= dynamics.MAX_YAW_ACC
        return pitches[1000:]

    light, severe = run(0.12), run(0.5)
    assert abs(statistics.fmean(severe)) < statistics.pstdev(severe) / 3
    assert statistics.pstdev(severe) > 2.5 * statistics.pstdev(light)
    assert statistics.pstdev(run(0.3, 2.0)) == pytest.approx(2 * statistics.pstdev(run(0.3)), rel=0.05)


def test_intensity_ramps_in_over_a_few_seconds():
    field = dynamics.GustField(rng=random.Random(1))
    airframe = dynamics.Airframe(weight_kg=60000)
    field.step(0.1, 0.4, 450, 33000, 0.38, airframe)
    assert 0.0 < field.edr < 0.4
    for _ in range(300):  # 30 s
        field.step(0.1, 0.4, 450, 33000, 0.38, airframe)
    assert field.edr == pytest.approx(0.4, abs=0.01)


def test_effect_is_cut_near_the_ground():
    assert height_factor(150) == 0.0
    assert height_factor(350) == pytest.approx(0.5)
    assert height_factor(800) == 1.0


# --------------------------------------------------------------------------- #
# Service


class FakeClient:
    def __init__(self, frames, refuse_extra=False, refuse_writes=False, repeat=False):
        self.frames = list(frames)
        # Rejoue la dernière image : l'état se relève pendant que le vol continue.
        self.repeat = repeat
        self.refuse_extra = refuse_extra
        self.refuse_writes = refuse_writes
        self.subscriptions = []
        self.writes = []
        self.closed = False

    def subscribe_simvars(self, variables):
        self.subscriptions.append(tuple(variables))
        return len(self.subscriptions)

    def next_frame(self, request_id, variables, timeout_s=1.0):
        if self.refuse_extra and tuple(variables) != CORE_VARIABLES:
            raise SimConnectRefused("refus", [7])
        if self.refuse_writes and self.writes:
            self.refuse_writes = False
            raise SimConnectRefused("refus", [20])
        self.served = getattr(self, "served", 0) + 1
        if self.repeat and len(self.frames) == 1:
            time.sleep(0.001)
            frame = dict(self.frames[0])
        elif not self.frames:
            time.sleep(0.01)
            return None
        else:
            frame = dict(self.frames.pop(0))
        if not getattr(self, "frozen", False):
            # Un avion en vol avance : une position figée signale la pause active.
            frame["PLANE LATITUDE"] = frame.get("PLANE LATITUDE", 46.0) + self.served * 1e-6
        return frame

    def write_simvars(self, variables, values):
        assert tuple(variables) == WRITE_VARIABLES
        self.writes.append(tuple(values))

    def close(self):
        self.closed = True


def _frame(**overrides):
    frame = {
        "PLANE LATITUDE": 46.0, "PLANE LONGITUDE": 6.0, "PLANE ALTITUDE": 35000.0,
        "PLANE ALT ABOVE GROUND": 33000.0, "SIM ON GROUND": 0.0, "AIRSPEED TRUE": 450.0,
        "TOTAL WEIGHT": 60000.0, "AMBIENT DENSITY": 0.00074, "AMBIENT WIND DIRECTION": 270.0,
        "AMBIENT WIND VELOCITY": 60.0, "AMBIENT IN CLOUD": 0.0,
    }
    frame.update(overrides)
    return frame


def _run_service(client, sources, frames_needed=lambda c: len(c.writes) >= 20):
    clock = iter(i / 30 for i in range(10 ** 6))
    service = TurbulenceService(lambda: sources, client_factory=lambda: client, clock=lambda: next(clock))
    service.configure(enabled=True, intensity_pct=100)
    deadline = time.monotonic() + 5
    while not frames_needed(client) and time.monotonic() < deadline:
        time.sleep(0.01)
    status = service.status()
    service.close()
    return service, status


def test_the_service_kicks_the_aircraft_velocities_inside_reported_turbulence():
    sources = model.Sources(reports=(model.Report(46.0, 6.0, 3, time.time() - 60, level_ft=35000),))
    client = FakeClient([_frame()], repeat=True)
    _service, status = _run_service(client, sources)
    assert len(client.writes) >= 20
    assert any(abs(value) > 0 for write in client.writes for value in write)
    assert status["state"] == "active"
    assert status["level"] == "SEV"
    assert client.closed


def test_the_service_writes_nothing_on_the_ground():
    sources = model.Sources(reports=(model.Report(46.0, 6.0, 3, time.time() - 60, level_ft=0),))
    client = FakeClient([_frame(**{"SIM ON GROUND": 1.0, "PLANE ALT ABOVE GROUND": 0.0}) for _ in range(30)])
    _run_service(client, sources, frames_needed=lambda c: not c.frames)
    assert client.writes == []


def test_refused_optional_variables_fall_back_to_the_core_set():
    sources = model.Sources(reports=(model.Report(46.0, 6.0, 2, time.time() - 60, level_ft=35000),))
    client = FakeClient([_frame() for _ in range(200)], refuse_extra=True)
    _run_service(client, sources)
    assert client.subscriptions[-1] == CORE_VARIABLES
    assert client.writes


def test_a_refused_write_stops_writing_but_keeps_reading():
    sources = model.Sources(reports=(model.Report(46.0, 6.0, 3, time.time() - 60, level_ft=35000),))
    client = FakeClient([_frame() for _ in range(100)], refuse_writes=True)
    _service, status = _run_service(client, sources, frames_needed=lambda c: not c.frames)
    assert len(client.writes) == 1
    assert status["state"] == "refused"


def test_disabled_service_never_opens_a_connection():
    opened = []
    service = TurbulenceService(model.Sources, client_factory=lambda: opened.append(1))
    service.configure(enabled=False, intensity_pct=100)
    time.sleep(0.05)
    service.close()
    assert opened == []
    assert service.status()["state"] == "off"


def test_turbulence_settings_are_off_by_default_and_clamped():
    settings = Settings()
    assert settings.turbulence_enabled is False
    updated = settings.with_user_values({"turbulence_enabled": True, "turbulence_intensity_pct": 900})
    assert updated.turbulence_enabled is True
    assert updated.turbulence_intensity_pct == 200
    assert updated.user_values()["turbulence_intensity_pct"] == 200
    # Une mise à jour qui ne parle pas de turbulence la laisse telle quelle.
    assert updated.with_user_values({"vatsim_enabled": True}).turbulence_enabled is True


def test_sources_are_built_from_the_ofp_profile_and_report_objects():
    class Report:
        latitude, longitude, rank, observed = 46.0, 6.0, 2, NOW
        level_ft, base_ft, top_ft = 35000, None, None

    sources = model.Sources.build(
        [{"lat": 46.0, "lon": 6.0, "altitude_ft": 35000, "shear": 5.0}, {"lat": None}],
        [Report()],
    )
    assert len(sources.forecast) == 1
    assert sources.reports[0].rank == 2


# --------------------------------------------------------------------------- #
# Relief au vent



class FakeResponse:
    def __init__(self, elevations):
        self.elevations = elevations

    def raise_for_status(self):
        return None

    def json(self):
        return {"elevation": self.elevations}


class FakeSession:
    def __init__(self, elevations=None, fail=False):
        self.elevations = elevations
        self.fail = fail
        self.calls = []

    def get(self, url, params, timeout, headers):
        self.calls.append(params)
        if self.fail:
            raise terrain_module.requests.ConnectionError("hors ligne")
        count = len(params["latitude"].split(","))
        return FakeResponse(self.elevations or [500.0] + [3000.0] * (count - 1))

    def close(self):
        pass


def test_the_upwind_line_heads_into_the_wind():
    line = terrain_module.upwind_line(46.0, 6.0, 270.0)  # vent d'ouest
    assert line[0] == pytest.approx((46.0, 6.0))
    assert line[-1][1] < 6.0 - 0.9  # 45 NM vers l'ouest
    assert len(line) == 16


def test_the_probe_reads_the_ridge_and_reuses_it_while_nothing_changes():
    session = FakeSession()
    probe = terrain_module.TerrainProbe(session=session)
    sample = probe.probe(46.0, 6.0, 270.0, now=0.0)
    assert sample.ridge_ft == pytest.approx(3000 * terrain_module.FT_PER_M)
    assert sample.relief_ft == pytest.approx(2500 * terrain_module.FT_PER_M)
    probe.probe(46.01, 6.0, 275.0, now=30.0)
    assert len(session.calls) == 1
    probe.probe(46.0, 6.0, 320.0, now=40.0)  # le vent a tourné
    assert len(session.calls) == 2


def test_an_unreachable_elevation_service_is_not_hammered():
    session = FakeSession(fail=True)
    probe = terrain_module.TerrainProbe(session=session)
    assert probe.probe(46.0, 6.0, 270.0, now=0.0) is None
    assert probe.probe(46.0, 6.0, 270.0, now=30.0) is None
    assert len(session.calls) == 1


def test_mountain_waves_need_both_relief_and_strong_wind():
    base = dict(altitude_ft=14000, height_agl_ft=9000, ridge_ft=12000, relief_ft=8000)
    assert model.mountain_wave_edr(_conditions(**base, wind_speed_kt=15)) == 0.0
    assert model.mountain_wave_edr(_conditions(**{**base, "relief_ft": 800}, wind_speed_kt=60)) == 0.0
    strong = model.mountain_wave_edr(_conditions(**base, wind_speed_kt=60))
    assert model.level(strong) == "SEV"
    high = model.mountain_wave_edr(_conditions(**{**base, "altitude_ft": 33000}, wind_speed_kt=60))
    assert high == 0.0


def test_the_service_probes_terrain_only_in_strong_wind():
    session = FakeSession()
    service = TurbulenceService(model.Sources, terrain=terrain_module.TerrainProbe(session=session))
    service._position = (46.0, 6.0, 270.0, 10.0, False)
    service.refresh_terrain()
    assert session.calls == []
    service._position = (46.0, 6.0, 270.0, 50.0, False)
    service.refresh_terrain()
    assert len(session.calls) == 1
    assert service.status()["relief_ft"] > 0


def test_jolts_are_counted_once_per_upward_crossing():
    from navixav.turbulence import service as service_module

    service = TurbulenceService(model.Sources)
    spread = service_module.PITCH_GAIN * 0.1
    sequence = [0.5, 2.0, 2.2, 1.0, 0.2, -1.9, -0.3, 1.7]
    for z in sequence:
        service._note_jolt(dynamics.Motion(z * spread, 0.0, 0.0, 0.1))
    status = service.status()
    assert status["jolts"] == 3
    assert status["jolt_g"] == pytest.approx(0.17)


def test_no_jolt_is_counted_in_barely_perceptible_turbulence():
    service = TurbulenceService(model.Sources)
    for z in (0.0, 3.0, 0.0, 3.0):
        service._note_jolt(dynamics.Motion(z * 0.005, 0.0, 0.0, 0.005))
    assert service.status()["jolts"] == 0


def test_only_the_vertical_speed_is_kicked_never_the_rotation_rates():
    # MSFS amplifie une vitesse de rotation écrite (≈ ×3,2) : la réécrire à
    # chaque image fait diverger l'avion (piqué engagé en essai réel).
    assert [name for name, _unit in WRITE_VARIABLES] == ["VELOCITY BODY Y"]
    motion = dynamics.Motion(0.32, -0.64, 0.0, 0.1, heave=0.3048)
    assert motion.kicks(0.1) == pytest.approx((0.1 / dynamics.VERTICAL_WRITE_RESPONSE,))
    sources = model.Sources(reports=(model.Report(46.0, 6.0, 3, time.time() - 60, level_ft=35000),))
    client = FakeClient([_frame(**{"VELOCITY BODY Y": 10.0})], repeat=True)
    _service, status = _run_service(client, sources)
    assert all(abs(write[0] - 10.0) < 1.0 for write in client.writes)
    assert "felt_pitch_deg_s" in status


def test_writing_stops_for_good_when_the_aircraft_behaves_abnormally():
    sources = model.Sources(reports=(model.Report(46.0, 6.0, 3, time.time() - 60, level_ft=35000),))
    frames = [_frame() for _ in range(30)] + [_frame(**{"ROTATION VELOCITY BODY Z": 0.5})] + [_frame()] * 30
    client = FakeClient(frames)
    _service, status = _run_service(client, sources, frames_needed=lambda c: not c.frames)
    written = len(client.writes)
    assert written <= 31
    assert status["state"] == "refused"
    for bad in ({"PLANE BANK DEGREES": 75.0}, {"PLANE PITCH DEGREES": -40.0}, {"ROTATION VELOCITY BODY X": -0.3}):
        from navixav.turbulence.service import _unsafe
        assert _unsafe(_frame(**bad))
    assert not _unsafe(_frame(**{"PLANE BANK DEGREES": 25.0, "ROTATION VELOCITY BODY X": 0.05}))


def test_moderate_cruise_turbulence_gives_bumps_within_safe_bounds():
    field = dynamics.GustField(rng=random.Random(3))
    field.edr = 0.25
    airframe = dynamics.Airframe(weight_kg=64000)
    loads = [field.step(1 / 26, 0.25, 450, 35000, 0.38, airframe).heave / dynamics.G for _ in range(26 * 60)]
    spread = (sum(x * x for x in loads) / len(loads)) ** 0.5
    # Commande ≈ 0,4 g d’écart-type ; MSFS en restitue ~40 %, soit ~0,15 g ressentis
    # (0,147 g mesurés en vol), crêtes d’environ 0,5 g.
    assert 0.25 < spread < 0.55
    assert max(abs(x) for x in loads) <= dynamics.MAX_HEAVE_ACC / dynamics.G


def test_nothing_is_written_while_msfs_is_in_active_pause():
    # En pause active, MSFS envoie encore des images, mais figées.
    sources = model.Sources(reports=(model.Report(46.0, 6.0, 3, time.time() - 60, level_ft=35000),))
    client = FakeClient([_frame() for _ in range(40)])
    client.frozen = True
    _service, status = _run_service(client, sources, frames_needed=lambda c: not c.frames)
    assert len(client.writes) <= 3  # le temps de constater 3 images figées
    assert status["state"] == "waiting"
