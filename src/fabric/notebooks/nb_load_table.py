# %% [markdown]
# # nb_load_table
# Loads ONE landing folder (CSV) into ONE Delta table in the attached lakehouse.
# Called once per table by the pipeline's ForEach (metadata-driven loading).
#
# Tips shown here:
# * **Parameter cell** - pipeline overrides these values at run time.
# * **Explicit schemas + FAILFAST** - bad files fail loudly instead of loading NULLs.
# * **Idempotent MERGE** - safe to re-run / retry without duplicating rows.
# * **Audit columns + run log** - every load is traceable in `etl_run_log`.
# * **notebookutils.notebook.exit()** - returns JSON the pipeline can read.

# %% [parameters]
table_name = "fact_sales"
source_path = "Files/landing/fact_sales"
load_mode = "merge"              # overwrite | append | merge
key_columns = "order_id,order_line"
batch_id = "manual-run"          # pipeline passes @pipeline().RunId
simulate_failure_for_table = ""  # set to a table name to demo a transient failure + retry

# %%
import json
import os
import time
from datetime import datetime, timezone

from delta.tables import DeltaTable
from pyspark.sql import functions as F
from pyspark.sql.types import (DateType, DecimalType, IntegerType, StringType,
                               StructField, StructType)

S, I, D = StringType(), IntegerType(), DateType()
MONEY, PCT = DecimalType(18, 2), DecimalType(5, 2)

SCHEMAS = {
    "dim_territory": [("territory_id", S), ("territory_name", S), ("region", S)],
    "dim_sales_rep": [("sales_rep_id", S), ("sales_rep_name", S), ("title", S), ("region", S),
                      ("territory_id", S), ("manager_id", S), ("hire_date", D)],
    "dim_product": [("product_id", S), ("product_name", S), ("category", S), ("subcategory", S),
                    ("list_price", MONEY), ("unit_cost", MONEY)],
    "dim_customer": [("customer_id", S), ("customer_name", S), ("industry", S), ("segment", S),
                     ("territory_id", S), ("city", S), ("country", S), ("customer_since", D)],
    "fact_sales": [("order_id", S), ("order_line", I), ("order_date", D), ("ship_date", D),
                   ("customer_id", S), ("product_id", S), ("sales_rep_id", S), ("territory_id", S),
                   ("channel", S), ("quantity", I), ("unit_price", MONEY), ("discount_pct", PCT),
                   ("net_amount", MONEY), ("cost_amount", MONEY), ("order_status", S)],
    "fact_sales_target": [("territory_id", S), ("month_start_date", D), ("target_amount", MONEY)],
}

RUN_LOG_DDL = ("batch_id string, table_name string, source_path string, load_mode string, status string, "
               "rows_read long, started_at timestamp, ended_at timestamp, duration_sec double, error_message string")
# Create up front: ForEach runs loads in parallel and they'd race to create it on the first run.
spark.sql(f"CREATE TABLE IF NOT EXISTS etl_run_log ({RUN_LOG_DDL}) USING DELTA")

started = datetime.now(timezone.utc)
t0 = time.time()
rows_read = 0
status, error_message = "Succeeded", None


def log_run():
    """Append one row to etl_run_log (success OR failure)."""
    log = spark.createDataFrame(
        [(batch_id, table_name, source_path, load_mode, status, rows_read,
          started, datetime.now(timezone.utc), round(time.time() - t0, 1), error_message)],
        RUN_LOG_DDL)
    log.write.mode("append").saveAsTable("etl_run_log")


# %%
try:
    # --- Demo: transient failure on the FIRST attempt only -> pipeline retry succeeds
    if simulate_failure_for_table == table_name:
        marker = f"/lakehouse/default/Files/_control/retry_{batch_id}_{table_name}.flag"
        if not os.path.exists(marker):
            os.makedirs(os.path.dirname(marker), exist_ok=True)
            open(marker, "w").write(started.isoformat())
            raise RuntimeError(f"Simulated transient failure for {table_name} (attempt 1). Retry will succeed.")

    if table_name not in SCHEMAS:
        raise ValueError(f"No schema registered for '{table_name}'")
    schema = StructType([StructField(c, t, True) for c, t in SCHEMAS[table_name]])
    # enforceSchema=False -> Spark checks EVERY file's header against the schema (catches renamed columns)
    # mode=FAILFAST       -> any value that doesn't fit its type (e.g. "N/A" in an int) fails the load
    df = (spark.read.option("header", True)
          .option("enforceSchema", False)
          .option("mode", "FAILFAST")
          .schema(schema).csv(source_path)
          .withColumn("_source_file", F.col("_metadata.file_name"))
          .withColumn("_batch_id", F.lit(batch_id))
          .withColumn("_loaded_at", F.current_timestamp()))
    rows_read = df.count()  # forces the FAILFAST parse

    keys = [k.strip() for k in key_columns.split(",") if k.strip()]
    if load_mode == "merge" and spark.catalog.tableExists(table_name):
        cond = " AND ".join(f"t.{k} = s.{k}" for k in keys)
        (DeltaTable.forName(spark, table_name).alias("t")
         .merge(df.dropDuplicates(keys).alias("s"), cond)
         .whenMatchedUpdateAll()
         .whenNotMatchedInsertAll()
         .execute())
    elif load_mode == "append":
        df.write.mode("append").saveAsTable(table_name)
    else:  # overwrite, or first-ever merge
        df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)
except Exception as e:
    status, error_message = "Failed", str(e)[:1000]
    raise
finally:
    log_run()

# %%
result = {"table": table_name, "status": status, "rows_read": rows_read,
          "duration_sec": round(time.time() - t0, 1)}
print(result)
notebookutils.notebook.exit(json.dumps(result))
