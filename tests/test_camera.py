"""Caméra cinématique : structure SimConnect, mouvement, plans, réalisateur, service."""

from __future__ import annotations

import itertools
import math
import random
import struct

import pytest

from navixav.camera import director as director_module
from navixav.camera.director import Director, phase_of
from navixav.camera.motion import Drift, Spring
from navixav.camera.scene import AircraftState, Kinematics, along_track_m, destination, distance_bearing
from navixav.camera.service import AUTO, CORE_VARIABLES, OFF, CameraService
from navixav.camera.shots import SHOTS, WORLD, Chase, FlyBy, Orbit, Spotter, Wingman
from navixav.msfs.client import (
    CAMERA_REFERENTIAL_SIMOBJECT,
    CAMERA_REFERENTIAL_WORLD,
    EXCEPTION_CAMERA_API,
    RECV_ID_CAMERA_STATUS,
    SimConnectRefused,
    pack_camera,
)


def _state(**overrides) -> AircraftState:
    values = dict(
        latitude=45.0, longitude=5.0, altitude_m=3000.0, height_m=2500.0, heading_deg=90.0,
        on_ground=False, span_m=34.0, ground_speed_mps=120.0, track_deg=90.0, vertical_speed_mps=0.0,
    )
    values.update(overrides)
    return AircraftState(**values)


# --------------------------------------------------------------------- #
# Structure SimConnect


def test_camera_payload_matches_the_84_byte_packed_layout():
    payload = pack_camera((1.0, 2.0, 3.0), CAMERA_REFERENTIAL_WORLD, (0.0, 0.0, 7.5))
    assert len(payload) == 84
    assert struct.unpack_from("<3d", payload, 0) == (1.0, 2.0, 3.0)
    assert struct.unpack_from("<iI", payload, 24) == (CAMERA_REFERENTIAL_WORLD, 0)
    assert struct.unpack_from("<3d", payload, 32) == (0.0, 0.0, 7.5)
    # Rotation laissée à MSFS : la cible est exprimée dans le repère de l'avion.
    assert struct.unpack_from("<iI", payload, 68) == (CAMERA_REFERENTIAL_SIMOBJECT, 0)
    assert struct.unpack_from("<d", payload, 76) == (0.0,)


# --------------------------------------------------------------------- #
# Mouvement


def test_the_spring_gives_the_same_motion_whatever_the_frame_rate():
    fast, slow = Spring(), Spring()
    for _ in range(120):
        fast.step(10.0, 1 / 120, 3.0)
    for _ in range(30):
        slow.step(10.0, 1 / 30, 3.0)
    assert fast.value == pytest.approx(slow.value, abs=1e-9)
    assert fast.velocity == pytest.approx(slow.velocity, abs=1e-9)


def test_the_spring_never_overshoots_even_after_a_long_frame():
    spring = Spring()
    values = [spring.step(10.0, dt, 6.0) for dt in (0.016, 0.25, 0.016, 0.5, 0.25, 0.25)]
    assert all(value <= 10.0 for value in values)
    assert values == sorted(values)


def test_drift_stays_smooth_and_bounded():
    drift = Drift(random.Random(4), 20.0)
    samples = [drift.value(t / 10) for t in range(2000)]
    assert max(abs(value) for value in samples) <= 1.0
    assert max(abs(b - a) for a, b in zip(samples, samples[1:])) < 0.05


def test_kinematics_reads_speed_track_and_climb_from_positions():
    kinematics = Kinematics()
    result = (0.0, None, 0.0)
    for step in range(31):
        t = step / 10
        latitude, longitude = destination(45.0, 5.0, 60.0, 100.0 * t)
        result = kinematics.update(t, latitude, longitude, 1000.0 + 5.0 * t)
    speed, track, climb = result
    assert speed == pytest.approx(100.0, rel=0.01)
    assert track == pytest.approx(60.0, abs=0.5)
    assert climb == pytest.approx(5.0, rel=0.01)


# --------------------------------------------------------------------- #
# Plans


@pytest.mark.parametrize("shot_type", [Orbit, Chase, Wingman])
@pytest.mark.parametrize("span", [11.0, 34.0, 80.0])
def test_attached_shots_keep_clear_of_the_airframe_and_scale_with_it(shot_type, span):
    rng = random.Random(7)
    distances = []
    for seed in range(30):
        shot = shot_type()
        state = _state(span_m=span)
        shot.start(state, random.Random(seed))
        for _ in range(60):
            command = shot.update(state, 1 / 30)
        x, _y, z = command.position
        distances.append(math.hypot(x, z))
    assert min(distances) > 0.6 * span
    assert max(distances) < 4.0 * span + 40.0
    del rng


def test_bigger_aircraft_are_filmed_from_further_away():
    def mean_distance(span: float) -> float:
        total = 0.0
        for seed in range(40):
            shot = Chase()
            shot.start(_state(span_m=span), random.Random(seed))
            x, _y, z = shot.update(_state(span_m=span), 0.0).position
            total += math.hypot(x, z)
        return total / 40

    assert mean_distance(80.0) > 2.5 * mean_distance(11.0)


def test_a_flyby_waits_ahead_of_the_aircraft_on_its_climb_path_and_ends_once_passed():
    state = _state(vertical_speed_mps=10.0, height_m=400.0, altitude_m=900.0)
    shot = FlyBy()
    shot.start(state, random.Random(3))
    command = shot.update(state, 0.0)
    latitude, longitude, altitude = command.position
    assert command.referential == WORLD and command.lock == command.position
    assert along_track_m(state, latitude, longitude) > 300.0
    # Il vise l'altitude que l'avion aura en passant, pas celle du départ.
    assert altitude > state.altitude_m + 20.0
    assert not shot.done(state)
    later_lat, later_lon = destination(state.latitude, state.longitude, 90.0, 3000.0)
    assert shot.done(_state(latitude=later_lat, longitude=later_lon))


def test_a_flyby_never_plants_the_camera_below_the_ground():
    state = _state(vertical_speed_mps=-15.0, height_m=60.0, altitude_m=560.0)
    for seed in range(20):
        shot = FlyBy()
        shot.start(state, random.Random(seed))
        assert shot.update(state, 0.0).position[2] >= state.ground_elevation_m + 3.0


def test_the_spotter_stands_at_eye_height_beside_the_runway():
    state = _state(on_ground=True, height_m=0.0, altitude_m=120.0, ground_speed_mps=60.0)
    shot = Spotter()
    shot.start(state, random.Random(1))
    latitude, longitude, altitude = shot.update(state, 0.0).position
    assert altitude == pytest.approx(121.7)
    assert along_track_m(state, latitude, longitude) > 120.0
    assert Spotter.suits(state)
    assert not Spotter.suits(_state(height_m=3000.0))


# --------------------------------------------------------------------- #
# Réalisateur


def test_flight_phases():
    assert phase_of(_state(on_ground=True, ground_speed_mps=0.0)) == director_module.PARKED
    assert phase_of(_state(on_ground=True, ground_speed_mps=8.0)) == director_module.TAXI
    assert phase_of(_state(on_ground=True, ground_speed_mps=60.0)) == director_module.RUNWAY
    assert phase_of(_state(height_m=300.0)) == director_module.LOW
    assert phase_of(_state(height_m=9000.0)) == director_module.ENROUTE


def test_the_director_never_repeats_a_shot_back_to_back_and_respects_the_phase():
    director = Director(random.Random(5))
    takeoff_roll = _state(on_ground=True, height_m=0.0, ground_speed_mps=60.0)
    names = [director.choose(takeoff_roll, float(t)) for t in range(40)]
    assert all(a != b for a, b in zip(names, names[1:]))
    assert set(names) <= {"spotter", "chase", "flyby"}
    parked = _state(on_ground=True, height_m=0.0, ground_speed_mps=0.0)
    assert {director.choose(parked, 0.0) for _ in range(20)} <= {"orbit", "chase"}


def test_liftoff_cuts_to_a_new_shot_once_the_new_phase_has_settled():
    director = Director(random.Random(2))
    roll = _state(on_ground=True, height_m=0.0, ground_speed_mps=70.0)
    director.choose(roll, 0.0)
    airborne = _state(height_m=20.0, ground_speed_mps=80.0)
    assert not director.should_cut(airborne, 1.0, False)
    assert not director.should_cut(airborne, 3.0, False)
    assert director.should_cut(airborne, 4.1, False)


def test_a_finished_fixed_shot_is_cut_at_once():
    director = Director(random.Random(2))
    state = _state()
    director.choose(state, 0.0)
    assert director.should_cut(state, 0.5, True)


# --------------------------------------------------------------------- #
# Service


def _status_message(availability: int, game_controlled: int) -> bytes:
    return struct.pack("<3I", 20, 6, RECV_ID_CAMERA_STATUS) + struct.pack("<Ii", availability, game_controlled)


class FakeClient:
    camera_supported = True

    def __init__(self, service, frames=60, messages=None, refuse_at=None):
        self.service = service
        self.frames = frames
        self.messages = messages or {}
        self.refuse_at = refuse_at
        self.index = 0
        self.calls: list[tuple] = []

    def subscribe_simvars(self, variables):
        self.calls.append(("subscribe", tuple(variables)))
        return 1

    def camera_subscribe_status(self):
        self.calls.append(("status",))

    def next_frame(self, request_id, variables, timeout_s=1.0, on_message=None):
        index = self.index
        self.index += 1
        if index in self.messages:
            message = self.messages[index]
            recv_id, raw = message if isinstance(message, tuple) else (RECV_ID_CAMERA_STATUS, message)
            on_message(recv_id, raw)
        if index == self.refuse_at:
            raise SimConnectRefused("refus", [EXCEPTION_CAMERA_API])
        if index >= self.frames:
            self.service.stop()
            return None
        latitude, longitude = destination(45.0, 5.0, 90.0, 120.0 * index / 30)
        return {
            "PLANE LATITUDE": latitude, "PLANE LONGITUDE": longitude,
            "PLANE ALTITUDE": 3000.0, "PLANE ALT ABOVE GROUND": 2500.0,
            "PLANE HEADING DEGREES TRUE": 90.0, "SIM ON GROUND": 0.0,
            "CAMERA STATE": 3.0, "WING SPAN": 111.0,
        }

    def camera_acquire(self, client_name="NaviXav"):
        self.calls.append(("acquire",))

    def camera_enable_flag(self, flag):
        self.calls.append(("flag", flag))

    def camera_set(self, position, referential, target=(0.0, 0.0, 0.0), fov_deg=None):
        self.calls.append(("set", referential, tuple(position), fov_deg))

    def read_towers(self, icaos, timeout_s=5.0):
        self.calls.append(("towers", tuple(icaos)))
        return {"LFLL": (45.0, 5.05, 300.0)}

    def camera_lock_world(self, latitude, longitude, altitude_m):
        self.calls.append(("lock",))

    def camera_unlock_world(self):
        self.calls.append(("unlock",))

    def camera_release(self, camera_definition="Pilot"):
        self.calls.append(("release",))

    def write_simvars(self, variables, values):
        self.calls.append(("write", tuple(variables), tuple(values)))

    def close(self):
        self.calls.append(("close",))


def _service(mode=AUTO) -> CameraService:
    ticks = itertools.count()
    service = CameraService(clock=lambda: next(ticks) / 30, rng=random.Random(11))
    service._mode = mode
    return service


def _kinds(client):
    return [call[0] for call in client.calls]


def test_the_service_takes_the_camera_once_films_and_gives_it_back_to_the_pilot():
    service = _service("orbit")
    client = FakeClient(service)
    service._session(client)
    kinds = _kinds(client)
    assert kinds.count("acquire") == 1
    assert kinds.count("set") == 60
    assert all(call[1] == CAMERA_REFERENTIAL_SIMOBJECT for call in client.calls if call[0] == "set")
    assert kinds.index("release") > kinds.index("set")
    # Le pilote était en vue extérieure : il la retrouve.
    assert ("write", (("CAMERA STATE", "Number"),), (3,)) in client.calls
    assert service.status()["mode"] == OFF


def test_the_service_waits_while_msfs_holds_the_camera_and_takes_it_back_afterwards():
    service = _service("chase")
    client = FakeClient(service, messages={10: _status_message(0, 1), 20: _status_message(0, 0)})
    service._session(client)
    kinds = _kinds(client)
    assert kinds.count("acquire") == 2
    assert kinds.count("set") == 50


def test_a_camera_api_refusal_stops_the_director_and_says_so():
    service = _service(AUTO)
    client = FakeClient(service, refuse_at=15)
    service._session(client)
    status = service.status()
    assert status["mode"] == OFF
    assert status["state"] == "refused"
    assert "release" in _kinds(client)


def test_fixed_shots_reserve_the_scenery_and_release_it():
    service = _service("flyby")
    client = FakeClient(service, frames=40)
    service._session(client)
    kinds = _kinds(client)
    assert "lock" in kinds and "unlock" in kinds
    assert any(call[0] == "set" and call[1] == CAMERA_REFERENTIAL_WORLD for call in client.calls)


def test_without_the_camera_api_the_service_reports_it_instead_of_failing():
    service = _service(AUTO)
    client = FakeClient(service)
    client.camera_supported = False
    service._stop.set()
    service._session(client)
    assert service.status()["state"] == "unsupported"
    assert "acquire" not in _kinds(client)


def test_next_shot_cuts_at_once_and_pace_stretches_the_holds():
    service = _service(AUTO)
    service.set_pace("calm")
    state = _state()
    shot, mode = service._direct(state, 0.0, AUTO, None, None)
    calm_hold = service._director.hold_s
    service.next_shot()
    other, _mode = service._direct(state, 0.1, AUTO, shot, mode)
    assert other is not shot and other.name != shot.name
    holds = []
    for pace in ("calm", "dynamic"):
        service.set_pace(pace)
        values = []
        for step in range(30):
            service.next_shot()
            service._direct(state, float(step), AUTO, other, AUTO)
            values.append(service._director.hold_s)
        holds.append(sum(values) / len(values))
    assert holds[0] > 2.0 * holds[1]
    assert calm_hold >= 18.0 * 1.6
    with pytest.raises(ValueError):
        service.set_pace("frantic")


def test_a_second_press_on_a_locked_shot_replants_it():
    service = _service("flyby")
    state = _state()
    shot, mode = service._direct(state, 0.0, "flyby", None, None)
    service.next_shot()
    again, _mode = service._direct(state, 0.1, "flyby", shot, mode)
    assert again is not shot and again.name == "flyby"


def test_every_camera_text_exists_in_the_eight_interface_languages():
    from pathlib import Path

    static = Path(__file__).resolve().parents[1] / "navixav" / "web" / "static"
    translations = (static / "i18n.js").read_text(encoding="utf-8")
    html = (static / "index.html").read_text(encoding="utf-8")
    javascript = (static / "app.js").read_text(encoding="utf-8")
    keys = sorted(set(
        key for key in __import__("re").findall(r"\b(camera_[a-z_]+):", translations)
    ))
    assert len(keys) > 40
    for key in keys:
        assert translations.count(f"{key}:") == 8, key
    for name in SHOTS:
        assert f'data-camera-mode="{name}"' in html
        for prefix in ("camera_shot_", "camera_hint_"):
            assert f"{prefix}{name}:" in translations
    for phase in ("parked", "taxi", "runway", "low", "enroute"):
        assert f"camera_phase_{phase}:" in translations
    for state in ("off", "waiting", "taken", "blocked", "refused", "unsupported"):
        assert f"camera_status_{state}:" in translations
        assert f"camera_chip_{state}:" in translations
    assert "initCameraControls();" in javascript


def test_the_camera_api_reports_and_validates_without_touching_the_simulator():
    from fastapi import HTTPException

    from navixav.config import Settings
    from navixav.web.app import CameraRequest, create_app

    app = create_app(Settings())
    try:
        routes = {(route.path, tuple(sorted(route.methods))): route.endpoint for route in app.routes
                  if getattr(route, "methods", None)}
        status = routes[("/api/camera/status", ("GET",))]()
        assert status["mode"] == OFF and status["pace"] == "normal"
        command = routes[("/api/camera", ("POST",))]
        assert command(CameraRequest(pace="dynamic"))["pace"] == "dynamic"
        # Plan suivant sans caméra en marche : rien ne démarre.
        assert command(CameraRequest(next=True))["mode"] == OFF
        for bad in (CameraRequest(mode="dolly"), CameraRequest(pace="frantic")):
            with pytest.raises(HTTPException) as refused:
                command(bad)
            assert refused.value.status_code == 400
    finally:
        app.state.close_resources()


def test_a_tracking_move_goes_around_the_aircraft_never_through_it():
    from navixav.camera.motion import Glide
    from navixav.camera.shots import station

    left, right = station(-90.0, 60.0, 10.0), station(90.0, 50.0, 5.0)
    glide = Glide(left, 3.0)
    points = [glide.step(right, 0.05) for _ in range(60)]
    assert glide.finished
    assert points[-1] == pytest.approx(right, abs=1e-6)
    assert min(math.hypot(x, z) for x, _y, z in points) >= 50.0 - 1e-6


def test_the_tower_zooms_in_as_the_aircraft_gets_further_away():
    from navixav.camera.shots import Tower

    tower = (45.0, 5.0, 250.0)
    near_lat, near_lon = destination(45.0, 5.0, 90.0, 400.0)
    far_lat, far_lon = destination(45.0, 5.0, 90.0, 3500.0)
    near = _state(latitude=near_lat, longitude=near_lon, altitude_m=260.0, height_m=0.0, on_ground=True, towers=(tower,))
    far = _state(latitude=far_lat, longitude=far_lon, altitude_m=400.0, height_m=150.0, towers=(tower,))
    shot = Tower()
    shot.start(near, random.Random(1))
    close_fov = shot.update(near, 0.0).fov_deg
    assert shot._fov(far) < close_fov / 2
    assert shot._fov(far) == Tower.MIN_FOV_DEG
    command = shot.update(near, 0.0)
    assert command.referential == WORLD
    # MSFS donne le pied de la tour : la caméra monte à la vigie, un pas vers l'avion.
    latitude, longitude, altitude = command.position
    offset, bearing = distance_bearing(45.0, 5.0, latitude, longitude)
    assert offset == pytest.approx(Tower.CAB_OFFSET_M, abs=0.5)
    assert bearing == pytest.approx(90.0, abs=1.0)
    assert altitude == pytest.approx(max(250.0, near.ground_elevation_m) + Tower.CAB_HEIGHT_M)
    assert Tower.suits(near) and Tower.suits(far)
    assert not Tower.suits(_state(towers=(tower,)))  # en croisière, trop haut et trop loin
    assert not Tower.suits(_state(on_ground=True, height_m=0.0))  # aucune tour connue


def test_short_final_is_a_phase_and_the_spotter_waits_at_the_touchdown_point():
    final = _state(height_m=150.0, altitude_m=650.0, vertical_speed_mps=-3.5, ground_speed_mps=70.0)
    assert phase_of(final) == director_module.FINAL
    shot = Spotter()
    shot.start(final, random.Random(2))
    latitude, longitude, altitude = shot.update(final, 0.0).position
    # 150 m à 3,5 m/s : toucher dans ~43 s, soit ~3 000 m devant à 70 m/s.
    assert along_track_m(final, latitude, longitude) == pytest.approx(70.0 * 150.0 / 3.5, rel=0.05)
    assert altitude == pytest.approx(final.ground_elevation_m + 1.7)


def test_the_playlist_limits_the_director_and_holding_stops_the_cuts():
    director = Director(random.Random(9))
    director.allowed = frozenset({"chase", "flyby"})
    names = {director.choose(_state(), float(t)) for t in range(30)}
    assert names <= {"chase", "flyby"}
    # Aucun plan de la sélection ne convient au parking : on garde quand même la sélection.
    director.allowed = frozenset({"flyby", "wingman", "orbit"})
    assert director.choose(_state(on_ground=True, height_m=0.0, ground_speed_mps=0.0), 0.0) == "orbit"
    director.held = True
    assert not director.should_cut(_state(), 10_000.0, False)
    assert director.should_cut(_state(), 10_000.0, True)


def test_a_held_fixed_shot_is_replanted_rather_than_replaced():
    service = _service(AUTO)
    service.set_playlist(["flyby", "chase"])
    service.set_held(True)
    state = _state()
    shot, mode = service._direct(state, 0.0, AUTO, None, None)
    while shot.name != "flyby":
        service.next_shot()
        shot, mode = service._direct(state, 0.0, AUTO, shot, mode)
    later_lat, later_lon = destination(state.latitude, state.longitude, 90.0, 5000.0)
    passed = _state(latitude=later_lat, longitude=later_lon)
    again, _mode = service._direct(passed, 1.0, AUTO, shot, mode)
    assert again is not shot and again.name == "flyby"


def test_tracking_transitions_start_from_where_the_camera_was():
    service = _service("orbit")
    service.set_transition("glide")
    client = FakeClient(service, frames=40)
    real_direct = service._direct

    def switch(state, now, mode, shot, shot_mode):
        # Au 20e appel, on passe en poursuite : le travelling doit partir de l'orbite.
        if client.index == 20:
            with service._lock:
                service._mode = "chase"
            mode = "chase"
        return real_direct(state, now, mode, shot, shot_mode)

    service._direct = switch
    service._session(client)
    sets = [call for call in client.calls if call[0] == "set"]
    before, after = sets[18][2], sets[19][2]
    assert math.dist(before, after) < 5.0


def test_towers_of_the_loaded_plan_are_read_on_a_separate_connection():
    ticks = itertools.count()
    service = CameraService(clock=lambda: next(ticks) / 30, rng=random.Random(1), airports=lambda: ("lfll", "LFPG"))
    opened = []

    def factory():
        client = FakeClient(service)
        opened.append(client)
        return client

    service._client_factory = factory
    service._maybe_refresh_towers(100.0)
    service._tower_thread.join(timeout=2)
    assert opened[0].calls[0] == ("towers", ("LFLL", "LFPG"))
    assert ("close",) in opened[0].calls
    assert service.status()["towers"] == ["LFLL"]
    service._maybe_refresh_towers(101.0)  # trop tôt : pas de nouvelle lecture
    assert len(opened) == 1


def test_the_camera_api_validates_editing_choices():
    from fastapi import HTTPException

    from navixav.config import Settings
    from navixav.web.app import CameraRequest, create_app

    app = create_app(Settings())
    try:
        command = next(route.endpoint for route in app.routes if getattr(route, "path", "") == "/api/camera")
        status = command(CameraRequest(playlist=["tower", "orbit"], transition="glide", held=True))
        assert status["playlist"] == ["orbit", "tower"]
        assert status["transition"] == "glide" and status["held"] is True
        for bad in (CameraRequest(playlist=[]), CameraRequest(playlist=["dolly"]), CameraRequest(transition="fade")):
            with pytest.raises(HTTPException):
                command(bad)
    finally:
        app.state.close_resources()


def _horizontal(command) -> float:
    x, _y, z = command.position
    return math.hypot(x, z)


def test_formation_flies_much_closer_than_before():
    distances = []
    for seed in range(40):
        shot = Wingman()
        shot.start(_state(span_m=34.0), random.Random(seed))
        for _ in range(900):  # 30 s de dérive
            distances.append(_horizontal(shot.update(_state(span_m=34.0), 1 / 30)))
    # Un A320 : jamais plus de ~70 m (contre ~115 m auparavant), jamais dans l'aile.
    assert max(distances) < 72.0
    assert min(distances) > 0.55 * 34.0


def test_framing_changes_apply_live_and_never_put_the_camera_inside_the_airframe():
    from navixav.camera.shots import Framing, closest_m

    framing = Framing()
    shot = Chase()
    shot.framing = framing
    state = _state()
    shot.start(state, random.Random(3))
    for _ in range(90):
        before = shot.update(state, 1 / 30)
    framing.distance = 2.0
    framing.height = 0.5
    for _ in range(150):
        after = shot.update(state, 1 / 30)
    assert _horizontal(after) > 1.7 * _horizontal(before)
    assert after.position[1] > before.position[1] + 0.4 * 34.0
    framing.distance = 0.4
    for _ in range(300):
        close = shot.update(state, 1 / 30)
    assert _horizontal(close) >= closest_m(34.0) * 0.93


def test_the_service_clamps_resets_and_replants_framing():
    service = _service("flyby")
    service.set_framing("wingman", distance=9.0, height=-3.0, angle=500.0)
    framing = service.status()["framing"]["wingman"]
    assert framing == {"distance": 2.5, "height": -1.0, "angle": 180}
    service.set_framing("orbit", angle=40.0)  # l'orbite n'a pas d'angle réglable
    assert service.status()["framing"]["orbit"]["angle"] == 0
    service.reset_framing("wingman")
    assert service.status()["framing"]["wingman"] == {"distance": 1.0, "height": 0.0, "angle": 0}
    service.set_framing("chase", distance=1.5)
    service.reset_framing()
    assert all(f == {"distance": 1.0, "height": 0.0, "angle": 0} for f in service.status()["framing"].values())
    # Un plan fixe à l'image se replace avec son nouveau cadrage.
    state = _state()
    shot, mode = service._direct(state, 0.0, "flyby", None, None)
    service._shot_name = "flyby"
    service.set_framing("flyby", distance=2.0)
    again, _mode = service._direct(state, 0.1, "flyby", shot, mode)
    assert again is not shot and again.framing is service._framing["flyby"]
    with pytest.raises(ValueError):
        service.set_framing("dolly", distance=1.0)


def test_the_camera_api_sets_and_resets_framing():
    from fastapi import HTTPException

    from navixav.config import Settings
    from navixav.web.app import CameraFramingRequest, CameraRequest, create_app

    app = create_app(Settings())
    try:
        command = next(route.endpoint for route in app.routes if getattr(route, "path", "") == "/api/camera")
        status = command(CameraRequest(framing=[CameraFramingRequest(shot="wingman", distance=0.6, angle=-20)]))
        assert status["framing"]["wingman"] == {"distance": 0.6, "height": 0.0, "angle": -20}
        assert status["adjustable"]["tower"] == ["distance"]
        status = command(CameraRequest(reset_framing="all"))
        assert status["framing"]["wingman"]["distance"] == 1.0
        for bad in (CameraRequest(reset_framing="dolly"), CameraRequest(framing=[CameraFramingRequest(shot="dolly")])):
            with pytest.raises(HTTPException):
                command(bad)
    finally:
        app.state.close_resources()


def test_unknown_modes_are_refused():
    with pytest.raises(ValueError):
        CameraService().start("dolly")
    assert set(SHOTS) == {"orbit", "chase", "wingman", "flyby", "spotter", "tower"}
    assert CORE_VARIABLES[0] == ("PLANE LATITUDE", "Degrees")


def _camera_data_message(fov: float) -> bytes:
    from navixav.msfs.client import RECV_ID_CAMERA_DATA, pack_camera

    body = pack_camera((0.0, 0.0, 0.0), 1, object_id=0, target_referential=0, target_object_id=0, fov_deg=fov)
    return struct.pack("<3I", 12 + len(body), 6, RECV_ID_CAMERA_DATA) + body


class FovClient(FakeClient):
    camera_get_supported = True

    def camera_get(self, referential):
        self.calls.append(("get", referential))


def test_without_the_pilot_field_of_view_no_field_of_view_is_imposed():
    # Une valeur dans une unité mal devinée reste posée dans MSFS et déforme
    # tous les plans suivants : sans valeur lue, on n'en envoie aucune.
    service = _service("orbit")
    client = FakeClient(service)
    service._session(client)
    assert {call[3] for call in client.calls if call[0] == "set"} == {None}


def test_the_pilot_field_of_view_is_read_before_acquiring_and_sent_back_unchanged():
    service = _service("orbit")
    client = FovClient(service, messages={2: (40, _camera_data_message(1.05))})
    service._session(client)
    kinds = _kinds(client)
    assert kinds.index("get") < kinds.index("acquire")
    fovs = [call[3] for call in client.calls if call[0] == "set"]
    assert fovs[0] is None
    assert all(fov == pytest.approx(1.05) for fov in fovs[3:])


def test_the_tower_zoom_only_narrows_the_pilot_field_of_view_whatever_its_unit():
    from navixav.camera.service import lens_for

    assert lens_for(None, None) is None
    assert lens_for(20.0, None) is None
    assert lens_for(None, 1.05) == 1.05
    # Radians : 1,05 rad ≈ 60° ; un zoom à 15° divise le champ par quatre.
    assert lens_for(15.0, 1.05) == pytest.approx(1.05 * 15.0 / math.degrees(1.05))
    # Degrés : même règle ; un zoom plus large que le pilote ne l'élargit pas.
    assert lens_for(15.0, 60.0) == pytest.approx(15.0)
    assert lens_for(90.0, 60.0) == 60.0
