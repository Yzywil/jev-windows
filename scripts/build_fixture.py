"""Compile only the checked-in fixture using the Windows .NET Framework compiler."""

import os
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    compiler = Path(os.environ.get("WINDIR", "C:/Windows")) / (
        "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    )
    if not compiler.is_file():
        raise SystemExit("Windows .NET Framework 4.x compiler required")
    dest = root / "local" / "fixture.exe"
    dest.parent.mkdir(exist_ok=True)
    subprocess.run(
        [
            str(compiler),
            "/nologo",
            "/target:winexe",
            f"/out:{dest}",
            "/r:System.Windows.Forms.dll",
            "/r:System.Drawing.dll",
            str(root / "examples" / "Fixture.cs"),
        ],
        check=True,
    )
    print(dest)


if __name__ == "__main__":
    main()
