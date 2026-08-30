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


def test_production_injection_updates_smoothed_positions_each_second():
    assert DEFAULT_INTERVAL_S == 1.0


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
