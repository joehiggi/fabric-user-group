# 02 · Notebooks (Spark)

## Core concepts
- Fabric notebooks run PySpark, Spark SQL, Scala or R on a managed Spark pool. Starter pools start in seconds.
- A notebook has a **default lakehouse**. Relative paths (`Files/...`) and `saveAsTable()` target it.
- The **parameter cell** holds values a pipeline can override at run time.
- `notebookutils.notebook.exit(value)` hands a value back to the calling pipeline, which reads it as `output.result.exitValue`.

## In this repo
| Notebook | Job |
|---|---|
| `nb_load_table` | Loads one landing folder into one Delta table (overwrite / append / **merge**), adds audit columns, writes `etl_run_log` |
| `nb_build_dim_date` | Generates the date table with a fiscal calendar and relative flags |
| `nb_data_quality` | SQL checks → `dq_results`. **Raises** if a critical check fails |
| `nb_table_maintenance` | `OPTIMIZE ... VORDER` + `VACUUM` |

Sources are plain `.py` files with `# %%` cells. `src/tools/build_notebooks.py` builds them into `.ipynb` (for manual import) and `*.Notebook/` folders (for `fab import` / Git).

## Tips & tricks
- **Use explicit schemas with `mode=FAILFAST` and `enforceSchema=False`.** A renamed column or `"N/A"` in a number column fails the load instead of silently loading NULLs.
- **Use idempotent MERGE on business keys.** Retries and re-runs never duplicate rows.
- **Add audit columns** (`_source_file`, `_batch_id`, `_loaded_at`). Every row can be traced to a file and a pipeline run.
- **Log in a `finally` block.** You get a run-log row for failures too, which are the ones you care about.
- **Generate your date table.** Never ship it as a file.
- **Parallel notebooks:** enable *high concurrency for pipelines* (workspace Spark settings) so ForEach iterations share a session. Or use `notebookutils.notebook.runMultiple()` from one orchestrator notebook.

## Gotchas
- Parallel writers creating the same table on the first run will race. Create shared log tables up front (`CREATE TABLE IF NOT EXISTS`).
- `notebookutils.notebook.exit()` stops the notebook. Put it in the last cell.
