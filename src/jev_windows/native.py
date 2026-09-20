"""Scoped, semantic UIA adapter over Windows-MCP 0.8.5's vendored UIA API.

No MCP server, global input, clipboard fallback, coordinate clicks or shell tool.
All calls run inside a disposable worker process (see worker.py).
"""

import importlib.metadata
import sys
import time

from .contracts import Candidate, Element, JevError, Snapshot, WindowIdentity, digest


def dependencies():
    if sys.platform != "win32":
        raise JevError("windows_required")
    try:
        if importlib.metadata.version("windows-mcp") != "0.8.5":
            raise JevError("unsupported_windows_mcp_version")
        import psutil
        import win32gui
        import win32process
        import windows_mcp.uia as uia
    except ImportError:
        raise JevError("install_windows_extra") from None
    return uia, psutil, win32gui, win32process


def list_windows() -> list[dict]:
    _, psutil, gui, process = dependencies()
    result = []

    def visit(hwnd, _):
        if not gui.IsWindowVisible(hwnd) or not gui.GetWindowText(hwnd):
            return
        try:
            _, pid = process.GetWindowThreadProcessId(hwnd)
            result.append(
                {
                    "handle": hwnd,
                    "pid": pid,
                    "executable": psutil.Process(pid).name(),
                    "title": gui.GetWindowText(hwnd),
                }
            )
        except (psutil.Error, OSError):
            pass

    gui.EnumWindows(visit, None)
    return result


class NativeDriver:
    def __init__(self, handle: int, executable: str, *, max_nodes: int = 2000, max_depth: int = 20):
        self.uia, self.psutil, self.gui, self.process = dependencies()
        self.handle, self.executable = handle, executable
        self.max_nodes, self.max_depth = max_nodes, max_depth
        self.binding = self._identity()
        self.controls = {}
        self.consumed = set()

    def _identity(self) -> WindowIdentity:
        if not self.gui.IsWindow(self.handle) or not self.gui.IsWindowVisible(self.handle):
            raise JevError("target_window_missing")
        _, pid = self.process.GetWindowThreadProcessId(self.handle)
        process = self.psutil.Process(pid)
        if process.name().casefold() != self.executable.casefold():
            raise JevError("wrong_executable")
        return WindowIdentity(self.handle, pid, process.create_time(), process.name())

    def _check_binding(self):
        if self._identity() != self.binding:
            raise JevError("window_identity_changed")

    def _patterns(self, control):
        ids = self.uia.PatternId
        return {
            op: control.GetPattern(pid)
            for op, pid in (
                ("invoke", ids.InvokePattern),
                ("set_value", ids.ValuePattern),
                ("toggle", ids.TogglePattern),
                ("select", ids.SelectionItemPattern),
            )
        }

    def _element(self, control) -> Element:
        runtime = tuple(control.GetRuntimeId())
        if not runtime:
            raise JevError("missing_runtime_id")
        ref = digest(runtime)[:24]
        protected = bool(control.IsPassword)
        # Do not read even the name or child subtree of a protected control.
        if protected:
            return Element(ref, "<protected>", "protected", password=True)
        patterns = self._patterns(control)
        value = patterns["set_value"]
        toggle = patterns["toggle"]
        select = patterns["select"]
        operations = tuple(
            op
            for op, pattern in patterns.items()
            if pattern is not None and not (op == "set_value" and value.IsReadOnly)
        )
        toggle_state = toggle.ToggleState if toggle else None
        return Element(
            ref=ref,
            name=control.Name or "",
            role=control.ControlTypeName,
            automation_id=control.AutomationId or "",
            operations=operations,
            enabled=bool(control.IsEnabled),
            visible=not bool(control.IsOffscreen),
            value=value.Value if value else None,
            checked=(bool(toggle_state) if toggle_state in (0, 1) else None),
            selected=bool(select.IsSelected) if select else None,
        )

    def observe(self) -> Snapshot:
        self._check_binding()
        captured = time.monotonic()
        root = self.uia.ControlFromHandle(self.handle)
        if root is None:
            raise JevError("target_window_missing")
        elements, controls = [], {}
        pending = [(root, 0)]
        complete = True
        try:
            while pending:
                if len(elements) >= self.max_nodes:
                    complete = False
                    break
                control, depth = pending.pop()
                element = self._element(control)
                if element.ref in controls:
                    raise JevError("duplicate_element_ref")
                elements.append(element)
                controls[element.ref] = control
                if element.password:
                    continue
                children = control.GetChildren()
                if depth >= self.max_depth and children:
                    complete = False
                    break
                pending.extend((child, depth + 1) for child in reversed(children))
        except JevError:
            raise
        except Exception:
            raise JevError("uia_capture_failed") from None
        self._check_binding()
        self.controls = controls
        return Snapshot(self.binding, tuple(elements), captured, complete)

    def execute(self, snapshot: Snapshot, candidate: Candidate, max_age: float) -> None:
        if time.monotonic() - snapshot.captured_at > max_age:
            raise JevError("stale_observation")
        if candidate.id in self.consumed:
            raise JevError("candidate_already_consumed")
        if candidate.fingerprint != snapshot.fingerprint or snapshot.window != self.binding:
            raise JevError("candidate_binding_mismatch")
        current = self.observe()
        if not current.complete or current.fingerprint != snapshot.fingerprint:
            raise JevError("stale_observation")
        if time.monotonic() - snapshot.captured_at > max_age:
            raise JevError("stale_observation")
        control = self.controls.get(candidate.element.ref)
        if control is None or self._element(control) != candidate.element:
            raise JevError("element_changed")
        e = candidate.element
        if e.password or not e.enabled or not e.visible:
            raise JevError("element_not_actionable")
        self._check_binding()
        patterns = self._patterns(control)
        op = candidate.operation
        expected_id = "a_" + digest([snapshot.fingerprint, e.ref, op, candidate.argument])[:20]
        if candidate.id != expected_id:
            raise JevError("candidate_binding_mismatch")
        if op in {"check", "uncheck"}:
            if "toggle" not in e.operations or type(e.checked) is not bool:
                raise JevError("unsupported_operation")
            wanted = op == "check"
            if candidate.argument is not wanted or e.checked is wanted:
                raise JevError("invalid_toggle")
        elif op not in e.operations or op not in {"invoke", "set_value", "select"}:
            raise JevError("unsupported_operation")
        if op == "set_value" and not isinstance(candidate.argument, str):
            raise JevError("invalid_input")
        # Consume BEFORE dispatch. A failed/unknown operation must not be replayed.
        self.consumed.add(candidate.id)
        try:
            if op == "invoke":
                ok = patterns["invoke"].Invoke(waitTime=0)
            elif op == "set_value":
                ok = patterns["set_value"].SetValue(candidate.argument, waitTime=0)
            elif op == "select":
                ok = patterns["select"].Select(waitTime=0)
            else:
                ok = patterns["toggle"].Toggle(waitTime=0)  # One call, never a retry loop.
            if ok is not True:
                raise JevError("dispatch_outcome_unknown")
        except Exception:
            raise JevError("dispatch_outcome_unknown") from None
