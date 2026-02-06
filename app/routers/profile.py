import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.goal import Goal
from app.models.transaction import Transaction
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.auth import get_current_user

router = APIRouter()

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
    total_goals = db.query(Goal).filter(Goal.user_id == current_user.id).count()
    completed_goals = db.query(Goal).filter(
        Goal.user_id == current_user.id,
        Goal.is_completed == True,
    ).count()
    total_transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).count()
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()
    total_income = sum(t.amount for t in transactions if t.is_income)
    total_expense = sum(t.amount for t in transactions if not t.is_income)
    expense_ratio = total_income / total_expense if total_expense > 0 else 10.0
    financial_index = min(
        100,
        max(0, int((expense_ratio * 20) + (completed_goals * 5) + (total_goals * 2))),
    )
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
    )


@router.put("/", response_model=ProfileResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление профиля пользователя"""
    update_data = profile_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return _profile_response(current_user, db)
