import json
import time

import pytest

from jev_windows.contracts import JevError, build_candidates
from jev_windows.demo import MemoryDriver, demo_task
from jev_windows.provider import NoRedirect, TypeSafeProvider, validate_response


def response(choices=("one", "abstain")):
    return {
        "model": "test-model",
        "answers": {
            "next": {
                "type": "choice",
                "choice": choices[0],
                "confidence": 0.98,
                "probabilities": {c: float(n == 0) for n, c in enumerate(choices)},
            }
        },
        "usage": {"input_tokens": 50, "output_tokens": 12},
    }


def test_valid_response():
    assert validate_response(response(), {"one", "abstain"}).input_tokens == 50


@pytest.mark.parametrize(
    "mutation",
    [
        lambda b: b["answers"]["next"].update(choice="shell"),
        lambda b: b["answers"]["next"].update(confidence=None),
        lambda b: b["answers"]["next"].update(confidence=".99"),
        lambda b: b["answers"]["next"].update(confidence=True),
        lambda b: b["answers"]["next"].update(confidence=float("nan")),
        lambda b: b["answers"]["next"].update(probabilities={"one": 1}),
        lambda b: b["answers"]["next"].update(probabilities={"one": 1, "abstain": 1}),
        lambda b: b["answers"]["next"].update(probabilities={"one": 0, "abstain": 1}),
        lambda b: b["usage"].update(input_tokens=-1),
        lambda b: b.update(model=None),
    ],
)
def test_invalid_responses(mutation):
    raw = response()
    mutation(raw)
    with pytest.raises(JevError, match="invalid_provider_response"):
        validate_response(raw, {"one", "abstain"})


def test_reject_redirect():
    with pytest.raises(JevError, match="provider_redirect_blocked"):
        NoRedirect().redirect_request(None, None, 302, "", {}, "http://attacker.invalid")


def run_choose(provider):
    task = demo_task()
    return provider.choose(
        task, build_candidates(task, MemoryDriver().observe()), time.monotonic() + 60
    )


def success_transport(payload, key, timeout):
    choices = list(payload["questions"]["next"]["criteria"])
    return 200, {}, json.dumps(response(choices)).encode()


def test_requests_and_usage_counted():
    p = TypeSafeProvider(api_key="not-a-secret", transport=success_transport)
    run_choose(p)
    assert (p.calls, p.input_tokens, p.output_tokens) == (1, 50, 12)


def test_retry_is_bounded_and_counted():
    pauses = []
    p = TypeSafeProvider(
        api_key="not-a-secret",
        retries=2,
        max_calls=2,
        sleep=pauses.append,
        transport=lambda *_: (429, {"Retry-After": "2"}, b""),
    )
    with pytest.raises(JevError, match="request_budget_exhausted"):
        run_choose(p)
    assert p.calls == 2
    assert pauses == [2, 2]


@pytest.mark.parametrize("status", [401, 403, 422, 529, 503])
def test_http_error_is_sanitized(status):
    p = TypeSafeProvider(
        api_key="do-not-leak",
        retries=0,
        transport=lambda *_: (status, {}, b"do-not-leak private server data"),
    )
    with pytest.raises(JevError, match=f"provider_http_{status}") as e:
        run_choose(p)
    assert "do-not-leak" not in str(e.value)
    assert p.calls == 1


def test_network_error_is_not_retried_or_echoed():
    def fail(*_):
        raise RuntimeError("do-not-leak")

    p = TypeSafeProvider(api_key="do-not-leak", retries=2, transport=fail)
    with pytest.raises(JevError, match="provider_transport_error"):
        run_choose(p)
    assert p.calls == 1


def test_deadline_before_request():
    p = TypeSafeProvider(api_key="not-a-secret", transport=success_transport)
    with pytest.raises(JevError, match="deadline_exceeded"):
        p.choose(demo_task(), (), time.monotonic() - 1)
    assert p.calls == 0


def test_missing_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(JevError, match="api_key_required"):
        TypeSafeProvider()
