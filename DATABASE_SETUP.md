# Настройка PostgreSQL для Finansly

## Быстрая установка

### 1. Установка PostgreSQL

**Windows:**
1. Скачайте установщик с [официального сайта](https://www.postgresql.org/download/windows/)
2. Запустите установщик и следуйте инструкциям
3. Запомните пароль для пользователя `postgres`

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

### 2. Создание базы данных

#### Вариант 1: Через psql (командная строка)

```bash
# Войдите в PostgreSQL
sudo -u postgres psql  # Linux
psql -U postgres       # Windows/macOS (если установлен в PATH)
```

Затем выполните:
```sql
CREATE DATABASE finansly;
CREATE USER finansly_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE finansly TO finansly_user;
\c finansly
GRANT ALL ON SCHEMA public TO finansly_user;
\q
```

#### Вариант 2: Использование готового SQL скрипта

1. Отредактируйте `setup_database.sql` и укажите свой пароль
2. Выполните скрипт:
```bash
sudo -u postgres psql -f setup_database.sql  # Linux
psql -U postgres -f setup_database.sql       # Windows/macOS
```

### 3. Настройка переменных окружения

Скопируйте `env.example` в `.env`:
```bash
cp env.example .env
```

Отредактируйте `.env` и укажите свои данные:
```env
DATABASE_USER=finansly_user
DATABASE_PASSWORD=your_secure_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=finansly

SECRET_KEY=your-secret-key-here
```

Для генерации безопасного SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Важно (Windows):** сохраните файл `.env` в кодировке **UTF-8** (в блокноте: «Сохранить как» → кодировка «UTF-8»). Пароль и логин в `.env` лучше задавать **только латинскими буквами и цифрами** — иначе при запуске бэкенда возможна ошибка `UnicodeDecodeError`.

### 4. Проверка подключения

```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите приложение
uvicorn app.main:app --reload
```

Приложение автоматически создаст все необходимые таблицы при первом запуске.

### Миграция: поля аватар и баннер в профиле

Если таблица `users` уже была создана до добавления полей `avatar_url` и `banner_url`, выполните в psql (подключившись к базе `finansly`):

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS banner_url VARCHAR;
```

### Миграция: подписки — день списания вместо даты

Если таблица `subscriptions` уже существует с полем `payment_date`, выполните в psql (подключившись к базе `finansly`):

```sql
ALTER TABLE subscriptions ADD COLUMN payment_day INTEGER;
UPDATE subscriptions SET payment_day = EXTRACT(DAY FROM payment_date)::INTEGER WHERE payment_date IS NOT NULL;
UPDATE subscriptions SET payment_day = 1 WHERE payment_day IS NULL;
ALTER TABLE subscriptions ALTER COLUMN payment_day SET NOT NULL;
ALTER TABLE subscriptions DROP COLUMN payment_date;
```

Для новой установки таблица создаётся с полем `payment_day` автоматически.

### Таблица учёта списаний по подпискам (subscription_payments)

При первом запуске после обновления кода таблица `subscription_payments` создаётся автоматически через `init_db()`. Если используете миграции вручную:

```sql
CREATE TABLE IF NOT EXISTS subscription_payments (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    payment_date DATE NOT NULL,
    UNIQUE(subscription_id, payment_date)
);
```

## Устранение проблем

### UnicodeDecodeError в psycopg2 на Windows (byte 0xc2, position 61)

Ошибка возникает в дочернем процессе при запуске с `--reload`. **Решение:** запускать без `--reload`.

- Запускайте бэкенд через **`run_backend.bat`** — он запускает uvicorn без `--reload`, сервер работает стабильно.
- После изменений в коде закройте окно и запустите `run_backend.bat` снова.

### Ошибка подключения

**Проблема:** `could not connect to server`

**Решение:**
- Убедитесь, что PostgreSQL запущен: `sudo systemctl status postgresql` (Linux)
- Проверьте, что порт 5432 не занят другим приложением
- Проверьте настройки firewall

### Роль "finansly_user" не существует (role "finansly_user" does not exist)

В `.env` указан пользователь `finansly_user`, но в PostgreSQL он ещё не создан.

**Быстрый вариант — использовать пользователя `postgres`:**

В `.env` задайте:
```env
DATABASE_USER=postgres
DATABASE_PASSWORD=пароль_который_задали_при_установке_PostgreSQL
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=finansly
```

Создайте базу (один раз) в psql или pgAdmin:
```sql
CREATE DATABASE finansly;
```
(подключившись как пользователь `postgres`).

**Вариант с отдельным пользователем:** выполните шаги из раздела «2. Создание базы данных» выше (CREATE USER finansly_user ...) и укажите эти логин/пароль в `.env`.

### Ошибка аутентификации

**Проблема:** `password authentication failed`

**Решение:**
- Проверьте правильность пароля в `.env`
- Убедитесь, что пользователь существует: `\du` в psql
- Проверьте настройки `pg_hba.conf` (обычно в `/etc/postgresql/*/main/pg_hba.conf`)

### Ошибка прав доступа

**Проблема:** `permission denied`

**Решение:**
```sql
-- Войдите в psql как суперпользователь
\c finansly
GRANT ALL ON SCHEMA public TO finansly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO finansly_user;
```

## Использование Docker (опционально)

Если у вас установлен Docker, можно использовать готовый контейнер:

```bash
docker run --name finansly-postgres \
  -e POSTGRES_USER=finansly_user \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=finansly \
  -p 5432:5432 \
  -d postgres:15
```

## Резервное копирование

### Создание бэкапа
```bash
pg_dump -U finansly_user -d finansly > backup.sql
```

### Восстановление из бэкапа
```bash
psql -U finansly_user -d finansly < backup.sql
```
