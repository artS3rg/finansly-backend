from pydantic import BaseModel, Field
from datetime import date, datetime


class SubscriptionCreate(BaseModel):
    name: str
    amount: float
    payment_day: int = Field(..., ge=1, le=31)


class SubscriptionUpdate(BaseModel):
    name: str | None = None
    amount: float | None = None
    payment_day: int | None = Field(None, ge=1, le=31)


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    name: str
    amount: float
    payment_day: int
    next_payment_date: date
    created_at: datetime

    class Config:
        from_attributes = True
