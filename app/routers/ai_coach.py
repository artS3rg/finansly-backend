from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.goal import Goal
from app.models.subscription import Subscription
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.ai_coach import AICoachRequest, AICoachResponse
from app.ai_module.financial_coach import FinancialCoach, analyze_last_30_days

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
    db: Session = Depends(get_db),
):
    """
    Анализ финансов за последние 30 дней: доходы, расходы по категориям,
    цели и их выполнение, подписки. Возвращает резюме и конкретные советы
    по сокращению расходов (в т.ч. через ИИ, если задан OPENAI_API_KEY).
    """
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30)

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.created_at >= since,
        )
        .order_by(Transaction.created_at.desc())
        .all()
    )

    goals = (
        db.query(Goal)
        .filter(Goal.user_id == current_user.id)
        .all()
    )

    subscriptions = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .all()
    )

    total_income = sum(t.amount for t in transactions if t.is_income)
    total_expense = sum(t.amount for t in transactions if not t.is_income)

    # Расходы по категориям (только расходы)
    expense_by_category: dict[str, float] = {}
    for t in transactions:
        if not t.is_income:
            expense_by_category[t.category] = expense_by_category.get(t.category, 0) + t.amount
    expense_by_category_list = [
        {"category": k, "amount": v}
        for k, v in sorted(expense_by_category.items(), key=lambda x: -x[1])
    ]

    context_30_days = {
        "total_income": total_income,
        "total_expense": total_expense,
        "expense_by_category": expense_by_category_list,
        "transactions": [
            {
                "description": t.description,
                "amount": t.amount,
                "is_income": t.is_income,
                "category": t.category,
                "date": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ],
        "goals": [
            {
                "title": g.title,
                "current_amount": g.current_amount,
                "finish_amount": g.finish_amount,
                "is_completed": g.is_completed,
            }
            for g in goals
        ],
        "subscriptions": [
            {"name": s.name, "amount": s.amount, "payment_day": s.payment_day}
            for s in subscriptions
        ],
    }

    return analyze_last_30_days(context_30_days)
