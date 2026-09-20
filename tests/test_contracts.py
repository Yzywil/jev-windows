from dataclasses import FrozenInstanceError, asdict, replace

import pytest

from jev_windows.contracts import (
    Element,
    JevError,
    Selector,
    Task,
    build_candidates,
    probability,
    verify,
)
from jev_windows.demo import MemoryDriver, demo_task
from jev_windows.policy import needs_confirmation
from jev_windows.provider import request_body


def test_candidates_are_compound_and_deterministic():
    driver, task = MemoryDriver(), demo_task()
    snap = driver.observe()
    candidates = build_candidates(task, snap)
    assert len(candidates) == 2
    assert candidates == build_candidates(task, snap)
    assert candidates[0].operation == "set_value"
    assert candidates[0].argument == "Hello Jev"
    assert candidates[1].operation == "invoke"
    with pytest.raises(FrozenInstanceError):
        candidates[0].argument = "overwrite"


def test_no_input_means_no_typing():
    task = replace(demo_task(), inputs=())
    assert [c.operation for c in build_candidates(task, MemoryDriver().observe())] == ["invoke"]


@pytest.mark.parametrize(
    "field,value", [("password", True), ("enabled", False), ("visible", False)]
)
def test_protected_controls_excluded(field, value):
    driver = MemoryDriver()
    snap = driver.observe()
    element = replace(snap.elements[0], **{field: value})
    candidates = build_candidates(demo_task(), replace(snap, elements=(element,)))
    assert not candidates


def test_no_silent_candidate_truncation():
    with pytest.raises(JevError, match="candidate_limit_exceeded"):
        build_candidates(demo_task(), MemoryDriver().observe(), limit=1)


def test_snapshot_must_be_complete():
    snap = replace(MemoryDriver().observe(), complete=False)
    with pytest.raises(JevError, match="incomplete_snapshot"):
        build_candidates(demo_task(), snap)
    assert not verify(demo_task(), snap)


def test_duplicate_and_ambiguous_selectors_stop():
    snap = MemoryDriver().observe()
    with pytest.raises(JevError, match="duplicate_element_ref"):
        build_candidates(demo_task(), replace(snap, elements=snap.elements * 2))
    duplicate = replace(snap.elements[0], ref="another")
    with pytest.raises(JevError, match="ambiguous_selector"):
        build_candidates(demo_task(), replace(snap, elements=(*snap.elements, duplicate)))


def test_wrong_window_executable():
    snap = MemoryDriver().observe()
    snap = replace(snap, window=replace(snap.window, executable="other.exe"))
    with pytest.raises(JevError, match="wrong_executable"):
        build_candidates(demo_task(), snap)
    assert not verify(demo_task(), snap)


def test_no_ui_values_in_request_and_no_out_of_scope_names():
    snap = MemoryDriver().observe()
    element = Element("secret", "private-bank-label", "TextControl", value="private-password")
    snap = replace(snap, elements=(*snap.elements, element))
    body = request_body(demo_task(), build_candidates(demo_task(), snap), "jev-latest")
    serialized = str(body)
    assert "private-bank-label" not in serialized
    assert "private-password" not in serialized
    assert "Hello Jev" not in serialized
    assert len(body["questions"]) == 1
    assert {"abstain", "reobserve"} <= set(body["questions"]["next"]["criteria"])


def test_verify_is_exact_not_substring_or_model_judgment():
    snap, task = MemoryDriver().observe(), demo_task()
    assert not verify(task, snap)
    result = replace(snap.elements[-1], name="Applied: Hello Jev EXTRA")
    assert not verify(task, replace(snap, elements=(*snap.elements[:2], result)))
    result = replace(result, name="Applied: Hello Jev")
    assert verify(task, replace(snap, elements=(*snap.elements[:2], result)))
    assert not verify(task, replace(snap, elements=(*snap.elements[:2], result, result)))


@pytest.mark.parametrize(
    "raw", [{}, {"role": "ButtonControl"}, {"name": ""}, {"name": "OK", "unknown": 1}, {"name": 1}]
)
def test_reject_selector(raw):
    with pytest.raises(JevError):
        Selector.parse(raw)


@pytest.mark.parametrize("value", [True, None, "0.8", float("nan"), float("inf"), -1, 1.01])
def test_invalid_probability(value):
    assert not probability(value)


def task_json():
    task = asdict(demo_task())
    task["version"] = 1
    for group in ("scope", "inputs", "grants", "assertions"):
        task[group] = list(task[group])
        for entry in task[group]:
            selector = entry.get("selector", entry)
            for k in list(selector):
                if selector[k] is None:
                    del selector[k]
    return task


def test_task_roundtrip():
    assert Task.parse(task_json()) == demo_task()


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", True),
        ("goal", ""),
        ("executable", "../cmd.exe"),
        ("scope", []),
        ("assertions", []),
        ("arbitrary", True),
        ("inputs", [{"selector": {"name": "A"}, "value": 1}]),
        ("grants", [{"selector": {"name": "A"}, "operation": "shell"}]),
    ],
)
def test_invalid_tasks(field, value):
    raw = task_json()
    raw[field] = value
    with pytest.raises(JevError):
        Task.parse(raw)


@pytest.mark.parametrize("label", ["Delete", "删除", "Ｓｅｎｄ", "D\u200belete", "Pay now"])
def test_sensitive_actions_need_confirmation_even_with_grant(label):
    task = demo_task()
    c = build_candidates(task, MemoryDriver().observe())[1]
    c = replace(c, element=replace(c.element, name=label))
    assert needs_confirmation(task, c)


def test_exact_grants_not_global_permissions():
    task = demo_task()
    candidate = build_candidates(task, MemoryDriver().observe())[0]
    assert not needs_confirmation(task, candidate)
    assert needs_confirmation(replace(task, grants=()), candidate)


def test_progress_contains_only_equality_not_values():
    from jev_windows.contracts import progress_state

    driver, task = MemoryDriver(), demo_task()
    before = progress_state(task, driver.observe())
    assert before["caller_inputs"][0]["matches_requested_value"] is False
    driver.elements = (replace(driver.elements[0], value="Hello Jev"), *driver.elements[1:])
    after = progress_state(task, driver.observe())
    assert after["caller_inputs"][0]["matches_requested_value"] is True
    assert "Hello Jev" not in str(after)


def test_checkbox_offers_explicit_direction_not_invoke():
    snap = MemoryDriver().observe()
    checkbox = replace(snap.elements[0], operations=("invoke", "toggle"), checked=False)
    candidates = build_candidates(demo_task(), replace(snap, elements=(checkbox,)))
    assert [c.operation for c in candidates] == ["check"]


def test_non_string_assertion_property_rejected():
    raw = task_json()
    raw["assertions"][0]["property"] = []
    with pytest.raises(JevError, match="invalid_assertion_property"):
        Task.parse(raw)
