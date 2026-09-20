"""Explicit opt-in native fixture test. Never collected by pytest/CI."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from jev_windows.cli import load_task
from jev_windows.demo import DemoProvider
from jev_windows.runner import RunConfig, run
from jev_windows.worker import ProcessDriver


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", type=int, required=True)
    args = parser.parse_args()
    task = load_task(Path(__file__).resolve().parents[1] / "examples/fixture-task.json")
    with ProcessDriver(args.window, "fixture.exe") as driver:
        result = run(task, driver, DemoProvider(), config=RunConfig(execute=True, max_steps=3))
    print(json.dumps({"mode": "native_mock", **asdict(result)}, ensure_ascii=False))
    return 0 if result.status == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
