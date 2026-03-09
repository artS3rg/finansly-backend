# Загрузка .env до любых импортов из app
from dotenv import load_dotenv
load_dotenv(encoding="utf-8")

# Убираем переменные libpq с путями (на Windows дают UnicodeDecodeError в psycopg2)
import os
from pathlib import Path
for _k in ("PGPASSFILE", "PGSYSCONFDIR", "PGSERVICE"):
    os.environ.pop(_k, None)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import auth, transactions, goals, subscriptions, analytics, profile, ai_coach, bonus
from app.database import init_db

# Инициализация базы данных при старте
init_db()

app = FastAPI(
    title="Finansly API",
    description="Backend API for Finansly Android application",
    version="1.0.0"
)

# CORS middleware для работы с Android приложением
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(goals.router, prefix="/api/goals", tags=["Goals"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(ai_coach.router, prefix="/api/ai-coach", tags=["AI Coach"])
app.include_router(bonus.router, prefix="/api/bonus", tags=["Bonus"])

# Раздача загруженных аватарок и баннеров (uploads/avatars, uploads/banners)
_uploads = Path(os.getenv("UPLOAD_DIR", "uploads"))
_uploads.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_uploads)), name="static")


@app.get("/")
async def root():
    return {"message": "Finansly API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
