from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.goal import Goal
from app.models.goal_member import GoalMember
from app.schemas.goal import (
    GoalCreate,
    GoalResponse,
    GoalUpdate,
    GoalDetailResponse,
    GoalParticipantResponse,
    AddParticipantRequest,
    ContributeRequest,
)
from app.auth import get_current_user

router = APIRouter()


def _build_participants(db: Session, goal: Goal) -> list[GoalParticipantResponse]:
    """Собирает список участников: создатель + все члены цели."""
    result = []
    creator = db.get(User, goal.user_id)
    if creator:
        creator_member = next(
            (m for m in goal.members if m.user_id == goal.user_id),
            None,
        )
        result.append(
            GoalParticipantResponse(
                user_id=creator.id,
                username=creator.username,
                email=creator.email,
                avatar_url=creator.avatar_url,
                contributed_amount=creator_member.contributed_amount if creator_member else 0,
                is_creator=True,
            )
        )
    for m in goal.members:
        if m.user_id == goal.user_id:
            continue
        u = db.get(User, m.user_id)
        if u:
            result.append(
                GoalParticipantResponse(
                    user_id=u.id,
                    username=u.username,
                    email=u.email,
                    avatar_url=u.avatar_url,
                    contributed_amount=m.contributed_amount,
                    is_creator=False,
                )
            )
    return result


@router.post("/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    goal: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Создание новой цели. Создатель автоматически добавляется как участник."""
    db_goal = Goal(
        user_id=current_user.id,
        title=goal.title,
        start_amount=goal.start_amount,
        finish_amount=goal.finish_amount,
        current_amount=goal.start_amount,
        party_count=goal.party_count,
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    member = GoalMember(
        goal_id=db_goal.id,
        user_id=current_user.id,
        contributed_amount=0,
    )
    db.add(member)
    db.commit()
    _recalc_goal_current_amount(db, db_goal)
    db.refresh(db_goal)
    return db_goal


@router.get("/", response_model=List[GoalResponse])
async def get_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получение списка целей пользователя (где он создатель или участник)."""
    created = db.query(Goal).filter(Goal.user_id == current_user.id).all()
    member_goal_ids = [
        row[0]
        for row in db.query(GoalMember.goal_id)
        .filter(GoalMember.user_id == current_user.id)
        .distinct()
        .all()
    ]
    from_ids = {g.id for g in created} | set(member_goal_ids)
    goals = db.query(Goal).filter(Goal.id.in_(from_ids)).order_by(Goal.created_at.desc()).all()
    return goals


@router.get("/{goal_id}", response_model=GoalDetailResponse)
async def get_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получение цели по ID. Доступно создателю и участникам."""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    is_creator = goal.user_id == current_user.id
    is_member = db.query(GoalMember).filter(
        GoalMember.goal_id == goal_id,
        GoalMember.user_id == current_user.id,
    ).first() is not None
    if not is_creator and not is_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    participants = _build_participants(db, goal)
    return GoalDetailResponse(
        id=goal.id,
        user_id=goal.user_id,
        title=goal.title,
        start_amount=goal.start_amount,
        finish_amount=goal.finish_amount,
        current_amount=goal.current_amount,
        party_count=goal.party_count,
        created_at=goal.created_at,
        completed_at=goal.completed_at,
        is_completed=goal.is_completed,
        participants=participants,
    )


@router.put("/{goal_id}", response_model=GoalDetailResponse)
async def update_goal(
    goal_id: int,
    goal_update: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Обновление цели. Только создатель."""
    db_goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id,
    ).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    update_data = goal_update.model_dump(exclude_unset=True)
    if update_data.get("is_completed") and not db_goal.is_completed:
        update_data["completed_at"] = datetime.utcnow()
    elif update_data.get("is_completed") is False:
        update_data["completed_at"] = None
    for field, value in update_data.items():
        setattr(db_goal, field, value)
    db.commit()
    db.refresh(db_goal)
    participants = _build_participants(db, db_goal)
    return GoalDetailResponse(
        id=db_goal.id,
        user_id=db_goal.user_id,
        title=db_goal.title,
        start_amount=db_goal.start_amount,
        finish_amount=db_goal.finish_amount,
        current_amount=db_goal.current_amount,
        party_count=db_goal.party_count,
        created_at=db_goal.created_at,
        completed_at=db_goal.completed_at,
        is_completed=db_goal.is_completed,
        participants=participants,
    )


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Удаление цели. Только создатель."""
    goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id,
    ).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    db.delete(goal)
    db.commit()
    return None


@router.post("/{goal_id}/complete", response_model=GoalDetailResponse)
async def complete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Завершение цели: текущая сумма = целевая. Только создатель."""
    db_goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id,
    ).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    db_goal.current_amount = db_goal.finish_amount
    db_goal.is_completed = True
    db_goal.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(db_goal)
    participants = _build_participants(db, db_goal)
    return GoalDetailResponse(
        id=db_goal.id,
        user_id=db_goal.user_id,
        title=db_goal.title,
        start_amount=db_goal.start_amount,
        finish_amount=db_goal.finish_amount,
        current_amount=db_goal.current_amount,
        party_count=db_goal.party_count,
        created_at=db_goal.created_at,
        completed_at=db_goal.completed_at,
        is_completed=db_goal.is_completed,
        participants=participants,
    )


@router.post("/{goal_id}/resume", response_model=GoalDetailResponse)
async def resume_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Возобновить цель (снять отметку о завершении). Только создатель."""
    db_goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id,
    ).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    db_goal.is_completed = False
    db_goal.completed_at = None
    db.commit()
    _recalc_goal_current_amount(db, db_goal)
    db.refresh(db_goal)
    participants = _build_participants(db, db_goal)
    return GoalDetailResponse(
        id=db_goal.id,
        user_id=db_goal.user_id,
        title=db_goal.title,
        start_amount=db_goal.start_amount,
        finish_amount=db_goal.finish_amount,
        current_amount=db_goal.current_amount,
        party_count=db_goal.party_count,
        created_at=db_goal.created_at,
        completed_at=db_goal.completed_at,
        is_completed=db_goal.is_completed,
        participants=participants,
    )


@router.post("/{goal_id}/participants", response_model=GoalDetailResponse)
async def add_participant(
    goal_id: int,
    body: AddParticipantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Добавить участника по email или user_id. Только создатель цели."""
    db_goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id,
    ).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    user_to_add = None
    if body.user_id is not None:
        user_to_add = db.get(User, body.user_id)
    elif body.email:
        user_to_add = db.query(User).filter(User.email == body.email.strip()).first()
    if not user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден",
        )
    existing = db.query(GoalMember).filter(
        GoalMember.goal_id == goal_id,
        GoalMember.user_id == user_to_add.id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Участник уже добавлен",
        )
    member = GoalMember(
        goal_id=goal_id,
        user_id=user_to_add.id,
        contributed_amount=0.0,
    )
    db.add(member)
    db.commit()
    _recalc_goal_current_amount(db, db_goal)
    db.refresh(db_goal)
    participants = _build_participants(db, db_goal)
    return GoalDetailResponse(
        id=db_goal.id,
        user_id=db_goal.user_id,
        title=db_goal.title,
        start_amount=db_goal.start_amount,
        finish_amount=db_goal.finish_amount,
        current_amount=db_goal.current_amount,
        party_count=db_goal.party_count,
        created_at=db_goal.created_at,
        completed_at=db_goal.completed_at,
        is_completed=db_goal.is_completed,
        participants=participants,
    )


def _recalc_goal_current_amount(db: Session, goal: Goal) -> None:
    """Пересчитывает current_amount = start_amount + сумма вкладов всех участников."""
    total_contributed = db.query(GoalMember.contributed_amount).filter(
        GoalMember.goal_id == goal.id
    ).all()
    goal.current_amount = goal.start_amount + sum(t[0] for t in total_contributed)
    db.commit()


@router.put("/{goal_id}/contribute", response_model=GoalDetailResponse)
async def contribute(
    goal_id: int,
    body: ContributeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Внести свою сумму в цель. Участник обновляет свой вклад. Сумма не может быть отрицательной."""
    if body.amount < 0:
        raise HTTPException(status_code=400, detail="Сумма не может быть отрицательной")
    db_goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    member = db.query(GoalMember).filter(
        GoalMember.goal_id == goal_id,
        GoalMember.user_id == current_user.id,
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не участник этой цели",
        )
    member.contributed_amount = body.amount
    db.commit()
    _recalc_goal_current_amount(db, db_goal)
    db.refresh(db_goal)
    participants = _build_participants(db, db_goal)
    return GoalDetailResponse(
        id=db_goal.id,
        user_id=db_goal.user_id,
        title=db_goal.title,
        start_amount=db_goal.start_amount,
        finish_amount=db_goal.finish_amount,
        current_amount=db_goal.current_amount,
        party_count=db_goal.party_count,
        created_at=db_goal.created_at,
        completed_at=db_goal.completed_at,
        is_completed=db_goal.is_completed,
        participants=participants,
    )


@router.delete("/{goal_id}/participants/{user_id}", response_model=GoalDetailResponse)
async def remove_participant(
    goal_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Удалить участника из цели. Только создатель. Нельзя удалить создателя."""
    db_goal = db.query(Goal).filter(
        Goal.id == goal_id,
        Goal.user_id == current_user.id,
    ).first()
    if not db_goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить создателя цели",
        )
    member = db.query(GoalMember).filter(
        GoalMember.goal_id == goal_id,
        GoalMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участник не найден",
        )
    db.delete(member)
    db.commit()
    _recalc_goal_current_amount(db, db_goal)
    db.refresh(db_goal)
    participants = _build_participants(db, db_goal)
    return GoalDetailResponse(
        id=db_goal.id,
        user_id=db_goal.user_id,
        title=db_goal.title,
        start_amount=db_goal.start_amount,
        finish_amount=db_goal.finish_amount,
        current_amount=db_goal.current_amount,
        party_count=db_goal.party_count,
        created_at=db_goal.created_at,
        completed_at=db_goal.completed_at,
        is_completed=db_goal.is_completed,
        participants=participants,
    )
