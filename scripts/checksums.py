import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "dist"
files = sorted(p for p in root.iterdir() if p.suffix in {".whl", ".gz", ".zip"})
if not files:
    raise SystemExit("No package artifacts")
(root / "SHA256SUMS.txt").write_text(
    "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files),
    encoding="utf-8",
)
