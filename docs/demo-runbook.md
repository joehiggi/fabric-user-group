# Live demo runbook

Set once: `LH="Fabric User Group Demo.Workspace/lh_sales.Lakehouse"`

## Before the session (day before, then again 30 min before)
- [ ] `make test` is green
- [ ] `make deploy ...` done, pipeline ran once, report opens
- [ ] Run `src/fabric/sql/01_reporting_views.sql` in the SQL endpoint (creates the joined views used in stage 02)
- [ ] Run `src/fabric/sql/03_reconciliation.sql` and check it matches `data/output/expected_kpis.csv`
- [ ] Notifications work: trigger one failure and confirm the email arrives
- [ ] Remove leftover drops: `fab rm "$LH/Files/landing/fact_sales/fact_sales_BROKEN.csv" -f` (if present)
- [ ] Browser tabs open: workspace, lakehouse, pipeline, Monitor hub, report, SQL endpoint
- [ ] Spark session warm (run any notebook cell 5 min before)

Four industry-standard stages, matching slides 2–4. Same syntax every time: **<verb> from <previous output>**.

| Stage | Medallion | Action | Fabric item |
|---|---|---|---|
| 01 Ingest | Bronze | Load from raw files | Lakehouse Files → Delta tables |
| 02 Transform | Silver | Join from loaded tables | Pipeline + notebook MERGE, SQL views |
| 03 Model | Gold | Model from joined tables | Direct Lake semantic model |
| 04 Serve | — | Report from the model | Power BI report |

## 01 · Ingest: load from raw files
1. Lakehouse → **Files/landing/**: one folder per table
2. Drop a new file live: `fab cp "$LH/Files/demo_drops/fact_sales_2026-11_mtd.csv" "$LH/Files/landing/fact_sales/"`
> 💡 One folder per table. New files load with no code change.

## 02 · Transform: join from loaded tables
1. **Pipeline:** open `pl_load_sales` (config → ForEach → notebook). The run started on the title slide with `simulate_failure_for_table = dim_product`. In Monitor hub, it fails once, retries and succeeds. November is loaded.
2. **Notebook:** a quick look at `nb_load_table`'s MERGE
3. **SQL endpoint:** `SELECT TOP 10 * FROM dbo.vw_sales_enriched`, the fact joined to every dimension
> 💡 Merge, don't append. Re-runs never duplicate.

## 03 · Model: model from joined tables
1. Open the `Sales` semantic model: the star schema and the `Revenue` measure
2. **Revenue MTD** includes November, picked up by Direct Lake with no copy
> 💡 Direct Lake, no copy. Business rules live in measures.

## 04 · Serve: report from the model
Executive Overview → **Pipeline Health** (the retry from stage 02 is on it).
> 💡 Show the data's health next to the data.

*Optional:* copy `fact_sales_BROKEN.csv` into `landing/fact_sales/` and run, to show the failure alert ("fail fast on bad data"). Remove it afterwards.

## Cut if running long
- Skip the notebook look in 02
- Skip the optional failure demo

## If things go wrong live
- Spark slow to start: talk through the pipeline JSON in VS Code while it spins up
- Notification delayed: show the run in Monitor hub and move on
- Report broken: open `vw_territory_monthly_attainment` in SQL and keep going
