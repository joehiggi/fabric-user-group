# %% [markdown]
# # nb_table_maintenance
# Tip: MERGE + frequent small loads = many small Parquet files. Compact them.
# * `OPTIMIZE ... VORDER` - bin-compacts files and applies V-Order (faster Direct Lake / SQL reads)
# * `VACUUM` - removes files no longer referenced (7-day retention keeps time travel working)
# Schedule weekly, or use Lakehouse > table "..." > Maintenance for one-offs.

# %% [parameters]
tables = "dim_territory,dim_sales_rep,dim_product,dim_customer,fact_sales,fact_sales_target,dim_date"
retain_hours = 168

# %%
import json

done = []
for t in [x.strip() for x in tables.split(",") if x.strip()]:
    before = spark.sql(f"DESCRIBE DETAIL {t}").collect()[0]["numFiles"]
    spark.sql(f"OPTIMIZE {t} VORDER")
    spark.sql(f"VACUUM {t} RETAIN {int(retain_hours)} HOURS")
    after = spark.sql(f"DESCRIBE DETAIL {t}").collect()[0]["numFiles"]
    done.append({"table": t, "files_before": before, "files_after": after})
    print(done[-1])

notebookutils.notebook.exit(json.dumps(done))
