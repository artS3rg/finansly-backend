from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.goal import Goal
from app.schemas.ai_coach import AICoachRequest, AICoachResponse
from app.auth import get_current_user
from app.ai_module.financial_coach import FinancialCoach

router = APIRouter()


@router.post("/ask", response_model=AICoachResponse)
async def ask_ai_coach(
    request: AICoachRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Задать вопрос финансовому коучу (ИИ)
    """
    # Получаем контекст пользователя для более точных ответов
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.created_at.desc()).limit(50).all()
    
    goals = db.query(Goal).filter(
        Goal.user_id == current_user.id
    ).all()
    
    # Подготавливаем контекст
    user_context = {
        "user_id": current_user.id,
        "transactions": [
            {
                "description": t.description,
                "amount": t.amount,
                "is_income": t.is_income,
                "category": t.category,
                "date": t.created_at.isoformat()
            }
            for t in transactions
        ],
        "goals": [
            {
                "title": g.title,
                "current_amount": g.current_amount,
                "finish_amount": g.finish_amount,
                "is_completed": g.is_completed
            }
            for g in goals
        ]
    }
    
    # Объединяем контекст из запроса и пользовательский контекст
    full_context = {**(request.context or {}), **user_context}
    
    # Используем модуль ИИ
    coach = FinancialCoach()
    response = coach.answer_question(request.question, full_context)
    
    return response


@router.post("/analyze", response_model=AICoachResponse)
async def analyze_finances(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Автоматический анализ финансов пользователя с рекомендациями
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()
    
    goals = db.query(Goal).filter(
        Goal.user_id == current_user.id
    ).all()
    
    # Формируем запрос для анализа
    total_income = sum(t.amount for t in transactions if t.is_income)
    total_expense = sum(t.amount for t in transactions if not t.is_income)
    
    analysis_question = f"""
    Проанализируй мои финансы:
    - Доходы: {total_income} руб
    - Расходы: {total_expense} руб
    - Баланс: {total_income - total_expense} руб
    - Количество целей: {len(goals)}
    - Завершенных целей: {sum(1 for g in goals if g.is_completed)}
    
    Дай рекомендации по улучшению финансового состояния.
    """
    
    user_context = {
        "transactions": [
            {
                "description": t.description,
                "amount": t.amount,
                "is_income": t.is_income,
                "category": t.category
            }
            for t in transactions[-20:]  # Последние 20 транзакций
        ],
        "goals": [
            {
                "title": g.title,
                "current_amount": g.current_amount,
                "finish_amount": g.finish_amount,
                "progress": (g.current_amount / g.finish_amount * 100) if g.finish_amount > 0 else 0
            }
            for g in goals
        ]
    }
    
    coach = FinancialCoach()
    response = coach.answer_question(analysis_question, user_context)
    
    return response
