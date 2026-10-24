"""Vercel finds the FastAPI app as `app` in backend/index.py (docs/17-deployment.md §3.2)."""

import importlib.util
from pathlib import Path

from fastapi import FastAPI

INDEX = Path(__file__).resolve().parents[2] / "index.py"


def test_the_vercel_entrypoint_exposes_the_fastapi_app() -> None:
    spec = importlib.util.spec_from_file_location("vercel_index", INDEX)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert isinstance(module.app, FastAPI)
