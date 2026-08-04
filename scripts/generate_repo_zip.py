from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
    "target",
    "zip",
}
IGNORED_SUFFIXES = {".zip", ".patch", ".pyc", ".log", ".png"}
SENSITIVE_NAMES = {".env", ".env.local", ".env.development", ".env.production", ".env.test"}


def include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in IGNORED_DIRS for part in relative.parts):
        return False
    if path.name in SENSITIVE_NAMES:
        return False
    return path.suffix.lower() not in IGNORED_SUFFIXES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", default="SkyDataStudio")
    args = parser.parse_args()

    output_dir = ROOT / "zip"
    output_dir.mkdir(exist_ok=True)
    output = output_dir / f"{args.name}.zip"

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and include(path) and path != output:
                archive.write(path, Path(ROOT.name) / path.relative_to(ROOT))

    print(f"Repository package written to {output}")


if __name__ == "__main__":
    main()
