# API Эндпоинты Finansly

## Базовый URL
```
http://localhost:8000
```

## Аутентификация

Все эндпоинты (кроме `/api/auth/register` и `/api/auth/login`) требуют JWT токен в заголовке:
```
Authorization: Bearer <token>
```

---

## 1. Аутентификация (`/api/auth`)

### Регистрация
```
POST /api/auth/register
Body: {
  "email": "user@example.com",
  "password": "password123"
}
Response: UserResponse
```

### Вход
```
POST /api/auth/login
Body: {
  "email": "user@example.com",
  "password": "password123"
}
Response: {
  "access_token": "eyJ...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

### Обновить access-токен
```
POST /api/auth/refresh
Body: {
  "refresh_token": "..."
}
Response: {
  "access_token": "eyJ...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

### Выход (отзыв refresh)
```
POST /api/auth/logout
Body: {
  "refresh_token": "..."
}
Response: 204 No Content
```

### Получить текущего пользователя
```
GET /api/auth/me
Headers: Authorization: Bearer <token>
Response: UserResponse
```

---

## 2. Транзакции (`/api/transactions`)

### Создать транзакцию
```
POST /api/transactions/
Body: {
  "description": "Зарплата",
  "amount": 50000.0,
  "is_income": true,
  "category": "Зарплата"
}
Response: TransactionResponse
```

### Получить список транзакций
```
GET /api/transactions/?skip=0&limit=100&is_income=true&category=Зарплата
Query params:
  - skip: int (по умолчанию 0)
  - limit: int (по умолчанию 100, макс 1000)
  - is_income: bool (опционально)
  - category: string (опционально)
  - start_date: datetime (опционально)
  - end_date: datetime (опционально)
Response: List[TransactionResponse]
```

### Получить транзакцию по ID
```
GET /api/transactions/{transaction_id}
Response: TransactionResponse
```

### Обновить транзакцию
```
PUT /api/transactions/{transaction_id}
Body: {
  "description": "Обновленное описание",
  "amount": 60000.0
}
Response: TransactionResponse
```

### Удалить транзакцию
```
DELETE /api/transactions/{transaction_id}
Response: 204 No Content
```

### Статистика транзакций
```
GET /api/transactions/stats/summary
Response: {
  "total_income": 100000.0,
  "total_expense": 50000.0,
  "balance": 50000.0,
  "transaction_count": 25
}
```

---

## 3. Цели (`/api/goals`)

### Создать цель
```
POST /api/goals/
Body: {
  "title": "Новый автомобиль",
  "start_amount": 0.0,
  "finish_amount": 2000000.0,
  "party_count": 1
}
Response: GoalResponse
```

### Получить список целей
```
GET /api/goals/
Response: List[GoalResponse]
```

### Получить цель по ID
```
GET /api/goals/{goal_id}
Response: GoalResponse
```

### Обновить цель
```
PUT /api/goals/{goal_id}
Body: {
  "current_amount": 500000.0,
  "is_completed": false
}
Response: GoalResponse
```

### Удалить цель
```
DELETE /api/goals/{goal_id}
Response: 204 No Content
```

---

## 4. Подписки (`/api/subscriptions`)

### Создать подписку
```
POST /api/subscriptions/
Body: {
  "name": "Netflix",
  "amount": 599.0,
  "payment_date": "2025-02-15"
}
Response: SubscriptionResponse
```

### Получить список подписок
```
GET /api/subscriptions/
Response: List[SubscriptionResponse]
```

### Получить подписку по ID
```
GET /api/subscriptions/{subscription_id}
Response: SubscriptionResponse
```

### Обновить подписку
```
PUT /api/subscriptions/{subscription_id}
Body: {
  "amount": 699.0,
  "payment_date": "2025-02-20"
}
Response: SubscriptionResponse
```

### Удалить подписку
```
DELETE /api/subscriptions/{subscription_id}
Response: 204 No Content
```

---

## 5. Аналитика (`/api/analytics`)

### Получить аналитику
```
GET /api/analytics/
Response: {
  "current_month": {
    "total_income": 50000.0,
    "total_expense": 30000.0,
    "balance": 20000.0,
    "category_statistics": [...]
  },
  "last_month": {...},
  "total_balance": 100000.0,
  "monthly_trend": [...]
}
```

---

## 6. Профиль (`/api/profile`)

### Получить профиль
```
GET /api/profile/
Response: {
  "id": 1,
  "email": "user@example.com",
  "username": "User",
  "created_at": "2025-01-01T00:00:00",
  "total_goals": 5,
  "completed_goals": 2,
  "total_transactions": 50,
  "financial_index": 78
}
```

### Обновить профиль
```
PUT /api/profile/
Body: {
  "username": "NewUsername"
}
Response: ProfileResponse
```

---

## 7. ИИ Финансовый коуч (`/api/ai-coach`)

### Задать вопрос коучу
```
POST /api/ai-coach/ask
Body: {
  "question": "Как мне сэкономить деньги?",
  "context": {}  // опционально
}
Response: {
  "answer": "На основе ваших данных...",
  "suggestions": [
    "Сократите расходы на развлечения",
    "Откладывайте 20% от дохода"
  ],
  "confidence": 0.8
}
```

### Автоматический анализ финансов
```
POST /api/ai-coach/analyze
Response: {
  "answer": "Анализ ваших финансов...",
  "suggestions": [...],
  "confidence": 0.75
}
```

---

## Примеры использования

### Python (requests)
```python
import requests

BASE_URL = "http://localhost:8000"

# Регистрация
response = requests.post(f"{BASE_URL}/api/auth/register", json={
    "email": "user@example.com",
    "password": "password123"
})

# Вход
response = requests.post(f"{BASE_URL}/api/auth/login", json={
    "email": "user@example.com",
    "password": "password123"
})
token = response.json()["access_token"]

# Создание транзакции
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    f"{BASE_URL}/api/transactions/",
    json={
        "description": "Зарплата",
        "amount": 50000.0,
        "is_income": True,
        "category": "Зарплата"
    },
    headers=headers
)
```

### cURL
```bash
# Вход
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Создание транзакции
curl -X POST "http://localhost:8000/api/transactions/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Зарплата",
    "amount": 50000.0,
    "is_income": true,
    "category": "Зарплата"
  }'
```
