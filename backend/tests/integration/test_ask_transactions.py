"""No transaction is open while the model thinks (B9 review).

On a SQLite file every write transaction takes the database lock (BEGIN IMMEDIATE), so a
question that kept one open during a 25 s model call would block every other writer.
"""

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from salary_api.core.db import create_engine_for_url, create_session_factory
from salary_api.core.permissions import Principal, Role
from salary_api.modules.ask import service
from salary_api.modules.ask.llm import LLMResponse, Message, ToolSpec
from salary_api.modules.ask.schemas import AskRequest
from tests.ask_fakes import FakeLLM, answer, call
from tests.conftest import upgrade_to_head
from tests.factories import make_fx_rates, make_settings, make_user


class _LockProbe(FakeLLM):
    """Tries to take the write lock from another connection during every model call."""

    def __init__(self, path: Path, *script: LLMResponse) -> None:
        super().__init__(*script)
        self.path = path
        self.writes: list[str] = []

    def complete(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> LLMResponse:
        other = sqlite3.connect(self.path, timeout=0.05)
        try:
            other.execute("BEGIN IMMEDIATE")
            other.rollback()
            self.writes.append("ok")
        except sqlite3.OperationalError as error:
            self.writes.append(str(error))
        finally:
            other.close()
        return super().complete(messages, tools)


def test_reproduce_no_write_lock_is_held_during_model_calls(tmp_path: Path) -> None:
    path = tmp_path / "ask.db"
    engine = create_engine_for_url(f"sqlite:///{path}")
    upgrade_to_head(engine)
    sessions = create_session_factory(engine)
    with sessions() as session:
        make_fx_rates(session)
        user = make_user(session, role=Role.HR_MANAGER)
        session.commit()
        principal = Principal(user.id, user.email, user.full_name, user.role)
    llm = _LockProbe(path, call("get_fx_rates"), call("get_fx_rates"), answer("Done."))

    try:
        with sessions() as session:
            response = service.ask(
                session,
                principal,
                AskRequest.model_validate({"messages": [{"role": "user", "content": "Q"}]}),
                llm=llm,
                settings=make_settings(llm_api_key="test-key"),
            )
    finally:
        engine.dispose()

    assert response.answer == "Done."
    assert llm.writes == ["ok", "ok", "ok"]
