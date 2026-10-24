"""POST /ask (docs/07-api-spec.md section 12)."""

from salary_api.core.config import Settings
from salary_api.modules.ask.llm import LLMClient


def get_llm_client(settings: Settings) -> LLMClient:
    raise NotImplementedError
