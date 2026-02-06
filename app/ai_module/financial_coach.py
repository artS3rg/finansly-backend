"""
Модуль самописного искусственного интеллекта для финансового коуча
Можно заменить на более сложную модель (например, с использованием ML библиотек)
"""

from typing import Dict, List
from app.schemas.ai_coach import AICoachResponse


class FinancialCoach:
    """
    Самописный ИИ финансовый коуч
    Анализирует финансовые данные и дает рекомендации
    """
    
    def __init__(self):
        self.keywords_income = ["доход", "зарплата", "прибыль", "заработать", "получить"]
        self.keywords_expense = ["расход", "трата", "потратить", "экономить", "сэкономить"]
        self.keywords_goal = ["цель", "накопить", "накопление", "сбережения"]
        self.keywords_budget = ["бюджет", "планирование", "план"]
    
    def answer_question(self, question: str, context: Dict) -> AICoachResponse:
        """
        Основной метод для ответа на вопрос пользователя
        """
        question_lower = question.lower()
        
        # Анализ вопроса и контекста
        answer = ""
        suggestions = []
        confidence = 0.7
        
        # Анализ транзакций
        transactions = context.get("transactions", [])
        goals = context.get("goals", [])
        
        # Расчет статистики
        total_income = sum(t.get("amount", 0) for t in transactions if t.get("is_income", False))
        total_expense = sum(t.get("amount", 0) for t in transactions if not t.get("is_income", False))
        balance = total_income - total_expense
        
        # Определение типа вопроса и генерация ответа
        if any(keyword in question_lower for keyword in self.keywords_income):
            answer = self._generate_income_advice(transactions, total_income, balance)
            suggestions = self._generate_income_suggestions(transactions)
            confidence = 0.8
        
        elif any(keyword in question_lower for keyword in self.keywords_expense):
            answer = self._generate_expense_advice(transactions, total_expense, balance)
            suggestions = self._generate_expense_suggestions(transactions)
            confidence = 0.8
        
        elif any(keyword in question_lower for keyword in self.keywords_goal):
            answer = self._generate_goal_advice(goals, balance)
            suggestions = self._generate_goal_suggestions(goals)
            confidence = 0.75
        
        elif any(keyword in question_lower for keyword in self.keywords_budget):
            answer = self._generate_budget_advice(transactions, total_income, total_expense)
            suggestions = self._generate_budget_suggestions(transactions)
            confidence = 0.8
        
        else:
            # Общий анализ
            answer = self._generate_general_advice(transactions, goals, total_income, total_expense, balance)
            suggestions = self._generate_general_suggestions(transactions, goals, balance)
            confidence = 0.7
        
        return AICoachResponse(
            answer=answer,
            suggestions=suggestions,
            confidence=confidence
        )
    
    def _generate_income_advice(self, transactions: List[Dict], total_income: float, balance: float) -> str:
        """Генерация совета по доходам"""
        income_transactions = [t for t in transactions if t.get("is_income", False)]
        
        if not income_transactions:
            return "У вас пока нет записей о доходах. Начните отслеживать свои доходы для лучшего контроля финансов."
        
        avg_income = total_income / len(income_transactions) if income_transactions else 0
        
        answer = f"Ваш общий доход составляет {total_income:.2f} руб. "
        answer += f"Средний доход на транзакцию: {avg_income:.2f} руб. "
        
        if balance < 0:
            answer += "Ваши расходы превышают доходы. Рекомендую пересмотреть свои траты или найти дополнительные источники дохода."
        elif balance > total_income * 0.3:
            answer += "Отличная финансовая дисциплина! Вы откладываете значительную часть дохода."
        else:
            answer += "Старайтесь откладывать хотя бы 10-20% от дохода на непредвиденные расходы и цели."
        
        return answer
    
    def _generate_expense_advice(self, transactions: List[Dict], total_expense: float, balance: float) -> str:
        """Генерация совета по расходам"""
        expense_transactions = [t for t in transactions if not t.get("is_income", False)]
        
        if not expense_transactions:
            return "У вас нет записей о расходах. Начните отслеживать траты для контроля бюджета."
        
        # Анализ по категориям
        categories = {}
        for t in expense_transactions:
            cat = t.get("category", "Другое")
            categories[cat] = categories.get(cat, 0) + t.get("amount", 0)
        
        top_category = max(categories.items(), key=lambda x: x[1]) if categories else None
        
        answer = f"Ваши общие расходы: {total_expense:.2f} руб. "
        
        if top_category:
            answer += f"Больше всего вы тратите на категорию '{top_category[0]}': {top_category[1]:.2f} руб. "
        
        if balance < 0:
            answer += "Ваши расходы превышают доходы! Необходимо сократить траты или увеличить доходы."
        elif total_expense > 0:
            expense_ratio = (total_expense / (total_expense + abs(balance))) * 100 if (total_expense + abs(balance)) > 0 else 0
            if expense_ratio > 80:
                answer += "Вы тратите более 80% дохода. Рекомендую сократить расходы."
            else:
                answer += "Ваши расходы находятся в разумных пределах."
        
        return answer
    
    def _generate_goal_advice(self, goals: List[Dict], balance: float) -> str:
        """Генерация совета по целям"""
        if not goals:
            return "У вас пока нет финансовых целей. Создайте первую цель для мотивации к накоплению!"
        
        active_goals = [g for g in goals if not g.get("is_completed", False)]
        completed_goals = [g for g in goals if g.get("is_completed", False)]
        
        answer = f"У вас {len(active_goals)} активных целей и {len(completed_goals)} завершенных. "
        
        if active_goals:
            total_needed = sum(g.get("finish_amount", 0) - g.get("current_amount", 0) for g in active_goals)
            answer += f"Для достижения всех целей нужно накопить еще {total_needed:.2f} руб. "
            
            if balance > 0:
                answer += f"У вас есть свободные средства ({balance:.2f} руб), которые можно направить на цели."
            else:
                answer += "Рекомендую начать откладывать часть дохода на достижение целей."
        
        return answer
    
    def _generate_budget_advice(self, transactions: List[Dict], total_income: float, total_expense: float) -> str:
        """Генерация совета по бюджету"""
        if total_income == 0:
            return "Начните отслеживать доходы для планирования бюджета."
        
        expense_ratio = (total_expense / total_income * 100) if total_income > 0 else 0
        
        answer = f"Ваш бюджет: доходы {total_income:.2f} руб, расходы {total_expense:.2f} руб. "
        answer += f"Расходы составляют {expense_ratio:.1f}% от доходов. "
        
        if expense_ratio > 90:
            answer += "Критическая ситуация! Расходы почти равны доходам. Необходимо срочно сократить траты."
        elif expense_ratio > 70:
            answer += "Расходы высоки. Рекомендую сократить траты до 60-70% от дохода."
        elif expense_ratio < 50:
            answer += "Отличное управление бюджетом! Вы откладываете значительную часть дохода."
        else:
            answer += "Бюджет в норме. Старайтесь откладывать 20-30% от дохода."
        
        return answer
    
    def _generate_general_advice(self, transactions: List[Dict], goals: List[Dict], 
                                 total_income: float, total_expense: float, balance: float) -> str:
        """Генерация общего совета"""
        answer = f"Анализ ваших финансов:\n"
        answer += f"- Доходы: {total_income:.2f} руб\n"
        answer += f"- Расходы: {total_expense:.2f} руб\n"
        answer += f"- Баланс: {balance:.2f} руб\n"
        answer += f"- Целей: {len(goals)}\n\n"
        
        if balance < 0:
            answer += "⚠️ Ваши расходы превышают доходы. Необходимо пересмотреть бюджет."
        elif balance > total_income * 0.2:
            answer += "✅ Отличная финансовая дисциплина! Продолжайте в том же духе."
        else:
            answer += "💡 Рекомендую откладывать 10-20% от дохода на цели и непредвиденные расходы."
        
        return answer
    
    def _generate_income_suggestions(self, transactions: List[Dict]) -> List[str]:
        """Генерация предложений по доходам"""
        suggestions = []
        
        income_count = sum(1 for t in transactions if t.get("is_income", False))
        if income_count < 5:
            suggestions.append("Добавьте больше записей о доходах для лучшего анализа")
        
        suggestions.append("Рассмотрите возможность создания дополнительных источников дохода")
        suggestions.append("Отслеживайте регулярные доходы (зарплата, подработка)")
        
        return suggestions
    
    def _generate_expense_suggestions(self, transactions: List[Dict]) -> List[str]:
        """Генерация предложений по расходам"""
        suggestions = []
        
        # Анализ категорий
        categories = {}
        for t in transactions:
            if not t.get("is_income", False):
                cat = t.get("category", "Другое")
                categories[cat] = categories.get(cat, 0) + t.get("amount", 0)
        
        if categories:
            top_category = max(categories.items(), key=lambda x: x[1])
            suggestions.append(f"Больше всего трат в категории '{top_category[0]}'. Пересмотрите эти расходы")
        
        suggestions.append("Ведите учет всех расходов для контроля бюджета")
        suggestions.append("Установите лимиты на категории расходов")
        
        return suggestions
    
    def _generate_goal_suggestions(self, goals: List[Dict]) -> List[str]:
        """Генерация предложений по целям"""
        suggestions = []
        
        active_goals = [g for g in goals if not g.get("is_completed", False)]
        if not active_goals:
            suggestions.append("Создайте новую финансовую цель для мотивации")
        else:
            suggestions.append(f"У вас {len(active_goals)} активных целей. Регулярно откладывайте средства")
            suggestions.append("Установите приоритеты между целями")
        
        suggestions.append("Отслеживайте прогресс по целям")
        
        return suggestions
    
    def _generate_budget_suggestions(self, transactions: List[Dict]) -> List[str]:
        """Генерация предложений по бюджету"""
        suggestions = [
            "Составьте месячный бюджет на основе ваших доходов",
            "Используйте правило 50/30/20: 50% на нужды, 30% на желания, 20% на сбережения",
            "Регулярно пересматривайте и корректируйте бюджет"
        ]
        return suggestions
    
    def _generate_general_suggestions(self, transactions: List[Dict], goals: List[Dict], balance: float) -> List[str]:
        """Генерация общих предложений"""
        suggestions = []
        
        if balance < 0:
            suggestions.append("Срочно сократите расходы или найдите дополнительные источники дохода")
        
        if len(goals) == 0:
            suggestions.append("Создайте финансовую цель для мотивации к накоплению")
        
        suggestions.append("Ведите учет всех финансовых операций")
        suggestions.append("Регулярно анализируйте свои траты")
        
        return suggestions
