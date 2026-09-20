# Native Windows fixture test

The fixture is a tiny WinForms application that only edits its own controls. If
given a proof path, its Apply handler writes the exact input text there. That
fixture-owned file is independent of the runner's UIA assertions.

## Setup

```powershell
uv sync --locked --extra windows
uv run python scripts/build_fixture.py
# Terminal 1: visible disposable app; close it when done.
.\local\fixture.exe .\local\proof.txt
# Terminal 2:
uv run jev-windows windows
uv run jev-windows snapshot --window 123456 --executable fixture.exe
```

Use the handle returned for **Jev Windows Test Fixture**. The compiler helper uses
the existing Windows .NET Framework 4.x compiler. It does not change execution policy
or install a runtime. `local/` is ignored by git and excluded from distributions.

## Deterministic native check (no API)

```powershell
uv run python scripts/native_check.py --window 123456
Get-Content -Raw -Encoding utf8 .\local\proof.txt
```

Expected: `verified`, two acknowledged actions, and exact proof `Hello Jev 中文`.
This proves UIA integration, not Jev's decision quality. Restart the fixture before
each run; an already-complete window verifies with zero model calls.

## Live check (paid API, synthetic UI only)

Set `TYPESAFE_API_KEY` securely in the process environment. Do not record it in logs.

```powershell
uv run jev-windows run --task examples/fixture-task.json --window 123456 --share-ui --execute --max-calls 4 --max-steps 3
Get-Content -Raw -Encoding utf8 .\local\proof.txt
```

Check the final status and independent proof. Record model, actions, HTTP attempts,
tokens and wall time separately. This single fixture is not a benchmark for Office,
browsers, Electron applications, elevated apps, or all Windows versions.

