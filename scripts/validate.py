from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print(f"> {' '.join(command)}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    print("SkyData Studio validation")
    print("=" * 28)

    if not compileall.compile_dir(ROOT / "apps" / "api", quiet=1):
        print("Python API compilation failed.", file=sys.stderr)
        return 1
    if not compileall.compile_dir(ROOT / "packages" / "contracts", quiet=1):
        print("Contract package compilation failed.", file=sys.stderr)
        return 1

    run([sys.executable, "-m", "pytest"])
    print("Validation completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
