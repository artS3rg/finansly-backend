-- Добавление полей TOTP (PostgreSQL). Выполните один раз на существующей БД.
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_pending_secret VARCHAR;
