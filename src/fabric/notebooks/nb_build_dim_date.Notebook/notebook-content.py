# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "{{LAKEHOUSE_ID}}",
# META       "default_lakehouse_name": "{{LAKEHOUSE_NAME}}",
# META       "default_lakehouse_workspace_id": "{{WORKSPACE_ID}}"
# META     }
# META   }
# META }

# MARKDOWN ********************

# # nb_build_dim_date
# Tip: **don't ship a date table as a file - generate it.** One Spark SQL statement,
# fiscal calendar included, plus "relative" flags (current month, YTD) that refresh every run.

# PARAMETERS CELL ********************

start_date = "2024-01-01"
end_date = "2027-12-31"
fiscal_year_start_month = 7  # July fiscal year (FY27 = Jul 2026 - Jun 2027)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import json

fy = int(fiscal_year_start_month)
df = spark.sql(f"""
WITH d AS (
  SELECT explode(sequence(to_date('{start_date}'), to_date('{end_date}'), interval 1 day)) AS date
)
SELECT
  date,
  CAST(date_format(date, 'yyyyMMdd') AS INT)              AS date_key,
  year(date)                                              AS year,
  concat('Q', quarter(date))                              AS quarter,
  month(date)                                             AS month_number,
  date_format(date, 'MMMM')                               AS month_name,
  date_format(date, 'MMM')                                AS month_short,
  trunc(date, 'MM')                                       AS month_start_date,
  date_format(date, 'yyyy-MM')                            AS year_month,
  year(date) * 100 + month(date)                          AS year_month_sort,
  dayofweek(date)                                         AS day_of_week_number,
  date_format(date, 'EEEE')                               AS day_name,
  dayofweek(date) IN (1, 7)                               AS is_weekend,
  weekofyear(date)                                        AS iso_week,
  CASE WHEN month(date) >= {fy} THEN year(date) + 1 ELSE year(date) END        AS fiscal_year_number,
  concat('FY', right(CAST(CASE WHEN month(date) >= {fy} THEN year(date) + 1 ELSE year(date) END AS STRING), 2)) AS fiscal_year,
  concat('FQ', CAST(floor(((month(date) - {fy} + 12) % 12) / 3) + 1 AS INT))   AS fiscal_quarter,
  trunc(date, 'MM') = trunc(current_date(), 'MM')         AS is_current_month,
  date <= current_date()                                  AS is_past_or_today,
  (year(date) = year(current_date()) AND date <= current_date()) AS is_ytd
FROM d
""")

df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("dim_date")
notebookutils.notebook.exit(json.dumps({"table": "dim_date", "rows": df.count()}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

