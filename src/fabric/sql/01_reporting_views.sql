/* ============================================================================
   Reporting views on the Lakehouse SQL analytics endpoint
   Run in: Lakehouse > SQL analytics endpoint > New SQL query
   Tip: the endpoint is read-only for TABLES, but you CAN create views,
        functions and procedures. Great for ad-hoc analysts & Excel users.
   ========================================================================== */

CREATE OR ALTER VIEW dbo.vw_sales_enriched AS
SELECT
    f.order_id,
    f.order_line,
    f.order_date,
    DATEFROMPARTS(YEAR(f.order_date), MONTH(f.order_date), 1) AS month_start_date,
    f.order_status,
    f.channel,
    c.customer_name,
    c.segment,
    c.industry,
    p.product_name,
    p.category,
    t.territory_name,
    t.region,
    r.sales_rep_name,
    f.quantity,
    f.net_amount,
    f.cost_amount,
    f.net_amount - f.cost_amount AS gross_margin,
    CASE WHEN f.order_status IN ('Completed', 'Shipped') THEN 1 ELSE 0 END AS is_revenue
FROM dbo.fact_sales      AS f
JOIN dbo.dim_customer    AS c ON c.customer_id  = f.customer_id
JOIN dbo.dim_product     AS p ON p.product_id   = f.product_id
JOIN dbo.dim_territory   AS t ON t.territory_id = f.territory_id
JOIN dbo.dim_sales_rep   AS r ON r.sales_rep_id = f.sales_rep_id;
GO

/* Monthly actual vs target by territory */
CREATE OR ALTER VIEW dbo.vw_territory_monthly_attainment AS
WITH actuals AS (
    SELECT territory_id,
           DATEFROMPARTS(YEAR(order_date), MONTH(order_date), 1) AS month_start_date,
           SUM(net_amount) AS revenue
    FROM dbo.fact_sales
    WHERE order_status IN ('Completed', 'Shipped')
    GROUP BY territory_id, DATEFROMPARTS(YEAR(order_date), MONTH(order_date), 1)
)
SELECT
    t.territory_name,
    t.region,
    tg.month_start_date,
    COALESCE(a.revenue, 0)                                   AS revenue,
    tg.target_amount,
    COALESCE(a.revenue, 0) - tg.target_amount                AS variance,
    CAST(COALESCE(a.revenue, 0) / NULLIF(tg.target_amount, 0) AS DECIMAL(9, 4)) AS attainment_pct
FROM dbo.fact_sales_target AS tg
JOIN dbo.dim_territory     AS t ON t.territory_id = tg.territory_id
LEFT JOIN actuals          AS a ON a.territory_id = tg.territory_id
                               AND a.month_start_date = tg.month_start_date;
GO

/* Rep leaderboard with window functions */
CREATE OR ALTER VIEW dbo.vw_rep_leaderboard AS
SELECT
    r.sales_rep_name,
    t.territory_name,
    YEAR(f.order_date)                            AS order_year,
    SUM(f.net_amount)                             AS revenue,
    COUNT(DISTINCT f.order_id)                    AS orders,
    RANK() OVER (PARTITION BY YEAR(f.order_date) ORDER BY SUM(f.net_amount) DESC) AS revenue_rank
FROM dbo.fact_sales    AS f
JOIN dbo.dim_sales_rep AS r ON r.sales_rep_id = f.sales_rep_id
JOIN dbo.dim_territory AS t ON t.territory_id = f.territory_id
WHERE f.order_status IN ('Completed', 'Shipped')
GROUP BY r.sales_rep_name, t.territory_name, YEAR(f.order_date);
GO
