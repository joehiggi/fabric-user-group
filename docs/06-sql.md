# 06 · SQL analytics endpoint

## Core concepts
- Every lakehouse has a **read-only T-SQL endpoint** over its Delta tables. Use SSMS, VS Code, Excel or any SQL tool.
- You can't `INSERT` or `UPDATE` lakehouse tables through it, but you **can** create **views, functions and stored procedures**.
- Need full T-SQL DML? Use a **Fabric Warehouse**. It can query lakehouse tables across items with three-part names.

## In this repo (`src/fabric/sql/`)
| File | Purpose |
|---|---|
| `01_reporting_views.sql` | `vw_sales_enriched`, `vw_territory_monthly_attainment`, `vw_rep_leaderboard` for analysts and Excel |
| `02_pipeline_monitoring.sql` | `vw_table_freshness` plus queries for retries, failures and DQ trend |
| `03_reconciliation.sql` | Totals to compare with `data/output/expected_kpis.csv` |

## Tips & tricks
- **Reconcile before you demo.** Compare totals to `expected_kpis.csv` so you know the numbers are right.
- **Retries are visible in SQL.** More than one row per `batch_id + table_name` in `etl_run_log` means a retry happened.
- **Expose views to SQL users and tables to Direct Lake.** Views force DirectQuery fallback in Direct Lake models.
- **Copy the SQL connection string** from the endpoint settings. It works in SSMS and Azure Data Studio with Entra ID auth.
