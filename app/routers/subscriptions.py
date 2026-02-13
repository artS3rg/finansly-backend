from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionPayment
from app.models.transaction import Transaction
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse, SubscriptionUpdate
from app.auth import get_current_user
from app.subscription_utils import get_next_payment_date, iter_payment_dates_from_to

router = APIRouter()

SUBSCRIPTIONS_CATEGORY = "Подписки"


def _ensure_subscription_transactions(db: Session, user_id: int) -> None:
    """Создаёт транзакции по подпискам за наступившие даты списания (категория «Подписки»)."""
    today = date.today()
    subscriptions = db.query(Subscription).filter(Subscription.user_id == user_id).all()
    for sub in subscriptions:
        start = sub.created_at.date() if hasattr(sub.created_at, "date") else sub.created_at
        for pay_date in iter_payment_dates_from_to(sub.payment_day, start, today):
            exists = db.query(SubscriptionPayment).filter(
                SubscriptionPayment.subscription_id == sub.id,
                SubscriptionPayment.payment_date == pay_date
            ).first()
            if exists:
                continue
            db.add(SubscriptionPayment(subscription_id=sub.id, payment_date=pay_date))
            tx = Transaction(
                user_id=user_id,
                description=sub.name,
                amount=sub.amount,
                is_income=False,
                category=SUBSCRIPTIONS_CATEGORY,
                created_at=datetime.combine(pay_date, datetime.min.time()),
            )
            db.add(tx)
    db.commit()


def _subscription_to_response(sub: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=sub.id,
        user_id=sub.user_id,
        name=sub.name,
        amount=sub.amount,
        payment_day=sub.payment_day,
        next_payment_date=get_next_payment_date(sub.payment_day),
        created_at=sub.created_at,
    )


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создание новой подписки. payment_day — день месяца списания (1-31)."""
    db_subscription = Subscription(
        user_id=current_user.id,
        name=subscription.name,
        amount=subscription.amount,
        payment_day=subscription.payment_day
    )
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return _subscription_to_response(db_subscription)


@router.get("/", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение списка подписок пользователя. Наступившие даты списания превращаются в транзакции (категория «Подписки»)."""
    _ensure_subscription_transactions(db, current_user.id)
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).order_by(Subscription.payment_day.asc()).all()
    return [_subscription_to_response(s) for s in subscriptions]


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение подписки по ID"""
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    return _subscription_to_response(subscription)


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_update: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление подписки"""
    db_subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    
    if not db_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    update_data = subscription_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_subscription, field, value)
    
    db.commit()
    db.refresh(db_subscription)
    return _subscription_to_response(db_subscription)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удаление подписки"""
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    db.delete(subscription)
    db.commit()
    return None
