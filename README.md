# Jev Windows

[![CI](https://github.com/Yzywil/jev-windows/actions/workflows/ci.yml/badge.svg)](https://github.com/Yzywil/jev-windows/actions/workflows/ci.yml)

**Small decisions. Scoped actions. Verified outcomes.**

[中文](README.zh-CN.md) · [Plan](docs/PLAN.md) · [Security](SECURITY.md)

Supervised Windows UI Automation powered by TypeSafe Jev. The model chooses one
complete action from a bounded candidate list; local code owns execution and
verification. **v0.1.0a1 is an alpha**, not an agent for arbitrary Windows software.

```text
Selected window → UIA snapshot → scoped action candidates → Jev Choice
                                                            ↓
Verified result ← independent assertion ← UIA action ← local policy + freshness
```

## Why a separate integration?

Inspired by [Jev-cu](https://github.com/Sac-Y/Jev-cu), but implemented independently
for Windows. It reuses [Windows-MCP](https://github.com/CursorTouch/Windows-MCP)'s
UIA library, not its general-purpose MCP server. No shell/registry tools, global
clicks, clipboard replacement, screenshot upload, or background service.

- **One bounded Choice:** operation, target and caller argument stay together.
- **Local permissions:** an exact task scope and grants; unknown/sensitive actions
  stop for single-action approval. Model confidence never grants permission.
- **Freshness:** HWND/PID/process-start binding, snapshot fingerprint, age limit and
  final element recheck. No automatic replay after an uncertain action.
- **Proof rather than “done”:** only the caller's exact UIA assertions yield `verified`.
- **Inspectable budgets:** separate actions, decisions, HTTP attempts and returned
  token counts. No claims of guaranteed speedup, accuracy, or billing cap.

## Try it without Windows or an API key

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```powershell
git clone https://github.com/Yzywil/jev-windows.git
cd jev-windows
uv sync --locked
uv run jev-windows demo
uv run pytest
```

The demo is an in-memory simulator, **not** a desktop or live-model test.

## Windows quickstart

Run from a normal non-administrator Windows 10/11 desktop session. Use a disposable
test document and keep confidential content out of the selected window.

```powershell
uv sync --locked --extra windows
uv run jev-windows doctor
uv run jev-windows windows
# Use a handle and executable from the returned list, not guessed values.
uv run jev-windows snapshot --window 123456 --executable fixture.exe
```

Read the snapshot locally and write a task with exact control names/automation IDs.
See [the fixture task](examples/fixture-task.json) and [task format](docs/TASKS.md).
Set `TYPESAFE_API_KEY` in your terminal environment; never put it in task JSON or
commit it. The CLI deliberately does not auto-load `.env` files.

```powershell
# Preview: paid inference, no UI action. Labels + goal leave your machine.
uv run jev-windows run --task examples/fixture-task.json --window 123456 --share-ui
# Execute only after reviewing the task's scope, grants, and assertions.
uv run jev-windows run --task examples/fixture-task.json --window 123456 --share-ui --execute
```

`--share-ui` explicitly permits transmitting the task goal, executable name and
**scoped candidate control labels/IDs/roles** and boolean input progress to TypeSafe.
Field values, full window
titles, full trees, and screenshots are not sent. Labels and goals can still contain
private text: this is minimization, not automatic anonymization.

An ungranted/sensitive action needs interactive `APPROVE`. In a noninteractive
terminal the runner stops with `confirm`; there is no “approve everything” flag.

## Supported alpha surface

| Operation | Requirement |
|---|---|
| Invoke button/menu item | UIA InvokePattern |
| Replace text | UIA ValuePattern, writable, caller supplies exact text |
| Select item/tab | UIA SelectionItemPattern |
| Check/uncheck | UIA TogglePattern, known boolean state; one toggle only |
| Verify | Exact unique-selector match on name/value/checked/selected |

Canvas-only apps, OCR, raw coordinates, keyboard shortcuts, clipboard pasting,
browser DOM, secure/elevated desktops, generated input text and cross-window flows
are outside this release. App compatibility depends on its UIA implementation.

The adapter uses a **pinned internal API** in `windows-mcp==0.8.5`; dependency
upgrades require contract and native tests. Its dependencies are larger than the
portable core. We do not start its server or import its telemetry service.

## Development and release

```powershell
uv sync --locked --extra windows
uv run ruff check .
uv run pytest --cov=jev_windows --cov-report=term-missing
uv build
```

See [architecture](docs/ARCHITECTURE.md), [validation](docs/VALIDATION.md),
[native fixture](docs/NATIVE_TEST.md), [contributing](CONTRIBUTING.md), and
[third-party attribution](THIRD_PARTY.md). CI runs offline checks on Windows/Linux;
interactive native and paid API checks are separate and never implied by a green CI.

MIT. Independent project; not affiliated with TypeSafe, Microsoft, OpenAI, or Windows-MCP.
