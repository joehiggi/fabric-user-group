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

# # nb_data_quality
# Runs SQL checks after loading. Results land in `dq_results` (report-able!).
# If any **critical** check fails the notebook raises -> pipeline failure path -> notification.
#
# Tip: each check is just a SQL query that returns the number of BAD rows. Easy to extend.

# PARAMETERS CELL ********************

batch_id = "manual-run"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import json
from datetime import datetime, timezone

CHECKS = [
    # (name, severity, sql returning count of bad rows)
    ("fact_sales has rows", "critical",
     "SELECT CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END FROM fact_sales"),
    ("no duplicate order lines", "critical",
     "SELECT COUNT(*) FROM (SELECT order_id, order_line FROM fact_sales GROUP BY 1, 2 HAVING COUNT(*) > 1)"),
    ("orphan customer_id", "critical",
     "SELECT COUNT(*) FROM fact_sales f LEFT ANTI JOIN dim_customer c ON f.customer_id = c.customer_id"),
    ("orphan product_id", "critical",
     "SELECT COUNT(*) FROM fact_sales f LEFT ANTI JOIN dim_product p ON f.product_id = p.product_id"),
    ("orphan sales_rep_id", "critical",
     "SELECT COUNT(*) FROM fact_sales f LEFT ANTI JOIN dim_sales_rep r ON f.sales_rep_id = r.sales_rep_id"),
    ("negative net_amount", "critical",
     "SELECT COUNT(*) FROM fact_sales WHERE net_amount < 0"),
    ("ship_date before order_date", "warning",
     "SELECT COUNT(*) FROM fact_sales WHERE ship_date < order_date"),
    ("discount above 30%", "warning",
     "SELECT COUNT(*) FROM fact_sales WHERE discount_pct > 0.30"),
    ("every territory has a target", "warning",
     "SELECT COUNT(*) FROM dim_territory t LEFT ANTI JOIN fact_sales_target s ON t.territory_id = s.territory_id"),
]

now = datetime.now(timezone.utc)
results = []
for name, severity, sql in CHECKS:
    bad = int(spark.sql(sql).collect()[0][0])
    results.append((batch_id, now, name, severity, bad, "Pass" if bad == 0 else "Fail"))

res_df = spark.createDataFrame(
    results, "batch_id string, checked_at timestamp, check_name string, severity string, bad_rows long, result string")
res_df.write.mode("append").saveAsTable("dq_results")
display(res_df)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

failed_critical = [r[2] for r in results if r[3] == "critical" and r[5] == "Fail"]
warnings = [r[2] for r in results if r[3] == "warning" and r[5] == "Fail"]
if failed_critical:
    raise Exception(f"Critical data quality checks failed: {failed_critical}")

notebookutils.notebook.exit(json.dumps({
    "checks": len(results), "failed_critical": 0, "warnings": len(warnings), "warning_names": warnings}))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

