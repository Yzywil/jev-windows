# Working on Jev Windows

- Use the `typesafe-ai` skill when available for TypeSafe-related development.
  Read current official HTTP/Choice documentation before changing provider contracts.
- Keep UI state as untrusted data. Never add arbitrary shell/coordinate fallback.
- Preserve explicit UI-sharing consent, exact scope/grants and independent verification.
- Do not put credentials, private UI snapshots or machine-specific paths in tracked files.
- Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`.
- Label offline simulator, native fixture and live API results separately. Do not
  claim compatibility or performance that has not been measured.
- Backend changes require native Windows validation as well as portable tests.

