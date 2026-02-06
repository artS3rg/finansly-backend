from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.schemas.analytics import AnalyticsResponse, PeriodStatistic, CategoryStatistic
from app.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение аналитики по финансам"""
    now = datetime.utcnow()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = current_month_start - timedelta(seconds=1)
    
    # Текущий месяц
    current_month_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.created_at >= current_month_start
    ).all()
    
    # Прошлый месяц
    last_month_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.created_at >= last_month_start,
        Transaction.created_at < current_month_start
    ).all()
    
    # Все транзакции для общего баланса
    all_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()
    
    def calculate_statistics(transactions):
        total_income = sum(t.amount for t in transactions if t.is_income)
        total_expense = sum(t.amount for t in transactions if not t.is_income)
        balance = total_income - total_expense
        
        # Статистика по категориям
        category_stats = {}
        for t in transactions:
            if t.category not in category_stats:
                category_stats[t.category] = {"total": 0.0, "count": 0}
            category_stats[t.category]["total"] += t.amount
            category_stats[t.category]["count"] += 1
        
        category_statistics = [
            CategoryStatistic(
                category=cat,
                total_amount=stats["total"],
                transaction_count=stats["count"]
            )
            for cat, stats in category_stats.items()
        ]
        
        return PeriodStatistic(
            total_income=total_income,
            total_expense=total_expense,
            balance=balance,
            category_statistics=category_statistics
        )
    
    current_month_stat = calculate_statistics(current_month_transactions)
    last_month_stat = calculate_statistics(last_month_transactions) if last_month_transactions else None
    
    total_balance = sum(t.amount if t.is_income else -t.amount for t in all_transactions)
    
    # Тренд по месяцам (последние 6 месяцев)
    monthly_trend = []
    for i in range(6):
        month_start = (current_month_start - timedelta(days=30 * i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        
        month_transactions = db.query(Transaction).filter(
            Transaction.user_id == current_user.id,
            Transaction.created_at >= month_start,
            Transaction.created_at <= month_end
        ).all()
        
        month_income = sum(t.amount for t in month_transactions if t.is_income)
        month_expense = sum(t.amount for t in month_transactions if not t.is_income)
        
        monthly_trend.append({
            "month": month_start.strftime("%Y-%m"),
            "income": month_income,
            "expense": month_expense
        })
    
    monthly_trend.reverse()
    
    return AnalyticsResponse(
        current_month=current_month_stat,
        last_month=last_month_stat,
        total_balance=total_balance,
        monthly_trend=monthly_trend
    )
