# Task format v1

Task files are trusted, user-authored configuration, not web page instructions.
Unknown fields, duplicate JSON keys, missing assertions and ambiguous selectors
are rejected. Files are capped at 128 KiB. Strings and lists have further bounds.

See `examples/fixture-task.json` for a complete task. Required fields:

- `version`: integer 1.
- `goal`: nonempty natural-language goal (up to 2,000 characters), sent to TypeSafe.
- `executable`: exact executable basename, compared case-insensitively.
- `scope`: nonempty exact selectors for controls that may be acted on.
- `assertions`: nonempty independent end-state conditions.

Optional fields:

- `inputs`: `{"selector": {...}, "value": "caller-supplied text"}`. Text never comes
  from the model; it is tied to that exact control. No automatic clipboard fallback.
- `grants`: `{"selector": {...}, "operation": "invoke"}`. Allows one class of
  operation on that exact control in this task, not all actions in the application.
  Sensitive-looking labels still require an interactive action-time approval.

## Selectors

`name`, `automation_id`, and `role` match exactly, case-sensitively. At least one
nonempty `name` or `automation_id` is required. Role-only and wildcard/regex matching
are not supported. All supplied fields must match. Two matches stop the run.
Names can change with language and app versions; prefer automation IDs when stable.

## Assertions

Each assertion has a `selector`, a `property`, and `equals`:

- `name` / `value`: exact string equality.
- `checked` / `selected`: a JSON boolean.

All assertions must match one visible, non-password element. A missing value,
missing/duplicate element, incomplete tree or mismatched executable is not success.
Do not use a tautological assertion such as “the Apply button exists” when the actual
goal is saving a document. Your verifier is only as meaningful as its assertion.

## Output and exit codes

The runner emits JSONL with redacted action metadata, then a final result.
`--log` exclusively creates a new file and never overwrites an old log.

| Exit | Meaning |
|---|---|
| 0 | `verified`, or successful `dry_run` / read-only command |
| 2 | stopped, abstained, configuration/provider/observation error |
| 3 | single-action human confirmation required or declined |
| 4 | action/readback outcome unknown; inspect before retrying |
| 130 | interrupted; an in-flight action may have occurred |

Automation must check the final JSON `status`, not exit 0 alone: preview is not success.
`steps` counts acknowledged dispatches; `unknown` may include one additional uncertain
dispatch. `requests` includes HTTP attempts and retries. Returned token counts exclude
unreported usage on network failures. Limits are not a dollar spending guarantee.

