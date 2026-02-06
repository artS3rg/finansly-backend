from datetime import datetime, timedelta, timezone
import hashlib
import logging
import os
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User

# Настройки JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(30 * 24 * 60)))

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# bcrypt принимает не более 72 байт; длинные пароли предварительно хешируем SHA256
BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    pwd = password.encode("utf-8")
    if len(pwd) > BCRYPT_MAX_BYTES:
        pwd = hashlib.sha256(pwd).digest()
    return pwd


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_password_bytes(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(_password_bytes(password))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание JWT токена. exp — целочисленный Unix timestamp (секунды с 1970-01-01 UTC)."""
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Получение текущего пользователя из токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.warning("JWT validation failed: %s", e)
        raise credentials_exception
    raw_sub = payload.get("sub")
    if raw_sub is None:
        logger.warning("JWT payload missing 'sub'")
        raise credentials_exception
    try:
        user_id = int(raw_sub)
    except (TypeError, ValueError):
        logger.warning("JWT 'sub' is not a valid user id: %r", raw_sub)
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.warning("User not found for id=%s (token valid, user missing in DB)", user_id)
        raise credentials_exception
    return user
