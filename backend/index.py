"""Vercel entrypoint: Vercel looks for a FastAPI instance named `app` in index.py.

The real app lives in src/salary_api (src layout), so put src/ on the import path first.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from salary_api.main import app

__all__ = ["app"]
