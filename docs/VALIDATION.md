# Validation record

Date: **2026-09-20**. Development host: Windows 11 build 26200, Python 3.12.10,
Windows-MCP 0.8.5. Evidence below is a small integration check, not a general
desktop benchmark. No private documents or user windows were sent to TypeSafe.

## Offline

- 103 tests passed on the development host.
- Ruff lint and format checks passed.
- Portable simulator: two actions, verified assertion, no API calls.
- Offline coverage across the whole package: 71%; contracts 96%, policy 100%,
  runner 90%, provider 91%. Native/worker paths have separate live fixture checks,
  not full automated offline coverage. Coverage is not a correctness guarantee.
- Task JSON Schema checked against the fixture task.
- Wheel installed into a clean virtual environment with no backend dependencies;
  version and offline simulator passed.

## Native Windows with deterministic decisions

The checked-in WinForms fixture ran under the normal desktop user. The scoped UIA
adapter observed its controls, excluded the protected field, set the Name field to
`Hello Jev 中文`, invoked Apply, and read the result label.

- Result: `verified`, 2 acknowledged actions, 2 mock decisions.
- Runner wall time: 3,297 ms (not including interpreter/worker startup).
- Independent readback: fixture-owned `proof.txt` contained exactly `Hello Jev 中文`.
- A separate Windows observation also showed `Applied: Hello Jev 中文`.
- This proves this fixture's SetValue/Invoke integration, not every app or every UIA pattern.

## Live Jev + native Windows

### Initial attempt — retained failure

The first live design omitted input-progress context. Jev selected SetValue with
0.89 confidence, then the next decision had only 0.23 confidence. The runner
stopped at the unchanged 0.80 confidence gate. One action, two HTTP requests,
1,064 input tokens and 178 output tokens, 3,328 ms.

Fix: provide locally computed booleans saying whether each caller input already
matches. No field text or full UI snapshot was added to the request. The confidence
threshold was **not lowered**.

### Fresh-window retest — passed

- Model returned: `jev-1.13.0`.
- Result: `verified`, 2 acknowledged actions, 2 decisions, 2 HTTP attempts.
- Decisions: SetValue at 0.97 confidence, Invoke at 0.91 confidence.
- Reported usage: 1,221 input tokens, 178 output tokens.
- Runner wall time: 3,796 ms, excluding interpreter/worker startup.
- Independent fixture readback and separate UI observation matched `Hello Jev 中文`.

This is one successful live retest, not a success-rate estimate. No comparative
speed/cost claims against Jev-cu, Windows-MCP agents, or larger language models follow
from this result. Token prices are not hard-coded. API calls can incur charges.

## Not yet validated

Office/WPS/WeChat workflows, browser or Electron app coverage, Windows 10, multiple
monitor/DPI combinations, elevated or secure desktop, remote sessions, ARM Windows,
adversarial accessibility providers, native SelectionItem/Toggle compatibility across
applications, and long multi-step tasks. A pinned dependency does not remove these limits.

## CI

The repository defines Windows/Linux Python 3.12/3.13 offline jobs and a Windows
optional-dependency import/fixture compilation job. These do not operate the CI
desktop or call TypeSafe. Consult the actual GitHub Actions run for remote status;
local validation does not establish that the remote run passed.

The [first remote CI run](https://github.com/Yzywil/jev-windows/actions/runs/35487359154)
passed all five jobs for commit `a81f85c` (94 tests at that commit). Additional
boundary tests subsequently brought the local suite to 103; the release commit's
own CI is the authority for that final revision.
