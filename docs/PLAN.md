# Jev Windows — v0.1.0 release plan

Status: **v0.1.0a1 published**; local/native/live validation and release-commit CI complete.
Initial release target: **alpha**, not universal desktop autonomy.

## Product

A local-first, supervised Windows desktop runner. Jev chooses one immutable action
from controls observed in one explicitly selected window. Local code owns permission,
execution, budgets, and deterministic completion checks. User text is supplied by the
caller; the model never generates commands, coordinates, or text to type.

## Architecture decisions

- Python 3.12+, portable standard-library decision core; optional Windows extra.
- Reuse the UI Automation layer in `windows-mcp==0.8.5`. Do not run its broad MCP
  server, shell, registry, clipboard, network listener, or desktop-wide snapshot.
- This is a pinned **internal-library integration**, not a promise of upstream API stability.
- Separate process for UIA access: timeout terminates the worker; uncertain actions
  are never retried. Bind HWND, PID, executable and process creation time.
- One Choice over complete action/target/argument candidates, including `abstain`
  and `reobserve`. No independent action and target heads that can disagree.
- Exact configured control scope. Stop on truncated trees, oversized candidate
  sets, stale snapshots, changed windows, ambiguity, and invalid provider output.
- Default dry-run. Live inference requires explicit consent to send scoped labels
  and task text to TypeSafe. Password controls excluded; field values withheld.
- Exact per-action local grants; sensitive or unknown actions require an interactive
  one-action confirmation. No model probability is authorization.
- Only a local declarative verifier can return `verified`. UI change is not success.
- JSONL metrics omit labels, typed text, API keys, raw UI trees, and provider bodies.

## Phases and acceptance

### P0 — contracts and scope
- [x] Review Jev-cu, TypeSafe HTTP/Choice/function-calling docs, Windows-MCP source.
- [x] Define product, threat model, backend constraints and alpha release scope.
- [x] Save architecture, task schema and supported/unsupported capability matrix.

### P1 — implementation
- [x] Immutable observations/candidates, exact-match task scope and verifier.
- [x] TypeSafe transport: fixed HTTPS endpoint, strict output validation, bounded
      retry/deadline/request accounting, no credential forwarding or response logging.
- [x] Policy, freshness checks, single-use action dispatch, bounded runner.
- [x] Native Windows adapter, isolated worker, CLI, offline simulator and examples.

### P2 — evidence
- [x] Offline unit and negative tests; no secrets or cloud calls in CI.
- [x] Native WinForms fixture: scoped observation + input + invoke + independent readback.
- [x] Small live Jev test on synthetic data, separate from deterministic tests.
- [x] Report actual calls, tokens and latency; make no unmeasured speed/accuracy claims.
- [x] Test package install/build, CLI help/demo and lint on this Windows host.

### P3 — release engineering
- [x] English README + Chinese quickstart, security/privacy, contribution guide,
      changelog, MIT license and upstream attribution without copying Jev-cu source.
- [x] Locked dependencies, Windows/Linux offline CI, packaging artifacts and release workflow.
- [x] Secret scan of tracked files/package; exclude .env, local state, private traces.
- [x] Local git commit and reproducible wheel/sdist/checksums.
- [x] Publish public GitHub repo and alpha release after account/repository resolution.
- [x] Inspect remote CI and release assets; record any validation still pending.

Published: https://github.com/Yzywil/jev-windows/releases/tag/v0.1.0a1

Release commit: `95a90498b6993a9b8349a30faf800a28064904b5`.
All five jobs in https://github.com/Yzywil/jev-windows/actions/runs/35487480768 passed.
Downloaded wheel and source archive match their published SHA-256 checksums and
the local build. 103 offline tests passed; native and live proof is in VALIDATION.md.
Future app coverage and beta gates remain explicitly tracked in ROADMAP.md.

## Non-goals for v0.1

Arbitrary software support, OCR/canvas/image grounding, browser DOM automation,
coordinate fallback, admin/elevated apps, secure desktop, credential entry, remote
access, persistence/startup services, arbitrary shell execution, unreviewed destructive
workflows, a guaranteed billing cap, and a hosted service.

## Release gates

If native UIA proof fails, label the backend unverified and do not claim working
desktop control. If GitHub authentication is missing, finish and package locally,
then request login; never include a user's `.env.local` in the repository or release.

## Sources reviewed (2026-09-20)

- https://github.com/Sac-Y/Jev-cu — architectural inspiration only.
- https://github.com/CursorTouch/Windows-MCP/tree/v0.8.5 — pinned UIA dependency.
- https://docs.typesafe.ai/api
- https://docs.typesafe.ai/primitives/choice
- https://docs.typesafe.ai/cookbooks/function_calling
- https://github.com/trycua/cua/tree/main/libs/cua-driver/examples/jev-use
