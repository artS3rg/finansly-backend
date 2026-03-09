import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.user_bonus import UserBonus
from app.models.goal import Goal
from app.models.subscription import Subscription
from app.models.transaction import Transaction
from app.schemas.profile import ProfileResponse, ProfileUpdate, PublicProfileResponse
from app.schemas.transaction import TransactionResponse
from app.schemas.goal import GoalResponse
from app.auth import get_current_user

router = APIRouter()

# --- Индекс финансового здоровья (0–100): учитывает доходы, расходы, цели, подписки, сбережения ---


def _compute_financial_index(
    *,
    total_income: float,
    total_expense: float,
    total_transactions: int,
    total_goals: int,
    completed_goals: int,
    active_goals_with_progress: int,
    subscriptions_monthly_sum: float,
    subscriptions_count: int,
) -> int:
    """
    Индекс от 0 до 100: насколько разумно ведутся финансы.
    100 = учёт ведётся, расходы под контролем, есть цели и сбережения.
    """
    score = 0.0

    # 1. Баланс доход/расход (макс 30)
    if total_income > 0:
        ratio = total_expense / total_income
        if ratio <= 0.5:
            score += 30
        elif ratio <= 0.7:
            score += 25
        elif ratio <= 0.85:
            score += 20
        elif ratio <= 1.0:
            score += 10
        # ratio > 1 → 0
    # нет дохода — 0 за этот блок

    # 2. Активность учёта (макс 25): есть и доходы, и расходы, достаточное число операций
    has_income = total_income > 0
    has_expense = total_expense > 0
    if has_income:
        score += 5
    if has_expense:
        score += 5
    if total_transactions >= 20:
        score += 15
    elif total_transactions >= 10:
        score += 10
    elif total_transactions >= 5:
        score += 5

    # 3. Цели (макс 25): есть цели, часть выполнена, есть прогресс по активным
    if total_goals > 0:
        score += 5
    if completed_goals >= 3:
        score += 15
    elif completed_goals >= 2:
        score += 10
    elif completed_goals >= 1:
        score += 5
    if active_goals_with_progress > 0:
        score += 5

    # 4. Подписки под контролем (макс 10)
    if subscriptions_count == 0:
        score += 10
    elif total_income > 0:
        sub_ratio = subscriptions_monthly_sum / total_income
        if sub_ratio < 0.1:
            score += 10
        elif sub_ratio < 0.2:
            score += 7
        elif sub_ratio < 0.3:
            score += 4

    # 5. Сбережения (макс 10): положительный баланс и доля от дохода
    if total_income > 0:
        balance = total_income - total_expense
        if balance > 0:
            savings_rate = balance / total_income
            if savings_rate >= 0.2:
                score += 10
            elif savings_rate >= 0.1:
                score += 6
            else:
                score += 3

    return min(100, max(0, int(round(score))))


# Папка для загруженных файлов (относительно рабочей директории при запуске)
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
AVATARS_DIR = UPLOAD_DIR / "avatars"
BANNERS_DIR = UPLOAD_DIR / "banners"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _ensure_upload_dirs():
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    BANNERS_DIR.mkdir(parents=True, exist_ok=True)


def _save_upload(file: UploadFile, dest_dir: Path, prefix: str) -> str:
    """Сохраняет файл и возвращает URL-путь для сохранения в БД (например /static/avatars/1_xxx.jpg)."""
    _ensure_upload_dirs()
    ext = Path(file.filename or "").suffix.lower() or ".jpg"
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = ".jpg"
    name = f"{prefix}_{uuid.uuid4().hex[:8]}{ext}"
    path = dest_dir / name
    with path.open("wb") as f:
        content = file.file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 5 МБ)")
        f.write(content)
    # URL-путь для отдачи через StaticFiles (mount на /static, директория uploads)
    return f"/static/{dest_dir.name}/{name}"


@router.get("/", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получение профиля пользователя со статистикой"""
    return _profile_response(current_user, db)


@router.get("/{user_id}", response_model=PublicProfileResponse)
async def get_public_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Публичный профиль пользователя: аватар, баннер, статистика, последняя транзакция, ближайшая цель."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return _public_profile_response(user, db)


@router.post("/avatar", response_model=ProfileResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Загрузка аватарки пользователя. Сохраняется на сервер и URL записывается в профиль."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Нужно изображение (image/*)")
    try:
        url_path = _save_upload(file, AVATARS_DIR, str(current_user.id))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения файла: {e}")
    current_user.avatar_url = url_path
    db.commit()
    db.refresh(current_user)
    return _profile_response(current_user, db)


@router.post("/banner", response_model=ProfileResponse)
async def upload_banner(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Загрузка баннера пользователя. Сохраняется на сервер и URL записывается в профиль."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Нужно изображение (image/*)")
    try:
        url_path = _save_upload(file, BANNERS_DIR, str(current_user.id))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения файла: {e}")
    current_user.banner_url = url_path
    db.commit()
    db.refresh(current_user)
    return _profile_response(current_user, db)


def _profile_response(current_user: User, db: Session) -> ProfileResponse:
    """Формирует ProfileResponse со статистикой для текущего пользователя."""
    goals = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    total_goals = len(goals)
    completed_goals = sum(1 for g in goals if g.is_completed)
    active_goals_with_progress = sum(
        1 for g in goals
        if not g.is_completed and g.current_amount > g.start_amount
    )
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()
    total_transactions = len(transactions)
    total_income = sum(t.amount for t in transactions if t.is_income)
    total_expense = sum(t.amount for t in transactions if not t.is_income)
    subs = db.query(Subscription).filter(Subscription.user_id == current_user.id).all()
    subscriptions_count = len(subs)
    subscriptions_monthly_sum = sum(s.amount for s in subs)
    financial_index = _compute_financial_index(
        total_income=total_income,
        total_expense=total_expense,
        total_transactions=total_transactions,
        total_goals=total_goals,
        completed_goals=completed_goals,
        active_goals_with_progress=active_goals_with_progress,
        subscriptions_monthly_sum=subscriptions_monthly_sum,
        subscriptions_count=subscriptions_count,
    )
    bonus_row = db.query(UserBonus).filter(UserBonus.user_id == current_user.id).first()
    bonus_points = bonus_row.points if bonus_row else 0
    level = (bonus_points // 100) + 1
    return ProfileResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        avatar_url=current_user.avatar_url,
        banner_url=current_user.banner_url,
        created_at=current_user.created_at,
        total_goals=total_goals,
        completed_goals=completed_goals,
        total_transactions=total_transactions,
        financial_index=financial_index,
        bonus_points=bonus_points,
        level=level,
    )


def _public_profile_response(user: User, db: Session) -> PublicProfileResponse:
    """Формирует публичный профиль пользователя с последней транзакцией и ближайшей целью."""
    goals = db.query(Goal).filter(Goal.user_id == user.id).all()
    total_goals = len(goals)
    completed_goals = sum(1 for g in goals if g.is_completed)
    active_goals_with_progress = sum(
        1 for g in goals
        if not g.is_completed and g.current_amount > g.start_amount
    )
    transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    total_transactions = len(transactions)
    total_income = sum(t.amount for t in transactions if t.is_income)
    total_expense = sum(t.amount for t in transactions if not t.is_income)
    subs = db.query(Subscription).filter(Subscription.user_id == user.id).all()
    subscriptions_count = len(subs)
    subscriptions_monthly_sum = sum(s.amount for s in subs)
    financial_index = _compute_financial_index(
        total_income=total_income,
        total_expense=total_expense,
        total_transactions=total_transactions,
        total_goals=total_goals,
        completed_goals=completed_goals,
        active_goals_with_progress=active_goals_with_progress,
        subscriptions_monthly_sum=subscriptions_monthly_sum,
        subscriptions_count=subscriptions_count,
    )
    last_tx = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .first()
    )
    last_transaction = (
        TransactionResponse.model_validate(last_tx) if last_tx else None
    )
    active_goals = (
        db.query(Goal)
        .filter(Goal.user_id == user.id, Goal.is_completed == False)
        .order_by(Goal.created_at.desc())
        .all()
    )
    nearest_goal = None
    if active_goals:
        def progress(g):
            r = g.finish_amount - g.start_amount
            if r <= 0:
                return 1.0
            return (g.current_amount - g.start_amount) / r
        nearest_goal_obj = max(active_goals, key=progress)
        nearest_goal = GoalResponse(
            id=nearest_goal_obj.id,
            user_id=nearest_goal_obj.user_id,
            title=nearest_goal_obj.title,
            start_amount=nearest_goal_obj.start_amount,
            finish_amount=nearest_goal_obj.finish_amount,
            current_amount=nearest_goal_obj.current_amount,
            party_count=nearest_goal_obj.party_count,
            created_at=nearest_goal_obj.created_at,
            completed_at=nearest_goal_obj.completed_at,
            is_completed=nearest_goal_obj.is_completed,
        )
    bonus_row = db.query(UserBonus).filter(UserBonus.user_id == user.id).first()
    bonus_points = bonus_row.points if bonus_row else 0
    level = (bonus_points // 100) + 1
    return PublicProfileResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        avatar_url=user.avatar_url,
        banner_url=user.banner_url,
        total_goals=total_goals,
        completed_goals=completed_goals,
        total_transactions=total_transactions,
        financial_index=financial_index,
        bonus_points=bonus_points,
        level=level,
        last_transaction=last_transaction,
        nearest_goal=nearest_goal,
    )


@router.put("/", response_model=ProfileResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Обновление профиля пользователя (почта, никнейм и т.д.)."""
    update_data = profile_update.model_dump(exclude_unset=True)
    if "email" in update_data:
        new_email = (update_data["email"] or "").strip().lower()
        if new_email:
            other = db.query(User).filter(User.email == new_email, User.id != current_user.id).first()
            if other:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            update_data["email"] = new_email
    for field, value in update_data.items():
        if value is not None:
            setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return _profile_response(current_user, db)
