/* ============================================================================
   Ops / observability queries over the tables the notebooks write
   (etl_run_log from nb_load_table, dq_results from nb_data_quality)
   ========================================================================== */

/* Latest run per table - "is my data fresh?" */
CREATE OR ALTER VIEW dbo.vw_table_freshness AS
SELECT table_name, status, rows_read, started_at, ended_at, duration_sec, error_message
FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY table_name ORDER BY started_at DESC) AS rn
    FROM dbo.etl_run_log
) x
WHERE rn = 1;
GO

/* Retries show up as >1 attempt for the same batch + table */
SELECT batch_id, table_name,
       COUNT(*)                                          AS attempts,
       SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) AS failed_attempts,
       MAX(CASE WHEN status = 'Succeeded' THEN 1 ELSE 0 END) AS eventually_succeeded
FROM dbo.etl_run_log
GROUP BY batch_id, table_name
HAVING COUNT(*) > 1
ORDER BY MAX(started_at) DESC;

/* Most recent failures with the error text */
SELECT TOP 20 started_at, table_name, batch_id, error_message
FROM dbo.etl_run_log
WHERE status = 'Failed'
ORDER BY started_at DESC;

/* Data quality trend */
SELECT CAST(checked_at AS DATE) AS check_date, severity, result, COUNT(*) AS checks
FROM dbo.dq_results
GROUP BY CAST(checked_at AS DATE), severity, result
ORDER BY check_date DESC, severity;
