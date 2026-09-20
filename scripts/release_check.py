"""Focused preflight, not a substitute for a full secret scanner or code review."""

import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
blocked = []
patterns = [
    r"gh[pousr]_[A-Za-z0-9]{30,}",
    r"github_pat_[A-Za-z0-9_]{30,}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"(?m)^TYPESAFE_API_KEY\s*=\s*[^\s#]+",
]
for name in filter(None, names):
    path = Path(name)
    if (path.name.startswith(".env") and path.name != ".env.example") or any(
        part in {".venv", "local", "runs", "__pycache__"} for part in path.parts
    ):
        blocked.append(name)
        continue
    data = (root / name).read_bytes()
    text = data.decode("utf-8", errors="replace")
    if any(re.search(pattern, text) for pattern in patterns):
        blocked.append(name)
if blocked:
    print("Review blocked files (contents intentionally withheld):")
    print("\n".join(blocked))
    raise SystemExit(1)
print(f"Release preflight passed for {len(list(filter(None, names)))} tracked files")
