"""Write the API's OpenAPI document to a file without starting a server.

Usage: `python -m salary_api.openapi ../frontend/openapi.json` (run by `make api-sync`).
Keys are sorted and indented, so the committed file only changes when the API does.
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from salary_api.main import app


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("path", type=Path, help="where to write openapi.json")
    path: Path = parser.parse_args(argv).path

    document = json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(document + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
