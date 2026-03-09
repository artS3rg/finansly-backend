"""
Финансовый коуч на базе LLM (OpenAI) с fallback на правило-ориентированную логику.
Анализирует данные за последние 30 дней и выдаёт конкретные советы по сокращению расходов.
"""

import json
import os
import re
from typing import Any, Dict, List

from app.schemas.ai_coach import AICoachResponse


def _build_30day_summary(context: Dict[str, Any]) -> str:
    """Собирает текстовую сводку для промпта из контекста за 30 дней."""
    lines = []

    total_income = context.get("total_income") or 0
    total_expense = context.get("total_expense") or 0
    balance = total_income - total_expense
    lines.append(f"Доходы за 30 дней: {total_income:.2f} руб.")
    lines.append(f"Расходы за 30 дней: {total_expense:.2f} руб.")
    lines.append(f"Баланс: {balance:.2f} руб.")

    by_category = context.get("expense_by_category") or []
    if by_category:
        lines.append("\nРасходы по категориям (руб.):")
        for cat in by_category[:15]:
            name = cat.get("category", "Без категории")
            amount = cat.get("amount", 0)
            lines.append(f"  - {name}: {amount:.2f}")

    transactions = context.get("transactions") or []
    if transactions:
        lines.append("\nПоследние траты (описание, сумма, категория):")
        for t in transactions[:40]:
            desc = (t.get("description") or "").strip() or "—"
            amount = t.get("amount", 0)
            cat = t.get("category", "—")
            kind = "доход" if t.get("is_income") else "расход"
            lines.append(f"  - {desc}: {amount:.2f} руб. ({cat}, {kind})")

    goals = context.get("goals") or []
    if goals:
        lines.append("\nЦели:")
        for g in goals:
            title = g.get("title", "—")
            current = g.get("current_amount", 0)
            finish = g.get("finish_amount", 0)
            done = "выполнена" if g.get("is_completed") else "в процессе"
            if finish and finish > 0:
                pct = round(100 * current / finish, 1)
                lines.append(f"  - {title}: {current:.2f} / {finish:.2f} руб. ({pct}%), {done}")
            else:
                lines.append(f"  - {title}: {current:.2f} руб., {done}")

    subscriptions = context.get("subscriptions") or []
    if subscriptions:
        lines.append("\nПодписки (ежемесячно):")
        for s in subscriptions:
            name = s.get("name", "—")
            amount = s.get("amount", 0)
            lines.append(f"  - {name}: {amount:.2f} руб./мес.")

    return "\n".join(lines)


def _call_openai(user_text: str, system_prompt: str) -> str | None:
    """Вызов OpenAI Chat Completions. Возвращает content или None при ошибке/отсутствии ключа."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            temperature=0.5,
            max_tokens=2000,
        )
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
    except Exception:
        pass
    return None


SYSTEM_PROMPT = """Ты — финансовый коуч. Тебе даны данные пользователя за последние 30 дней: доходы, расходы по категориям, список трат, цели накопления и подписки.

Твоя задача:
1. Кратко резюмировать ситуацию (2–4 предложения): как идут дела с деньгами, где основные траты, как продвигаются цели.
2. Дам 5–8 конкретных советов по сокращению расходов. Советы должны быть прикладными и персональными, опираясь на реальные категории и траты пользователя.

Примеры формата советов:
- "Попробуйте пить кофе через день — за месяц можно сэкономить заметную сумму."
- "Больше всего расходов в категории «Продукты» — планируйте покупки по списку и не ходите в магазин голодным."
- "Подписка на X стоит N руб./мес. — оцените, пользуетесь ли вы ей каждый месяц."

Ответь строго в формате JSON с двумя полями:
- "answer": строка с кратким резюме (без списков, просто текст).
- "suggestions": массив строк, каждая строка — один конкретный совет (без нумерации и буллетов в начале).

Пиши только валидный JSON, без markdown и комментариев."""


def _parse_llm_response(raw: str) -> AICoachResponse | None:
    """Парсит ответ LLM в AICoachResponse."""
    raw = raw.strip()
    # Убрать обёртку в ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        raw = m.group(1).strip()
    try:
        data = json.loads(raw)
        answer = data.get("answer") or "Нет текста от модели."
        suggestions = data.get("suggestions")
        if not isinstance(suggestions, list):
            suggestions = []
        suggestions = [str(s).strip() for s in suggestions if s]
        return AICoachResponse(
            answer=answer,
            suggestions=suggestions,
            confidence=0.85,
        )
    except (json.JSONDecodeError, TypeError):
        return None


def analyze_last_30_days(context_30_days: Dict[str, Any]) -> AICoachResponse:
    """
    Анализ финансов за последние 30 дней с выдачей советов.
    Использует OpenAI, если задан OPENAI_API_KEY; иначе — правило-ориентированный fallback.
    """
    summary = _build_30day_summary(context_30_days)
    user_text = "Данные пользователя за последние 30 дней:\n\n" + summary

    raw = _call_openai(user_text, SYSTEM_PROMPT)
    if raw:
        parsed = _parse_llm_response(raw)
        if parsed:
            return parsed

    # Fallback: правило-ориентированная логика
    return _fallback_analyze(context_30_days)


def _fallback_analyze(context: Dict[str, Any]) -> AICoachResponse:
    """Правило-ориентированный анализ при отсутствии или ошибке LLM."""
    total_income = context.get("total_income") or 0
    total_expense = context.get("total_expense") or 0
    balance = total_income - total_expense
    expense_by_category = context.get("expense_by_category") or []
    goals = context.get("goals") or []
    subscriptions = context.get("subscriptions") or []

    parts = []
    parts.append(f"За последние 30 дней доходы: {total_income:.2f} руб., расходы: {total_expense:.2f} руб.")
    if balance >= 0:
        parts.append(f"Баланс положительный: {balance:.2f} руб.")
    else:
        parts.append(f"Расходы превышают доходы на {abs(balance):.2f} руб. Стоит сократить траты или увеличить доходы.")

    suggestions: List[str] = []

    if expense_by_category:
        top = expense_by_category[0]
        cat_name = top.get("category", "расходы")
        amount = top.get("amount", 0)
        suggestions.append(
            f"Больше всего расходов в категории «{cat_name}» ({amount:.2f} руб.) — пересмотрите траты в этой категории."
        )
    if total_expense > 0 and total_income > 0:
        ratio = total_expense / total_income
        if ratio > 0.8:
            suggestions.append("Расходы составляют более 80% дохода. Попробуйте откладывать 10–20% и сократить необязательные траты.")
    if subscriptions:
        total_sub = sum(s.get("amount", 0) for s in subscriptions)
        suggestions.append(f"Подписки отнимают {total_sub:.2f} руб./мес. — отмените те, которыми редко пользуетесь.")
    completed_goals = sum(1 for g in goals if g.get("is_completed"))
    active_goals = [g for g in goals if not g.get("is_completed")]
    if active_goals:
        suggestions.append(f"У вас {len(active_goals)} активных целей. Откладывайте понемногу каждый месяц.")
    if completed_goals and not suggestions:
        suggestions.append("Отличная динамика по целям. Можно поставить новую цель накопления.")

    if not suggestions:
        suggestions.append("Ведите учёт трат по категориям — так проще найти, где сократить расходы.")

    return AICoachResponse(
        answer=" ".join(parts),
        suggestions=suggestions,
        confidence=0.7,
    )


class FinancialCoach:
    """
    Коуч с поддержкой произвольного вопроса (answer_question) и анализа за 30 дней (через analyze_last_30_days).
    """

    def __init__(self) -> None:
        self.keywords_income = ["доход", "зарплата", "прибыль", "заработать", "получить"]
        self.keywords_expense = ["расход", "трата", "потратить", "экономить", "сэкономить"]
        self.keywords_goal = ["цель", "накопить", "накопление", "сбережения"]
        self.keywords_budget = ["бюджет", "планирование", "план"]

    def answer_question(self, question: str, context: Dict[str, Any]) -> AICoachResponse:
        """
        Ответ на произвольный вопрос пользователя (старая логика для /ask).
        Для автоматического анализа за 30 дней используйте analyze_last_30_days().
        """
        question_lower = question.lower()
        transactions = context.get("transactions", [])
        goals = context.get("goals", [])
        total_income = sum(t.get("amount", 0) for t in transactions if t.get("is_income", False))
        total_expense = sum(t.get("amount", 0) for t in transactions if not t.get("is_income", False))
        balance = total_income - total_expense

        if any(k in question_lower for k in self.keywords_income):
            answer = self._generate_income_advice(transactions, total_income, balance)
            suggestions = self._generate_income_suggestions(transactions)
            confidence = 0.8
        elif any(k in question_lower for k in self.keywords_expense):
            answer = self._generate_expense_advice(transactions, total_expense, balance)
            suggestions = self._generate_expense_suggestions(transactions)
            confidence = 0.8
        elif any(k in question_lower for k in self.keywords_goal):
            answer = self._generate_goal_advice(goals, balance)
            suggestions = self._generate_goal_suggestions(goals)
            confidence = 0.75
        elif any(k in question_lower for k in self.keywords_budget):
            answer = self._generate_budget_advice(transactions, total_income, total_expense)
            suggestions = self._generate_budget_suggestions(transactions)
            confidence = 0.8
        else:
            answer = self._generate_general_advice(transactions, goals, total_income, total_expense, balance)
            suggestions = self._generate_general_suggestions(transactions, goals, balance)
            confidence = 0.7

        return AICoachResponse(answer=answer, suggestions=suggestions, confidence=confidence)

    def _generate_income_advice(
        self, transactions: List[Dict], total_income: float, balance: float
    ) -> str:
        income_t = [t for t in transactions if t.get("is_income", False)]
        if not income_t:
            return "У вас пока нет записей о доходах. Начните отслеживать доходы для лучшего контроля."
        avg = total_income / len(income_t)
        s = f"Общий доход: {total_income:.2f} руб., в среднем на запись: {avg:.2f} руб. "
        if balance < 0:
            s += "Расходы превышают доходы — пересмотрите траты или ищите доп. доходы."
        elif balance > total_income * 0.3:
            s += "Хорошая дисциплина: значимая часть дохода откладывается."
        else:
            s += "Старайтесь откладывать 10–20% дохода на цели и непредвиденные расходы."
        return s

    def _generate_expense_advice(
        self, transactions: List[Dict], total_expense: float, balance: float
    ) -> str:
        expense_t = [t for t in transactions if not t.get("is_income", False)]
        if not expense_t:
            return "Нет записей о расходах. Начните учитывать траты для контроля бюджета."
        categories: Dict[str, float] = {}
        for t in expense_t:
            cat = t.get("category", "Другое")
            categories[cat] = categories.get(cat, 0) + t.get("amount", 0)
        top = max(categories.items(), key=lambda x: x[1]) if categories else None
        s = f"Общие расходы: {total_expense:.2f} руб. "
        if top:
            s += f"Больше всего в категории «{top[0]}»: {top[1]:.2f} руб. "
        if balance < 0:
            s += "Расходы превышают доходы — нужно сократить траты или увеличить доходы."
        return s

    def _generate_goal_advice(self, goals: List[Dict], balance: float) -> str:
        if not goals:
            return "Нет финансовых целей. Создайте цель — это мотивирует к накоплению."
        active = [g for g in goals if not g.get("is_completed", False)]
        completed = [g for g in goals if g.get("is_completed", False)]
        s = f"Активных целей: {len(active)}, завершённых: {len(completed)}. "
        if active:
            need = sum(
                g.get("finish_amount", 0) - g.get("current_amount", 0)
                for g in active
            )
            s += f"До достижения всех целей осталось накопить {need:.2f} руб. "
            if balance > 0:
                s += f"Свободных средств {balance:.2f} руб. — можно направить часть на цели."
        return s

    def _generate_budget_advice(
        self,
        transactions: List[Dict],
        total_income: float,
        total_expense: float,
    ) -> str:
        if total_income <= 0:
            return "Начните учитывать доходы для планирования бюджета."
        ratio = (total_expense / total_income) * 100
        s = f"Доходы {total_income:.2f} руб., расходы {total_expense:.2f} руб. ({ratio:.1f}% от дохода). "
        if ratio > 90:
            s += "Критично: расходы почти равны доходам. Срочно сокращайте траты."
        elif ratio > 70:
            s += "Расходы высоки. Цель — снизить до 60–70% дохода."
        elif ratio < 50:
            s += "Хорошее управление бюджетом."
        else:
            s += "Старайтесь откладывать 20–30% дохода."
        return s

    def _generate_general_advice(
        self,
        transactions: List[Dict],
        goals: List[Dict],
        total_income: float,
        total_expense: float,
        balance: float,
    ) -> str:
        s = f"Доходы: {total_income:.2f} руб., расходы: {total_expense:.2f} руб., баланс: {balance:.2f} руб. Целей: {len(goals)}. "
        if balance < 0:
            s += "Расходы превышают доходы — пересмотрите бюджет."
        elif balance > total_income * 0.2:
            s += "Финансовая дисциплина в порядке."
        else:
            s += "Рекомендуется откладывать 10–20% дохода."
        return s

    def _generate_income_suggestions(self, transactions: List[Dict]) -> List[str]:
        return [
            "Добавьте больше записей о доходах для анализа",
            "Рассмотрите дополнительные источники дохода",
            "Отслеживайте регулярные доходы (зарплата, подработка)",
        ]

    def _generate_expense_suggestions(self, transactions: List[Dict]) -> List[str]:
        suggestions = []
        categories: Dict[str, float] = {}
        for t in transactions:
            if not t.get("is_income", False):
                cat = t.get("category", "Другое")
                categories[cat] = categories.get(cat, 0) + t.get("amount", 0)
        if categories:
            top = max(categories.items(), key=lambda x: x[1])
            suggestions.append(f"Больше всего трат в категории «{top[0]}» — пересмотрите эти расходы.")
        suggestions.append("Ведите учёт всех расходов и ставьте лимиты по категориям.")
        return suggestions

    def _generate_goal_suggestions(self, goals: List[Dict]) -> List[str]:
        active = [g for g in goals if not g.get("is_completed", False)]
        if not active:
            return ["Создайте новую финансовую цель для мотивации."]
        return [
            f"У вас {len(active)} активных целей — откладывайте регулярно",
            "Расставьте приоритеты между целями",
            "Отслеживайте прогресс по целям",
        ]

    def _generate_budget_suggestions(self, transactions: List[Dict]) -> List[str]:
        return [
            "Составьте месячный бюджет по доходам",
            "Правило 50/30/20: 50% нужды, 30% желания, 20% сбережения",
            "Регулярно пересматривайте бюджет",
        ]

    def _generate_general_suggestions(
        self, transactions: List[Dict], goals: List[Dict], balance: float
    ) -> List[str]:
        suggestions = []
        if balance < 0:
            suggestions.append("Сократите расходы или найдите доп. доходы.")
        if not goals:
            suggestions.append("Создайте финансовую цель.")
        suggestions.append("Ведите учёт операций и анализируйте траты.")
        return suggestions
