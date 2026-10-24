"""Run the Ask eval set against a real LLM (docs/10 section 11). Manual; never in CI."""

from pathlib import Path
from typing import Any

from salary_api.modules.ask.schemas import AskResponse


def load_cases(path: Path) -> list[dict[str, Any]]:
    raise NotImplementedError


def missing_key_message(api_key: str) -> str | None:
    raise NotImplementedError


def score(expect: dict[str, Any], response: AskResponse) -> list[Any]:
    raise NotImplementedError
