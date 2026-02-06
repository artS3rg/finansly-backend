from pydantic import BaseModel
from typing import List, Dict


class CategoryStatistic(BaseModel):
    category: str
    total_amount: float
    transaction_count: int


class PeriodStatistic(BaseModel):
    total_income: float
    total_expense: float
    balance: float
    category_statistics: List[CategoryStatistic]


class AnalyticsResponse(BaseModel):
    current_month: PeriodStatistic
    last_month: PeriodStatistic | None = None
    total_balance: float
    monthly_trend: List[Dict[str, float]]  # [{month: "2025-01", income: 1000, expense: 500}]
