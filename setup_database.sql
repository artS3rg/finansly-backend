-- SQL скрипт для создания базы данных и пользователя PostgreSQL
-- Выполните этот скрипт от имени суперпользователя PostgreSQL

-- Создание базы данных
CREATE DATABASE finansly;

-- Создание пользователя
CREATE USER finansly_user WITH PASSWORD 'your_password_here';

-- Предоставление прав
GRANT ALL PRIVILEGES ON DATABASE finansly TO finansly_user;

-- Подключение к базе данных и предоставление прав на схему
\c finansly
GRANT ALL ON SCHEMA public TO finansly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO finansly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO finansly_user;

-- Выход
\q
