from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str | None
    created_at: datetime
    is_active: bool
    totp_enabled: bool = False

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Ответ POST /login: либо токен, либо запрос второго фактора."""

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    requires_totp: bool = False
    pending_token: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class CompleteTotpLoginRequest(BaseModel):
    pending_token: str
    code: str


class TotpSetupStartResponse(BaseModel):
    secret: str
    otpauth_url: str


class TotpSetupConfirmRequest(BaseModel):
    code: str


class TotpDisableRequest(BaseModel):
    password: str
