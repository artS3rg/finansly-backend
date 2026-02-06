from pydantic import BaseModel
from typing import List, Optional


class AICoachRequest(BaseModel):
    question: str
    context: Optional[dict] = None  # Дополнительный контекст (транзакции, цели и т.д.)


class AICoachResponse(BaseModel):
    answer: str
    suggestions: List[str] = []  # Список рекомендаций
    confidence: float = 0.0  # Уверенность ИИ в ответе (0-1)
