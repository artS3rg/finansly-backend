from pydantic import BaseModel
from datetime import date


# Ключи типов заданий (локализация на клиенте)
TASK_TYPE_KEYS = [
    "create_transaction",   # Создайте 1 финансовую операцию
    "create_goal",         # Создайте цель
    "add_income",         # Добавьте доход
    "log_expense",        # Внесите расход
    "complete_goal",      # Выполните цель
    "create_subscription", # Добавьте подписку
]


class DailyTaskResponse(BaseModel):
    id: int
    task_type: str
    completed: bool
    position: int


class BonusStateResponse(BaseModel):
    points: int
    level: int
    progress_to_next: float  # 0.0 .. 1.0
    tasks: list[DailyTaskResponse]
