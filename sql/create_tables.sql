-- SQLite 3.37+ (STRICT); выполняется в новой базе.
-- PRAGMA применяется к каждому соединению, до начала транзакции.
PRAGMA foreign_keys = ON;

-- ============================================
-- 1. Удаление существующих таблиц
-- ============================================

-- Удаляем таблицы в обратном порядке зависимостей
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;

-- ============================================
-- 2. Создание таблиц
-- ============================================

-- Покупатели
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY NOT NULL,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    email TEXT NOT NULL UNIQUE CHECK (length(trim(email)) > 0),
    registered_at TEXT NOT NULL CHECK (
        registered_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        AND date(registered_at) IS NOT NULL AND date(registered_at) = registered_at
    )
) STRICT;

-- Категории товаров
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY NOT NULL,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0)
) STRICT;

-- Товары
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    price_kopecks INTEGER NOT NULL CHECK (price_kopecks > 0)
) STRICT;

-- Заказы
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    order_date TEXT NOT NULL CHECK (
        order_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        AND date(order_date) IS NOT NULL AND date(order_date) = order_date
    ),
    status TEXT NOT NULL CHECK (status IN ('completed', 'pending', 'cancelled'))
) STRICT;

-- Позиции заказов
CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_kopecks INTEGER NOT NULL CHECK (unit_price_kopecks > 0),
    PRIMARY KEY (order_id, product_id)
) STRICT;

-- ============================================
-- 3. Создание индексов
-- ============================================

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_items_product ON order_items(product_id);

-- ============================================
-- 4. Проверка целостности
-- ============================================

PRAGMA foreign_key_check;