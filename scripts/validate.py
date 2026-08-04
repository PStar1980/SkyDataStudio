from __future__ import annotations

import compileall
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "apps" / "web"


class ValidationConfigurationError(RuntimeError):
    """Raised when a required local validation tool is unavailable."""


def command_path(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise ValidationConfigurationError(
            f"Required command '{name}' was not found on PATH. "
            f"Install it before running SkyData Studio validation."
        )
    return executable


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    display = " ".join(command)
    print(f"\n> {display}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def compile_python() -> None:
    targets = (
        (ROOT / "apps" / "api", "Python API"),
        (ROOT / "packages" / "contracts", "Contract package"),
    )
    for target, label in targets:
        if not compileall.compile_dir(target, quiet=1):
            raise RuntimeError(f"{label} compilation failed.")


def sync_python_dependencies(uv: str) -> None:
    lock_file = ROOT / "uv.lock"
    command = [uv, "sync", "--dev"]
    if lock_file.exists():
        command.append("--locked")
    else:
        print("No uv.lock found; uv will generate the initial Python lockfile.")
    run(command)

    if not lock_file.exists():
        raise RuntimeError("uv completed without producing uv.lock.")


def sync_frontend_dependencies(npm: str) -> None:
    lock_file = WEB_ROOT / "package-lock.json"
    if lock_file.exists():
        run([npm, "ci"], cwd=WEB_ROOT)
        return

    print("No package-lock.json found; npm will generate the initial frontend lockfile.")
    run([npm, "install"], cwd=WEB_ROOT)
    if not lock_file.exists():
        raise RuntimeError("npm completed without producing package-lock.json.")


def main() -> int:
    print("SkyData Studio validation")
    print("=" * 30)

    try:
        uv = command_path("uv")
        npm = command_path("npm")

        sync_python_dependencies(uv)
        compile_python()
        run([uv, "run", "ruff", "check", "."])
        run([uv, "run", "mypy", "apps/api", "packages/contracts"])
        run([uv, "run", "pytest"])

        sync_frontend_dependencies(npm)
        run([npm, "run", "lint"], cwd=WEB_ROOT)
        run([npm, "run", "build"], cwd=WEB_ROOT)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"\nValidation failed: {error}", file=sys.stderr)
        return 1

    print("\nValidation completed successfully.")
    print("Python and frontend lockfiles are ready for source control.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
