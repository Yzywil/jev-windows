# Jev Windows 0.1.0a1 — initial alpha

A supervised Windows UI Automation runner with TypeSafe Jev as a bounded chooser.

## Included

- Complete operation/target/caller-argument choices in one Jev question.
- Scoped controls, default preview, explicit data-sharing consent and local grants.
- Window/process binding, freshness checks, timeout-isolated UIA worker.
- Deterministic completion assertions and redacted JSONL metrics.
- Portable simulator, disposable WinForms fixture, tests, bilingual docs, CI and packages.

## Evidence

Offline tests passed locally. The native fixture passed with mock decisions and,
after a documented progress-context correction, with live `jev-1.13.0`: two actions,
two HTTP calls, 1,221 input / 178 output tokens. Independent fixture readback matched.
See `docs/VALIDATION.md` for the initial stopped attempt and exact scope.

## Requirements and limits

Python 3.12+. Windows 10/11 for native use; actual local validation was Windows 11.
Install the `windows` extra and provide your own TypeSafe key for live decisions.
The UIA integration pins the internal API of Windows-MCP 0.8.5.

This is an **alpha prerelease**, not production-grade general desktop autonomy.
No screenshots, arbitrary shell tools, coordinate fallback, clipboard typing,
elevated-app support or unattended high-impact workflows. Do not include secrets
or private documents in tasks. API calls are billed by TypeSafe.

Wheel and source distribution are provided with SHA-256 checksums. No PyPI upload
is performed by this release process. Install a downloaded wheel with its Windows
extra, for example `python -m pip install "./jev_windows-0.1.0a1-py3-none-any.whl[windows]"`.
