# 01 · Lakehouse

## Core concepts
- **OneLake** is the single data lake behind every Fabric workspace. Every item stores its data there in open formats.
- A **Lakehouse** has two areas:
  - **Files** is any file (CSV, JSON, Parquet), like a folder. It's our *landing zone*.
  - **Tables** holds managed **Delta** tables (Parquet + transaction log). Spark, SQL, Power BI and others all read these.
- Every lakehouse automatically gets a **SQL analytics endpoint**: read-only T-SQL over the Delta tables.
- **Delta** gives you ACID transactions, MERGE/UPDATE, time travel (`VERSION AS OF`) and schema enforcement.

## In this repo
| Path | Lakehouse location |
|---|---|
| `data/input/landing/<table>/*.csv` | `Files/landing/<table>/` (one folder per table) |
| `src/fabric/config/table_config.json` | `Files/config/table_config.json` |
| `data/input/incremental`, `data/input/bad` | `Files/demo_drops/` (moved into `landing/` during the demo) |

## Tips & tricks
- **Use one folder per table, not one file.** Loads read the *folder*, so a new monthly file just drops in. No code change.
- **Keep landing and tables separate.** Raw files stay replayable, and you can rebuild any table from Files.
- **Use shortcuts** to reference data in ADLS, S3 or another workspace without copying it.
- **Schemas-enabled lakehouses** (`dbo`, `sales`, …) make large lakehouses easier to navigate.
- **Run table maintenance** (`OPTIMIZE` + `VACUUM`) after many small MERGEs. See `nb_table_maintenance`.

## Gotchas
- The SQL endpoint **syncs metadata asynchronously**. A brand-new table can take a moment to appear in SQL and Power BI.
- `VACUUM` with less than 7 days' retention breaks time travel for older versions.
