-- Q1 | expensive_products
-- Товары дороже 50 000 руб. Цель: выделить дорогую часть текущего каталога.
-- Порог 5000000 задан в копейках и может быть изменён в WHERE.
SELECT id AS product_id, name AS product, price_kopecks / 100.0 AS price_rub
FROM products
WHERE price_kopecks > 5000000
ORDER BY price_kopecks DESC, id;

-- Q2 | category_revenue
-- Выручка всех категорий. Цель: сравнить вклад категорий, включая нулевой.
-- Фильтр статуса в ON сохраняет категории без завершённых продаж.
SELECT c.id AS category_id, c.name AS category,
       COALESCE(SUM(CASE WHEN o.id IS NOT NULL
           THEN oi.quantity * oi.unit_price_kopecks ELSE 0 END), 0) / 100.0 AS revenue_rub
FROM categories c
LEFT JOIN products p ON p.category_id = c.id
LEFT JOIN order_items oi ON oi.product_id = p.id
LEFT JOIN orders o ON o.id = oi.order_id AND o.status = 'completed'
GROUP BY c.id, c.name
ORDER BY revenue_rub DESC, c.id;

-- Q3 | top_products
-- Топ-10 товаров по проданным единицам. Цель: оценить популярность по объёму.
SELECT p.id AS product_id, p.name AS product, SUM(oi.quantity) AS units_sold
FROM products p
INNER JOIN order_items oi ON oi.product_id = p.id
INNER JOIN orders o ON o.id = oi.order_id
WHERE o.status = 'completed'
GROUP BY p.id, p.name
ORDER BY units_sold DESC, p.id
LIMIT 10;

-- Q4 | frequent_customers
-- Более трёх завершённых заказов. Цель: найти повторных покупателей.
-- orders не соединяется с позициями: каждый заказ учитывается ровно один раз.
SELECT c.id AS customer_id, c.name AS customer, COUNT(o.id) AS completed_orders
FROM customers c
INNER JOIN orders o ON o.customer_id = c.id
WHERE o.status = 'completed'
GROUP BY c.id, c.name
HAVING COUNT(o.id) > 3
ORDER BY completed_orders DESC, c.id;

-- Q5 | monthly_revenue
-- Помесячная выручка. Цель: сравнить сумму завершённых продаж по дате заказа.
SELECT strftime('%Y-%m', o.order_date) AS month,
       SUM(oi.quantity * oi.unit_price_kopecks) / 100.0 AS revenue_rub
FROM orders o
INNER JOIN order_items oi ON oi.order_id = o.id
WHERE o.status = 'completed'
GROUP BY strftime('%Y-%m', o.order_date)
ORDER BY month;

-- Q6 | monthly_average_order
-- Средний чек по месяцам. Цель: отделить стоимость заказа от числа позиций.
-- CTE сначала получает ОДНУ строку на завершённый заказ; только затем AVG.
WITH order_totals AS (
    SELECT o.id, strftime('%Y-%m', o.order_date) AS month,
           SUM(oi.quantity * oi.unit_price_kopecks) AS total_kopecks
    FROM orders o
    INNER JOIN order_items oi ON oi.order_id = o.id
    WHERE o.status = 'completed'
    GROUP BY o.id, strftime('%Y-%m', o.order_date)
)
SELECT month, COUNT(*) AS completed_orders,
       ROUND(AVG(total_kopecks) / 100.0, 2) AS average_order_rub
FROM order_totals
GROUP BY month
ORDER BY month;

-- Q7 | customers_without_orders
-- Покупатели без заказов любого статуса. Цель: найти неактивные регистрации.
SELECT c.id AS customer_id, c.name AS customer, c.email, c.registered_at
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.id IS NULL
ORDER BY c.id;

-- Q8 | categories_above_average
-- Категории выше среднего по ВСЕМ категориям, в том числе с нулевой выручкой.
-- Цель: сравнить вклад категории с равномерным распределением общей выручки.
WITH category_totals AS (
    SELECT c.id, c.name,
           COALESCE(SUM(CASE WHEN o.id IS NOT NULL
               THEN oi.quantity * oi.unit_price_kopecks ELSE 0 END), 0) AS total_kopecks
    FROM categories c
    LEFT JOIN products p ON p.category_id = c.id
    LEFT JOIN order_items oi ON oi.product_id = p.id
    LEFT JOIN orders o ON o.id = oi.order_id AND o.status = 'completed'
    GROUP BY c.id, c.name
)
SELECT id AS category_id, name AS category, total_kopecks / 100.0 AS revenue_rub,
       ROUND((SELECT AVG(total_kopecks) FROM category_totals) / 100.0, 2) AS average_category_rub
FROM category_totals
WHERE total_kopecks > (SELECT AVG(total_kopecks) FROM category_totals)
ORDER BY total_kopecks DESC, id;
