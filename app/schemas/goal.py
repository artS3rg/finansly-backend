from pydantic import BaseModel
from datetime import datetime


class GoalCreate(BaseModel):
    title: str
    start_amount: float = 0.0
    finish_amount: float
    party_count: int = 1


class GoalUpdate(BaseModel):
    title: str | None = None
    start_amount: float | None = None
    finish_amount: float | None = None
    current_amount: float | None = None
    party_count: int | None = None
    is_completed: bool | None = None


class GoalResponse(BaseModel):
    id: int
    user_id: int
    title: str
    start_amount: float
    finish_amount: float
    current_amount: float
    party_count: int
    created_at: datetime
    completed_at: datetime | None
    is_completed: bool

    class Config:
        from_attributes = True
