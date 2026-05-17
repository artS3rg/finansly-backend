from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    LoginResponse,
    CompleteTotpLoginRequest,
    TotpSetupStartResponse,
    TotpSetupConfirmRequest,
    TotpDisableRequest,
    RefreshTokenRequest,
)
from app.auth import (
    verify_password,
    get_password_hash,
    get_current_user,
    create_totp_pending_token,
    decode_totp_pending_token,
)
from app.refresh_tokens import issue_token_pair, refresh_access_token, revoke_refresh_token
from app.totp_utils import generate_totp_secret, provisioning_uri, verify_totp_code

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_password = get_password_hash(user_data.password)
    username = (user_data.username or "").strip() or None
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        username=username,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=LoginResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Вход: при включённом TOTP возвращает pending_token для шага с кодом."""
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.totp_enabled and user.totp_secret:
        pending = create_totp_pending_token(user.id)
        return LoginResponse(requires_totp=True, pending_token=pending)

    tokens = issue_token_pair(db, user)
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
    )


@router.post("/refresh", response_model=Token)
async def refresh_tokens(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Обновление access-токена по refresh-токену (с ротацией refresh)."""
    tokens = refresh_access_token(db, body.refresh_token.strip())
    return Token(**tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshTokenRequest | None = None,
    db: Session = Depends(get_db),
):
    """Отзыв refresh-токена при выходе."""
    if body and body.refresh_token.strip():
        revoke_refresh_token(db, body.refresh_token.strip())
    return None


@router.post("/login/complete-totp", response_model=Token)
async def complete_totp_login(body: CompleteTotpLoginRequest, db: Session = Depends(get_db)):
    """Завершение входа после ввода одноразового кода."""
    user_id = decode_totp_pending_token(body.pending_token)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="TOTP not configured",
        )
    if not verify_totp_code(user.totp_secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticator code",
        )
    tokens = issue_token_pair(db, user)
    return Token(**tokens)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return current_user


@router.post("/totp/setup/start", response_model=TotpSetupStartResponse)
async def totp_setup_start(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Начать подключение TOTP: сохраняет pending-секрет и возвращает otpauth URL для QR."""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP already enabled",
        )
    secret = generate_totp_secret()
    current_user.totp_pending_secret = secret
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    url = provisioning_uri(secret, current_user.email)
    return TotpSetupStartResponse(secret=secret, otpauth_url=url)


@router.post("/totp/setup/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def totp_setup_confirm(
    body: TotpSetupConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Подтвердить секрет первым верным кодом из приложения-аутентификатора."""
    pending = current_user.totp_pending_secret
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start TOTP setup first",
        )
    if not verify_totp_code(pending, body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticator code",
        )
    current_user.totp_secret = pending
    current_user.totp_pending_secret = None
    current_user.totp_enabled = True
    db.add(current_user)
    db.commit()
    return None


@router.post("/totp/disable", status_code=status.HTTP_204_NO_CONTENT)
async def totp_disable(
    body: TotpDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Отключить TOTP (по паролю)."""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP not enabled",
        )
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )
    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_pending_secret = None
    db.add(current_user)
    db.commit()
    return None
