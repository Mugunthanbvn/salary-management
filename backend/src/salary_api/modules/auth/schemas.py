from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from salary_api.core.permissions import Permission, Role

# Emails are stored and compared trimmed and lowercased (docs/06-data-model.md section 4.1).
NormalisedEmail = Annotated[
    str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=254)
]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalisedEmail
    # Capped so a huge body cannot make argon2 work for long.
    password: str = Field(min_length=1, max_length=1024)


class SessionUser(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role


class LoginResponse(BaseModel):
    """The signed-in user and the permissions of their current role."""

    user: SessionUser
    permissions: list[Permission]


class Features(BaseModel):
    """Optional features. `ask` is false when no LLM_API_KEY is configured."""

    ask: bool


class MeResponse(LoginResponse):
    features: Features
