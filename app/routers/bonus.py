import random
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.user_bonus import UserBonus
from app.models.daily_task import DailyTask
from app.schemas.bonus import BonusStateResponse, DailyTaskResponse, TASK_TYPE_KEYS

router = APIRouter()

POINTS_PER_TASK = 20
LEVEL_POINTS = 100  # за каждые 100 очков новый уровень


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _get_or_create_bonus(db: Session, user_id: int) -> UserBonus:
    row = db.query(UserBonus).filter(UserBonus.user_id == user_id).first()
    if row is None:
        row = UserBonus(user_id=user_id, points=0)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _ensure_daily_tasks(db: Session, user_id: int, task_date: date) -> list[DailyTask]:
    existing = (
        db.query(DailyTask)
        .filter(DailyTask.user_id == user_id, DailyTask.task_date == task_date)
        .order_by(DailyTask.position)
        .all()
    )
    if len(existing) >= 5:
        return existing
    # Создаём 5 случайных заданий
    chosen = random.sample(TASK_TYPE_KEYS, min(5, len(TASK_TYPE_KEYS)))
    for i, task_type in enumerate(chosen):
        t = DailyTask(
            user_id=user_id,
            task_date=task_date,
            position=i,
            task_type=task_type,
            completed=False,
        )
        db.add(t)
    db.commit()
    tasks = (
        db.query(DailyTask)
        .filter(DailyTask.user_id == user_id, DailyTask.task_date == task_date)
        .order_by(DailyTask.position)
        .all()
    )
    return tasks


def points_to_level(points: int) -> int:
    """Уровень: 0 очков = 1 уровень, 100 = 2, 200 = 3, ..."""
    return (points // LEVEL_POINTS) + 1


def points_to_progress(points: int) -> float:
    """Прогресс до следующего уровня 0.0 .. 1.0."""
    remainder = points % LEVEL_POINTS
    return remainder / LEVEL_POINTS if LEVEL_POINTS else 0.0


@router.get("/daily", response_model=BonusStateResponse)
async def get_daily_bonus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Текущее состояние бонусов: очки, уровень, прогресс и 5 ежедневных заданий на сегодня."""
    today = _today_utc()
    bonus = _get_or_create_bonus(db, current_user.id)
    tasks = _ensure_daily_tasks(db, current_user.id, today)
    level = points_to_level(bonus.points)
    progress = points_to_progress(bonus.points)
    return BonusStateResponse(
        points=bonus.points,
        level=level,
        progress_to_next=progress,
        tasks=[
            DailyTaskResponse(id=t.id, task_type=t.task_type, completed=t.completed, position=t.position)
            for t in tasks
        ],
    )


def try_complete_task(db: Session, user_id: int, task_type: str) -> bool:
    """
    Отмечает задание типа task_type за сегодня как выполненное и начисляет очки.
    Вызывается из роутеров транзакций/целей и т.д.
    Возвращает True, если задание было найдено и отмечено.
    """
    today = _today_utc()
    task = (
        db.query(DailyTask)
        .filter(
            DailyTask.user_id == user_id,
            DailyTask.task_date == today,
            DailyTask.task_type == task_type,
            DailyTask.completed == False,
        )
        .first()
    )
    if not task:
        return False
    task.completed = True
    bonus = _get_or_create_bonus(db, user_id)
    bonus.points += POINTS_PER_TASK
    db.commit()
    return True
