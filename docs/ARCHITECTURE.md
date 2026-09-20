# Architecture

## Components

`contracts.py` defines frozen snapshots, compound candidates and strict task parsing.
`provider.py` is a small TypeSafe HTTP adapter. `policy.py` contains local grants and
conservative label checks. `runner.py` orchestrates bounded steps. `native.py`
implements scoped UIA access, hosted in `worker.py`'s killable subprocess. `cli.py`
owns consent and the human confirmation channel. The offline simulator is separate.

## Why not just configure another MCP server?

Windows-MCP already supplies a useful Windows UIA implementation. We reuse its
`windows_mcp.uia` module at exactly 0.8.5. Its general server exposes many tools that
are unnecessary here. Importing the UIA layer lets us construct immutable structured
candidates without parsing a human-readable desktop-wide tree or letting a model
choose a shell tool. This is an **internal-library adapter** and must be regression
tested on upgrades. Nothing from Jev-cu was copied into this package.

## Decision optimization

Each option is `(observed element, supported operation, caller argument)`. This
eliminates the invalid combinations possible when independent questions select an
operation and a target. It also reduces the normal logical decision to one Choice
question per step. It does NOT establish a latency/cost improvement over another
project: no comparative benchmark has been run. More candidates cost more tokens.

Only exact scoped controls are eligible. A missing control does not invite a guessed
coordinate. More than 64 candidates, incomplete capture, duplicate refs or ambiguous
selectors stop the run. Disabled, offscreen and protected controls are excluded.

## State machine

1. Read the selected window locally and capture its identity and monotonic time.
2. Evaluate the exact local assertions. Return `verified` only if every one holds.
3. Build eligible candidate actions; ask Jev once (plus bounded transient retries).
4. Validate type, candidate membership, finite probabilities, distribution and confidence.
5. `abstain` stops; `reobserve` is bounded. Default dry-run stops before any action.
6. Check the exact local grant; ask a human for ungranted or sensitive-labeled actions.
7. Check age/deadline, reread the window and require the same fingerprint.
8. The backend rereads again, checks identity and the concrete control, consumes the
   action ID before dispatch, then performs one semantic UIA operation.
9. Read back and evaluate assertions, including after the last allowed step.

Failures during dispatch/readback are `unknown`, not success and not an instruction
to repeat the action. Native worker calls have a 15-second timeout. A blocking
confirmation may exceed the run deadline, but returning from it never permits a
late action. Native calls may overrun the overall deadline by their call timeout;
this is a bounded stop mechanism, not real-time scheduling.

## Known race and trust boundaries

Windows offers no atomic transaction combining arbitrary UIA observation with
invocation. An app can change between the final check and dispatch. We minimize,
not eliminate, that race. A malicious app can forge accessibility metadata. Do not
use this with adversarial apps, unattended sensitive workflows or a compromised OS.

Labels/automation IDs are untrusted data. Prompting and keyword checks are defense
in depth, not a complete prompt-injection defense. Exact user-reviewed task scopes,
grants, strict output validation and no general-purpose command tool bound the
effects. Treat task files as executable intent: review them like scripts.

## Library integration

The portable `run(task, driver, provider, config=...)` accepts adapters implementing
`observe` and `execute`. Native COM access stays in its child process and never
crosses COM objects through IPC. IPC uses a private parent-child pipe, not a network
listener. A fixture/mock provider is never used as fallback after a live error.

