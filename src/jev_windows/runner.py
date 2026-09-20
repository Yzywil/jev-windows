"""Bounded execution. Model completion claims are deliberately not part of this API."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .contracts import (
    Candidate,
    JevError,
    Snapshot,
    Task,
    build_candidates,
    probability,
    progress_state,
    verify,
)
from .policy import needs_confirmation


class Driver(Protocol):
    def observe(self) -> Snapshot: ...
    def execute(self, snapshot: Snapshot, candidate: Candidate, max_age: float) -> None: ...


@dataclass(frozen=True)
class RunConfig:
    execute: bool = False
    max_steps: int = 10
    max_decisions: int = 20
    seconds: float = 120
    max_age: float = 20
    min_confidence: float = 0.8
    max_no_progress: int = 2

    def __post_init__(self):
        if (
            not 1 <= self.max_steps <= 50
            or not 1 <= self.max_decisions <= 100
            or not 0 < self.seconds <= 600
            or not 0 < self.max_age <= 60
            or not probability(self.min_confidence)
            or self.min_confidence < 0.5
            or not 1 <= self.max_no_progress <= 5
        ):
            raise JevError("invalid_run_config")


@dataclass(frozen=True)
class Result:
    status: str
    steps: int
    decisions: int
    requests: int
    input_tokens: int
    output_tokens: int
    elapsed_ms: int
    reason: str = ""


def run(
    task: Task,
    driver: Driver,
    provider,
    *,
    config: RunConfig | None = None,
    confirm: Callable[[Candidate], bool] | None = None,
    emit=lambda event: None,
    clock=time.monotonic,
    sleep=time.sleep,
) -> Result:
    config = config or RunConfig()
    started = clock()
    deadline = started + config.seconds
    steps = decisions = unchanged = 0
    binding = None

    def finish(status, reason=""):
        result = Result(
            status,
            steps,
            decisions,
            provider.calls,
            provider.input_tokens,
            provider.output_tokens,
            round((clock() - started) * 1000),
            reason,
        )
        return result

    try:
        snapshot = driver.observe()
        binding = snapshot.window
        while True:
            if clock() >= deadline:
                return finish("stopped", "deadline_exceeded")
            if snapshot.window != binding:
                return finish("stopped", "window_identity_changed")
            if not snapshot.complete:
                return finish("stopped", "incomplete_snapshot")
            if verify(task, snapshot):
                return finish("verified")
            if steps >= config.max_steps or decisions >= config.max_decisions:
                return finish("stopped", "step_or_decision_budget_exhausted")
            if unchanged >= config.max_no_progress:
                return finish("stopped", "no_progress")
            candidates = build_candidates(task, snapshot)
            if not candidates:
                return finish("stopped", "no_candidates")
            decision = provider.choose(task, candidates, deadline, progress_state(task, snapshot))
            decisions += 1
            emit(
                {
                    "event": "decision",
                    "number": decisions,
                    "candidates": len(candidates),
                    "choice": decision.choice,
                    "confidence": decision.confidence,
                    "model": decision.model,
                    "requests": provider.calls,
                }
            )
            if clock() >= deadline:
                return finish("stopped", "deadline_exceeded")
            if not probability(decision.confidence) or decision.confidence < config.min_confidence:
                return finish("stopped", "low_confidence")
            if decision.choice == "abstain":
                return finish("abstained")
            if decision.choice == "reobserve":
                if not config.execute:
                    return finish("dry_run", "reobserve")
                sleep(min(0.2, max(0, deadline - clock())))
                fresh = driver.observe()
                unchanged = unchanged + 1 if fresh.fingerprint == snapshot.fingerprint else 0
                snapshot = fresh
                continue
            candidate = next((c for c in candidates if c.id == decision.choice), None)
            if candidate is None:
                return finish("stopped", "unknown_candidate")
            if not config.execute:
                emit(
                    {
                        "event": "preview",
                        "operation": candidate.operation,
                        "requires_confirmation": needs_confirmation(task, candidate),
                    }
                )
                return finish("dry_run")
            if needs_confirmation(task, candidate):
                if confirm is None or confirm(candidate) is not True:
                    return finish("confirm", "action_not_approved")
            if clock() >= deadline:
                return finish("stopped", "deadline_exceeded")
            if clock() - snapshot.captured_at > config.max_age:
                return finish("stopped", "stale_observation")
            # Re-read after inference and human confirmation; never execute against old refs.
            fresh = driver.observe()
            if fresh.window != binding or not fresh.complete:
                return finish("stopped", "window_or_capture_changed")
            if fresh.fingerprint != snapshot.fingerprint:
                return finish("stopped", "stale_observation")
            if clock() >= deadline:
                return finish("stopped", "deadline_exceeded")
            try:
                driver.execute(snapshot, candidate, config.max_age)
                steps += 1
                sleep(min(0.15, max(0, deadline - clock())))
                after = driver.observe()
            except Exception:
                # Dispatch/refresh could have succeeded. Do not replay an unknown outcome.
                return finish("unknown", "dispatch_or_readback_failed")
            emit({"event": "action", "number": steps, "operation": candidate.operation})
            unchanged = unchanged + 1 if after.fingerprint == snapshot.fingerprint else 0
            snapshot = after
    except JevError as e:
        return finish("stopped", e.code)
    except Exception:
        return finish("error", "unexpected_error")
