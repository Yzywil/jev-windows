import io
import json
import time
from dataclasses import replace
from unittest.mock import patch

import pytest

from jev_windows.contracts import JevError
from jev_windows.demo import DemoProvider, MemoryDriver, demo_task
from jev_windows.provider import ENDPOINT, TypeSafeProvider, http_post
from jev_windows.runner import RunConfig, run


def test_http_transport_uses_only_fixed_endpoint_and_auth_header():
    class Response(io.BytesIO):
        status = 200
        headers = {"Content-Type": "application/json"}

    captured = []

    class Opener:
        def open(self, request, timeout):
            captured.append((request, timeout))
            return Response(b'{"ok":true}')

    with patch("urllib.request.build_opener", return_value=Opener()):
        status, _, body = http_post({"state": "synthetic"}, "not-a-real-key", 4)
    assert status == 200 and json.loads(body) == {"ok": True}
    req, timeout = captured[0]
    assert req.full_url == ENDPOINT and req.method == "POST" and timeout == 4
    assert req.get_header("Authorization") == "Bearer not-a-real-key"
    assert b"not-a-real-key" not in req.data


def test_provider_invalid_json_is_clean_error():
    p = TypeSafeProvider(api_key="fake", transport=lambda *_: (200, {}, b"<html>private</html>"))
    with pytest.raises(JevError, match="invalid_provider_json"):
        p.choose(demo_task(), (), time.monotonic() + 5)


def test_long_confirmation_expires_without_action():
    d = MemoryDriver()
    task = replace(demo_task(), grants=())

    def approve(candidate):
        # Simulate time passing only in the runner's monotonic clock.
        ticks[0] += 30
        return True

    ticks = [time.monotonic()]
    result = run(
        task,
        d,
        DemoProvider(),
        config=RunConfig(execute=True),
        clock=lambda: ticks[0],
        confirm=approve,
    )
    assert result.reason == "stale_observation" and d.executions == 0


def test_window_identity_changes_during_inference():
    d = MemoryDriver()

    class Changes(DemoProvider):
        def choose(self, *args):
            decision = super().choose(*args)
            d.window = replace(d.window, process_started=999)
            return decision

    result = run(demo_task(), d, Changes(), config=RunConfig(execute=True))
    assert result.reason == "window_or_capture_changed" and d.executions == 0


def test_no_candidates_never_calls_provider():
    d = MemoryDriver()
    d.elements = (d.elements[-1],)
    p = DemoProvider()
    result = run(demo_task(), d, p, config=RunConfig(execute=True))
    assert result.reason == "no_candidates" and p.calls == 0


def test_already_verified_never_calls_provider():
    d = MemoryDriver()
    d.elements = (*d.elements[:2], replace(d.elements[-1], name="Applied: Hello Jev"))
    p = DemoProvider()
    result = run(demo_task(), d, p)
    assert result.status == "verified" and result.steps == 0 and p.calls == 0


@pytest.mark.parametrize("config", [{"max_calls": 0}, {"retries": 3}, {"timeout": 0}])
def test_provider_budgets_validated(config):
    with pytest.raises(JevError, match="invalid_provider_budget"):
        TypeSafeProvider(api_key="fake", **config)
