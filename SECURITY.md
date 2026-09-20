# Security and privacy

This is an **alpha supervised automation tool**, not a security sandbox. Use a
normal user session and disposable documents. Do not use it for financial,
credential, medical, legal, destructive, or other high-impact workflows.

## Data flow

- Local: selected-window UIA controls, including non-password values for change
  detection and verification. Protected controls' names/values/subtrees are excluded.
- To `https://api.typesafe.ai/v1/systemone`: task goal, executable name, scoped
  candidate labels, automation IDs, roles, operation descriptions and boolean
  progress (whether a supplied input already matches). User input
  arguments are represented by an index, not their text. The goal itself may include
  text you supplied. Labels can contain sensitive data. `--share-ui` is explicit consent.
- API key: sent only as a bearer header to that fixed HTTPS endpoint. Redirects are
  rejected. Normal TLS verification remains enabled. Never paste keys into issues.
- Logs: choices, operation types, counts, model identity, durations and stop reasons.
  No raw UI trees, field values, task goal, response body or credentials are logged.
  `snapshot` is a local inspection command: its displayed labels may be private.

No local HTTP server, remote-control listener, autorun task, clipboard fallback,
shell/registry action, screenshot capture or screenshot transmission is implemented.
The optional backend has transitive dependencies; we import only its UIA module,
not the Windows-MCP server or telemetry entrypoints.

## Limits

- Model confidence is not correctness, consent or authorization.
- The sensitive-label heuristic is incomplete (languages, aliases, misleading labels).
  Exact grants are explicit user permission, not a judgment that an action is harmless.
- A malicious app can lie through its accessibility provider. UIA has no atomic
  observation-and-action transaction. Freshness checks reduce but do not eliminate races.
- Task files are trusted action configuration. Review downloaded tasks before use.
- Password detection depends on the app correctly marking its control. Other private
  content can appear in names. Do not select confidential windows for live inference.
- A process timeout can stop waiting, not undo an action already delivered.
- A compromised dependency/OS or user sharing the session is outside this threat model.
- No automatic retries after native dispatch or ambiguous network outcomes.

## Reporting

Use GitHub's private vulnerability reporting when enabled on the repository. If it
is unavailable, open an issue requesting a private channel **without exploit details,
private window contents or credentials**. Do not publish secrets in reproduction logs.
Only the latest alpha is maintained; no security support SLA is offered.
