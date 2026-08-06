import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from skydata_studio.db.bootstrap import create_metadata_schema  # noqa: E402
from skydata_studio.db.session import get_engine  # noqa: E402


def main() -> None:
    engine = get_engine()
    create_metadata_schema(engine)
    print("SkyData Studio metadata schema is ready.")
    print(f"Database: {engine.url.render_as_string(hide_password=True)}")


if __name__ == "__main__":
    main()
