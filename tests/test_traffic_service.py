import threading
import time

from navixav.traffic.fsltl import FsltlInstallation, FsltlStatus
from navixav.traffic.service import DEFAULT_INTERVAL_S, TrafficService


class _Provider:
    name = "TEST"

    def traffic(self, limit=None):
        return []

    def close(self):
        raise AssertionError("le service ne possède pas la source partagée")


class _Injector:
    """Injecteur qui ne touche jamais SimConnect."""

    def __init__(self):
        self.owned = {}
        self.closed = False

    def reconcile(self, radius_m):
        return []

    def upsert(self, aircraft, model):
        self.owned[aircraft.uid] = object()

    def remove(self, uid):
        self.owned.pop(uid, None)

    def close(self):
        self.closed = True


class _Models:
    def __init__(self, installation):
        self.installation = installation

    def match(self, aircraft):
        return None


def _detected():
    return FsltlInstallation(FsltlStatus.DETECTED, version="1.6.1", config_count=12)


def _missing():
    return FsltlInstallation(FsltlStatus.NOT_DETECTED, reason="FSLTL Base Models absent")


def test_late_animation_keeps_cadence_without_burst_or_extra_full_delay(monkeypatch):
    from navixav.traffic import service as module
    clock = [0.0]
    starts = []
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    class Manager:
        def render_once(self):
            starts.append(clock[0])
            clock[0] += 0.04 if len(starts) == 1 else 0.001
    class Stop:
        def wait(self, delay):
            assert delay >= 0
            clock[0] += delay
            return len(starts) == 3
    _service(_missing)._animate(Manager(), Stop())
    assert abs(starts[1] - 2 / 30) < 1e-9
    assert abs(starts[2] - 3 / 30) < 1e-9


def _service(detect, injector=None):
    return TrafficService(
        detect,
        lambda: (48.0, 2.0),
        lambda: 1000.0,
        interval_s=0.01,
        injector_factory=(lambda: injector) if injector else _Injector,
        models_factory=_Models,
    )


def _wait_until(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_the_service_reports_whether_injection_actually_runs():
    """L'état visible du dehors est ce qui manquait quand tout vivait en fermeture."""
    service = _service(_detected)
    try:
        assert service.active is False
        service.configure(enabled=True, provider=_Provider())
        assert service.active is True
        service.configure(enabled=False, provider=_Provider())
        assert service.active is False
    finally:
        service.close()


def test_production_injection_updates_smoothed_positions_four_times_each_second():
    assert DEFAULT_INTERVAL_S == 0.25


def test_configured_limits_are_passed_to_the_traffic_manager(monkeypatch):
    from navixav.traffic import service as module
    received = {}

    class Manager:
        def __init__(self, *args, **kwargs):
            received.update(kwargs)
            self.progress = lambda value: None
            self.cancelled = lambda: False
        def close(self): pass
        def sync_once(self):
            return {"created_or_updated": 0, "recreated": 0, "removed": 0, "skipped": 0}
        def render_once(self): pass

    monkeypatch.setattr(module, "TrafficManager", Manager)
    service = _service(_detected)
    try:
        service.configure(enabled=True, provider=_Provider(), radius_nm=32, max_aircraft=7)
        assert received["radius_nm"] == 32
        assert received["max_aircraft"] == 7
    finally:
        service.close()


def test_a_missing_fsltl_package_leaves_the_service_idle():
    service = _service(_missing)
    try:
        service.configure(enabled=True, provider=_Provider())
        assert service.active is False
        assert service.fsltl.status is FsltlStatus.NOT_DETECTED
    finally:
        service.close()


def test_the_package_is_detected_again_at_every_configuration():
    """Installer FSLTL pendant que NaviXav tourne doit suffire, sans redémarrage."""
    states = [_missing(), _detected()]
    service = _service(lambda: states.pop(0) if states else _detected())
    try:
        assert service.fsltl.status is FsltlStatus.NOT_DETECTED
        service.configure(enabled=True, provider=_Provider())
        assert service.fsltl.status is FsltlStatus.DETECTED
        assert service.active is True
    finally:
        service.close()


def test_closing_releases_the_thread_and_the_simconnect_objects():
    injector = _Injector()
    service = _service(_detected, injector)
    service.configure(enabled=True, provider=_Provider())
    names = [t.name for t in threading.enumerate()]
    assert any("TEST-traffic" in name for name in names)

    service.close()

    assert injector.closed is True
    assert service.active is False
    assert _wait_until(
        lambda: not any("TEST-traffic" in t.name for t in threading.enumerate())
    ), "le fil d'injection n'est pas retombé"


def test_stopping_twice_is_harmless():
    service = _service(_detected)
    service.configure(enabled=True, provider=_Provider())
    service.stop()
    service.stop()
    assert service.active is False


def test_empty_source_is_not_reported_as_confirmed_traffic():
    service = _service(_detected)
    try:
        service.configure(enabled=True, provider=_Provider())
        assert _wait_until(lambda: service.status['state'] == 'empty')
        assert service.status['confirmed'] == 0
    finally:
        service.close()
    assert service.status['state'] == 'off'


def test_source_failure_is_visible_and_can_recover():
    class Provider(_Provider):
        failed = True

        def traffic(self, limit=None):
            if self.failed:
                raise RuntimeError('unavailable')
            return []

    provider = Provider()
    service = _service(_detected)
    try:
        service.configure(enabled=True, provider=provider)
        assert _wait_until(lambda: service.status['state'] == 'error')
        assert service.status['reason'] == 'unavailable'
        assert service.status['age_s'] is not None
        provider.failed = False
        assert _wait_until(lambda: service.status['state'] == 'empty')
    finally:
        service.close()


def test_structured_source_failure_reaches_both_interfaces():
    class QuotaError(RuntimeError):
        code = "opensky_daily_quota"
        retry_after_s = 87.2

    class Provider(_Provider):
        def traffic(self, limit=None):
            raise QuotaError("quota")

    service = _service(_detected)
    try:
        service.configure(enabled=True, provider=Provider())
        assert _wait_until(lambda: service.status['state'] == 'error')
        assert service.status['error_code'] == 'opensky_daily_quota'
        assert service.status['retry_after_s'] == 88
    finally:
        service.close()


def test_reconfiguring_never_leaves_two_threads_behind():
    """Chaque enregistrement des paramètres reconfigure : rien ne doit s'empiler."""
    service = _service(_detected)
    try:
        for _ in range(4):
            service.configure(enabled=True, provider=_Provider())
        running = [t for t in threading.enumerate() if "TEST-traffic" in t.name]
        assert len(running) == 1
    finally:
        service.close()
