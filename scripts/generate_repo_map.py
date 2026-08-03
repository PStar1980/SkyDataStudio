from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "repository-map.txt"
IGNORED = {".git", ".venv", "node_modules", "dist", "target", "zip", "__pycache__"}


def walk(path: Path, prefix: str = "") -> list[str]:
    entries = sorted(
        [entry for entry in path.iterdir() if entry.name not in IGNORED],
        key=lambda item: (item.is_file(), item.name.lower()),
    )
    lines: list[str] = []
    for index, entry in enumerate(entries):
        branch = "└── " if index == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{branch}{entry.name}")
        if entry.is_dir():
            extension = "    " if index == len(entries) - 1 else "│   "
            lines.extend(walk(entry, prefix + extension))
    return lines


def main() -> None:
    content = "SkyDataStudio\n" + "\n".join(walk(ROOT)) + "\n"
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Repository map written to {OUTPUT}")


if __name__ == "__main__":
    main()
