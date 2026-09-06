from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

from navixav.live.base import AircraftState, PositionUnavailable
from navixav.live.registry import LiveTracker


class Source:
    name = 'TEST'

    def __init__(self):
        self.calls = 0
        self.failed = False

    def is_available(self):
        return True

    def read(self):
        self.calls += 1
        if self.failed:
            raise PositionUnavailable('disconnected')
        return AircraftState(latitude=self.calls, longitude=2, altitude_ft=1000 * self.calls)

    def set_aircraft_hint(self, hint):
        pass

    def close(self):
        pass


def tracker_with(source, now):
    tracker = LiveTracker(clock=lambda: now[0])
    tracker._sources = [source]
    return tracker


def test_consumers_share_one_sample_and_refresh_after_expiry():
    source, now = Source(), [0.0]
    tracker = tracker_with(source, now)
    first = tracker.read()
    now[0] = .249
    assert tracker.read() is first
    assert source.calls == 1
    now[0] = .25
    second = tracker.read()
    assert second.latitude == 2 and second.altitude_ft == 2000
    assert source.calls == 2
    tracker.close()


def test_simultaneous_consumers_wait_for_the_same_sample():
    entered, release = threading.Event(), threading.Event()

    class SlowSource(Source):
        def read(self):
            entered.set()
            assert release.wait(2)
            return super().read()

    source = SlowSource()
    tracker = tracker_with(source, [0.0])
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(tracker.read) for _ in range(4)]
        try:
            assert entered.wait(1)
        finally:
            release.set()
        states = [future.result(timeout=2) for future in futures]
    assert source.calls == 1
    assert all(state is states[0] for state in states)
    tracker.close()


def test_failed_sample_is_not_reused_and_recovery_still_works():
    source, now = Source(), [0.0]
    tracker = tracker_with(source, now)
    tracker.read()
    now[0] = .3
    source.failed = True
    with pytest.raises(PositionUnavailable):
        tracker.read()
    source.failed = False
    with pytest.raises(PositionUnavailable):
        tracker.read()
    assert source.calls == 2
    now[0] = 9
    assert tracker.read().latitude == 3
    tracker.close()
    with pytest.raises(PositionUnavailable):
        tracker.read()
    assert source.calls == 3


def test_aircraft_hint_invalidates_only_when_changed():
    source = Source()
    tracker = tracker_with(source, [0.0])
    tracker.set_aircraft_hint('A320')
    first = tracker.read()
    tracker.set_aircraft_hint('A320')
    assert tracker.read() is first
    tracker.set_aircraft_hint('Fenix A320')
    assert tracker.read() is not first
    assert source.calls == 2
    tracker.close()
