from pydantic import BaseModel
from datetime import datetime


class ProfileResponse(BaseModel):
    id: int
    email: str
    username: str | None
    avatar_url: str | None = None
    banner_url: str | None = None
    created_at: datetime
    total_goals: int
    completed_goals: int
    total_transactions: int
    financial_index: int  # Индекс финансового здоровья


class ProfileUpdate(BaseModel):
    username: str | None = None
    avatar_url: str | None = None
    banner_url: str | None = None
