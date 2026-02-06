from pydantic import BaseModel
from datetime import datetime


class TransactionCreate(BaseModel):
    description: str
    amount: float
    is_income: bool
    category: str


class TransactionUpdate(BaseModel):
    description: str | None = None
    amount: float | None = None
    is_income: bool | None = None
    category: str | None = None


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    description: str
    amount: float
    is_income: bool
    category: str
    created_at: datetime

    class Config:
        from_attributes = True
