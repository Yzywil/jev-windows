"""Native adapter logic tested against fake controls, never the user's desktop."""

import time
from dataclasses import replace
from types import SimpleNamespace

import pytest

from jev_windows.contracts import JevError, build_candidates
from jev_windows.demo import MemoryDriver, demo_task
from jev_windows.native import NativeDriver


class Pattern:
    def __init__(self, ok=True):
        self.calls = []
        self.ok = ok

    def SetValue(self, value, **kwargs):
        self.calls.append(value)
        return self.ok

    def Invoke(self, **kwargs):
        self.calls.append("invoke")
        return self.ok

    def Toggle(self, **kwargs):
        self.calls.append("toggle")
        return self.ok

    def Select(self, **kwargs):
        self.calls.append("select")
        return self.ok


def fake_native(snapshot):
    driver = object.__new__(NativeDriver)
    driver.binding = snapshot.window
    driver.consumed = set()
    driver.controls = {e.ref: e for e in snapshot.elements}
    driver.observe = lambda: snapshot
    driver._element = lambda c: c
    driver._check_binding = lambda: None
    pattern = Pattern()
    driver._patterns = lambda _: dict.fromkeys(["invoke", "set_value", "toggle", "select"], pattern)
    return driver, pattern


def test_native_dispatch_once():
    snapshot = MemoryDriver().observe()
    candidate = build_candidates(demo_task(), snapshot)[0]
    driver, pattern = fake_native(snapshot)
    driver.execute(snapshot, candidate, 20)
    assert pattern.calls == ["Hello Jev"]
    with pytest.raises(JevError, match="already_consumed"):
        driver.execute(snapshot, candidate, 20)


def test_native_failed_dispatch_is_still_consumed():
    snapshot = MemoryDriver().observe()
    candidate = build_candidates(demo_task(), snapshot)[1]
    driver, pattern = fake_native(snapshot)
    pattern.ok = False
    with pytest.raises(JevError, match="outcome_unknown"):
        driver.execute(snapshot, candidate, 20)
    assert len(pattern.calls) == 1 and candidate.id in driver.consumed


def test_native_rejects_replaced_window():
    snapshot = MemoryDriver().observe()
    candidate = build_candidates(demo_task(), snapshot)[0]
    driver, pattern = fake_native(snapshot)
    driver.binding = replace(snapshot.window, process_started=2.0)
    with pytest.raises(JevError, match="binding_mismatch"):
        driver.execute(snapshot, candidate, 20)
    assert not pattern.calls


def test_native_stale_and_mutated():
    snapshot = MemoryDriver().observe()
    candidate = build_candidates(demo_task(), snapshot)[0]
    driver, pattern = fake_native(snapshot)
    old = replace(snapshot, captured_at=time.monotonic() - 30)
    with pytest.raises(JevError, match="stale_observation"):
        driver.execute(old, candidate, 20)
    with pytest.raises(JevError, match="binding_mismatch"):
        driver.execute(snapshot, replace(candidate, id="fake"), 20)
    assert not pattern.calls


def test_password_control_never_reads_name_or_children():
    class Protected:
        IsPassword = True

        def GetRuntimeId(self):
            return [1, 2, 3]

        @property
        def Name(self):
            raise AssertionError("Protected name was read")

    driver = object.__new__(NativeDriver)
    e = driver._element(Protected())
    assert e.password and e.value is None and e.operations == ()


def test_incomplete_snapshot_never_dispatches():
    snapshot = MemoryDriver().observe()
    candidate = build_candidates(demo_task(), snapshot)[0]
    driver, pattern = fake_native(replace(snapshot, complete=False))
    with pytest.raises(JevError, match="stale_observation"):
        driver.execute(snapshot, candidate, 20)
    assert not pattern.calls


def test_worker_timeout_terminates_instead_of_waiting_forever():
    from jev_windows.worker import ProcessDriver

    driver = object.__new__(ProcessDriver)
    driver.timeout = 0.01
    driver.closed = False
    events = []
    driver.connection = SimpleNamespace(
        poll=lambda timeout: False, close=lambda: events.append("pipe")
    )
    driver.process = SimpleNamespace(
        is_alive=lambda: False, join=lambda timeout: events.append("join")
    )
    with pytest.raises(JevError, match="native_worker_timeout"):
        driver._receive()
    assert driver.closed and events == ["pipe", "join"]


def test_worker_error_is_code_only():
    from jev_windows.worker import ProcessDriver

    driver = object.__new__(ProcessDriver)
    driver.timeout = 1
    driver.connection = SimpleNamespace(poll=lambda _: True, recv=lambda: (False, "test_error"))
    with pytest.raises(JevError, match="test_error"):
        driver._receive()
