# Finansly Backend API

Backend API для Android приложения Finansly на FastAPI.

## Структура проекта

```
FinBackend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Главный файл приложения
│   ├── database.py             # Настройка базы данных
│   ├── auth.py                 # Аутентификация и JWT
│   ├── models/                 # SQLAlchemy модели
│   │   ├── user.py
│   │   ├── transaction.py
│   │   ├── goal.py
│   │   └── subscription.py
│   ├── schemas/                # Pydantic схемы
│   │   ├── user.py
│   │   ├── transaction.py
│   │   ├── goal.py
│   │   ├── subscription.py
│   │   ├── analytics.py
│   │   ├── profile.py
│   │   └── ai_coach.py
│   ├── routers/                # API роутеры
│   │   ├── auth.py
│   │   ├── transactions.py
│   │   ├── goals.py
│   │   ├── subscriptions.py
│   │   ├── analytics.py
│   │   ├── profile.py
│   │   └── ai_coach.py
│   └── ai_module/              # Модуль ИИ
│       └── financial_coach.py
├── requirements.txt
└── README.md
```

## Установка и запуск

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка PostgreSQL

#### Установка PostgreSQL

**Windows:**
- Скачайте и установите с [официального сайта](https://www.postgresql.org/download/windows/)
- Или используйте установщик через [EnterpriseDB](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

#### Создание базы данных

```bash
# Войдите в PostgreSQL
sudo -u postgres psql  # Linux
psql -U postgres       # Windows/macOS

# Создайте базу данных и пользователя
CREATE DATABASE finansly;
CREATE USER finansly_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE finansly TO finansly_user;
\q
```

#### Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
DATABASE_USER=finansly_user
DATABASE_PASSWORD=your_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=finansly

# Или используйте полный DATABASE_URL:
# DATABASE_URL=postgresql://finansly_user:your_password@localhost:5432/finansly

SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
```

### 3. Инициализация базы данных

База данных создается автоматически при первом запуске приложения.

### 4. Запуск сервера

```bash
# Разработка
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Продакшн
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Документация API

После запуска сервера документация доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Эндпоинты

### Аутентификация (`/api/auth`)

- `POST /api/auth/register` - Регистрация нового пользователя
- `POST /api/auth/login` - Вход (access + refresh JWT)
- `POST /api/auth/refresh` - Обновление access-токена по refresh-токену
- `POST /api/auth/logout` - Отзыв refresh-токена
- `GET /api/auth/me` - Получение информации о текущем пользователе

### Транзакции (`/api/transactions`)

- `POST /api/transactions/` - Создание новой транзакции
- `GET /api/transactions/` - Получение списка транзакций (с фильтрацией)
- `GET /api/transactions/{transaction_id}` - Получение транзакции по ID
- `PUT /api/transactions/{transaction_id}` - Обновление транзакции
- `DELETE /api/transactions/{transaction_id}` - Удаление транзакции
- `GET /api/transactions/stats/summary` - Статистика по транзакциям

### Цели (`/api/goals`)

- `POST /api/goals/` - Создание новой цели
- `GET /api/goals/` - Получение списка целей
- `GET /api/goals/{goal_id}` - Получение цели по ID
- `PUT /api/goals/{goal_id}` - Обновление цели
- `DELETE /api/goals/{goal_id}` - Удаление цели

### Подписки (`/api/subscriptions`)

- `POST /api/subscriptions/` - Создание новой подписки
- `GET /api/subscriptions/` - Получение списка подписок
- `GET /api/subscriptions/{subscription_id}` - Получение подписки по ID
- `PUT /api/subscriptions/{subscription_id}` - Обновление подписки
- `DELETE /api/subscriptions/{subscription_id}` - Удаление подписки

### Аналитика (`/api/analytics`)

- `GET /api/analytics/` - Получение аналитики по финансам

### Профиль (`/api/profile`)

- `GET /api/profile/` - Получение профиля со статистикой
- `PUT /api/profile/` - Обновление профиля

### ИИ Финансовый коуч (`/api/ai-coach`)

- `POST /api/ai-coach/ask` - Задать вопрос финансовому коучу
- `POST /api/ai-coach/analyze` - Автоматический анализ финансов с рекомендациями

## Модуль ИИ

Модуль `app/ai_module/financial_coach.py` содержит самописный искусственный интеллект для финансового коуча. Он анализирует:
- Доходы и расходы пользователя
- Финансовые цели
- Бюджет и финансовое состояние
- Дает персонализированные рекомендации

Модуль можно расширить, добавив:
- Машинное обучение (scikit-learn, TensorFlow)
- Анализ паттернов трат
- Прогнозирование бюджета
- Интеграцию с внешними API для финансовых данных

## Аутентификация

API использует пару access JWT (короткий срок) и opaque refresh-токен (хранится в БД). После входа (`/api/auth/login`) передавайте access в заголовке:

```
Authorization: Bearer <access_token>
```

Для обновления access: `POST /api/auth/refresh` с телом `{"refresh_token": "..."}` (refresh ротируется).

## База данных

Проект использует PostgreSQL. Настройка подключения выполняется через переменные окружения (см. раздел "Настройка PostgreSQL" выше).

### Миграции базы данных

Для управления миграциями рекомендуется использовать Alembic:

```bash
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Переменные окружения

Все настройки конфигурации хранятся в файле `.env`. См. `env.example` для примера.

Скопируйте `env.example` в `.env` и заполните своими данными:
```bash
cp env.example .env
```

## Безопасность

⚠️ **Важно для продакшена:**
- Измените `SECRET_KEY` в `app/auth.py` на случайную строку
- Настройте CORS для конкретных доменов в `app/main.py`
- Используйте HTTPS
- Настройте rate limiting
- Добавьте валидацию входных данных

## Разработка

Для разработки рекомендуется использовать виртуальное окружение:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## Лицензия

MIT
