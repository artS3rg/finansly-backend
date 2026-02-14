from pydantic import BaseModel
from datetime import datetime
from app.schemas.transaction import TransactionResponse
from app.schemas.goal import GoalResponse


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


class PublicProfileResponse(BaseModel):
    """Публичный профиль пользователя для просмотра другими."""
    id: int
    email: str
    username: str | None
    avatar_url: str | None = None
    banner_url: str | None = None
    total_goals: int
    completed_goals: int
    total_transactions: int
    financial_index: int
    last_transaction: TransactionResponse | None = None
    nearest_goal: GoalResponse | None = None


class ProfileUpdate(BaseModel):
    email: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    banner_url: str | None = None
