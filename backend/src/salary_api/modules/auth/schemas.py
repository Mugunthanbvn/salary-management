from pydantic import BaseModel, ConfigDict, Field

from salary_api.core.permissions import Permission, Role


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, max_length=254)
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
