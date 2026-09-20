"""Portable deterministic simulator; explicitly NOT evidence of desktop control."""

import time
from dataclasses import replace

from .contracts import Element, JevError, Snapshot, Task, WindowIdentity
from .provider import Decision


def demo_task():
    return Task.parse(
        {
            "version": 1,
            "goal": "Set the Name field to the supplied input, then click Apply.",
            "executable": "fixture.exe",
            "scope": [{"automation_id": "name"}, {"automation_id": "apply"}],
            "inputs": [{"selector": {"automation_id": "name"}, "value": "Hello Jev"}],
            "grants": [
                {"selector": {"automation_id": "name"}, "operation": "set_value"},
                {"selector": {"automation_id": "apply"}, "operation": "invoke"},
            ],
            "assertions": [
                {
                    "selector": {"automation_id": "result"},
                    "property": "name",
                    "equals": "Applied: Hello Jev",
                }
            ],
        }
    )


class MemoryDriver:
    def __init__(self):
        self.window = WindowIdentity(1, 1, 1.0, "fixture.exe")
        self.elements = (
            Element("name", "Name", "EditControl", "name", ("set_value",), value=""),
            Element("apply", "Apply", "ButtonControl", "apply", ("invoke",)),
            Element("result", "Ready", "TextControl", "result"),
        )
        self.executions = 0
        self.consumed = set()

    def observe(self):
        return Snapshot(self.window, self.elements, time.monotonic())

    def execute(self, snapshot, candidate, max_age):
        if candidate.id in self.consumed or snapshot.fingerprint != self.observe().fingerprint:
            raise JevError("stale_observation")
        self.consumed.add(candidate.id)
        self.executions += 1
        if candidate.operation == "set_value":
            self.elements = (
                replace(self.elements[0], value=candidate.argument),
                *self.elements[1:],
            )
        else:
            self.elements = (
                *self.elements[:2],
                replace(self.elements[2], name="Applied: " + self.elements[0].value),
            )


class DemoProvider:
    def __init__(self):
        self.calls = self.input_tokens = self.output_tokens = 0

    def choose(self, task, candidates, deadline, progress=None):
        self.calls += 1
        target = next((c for c in candidates if c.operation == "set_value"), candidates[0])
        return Decision(target.id, 1.0)
