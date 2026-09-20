"""CLI entrypoints. Desktop execution and outbound UI sharing are separate opt-ins."""

import argparse
import importlib.metadata
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .contracts import Candidate, JevError, Task
from .demo import DemoProvider, MemoryDriver, demo_task
from .provider import TypeSafeProvider
from .runner import RunConfig, run
from .worker import ProcessDriver


def output(data):
    print(json.dumps(data, ensure_ascii=False, allow_nan=False), flush=True)


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise JevError("duplicate_json_key")
        result[key] = value
    return result


def load_task(path):
    if Path(path).stat().st_size > 131072:
        raise JevError("task_too_large")
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique_keys)
        return Task.parse(raw)
    except (ValueError, UnicodeError):
        raise JevError("invalid_task_json") from None


def human_confirm(candidate: Candidate) -> bool:
    if not sys.stdin.isatty():
        return False
    # Only the local TTY sees the description, not persisted telemetry.
    label = json.dumps(candidate.element.name, ensure_ascii=True)
    print(
        f"Approve one {candidate.operation} action on {label}? Type APPROVE: ",
        end="",
        file=sys.stderr,
        flush=True,
    )
    return input().strip() == "APPROVE"


def parser():
    p = argparse.ArgumentParser(
        prog="jev-windows", description="Supervised, bounded Jev desktop use"
    )
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Report prerequisites without reading secrets or calling APIs")
    sub.add_parser("windows", help="List visible windows locally; no API call")
    snap = sub.add_parser("snapshot", help="Read one window locally; field values withheld")
    snap.add_argument("--window", required=True, type=int)
    snap.add_argument("--executable", required=True)
    sub.add_parser("demo", help="Run an offline simulator; not a real desktop test")
    live = sub.add_parser("run", help="One-window workflow; dry-run unless --execute")
    live.add_argument("--task", required=True)
    live.add_argument("--window", required=True, type=int)
    live.add_argument("--execute", action="store_true")
    live.add_argument(
        "--share-ui",
        action="store_true",
        help="Consent to send scoped UI labels and task goal to TypeSafe",
    )
    live.add_argument("--max-steps", type=int, default=10)
    live.add_argument("--max-calls", type=int, default=20)
    live.add_argument("--seconds", type=float, default=120)
    live.add_argument("--log", help="Create a NEW redacted JSONL log (never overwrite)")
    live.add_argument("--model", default="jev-latest")
    return p


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    log = None
    try:
        if args.command == "doctor":
            try:
                backend = importlib.metadata.version("windows-mcp")
            except importlib.metadata.PackageNotFoundError:
                backend = None
            output(
                {
                    "version": __version__,
                    "python": sys.version.split()[0],
                    "windows": sys.platform == "win32",
                    "backend_version": backend,
                    "backend_version_supported": backend == "0.8.5",
                    "api_key_configured": bool(os.environ.get("TYPESAFE_API_KEY", "").strip()),
                    "network_tested": False,
                    "desktop_tested": False,
                }
            )
            return 0
        if args.command == "demo":
            result = run(
                demo_task(),
                MemoryDriver(),
                DemoProvider(),
                config=RunConfig(execute=True),
                emit=output,
            )
            output({"event": "result", "mode": "offline_simulator", **asdict(result)})
            return 0 if result.status == "verified" else 1
        if args.command == "windows":
            with ProcessDriver() as driver:
                output(driver.windows())
            return 0
        if args.command == "snapshot":
            with ProcessDriver(args.window, args.executable) as driver:
                snapshot = driver.observe()
                output(
                    {
                        "complete": snapshot.complete,
                        "window": asdict(snapshot.window),
                        "elements": [
                            {k: v for k, v in asdict(e).items() if k != "value"}
                            for e in snapshot.elements
                            if not e.password
                        ],
                    }
                )
            return 0
        task = load_task(args.task)
        config = RunConfig(execute=args.execute, max_steps=args.max_steps, seconds=args.seconds)
        if not args.share_ui:
            raise JevError("share_ui_consent_required")
        provider = TypeSafeProvider(model=args.model, max_calls=args.max_calls)
        if args.log:
            log = open(args.log, "x", encoding="utf-8")

        def emit(event):
            output(event)
            if log:
                log.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
                log.flush()

        with ProcessDriver(args.window, task.executable) as driver:
            result = run(task, driver, provider, config=config, confirm=human_confirm, emit=emit)
        emit({"event": "result", **asdict(result)})
        return {"verified": 0, "dry_run": 0, "confirm": 3, "unknown": 4}.get(result.status, 2)
    except JevError as e:
        output({"event": "error", "code": e.code})
        return 2
    except KeyboardInterrupt:
        output({"event": "error", "code": "interrupted_outcome_may_be_unknown"})
        return 130
    except (OSError, ValueError):
        output({"event": "error", "code": "local_file_or_configuration_error"})
        return 2
    finally:
        if log:
            log.close()


if __name__ == "__main__":
    raise SystemExit(main())
