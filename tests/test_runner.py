from dataclasses import replace

import pytest

from jev_windows.contracts import JevError
from jev_windows.demo import DemoProvider, MemoryDriver, demo_task
from jev_windows.provider import Decision
from jev_windows.runner import RunConfig, run


def test_full_loop_verified():
    d = MemoryDriver()
    result = run(
        demo_task(), d, DemoProvider(), config=RunConfig(execute=True), sleep=lambda _: None
    )
    assert (result.status, result.steps, result.decisions) == ("verified", 2, 2)
    assert d.executions == 2


def test_default_is_preview_without_actions():
    d = MemoryDriver()
    result = run(demo_task(), d, DemoProvider())
    assert result.status == "dry_run" and result.decisions == 1
    assert d.executions == 0


def test_ungranted_action_stops():
    d = MemoryDriver()
    result = run(replace(demo_task(), grants=()), d, DemoProvider(), config=RunConfig(execute=True))
    assert result.status == "confirm"
    assert d.executions == 0


def test_approval_is_once_per_action():
    approvals = []
    result = run(
        replace(demo_task(), grants=()),
        MemoryDriver(),
        DemoProvider(),
        config=RunConfig(execute=True),
        confirm=lambda c: approvals.append(c.id) is None,
        sleep=lambda _: None,
    )
    assert result.status == "verified" and len(set(approvals)) == 2


def test_never_replay_uncertain_dispatch():
    class Broken(MemoryDriver):
        def execute(self, *args):
            self.executions += 1
            raise RuntimeError("Private UI content")

    d = Broken()
    result = run(demo_task(), d, DemoProvider(), config=RunConfig(execute=True))
    assert result.status == "unknown" and d.executions == 1
    assert "Private" not in str(result)


def test_stale_result_has_no_execution():
    d = MemoryDriver()

    class Mutating(DemoProvider):
        def choose(self, *args):
            result = super().choose(*args)
            d.elements = (replace(d.elements[0], name="New field"), *d.elements[1:])
            return result

    result = run(demo_task(), d, Mutating(), config=RunConfig(execute=True))
    assert result.reason == "stale_observation" and d.executions == 0


@pytest.mark.parametrize("choice,status", [("abstain", "abstained"), ("invented", "stopped")])
def test_sentinel_or_unknown(choice, status):
    class Fixed(DemoProvider):
        def choose(self, *args):
            self.calls += 1
            return Decision(choice, 1)

    d = MemoryDriver()
    assert run(demo_task(), d, Fixed(), config=RunConfig(execute=True)).status == status
    assert d.executions == 0


def test_reobserve_budget():
    class Again(DemoProvider):
        def choose(self, *args):
            self.calls += 1
            return Decision("reobserve", 1)

    result = run(
        demo_task(), MemoryDriver(), Again(), config=RunConfig(execute=True), sleep=lambda _: None
    )
    assert result.reason == "no_progress" and result.decisions == 2


def test_low_confidence_is_not_permission():
    class Uncertain(DemoProvider):
        def choose(self, *args):
            return replace(super().choose(*args), confidence=0.5)

    d = MemoryDriver()
    result = run(demo_task(), d, Uncertain(), config=RunConfig(execute=True))
    assert result.reason == "low_confidence" and d.executions == 0


def test_last_step_still_verified():
    result = run(
        demo_task(),
        MemoryDriver(),
        DemoProvider(),
        config=RunConfig(execute=True, max_steps=2),
        sleep=lambda _: None,
    )
    assert result.status == "verified"


def test_step_budget_is_not_success():
    result = run(
        demo_task(),
        MemoryDriver(),
        DemoProvider(),
        config=RunConfig(execute=True, max_steps=1),
        sleep=lambda _: None,
    )
    assert result.status == "stopped" and result.steps == 1


def test_logs_do_not_contain_ui_text():
    events = []
    run(
        demo_task(),
        MemoryDriver(),
        DemoProvider(),
        config=RunConfig(execute=True),
        emit=events.append,
        sleep=lambda _: None,
    )
    assert "Hello Jev" not in str(events) and "Name" not in str(events)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_steps": 0},
        {"max_steps": 100},
        {"seconds": -1},
        {"min_confidence": 0.1},
        {"max_age": 100},
        {"max_decisions": 0},
    ],
)
def test_invalid_budgets(kwargs):
    with pytest.raises(JevError):
        RunConfig(**kwargs)
