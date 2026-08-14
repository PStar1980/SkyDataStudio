from __future__ import annotations

import compileall
import os
import shutil
import socket
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


def validation_environment() -> dict[str, str]:
    environment = os.environ.copy()
    if sys.platform == "win32":
        environment.setdefault("UV_LINK_MODE", "copy")
    return environment


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    display = " ".join(command)
    print(f"\n> {display}", flush=True)
    subprocess.run(
        command,
        cwd=cwd,
        check=True,
        env=validation_environment(),
    )


def compile_python() -> None:
    targets = (
        (ROOT / "apps" / "api", "Python API"),
        (ROOT / "packages" / "contracts", "Contract package"),
    )
    for target, label in targets:
        if not compileall.compile_dir(target, quiet=1):
            raise RuntimeError(f"{label} compilation failed.")


def pytest_command(uv: str) -> list[str]:
    """Run pytest through Python instead of the Windows console launcher.

    Some Windows App Control policies allow the project Python interpreter while
    blocking generated console entry points such as ``pytest.exe``. Executing
    pytest as a module preserves the same test suite while avoiding that launcher.
    """
    return [uv, "run", "python", "-m", "pytest"]


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


def development_service_running(
    *,
    host: str = "127.0.0.1",
    port: int,
) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


def api_dev_server_running() -> bool:
    return development_service_running(port=8100)


def frontend_dev_server_running() -> bool:
    return development_service_running(port=5174)


def ensure_development_servers_stopped() -> None:
    running: list[str] = []
    if api_dev_server_running():
        running.append("FastAPI on port 8100")
    if frontend_dev_server_running():
        running.append("Vite on port 5174")
    if running:
        services = " and ".join(running)
        raise RuntimeError(
            f"SkyData Studio development services are running: {services}. "
            "Stop the API and frontend before validation because uv sync and "
            "npm ci rebuild local dependency environments."
        )


def ensure_frontend_server_stopped() -> None:
    if frontend_dev_server_running():
        raise RuntimeError(
            "SkyData Studio frontend is running on port 5174. "
            "Stop Vite before validation because npm ci rebuilds node_modules."
        )


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

        if sys.platform == "win32" and "UV_LINK_MODE" not in os.environ:
            print("Windows detected; uv subprocesses will use copy mode.")

        ensure_development_servers_stopped()
        sync_python_dependencies(uv)
        compile_python()
        run([uv, "run", "ruff", "check", "."])
        run([uv, "run", "mypy", "apps/api", "packages/contracts"])
        run(pytest_command(uv))

        sync_frontend_dependencies(npm)
        run([npm, "audit", "--audit-level=high"], cwd=WEB_ROOT)
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
