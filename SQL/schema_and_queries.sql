-- =============================================================================
-- Sales & Performance Dashboard — SQL Schema + Analytical Queries
-- Compatible with: PostgreSQL / MySQL / SQL Server (minor syntax tweaks noted)
-- =============================================================================


-- =============================================================================
-- 1. SCHEMA
-- =============================================================================

CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id   VARCHAR(20) PRIMARY KEY,
    customer_name VARCHAR(100),
    region        VARCHAR(50),
    segment       VARCHAR(50)           -- e.g. Consumer, Corporate, Home Office
);

CREATE TABLE IF NOT EXISTS dim_products (
    product_id    VARCHAR(20) PRIMARY KEY,
    category      VARCHAR(50),
    sub_category  VARCHAR(50),
    product_name  VARCHAR(150),
    unit_price    DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS dim_sales_reps (
    rep_id        VARCHAR(20) PRIMARY KEY,
    rep_name      VARCHAR(100),
    region        VARCHAR(50),
    hire_date     DATE
);

CREATE TABLE IF NOT EXISTS fact_sales (
    order_id      VARCHAR(20) PRIMARY KEY,
    order_date    DATE        NOT NULL,
    ship_date     DATE,
    ship_mode     VARCHAR(30),
    customer_id   VARCHAR(20) REFERENCES dim_customers(customer_id),
    rep_id        VARCHAR(20) REFERENCES dim_sales_reps(rep_id),
    product_id    VARCHAR(20) REFERENCES dim_products(product_id),
    quantity      INT,
    unit_price    DECIMAL(10,2),
    discount      DECIMAL(5,2),
    sales         DECIMAL(12,2),
    cost          DECIMAL(12,2),
    profit        DECIMAL(12,2),
    profit_pct    DECIMAL(6,2)
);

-- Indexes for query performance
CREATE INDEX idx_sales_order_date   ON fact_sales(order_date);
CREATE INDEX idx_sales_customer     ON fact_sales(customer_id);
CREATE INDEX idx_sales_rep          ON fact_sales(rep_id);
CREATE INDEX idx_sales_product      ON fact_sales(product_id);


-- =============================================================================
-- 2. ANALYTICAL QUERIES
-- =============================================================================

-- ── KPI 1: Total Revenue, Profit, and Orders (Overall) ───────────────────────
SELECT
    COUNT(order_id)          AS total_orders,
    ROUND(SUM(sales),  2)    AS total_revenue,
    ROUND(SUM(cost),   2)    AS total_cost,
    ROUND(SUM(profit), 2)    AS total_profit,
    ROUND(AVG(profit_pct), 2) AS avg_profit_margin_pct
FROM fact_sales;


-- ── KPI 2: Monthly Revenue & Profit Trend ────────────────────────────────────
SELECT
    DATE_TRUNC('month', order_date) AS month,   -- PostgreSQL
    -- DATE_FORMAT(order_date, '%Y-%m') AS month,  -- MySQL
    -- FORMAT(order_date, 'yyyy-MM')    AS month,  -- SQL Server
    COUNT(order_id)                 AS orders,
    ROUND(SUM(sales),  2)           AS revenue,
    ROUND(SUM(profit), 2)           AS profit,
    ROUND(AVG(profit_pct), 2)       AS avg_margin
FROM fact_sales
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;


-- ── KPI 3: Revenue & Profit by Region ────────────────────────────────────────
SELECT
    c.region,
    COUNT(f.order_id)          AS total_orders,
    ROUND(SUM(f.sales),  2)    AS total_revenue,
    ROUND(SUM(f.profit), 2)    AS total_profit,
    ROUND(AVG(f.profit_pct), 2) AS avg_profit_margin
FROM fact_sales f
JOIN dim_customers c ON f.customer_id = c.customer_id
GROUP BY c.region
ORDER BY total_revenue DESC;


-- ── KPI 4: Category Performance ──────────────────────────────────────────────
SELECT
    p.category,
    p.sub_category,
    COUNT(f.order_id)           AS orders,
    SUM(f.quantity)             AS units_sold,
    ROUND(SUM(f.sales),  2)     AS revenue,
    ROUND(SUM(f.profit), 2)     AS profit,
    ROUND(AVG(f.profit_pct), 2) AS margin_pct
FROM fact_sales f
JOIN dim_products p ON f.product_id = p.product_id
GROUP BY p.category, p.sub_category
ORDER BY revenue DESC;


-- ── KPI 5: Top 10 Sales Reps by Revenue ──────────────────────────────────────
SELECT
    r.rep_name,
    r.region,
    COUNT(f.order_id)           AS deals_closed,
    ROUND(SUM(f.sales),  2)     AS total_revenue,
    ROUND(SUM(f.profit), 2)     AS total_profit,
    ROUND(AVG(f.discount)*100, 1) AS avg_discount_pct
FROM fact_sales f
JOIN dim_sales_reps r ON f.rep_id = r.rep_id
GROUP BY r.rep_name, r.region
ORDER BY total_revenue DESC
LIMIT 10;


-- ── KPI 6: Top 10 Customers by Revenue ───────────────────────────────────────
SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    COUNT(f.order_id)       AS total_orders,
    ROUND(SUM(f.sales), 2)  AS lifetime_value,
    ROUND(SUM(f.profit), 2) AS total_profit
FROM fact_sales f
JOIN dim_customers c ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name, c.segment
ORDER BY lifetime_value DESC
LIMIT 10;


-- ── KPI 7: Revenue vs Previous Month (MoM Growth) — CTE ─────────────────────
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', order_date) AS month,
        ROUND(SUM(sales), 2)            AS revenue
    FROM fact_sales
    GROUP BY DATE_TRUNC('month', order_date)
),
lagged AS (
    SELECT
        month,
        revenue,
        LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue
    FROM monthly
)
SELECT
    month,
    revenue,
    prev_month_revenue,
    ROUND(
        ((revenue - prev_month_revenue) / NULLIF(prev_month_revenue, 0)) * 100, 2
    ) AS mom_growth_pct
FROM lagged
ORDER BY month;


-- ── KPI 8: Discount Impact on Profit ─────────────────────────────────────────
SELECT
    CASE
        WHEN discount = 0          THEN 'No Discount'
        WHEN discount <= 0.10      THEN 'Low (1-10%)'
        WHEN discount <= 0.20      THEN 'Medium (11-20%)'
        ELSE                            'High (>20%)'
    END AS discount_band,
    COUNT(order_id)             AS orders,
    ROUND(AVG(profit_pct), 2)   AS avg_margin,
    ROUND(SUM(profit), 2)       AS total_profit
FROM fact_sales
GROUP BY discount_band
ORDER BY avg_margin DESC;


-- ── KPI 9: Shipping Mode Performance ─────────────────────────────────────────
SELECT
    ship_mode,
    COUNT(order_id)                                               AS orders,
    ROUND(AVG(ship_date - order_date), 1)                         AS avg_ship_days,  -- PostgreSQL
    -- ROUND(AVG(DATEDIFF(ship_date, order_date)), 1)              AS avg_ship_days,  -- MySQL
    ROUND(SUM(sales), 2)                                          AS revenue,
    ROUND(AVG(profit_pct), 2)                                     AS avg_margin
FROM fact_sales
GROUP BY ship_mode
ORDER BY orders DESC;


-- ── KPI 10: YoY Revenue Comparison ───────────────────────────────────────────
SELECT
    EXTRACT(YEAR FROM order_date)  AS year,
    COUNT(order_id)                AS orders,
    ROUND(SUM(sales), 2)           AS revenue,
    ROUND(SUM(profit), 2)          AS profit,
    ROUND(AVG(profit_pct), 2)      AS avg_margin
FROM fact_sales
GROUP BY EXTRACT(YEAR FROM order_date)
ORDER BY year;


-- ── VIEW: Unified Reporting View ──────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_sales_report AS
SELECT
    f.order_id,
    f.order_date,
    f.ship_date,
    f.ship_mode,
    c.customer_id,
    c.customer_name,
    c.region,
    c.segment,
    r.rep_name,
    p.category,
    p.sub_category,
    p.product_name,
    f.quantity,
    f.unit_price,
    f.discount,
    f.sales,
    f.cost,
    f.profit,
    f.profit_pct
FROM fact_sales f
JOIN dim_customers  c ON f.customer_id = c.customer_id
JOIN dim_sales_reps r ON f.rep_id      = r.rep_id
JOIN dim_products   p ON f.product_id  = p.product_id;
