# Contributing

1. Discuss changes to action capabilities, grants or data transmission in an issue.
2. Install Python 3.12+ and uv, then `uv sync --locked`.
3. Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`.
4. Add negative tests before extending the action/response schema.
5. For backend changes, also test the native fixture on Windows and report the
   platform, dependency version and independent readback result.

Tests and CI must not need credentials, cloud access or the user's desktop. Native
and live tests are explicitly separate. Never add `.env`, private UI snapshots,
personal paths, API keys or account metadata to fixtures. Keep telemetry redacted.

Dependency upgrades need lock updates plus native contract tests. Keep Windows
imports lazy so the portable core tests on Linux. Do not silently fall back from
UIA to arbitrary coordinates, clipboard pasting, generated code or a shell.

