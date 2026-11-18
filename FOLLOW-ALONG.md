# Fabric Tips & Tricks: follow along

This guide matches the talk slide by slide. Do it live with the session, or work through it on your own afterwards. Every stage follows the same pattern: **what you'll do → steps → check → tip → try it yourself**.

> **Presenter:** Joey Higgins · [LinkedIn](https://www.linkedin.com/in/your-handle)

---

## 0 · Set up (before the session)

You need a Fabric workspace on a capacity (a trial capacity works), Python 3.10+ and Git.

```bash
git clone https://github.com/joehiggi/fabric-user-group.git
cd fabric-user-group
make                      # regenerates the data, builds the artifacts, runs the tests
make config               # creates config/environment.json
```

Edit `config/environment.json` and set your `workspace` and `capacity`. Then:

```bash
pip install ms-fabric-cli
fab auth login            # sign in to your tenant
make dry-run              # preview: prints every command, changes nothing
make deploy               # creates the lakehouse, uploads files, imports items, runs the pipeline
```

✅ **Check:** your workspace has `lh_sales`, four `nb_*` notebooks, `pl_load_sales`, and a `Sales` semantic model and report.

For convenience in the commands below:
```bash
LH="<your workspace>.Workspace/lh_sales.Lakehouse"
```

<details><summary>No CLI? Set it up by hand</summary>

1. Create a lakehouse called `lh_sales`
2. Upload `data/input/landing/*` to `Files/landing/` (keep the folder per table) and `config/table_config.json` to `Files/config/`
3. Import `src/fabric/notebooks/ipynb/*.ipynb` (Workspace → Import → Notebook) and attach each one to `lh_sales`
4. Run `nb_load_table` once per row in `table_config.json` (edit the parameter cell each time), then `nb_build_dim_date`
5. Build the pipeline from [docs/03-pipeline.md](docs/03-pipeline.md), and the model from [docs/04-semantic-model.md](docs/04-semantic-model.md)
</details>

---

## Slide 2 · The dataset

A made-up B2B company that sells software, services, hardware and support. It's small on purpose, so every step runs in seconds.

| Table | Rows | What it is |
|---|---|---|
| `fact_sales` | 2,901 | one row per order line, Jan 2025 to Oct 2026 |
| `dim_customer` | 60 | Enterprise, Mid-Market, SMB |
| `dim_product` | 16 | Software, Services, Hardware, Support |
| `dim_territory` | 8 | Americas, EMEA, APAC |
| `dim_sales_rep` · `fact_sales_target` | 12 · 192 | reps and monthly targets |

🔎 **Look:** open `data/input/landing/fact_sales/*.csv` locally. This is the "raw file" everything starts from.

💡 **Tip:** generate demo data from a script with a fixed seed (`src/data_gen/generate_data.py`). Anyone can rebuild it identically, and there's no real company data to worry about.

---

## Slide 3 · The same four stages, in Fabric

| Stage | Medallion | Pattern |
|---|---|---|
| 01 Ingest | Bronze | **Load** from raw files |
| 02 Transform | Silver | **Join** from loaded tables |
| 03 Model | Gold | **Model** from joined tables |
| 04 Serve | | **Report** from the model |

### 01 · Ingest: load from raw files

**What you'll do:** see how raw files become Delta tables, then drop in a new month of data.

1. Open `lh_sales` → **Files/landing/**. There is one folder per table.
2. Open **Tables** → `fact_sales` and look at the last three columns: `_source_file`, `_batch_id`, `_loaded_at`.
3. Drop in November's file:
   ```bash
   fab cp "$LH/Files/demo_drops/fact_sales_2026-11_mtd.csv" "$LH/Files/landing/fact_sales/"
   ```

✅ **Check:** `Files/landing/fact_sales/` now has two CSVs. The table hasn't changed yet, because loading is the next stage.

💡 **Tip: keep one folder per table.** The loader reads the folder, not a file name, so new files load with no code change.

🧪 **Try it yourself:** open `config/table_config.json`. Which table loads with `merge`, and which with `overwrite`? Why might a dimension use `overwrite`?

### 02 · Transform: join from loaded tables

**What you'll do:** run the pipeline, watch a retry happen, then query the joined result.

1. Open `pl_load_sales`. The flow is **Get table config → Enabled tables → Load tables (ForEach) → Build dim_date → Data quality**.
2. Click **Run** and set `simulate_failure_for_table` = `dim_product`.
3. Open **Monitor hub** → the run → `Load table`. The dim_product load **fails once, waits 30s, retries and succeeds**.
4. Open `nb_load_table` and find the `MERGE` (it matches on `order_id, order_line`).
5. In the lakehouse **SQL analytics endpoint**, run `src/fabric/sql/01_reporting_views.sql` once, then:
   ```sql
   SELECT TOP 10 * FROM dbo.vw_sales_enriched;                       -- the fact joined to every dimension
   SELECT COUNT(*) FROM dbo.fact_sales WHERE order_date >= '2026-11-01'; -- November rows
   ```

✅ **Check:** the second query returns **67**. Run the pipeline again (no parameters) and re-run the query. It's still 67.

💡 **Tip: merge instead of append.** A retry or re-run updates the same rows instead of duplicating them.

🧪 **Try it yourself:** run the retry check in `src/fabric/sql/02_pipeline_monitoring.sql`. Can you find your dim_product load with 2 attempts?

### 03 · Model: model from joined tables

**What you'll do:** see a star schema with business logic in measures, served by Direct Lake.

1. Open the `Sales` semantic model → **Open data model**.
2. Notice the star: `fact_sales` in the middle and the `dim_*` tables around it. Keys and raw amounts are hidden.
3. Select the **Revenue** measure:
   ```dax
   CALCULATE ( SUM ( fact_sales[net_amount] ),
               KEEPFILTERS ( fact_sales[order_status] IN { "Completed", "Shipped" } ) )
   ```
   The rule "which orders count as revenue" lives here, once.
4. Check **Revenue MTD** for November 2026. Direct Lake read the new rows, with no import refresh and no copy.

✅ **Check:** totals match `data/output/expected_kpis.csv` (2025 revenue = **26,495,073.50**). Run `src/fabric/sql/03_reconciliation.sql` to compare.

💡 **Tip: put rules in measures.** Define a rule once and every report uses the same number.

🧪 **Try it yourself:** add a measure `Revenue per Customer = DIVIDE ( [Revenue], DISTINCTCOUNT ( fact_sales[customer_id] ) )`.

### 04 · Serve: report from the model

**What you'll do:** read the finished report, including how healthy the data behind it is.

1. Open the `Sales` report → **Executive Overview**: KPI cards, then the trend, then the breakdown.
2. Go to **Pipeline Health**: last successful load, failed loads, the run log and data-quality results. Your retry from stage 02 is there.

✅ **Check:** "Last Successful Load" shows the time of your latest run.

💡 **Tip: report on pipeline health.** People trust numbers more when they can see how fresh they are.

🧪 **Try it yourself (optional, shows fail fast):**
```bash
fab cp "$LH/Files/demo_drops/fact_sales_BROKEN.csv" "$LH/Files/landing/fact_sales/"
```
Run the pipeline. The load fails on a renamed column and an `"N/A"` number, and Pipeline Health shows the error. Clean up afterwards:
```bash
fab rm "$LH/Files/landing/fact_sales/fact_sales_BROKEN.csv" -f
```

---

## Slide 4 · Four habits to take home

- [ ] **Ingest:** keep one folder per table
- [ ] **Transform:** merge instead of append
- [ ] **Model:** put rules in measures
- [ ] **Serve:** report on pipeline health

Across all four: retry transient failures, and fail fast on bad data.

---

## Slide 5 · Let's connect

- **Joey Higgins** · [LinkedIn](https://www.linkedin.com/in/your-handle)
- Questions, issues or ideas: [open an issue](https://github.com/joehiggi/fabric-user-group/issues)
- Go deeper: one short brief per component in [`docs/`](docs/)

## Clean up

Delete the workspace (or just the items) when you're done, so it doesn't use capacity.
