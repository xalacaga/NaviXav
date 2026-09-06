"""Injecteurs concurrents : NaviXav cède la place au lieu de doubler le trafic."""

import time

from navixav.traffic.conflicts import KNOWN_INJECTORS, process_names, running_injectors
from navixav.traffic.fsltl import FsltlInstallation, FsltlStatus
from navixav.traffic.service import TrafficService


class _Provider:
    name = "TEST"

    def traffic(self, limit=None):
        return []

    def close(self):
        raise AssertionError("le service ne possède pas la source partagée")


class _Injector:
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


def _service(probe, injector=None, interval_s=0.01):
    return TrafficService(
        _detected,
        lambda: (48.0, 2.0),
        lambda: 1000.0,
        interval_s=interval_s,
        injector_factory=(lambda: injector) if injector else _Injector,
        models_factory=_Models,
        conflict_probe=probe,
    )


def _wait_until(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_known_injectors_are_recognised_whatever_the_case():
    assert running_injectors(["explorer.exe", "FSLTL-TrafficInjector.exe"]) == (
        "FSLTL Traffic Injector",
    )
    assert running_injectors(["AIGTC.exe"]) == ("AIG Traffic Controller",)
    assert running_injectors(["msfs.exe", "notepad.exe"]) == ()
    # Le même programme vu deux fois ne se dédouble pas dans le message.
    assert running_injectors(["AIGTC.exe", "AIG Traffic Controller.exe"]) == (
        "AIG Traffic Controller",
    )


def test_the_real_enumeration_answers_without_privileges():
    """Le relevé doit fonctionner sur la machine du pilote, sans droits."""
    names = process_names()
    assert names, "aucun processus énuméré"
    assert all(isinstance(name, str) for name in names)
    # Rien n'est inventé : NaviXav lui-même n'est pas un injecteur connu.
    assert "python.exe" not in KNOWN_INJECTORS


def test_injection_is_refused_while_a_competing_injector_runs():
    service = _service(lambda: ("FSLTL Traffic Injector",))
    try:
        service.configure(enabled=True, provider=_Provider())
        assert service.active is False
        assert service.conflicts == ("FSLTL Traffic Injector",)
    finally:
        service.close()


def test_closing_the_competitor_lets_the_injection_start_again():
    found = ["AIG Traffic Controller"]
    service = _service(lambda: tuple(found))
    try:
        service.configure(enabled=True, provider=_Provider())
        assert service.active is False

        found.clear()
        service.configure(enabled=True, provider=_Provider())
        assert service.active is True
        assert service.conflicts == ()
    finally:
        service.close()


def test_a_competitor_started_in_flight_stops_the_injection():
    """Le pilote peut lancer l'autre outil après le décollage : il faut le voir."""
    import navixav.traffic.service as service_module

    original = service_module.CONFLICT_INTERVAL_S
    service_module.CONFLICT_INTERVAL_S = 0.0
    found: list[str] = []
    injector = _Injector()
    service = _service(lambda: tuple(found), injector)
    try:
        service.configure(enabled=True, provider=_Provider())
        assert service.active is True

        found.append("FSLTL Traffic Injector")
        assert _wait_until(lambda: not service.active), "l'injection n'a pas cédé"
        assert service.conflicts == ("FSLTL Traffic Injector",)
        # Les objets créés sont rendus au simulateur, pas abandonnés.
        assert injector.closed is True
    finally:
        service_module.CONFLICT_INTERVAL_S = original
        service.close()
