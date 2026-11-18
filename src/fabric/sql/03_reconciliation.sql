/* ============================================================================
   Reconciliation: do the Lakehouse numbers match what the generator produced?
   Compare against data/output/expected_kpis.csv (history load, before the
   November incremental file). Tip: reconcile BEFORE you demo a report.
   ========================================================================== */

SELECT
    YEAR(order_date)                         AS order_year,
    SUM(net_amount)                          AS revenue,
    SUM(net_amount) - SUM(cost_amount)       AS gross_margin,
    COUNT(DISTINCT order_id)                 AS orders
FROM dbo.fact_sales
WHERE order_status IN ('Completed', 'Shipped')
  AND order_date <= '2026-10-31'
GROUP BY YEAR(order_date)
ORDER BY order_year;

SELECT YEAR(order_date) AS order_year, territory_id, SUM(net_amount) AS revenue
FROM dbo.fact_sales
WHERE order_status IN ('Completed', 'Shipped')
  AND order_date <= '2026-10-31'
GROUP BY YEAR(order_date), territory_id
ORDER BY order_year, territory_id;

/* Row counts per table (expected: 8 / 12 / 16 / 60 / 2901 / 192 before incremental) */
SELECT 'dim_territory' AS table_name, COUNT(*) AS row_count FROM dbo.dim_territory UNION ALL
SELECT 'dim_sales_rep',     COUNT(*) FROM dbo.dim_sales_rep UNION ALL
SELECT 'dim_product',       COUNT(*) FROM dbo.dim_product   UNION ALL
SELECT 'dim_customer',      COUNT(*) FROM dbo.dim_customer  UNION ALL
SELECT 'fact_sales',        COUNT(*) FROM dbo.fact_sales    UNION ALL
SELECT 'fact_sales_target', COUNT(*) FROM dbo.fact_sales_target;
