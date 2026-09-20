"""Portable immutable contracts. No native imports or network side effects."""

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any


class JevError(Exception):
    """Errors carry machine-readable codes, never private provider/UI payloads."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def digest(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def probability(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


@dataclass(frozen=True)
class WindowIdentity:
    handle: int
    pid: int
    process_started: float
    executable: str


@dataclass(frozen=True)
class Element:
    ref: str
    name: str
    role: str
    automation_id: str = ""
    operations: tuple[str, ...] = ()
    enabled: bool = True
    visible: bool = True
    password: bool = False
    value: str | None = None
    checked: bool | None = None
    selected: bool | None = None


@dataclass(frozen=True)
class Snapshot:
    window: WindowIdentity
    elements: tuple[Element, ...]
    captured_at: float
    complete: bool = True

    @property
    def fingerprint(self) -> str:
        return digest(
            {"window": asdict(self.window), "elements": [asdict(e) for e in self.elements]}
        )


@dataclass(frozen=True)
class Selector:
    name: str | None = None
    automation_id: str | None = None
    role: str | None = None

    def matches(self, element: Element) -> bool:
        return all(
            value is None or getattr(element, key) == value for key, value in asdict(self).items()
        )

    @classmethod
    def parse(cls, raw: dict) -> "Selector":
        if not isinstance(raw, dict) or not raw or set(raw) - {"name", "automation_id", "role"}:
            raise JevError("invalid_selector")
        if not (raw.get("name") or raw.get("automation_id")):
            raise JevError("selector_needs_exact_name_or_id")
        if any(not isinstance(v, str) or not v or len(v) > 512 for v in raw.values()):
            raise JevError("invalid_selector")
        return cls(**raw)


@dataclass(frozen=True)
class InputValue:
    selector: Selector
    value: str


@dataclass(frozen=True)
class Assertion:
    selector: Selector
    property: str
    equals: str | bool


@dataclass(frozen=True)
class Grant:
    selector: Selector
    operation: str


OPERATIONS = {"invoke", "set_value", "select", "check", "uncheck"}


@dataclass(frozen=True)
class Task:
    goal: str
    executable: str
    scope: tuple[Selector, ...]
    assertions: tuple[Assertion, ...]
    inputs: tuple[InputValue, ...] = ()
    grants: tuple[Grant, ...] = ()

    @classmethod
    def parse(cls, raw: dict) -> "Task":
        if not isinstance(raw, dict) or set(raw) - {
            "version",
            "goal",
            "executable",
            "scope",
            "assertions",
            "inputs",
            "grants",
        }:
            raise JevError("invalid_task_fields")
        if type(raw.get("version")) is not int or raw["version"] != 1:
            raise JevError("invalid_task_version")
        goal, exe = raw.get("goal"), raw.get("executable")
        if not isinstance(goal, str) or not goal.strip() or len(goal) > 2000:
            raise JevError("invalid_goal")
        if (
            not isinstance(exe, str)
            or not exe.lower().endswith(".exe")
            or any(c in exe for c in "/\\\r\n")
            or len(exe) > 255
        ):
            raise JevError("invalid_executable")
        for key in ("scope", "assertions", "inputs", "grants"):
            items = raw.get(key, [])
            if not isinstance(items, list) or len(items) > 64:
                raise JevError("invalid_task_list")
        if not raw.get("scope") or not raw.get("assertions"):
            raise JevError("scope_and_assertions_required")
        inputs, assertions, grants = [], [], []
        for item in raw.get("inputs", []):
            if not isinstance(item, dict) or set(item) != {"selector", "value"}:
                raise JevError("invalid_input")
            if not isinstance(item["value"], str) or len(item["value"]) > 4096:
                raise JevError("invalid_input")
            inputs.append(InputValue(Selector.parse(item["selector"]), item["value"]))
        for item in raw["assertions"]:
            if not isinstance(item, dict) or set(item) != {"selector", "property", "equals"}:
                raise JevError("invalid_assertion")
            prop, expected = item["property"], item["equals"]
            if not isinstance(prop, str) or prop not in {"name", "value", "checked", "selected"}:
                raise JevError("invalid_assertion_property")
            expected_type = bool if prop in {"checked", "selected"} else str
            if type(expected) is not expected_type:
                raise JevError("invalid_assertion_value")
            if isinstance(expected, str) and len(expected) > 4096:
                raise JevError("invalid_assertion_value")
            assertions.append(Assertion(Selector.parse(item["selector"]), prop, expected))
        for item in raw.get("grants", []):
            if not isinstance(item, dict) or set(item) != {"selector", "operation"}:
                raise JevError("invalid_grant")
            if not isinstance(item["operation"], str) or item["operation"] not in OPERATIONS:
                raise JevError("invalid_grant_operation")
            grants.append(Grant(Selector.parse(item["selector"]), item["operation"]))
        return cls(
            goal,
            exe,
            tuple(map(Selector.parse, raw["scope"])),
            tuple(assertions),
            tuple(inputs),
            tuple(grants),
        )


@dataclass(frozen=True)
class Candidate:
    id: str
    fingerprint: str
    element: Element
    operation: str
    argument: str | bool | None = None
    input_index: int | None = None


def build_candidates(task: Task, snapshot: Snapshot, limit: int = 64) -> tuple[Candidate, ...]:
    if not snapshot.complete:
        raise JevError("incomplete_snapshot")
    if snapshot.window.executable.casefold() != task.executable.casefold():
        raise JevError("wrong_executable")
    if len({e.ref for e in snapshot.elements}) != len(snapshot.elements):
        raise JevError("duplicate_element_ref")
    for selector in (*task.scope, *(i.selector for i in task.inputs)):
        if sum(selector.matches(e) for e in snapshot.elements) > 1:
            raise JevError("ambiguous_selector")
    fingerprint = snapshot.fingerprint
    result = []
    for e in snapshot.elements:
        if e.password or not e.enabled or not e.visible:
            continue
        if not any(s.matches(e) for s in task.scope):
            continue
        arguments = []
        if "invoke" in e.operations and not {"toggle", "select"}.intersection(e.operations):
            arguments.append(("invoke", None, None))
        if "select" in e.operations and e.selected is False:
            arguments.append(("select", None, None))
        if "toggle" in e.operations and type(e.checked) is bool:
            arguments.append(("uncheck" if e.checked else "check", not e.checked, None))
        if "set_value" in e.operations:
            matching_inputs = [(n, i) for n, i in enumerate(task.inputs) if i.selector.matches(e)]
            if len(matching_inputs) > 1:
                raise JevError("ambiguous_input")
            for index, item in matching_inputs:
                if item.value != e.value:
                    arguments.append(("set_value", item.value, index))
        for op, arg, index in arguments:
            cid = "a_" + digest([fingerprint, e.ref, op, arg])[:20]
            result.append(Candidate(cid, fingerprint, e, op, arg, index))
    if len(result) > limit:
        raise JevError("candidate_limit_exceeded")
    return tuple(result)


def verify(task: Task, snapshot: Snapshot) -> bool:
    if not snapshot.complete or snapshot.window.executable.casefold() != task.executable.casefold():
        return False
    for assertion in task.assertions:
        matches = [e for e in snapshot.elements if assertion.selector.matches(e)]
        if len(matches) != 1 or matches[0].password or not matches[0].visible:
            return False
        actual = getattr(matches[0], assertion.property)
        if type(actual) is not type(assertion.equals) or actual != assertion.equals:
            return False
    return bool(task.assertions)


def progress_state(task: Task, snapshot: Snapshot) -> dict:
    """Only local equality booleans, never input values or assertion expected text."""
    inputs = []
    for index, item in enumerate(task.inputs):
        found = [e for e in snapshot.elements if item.selector.matches(e) and not e.password]
        inputs.append(
            {
                "index": index,
                "present": len(found) == 1,
                "matches_requested_value": len(found) == 1 and found[0].value == item.value,
            }
        )
    return {"caller_inputs": inputs, "goal_verified_locally": verify(task, snapshot)}
