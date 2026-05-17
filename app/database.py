from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from urllib.parse import quote_plus


def _ascii_only(s: str, default: str = "") -> str:
    if s is None:
        return default
    s = str(s).strip()
    out = "".join(c for c in s if ord(c) < 128)
    return out if out else default


DATABASE_USER = _ascii_only(os.getenv("DATABASE_USER"), "postgres")
DATABASE_PASSWORD = _ascii_only(os.getenv("DATABASE_PASSWORD"), "postgres")
DATABASE_HOST = _ascii_only(os.getenv("DATABASE_HOST"), "localhost") or "localhost"
_dataport = "".join(c for c in (os.getenv("DATABASE_PORT") or "5432") if c.isdigit())
DATABASE_PORT = _dataport or "5432"
DATABASE_NAME = _ascii_only(os.getenv("DATABASE_NAME"), "finansly")

# psycopg v3 — нет UnicodeDecodeError на Windows (в отличие от psycopg2/libpq)
DATABASE_URL = f"postgresql+psycopg://{quote_plus(DATABASE_USER)}:{quote_plus(DATABASE_PASSWORD)}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
DATABASE_URL = DATABASE_URL.encode("ascii", "replace").decode("ascii")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Инициализация базы данных"""
    import app.models  # noqa: F401 — регистрация всех моделей на Base

    Base.metadata.create_all(bind=engine)
