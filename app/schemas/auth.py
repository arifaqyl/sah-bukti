from pydantic import BaseModel, Field


class AuthSignup(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    business_name: str | None = Field(default=None, max_length=160)


class AuthLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class AuthMe(BaseModel):
    id: int
    email: str
    display_name: str | None = None


class MembershipResponse(BaseModel):
    id: int
    user_id: int
    business_id: int
    role: str
    created_at: str
    business_name: str


class BusinessListItem(BaseModel):
    id: int
    name: str
    owner_whatsapp: str | None = None
    industry: str
    tagline: str | None = None
    theme_color: str | None = None
    role: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthMe


class LogoutResponse(BaseModel):
    ok: bool
