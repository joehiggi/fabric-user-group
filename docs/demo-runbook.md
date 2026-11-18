# Live demo runbook

Set once: `LH="Fabric User Group Demo.Workspace/lh_sales.Lakehouse"`

## Before the session (day before, then again 30 min before)
- [ ] `make test` is green
- [ ] `make deploy ...` done, pipeline ran once, report opens
- [ ] Run `src/fabric/sql/03_reconciliation.sql` and check it matches `data/output/expected_kpis.csv`
- [ ] Notifications work: trigger one failure and confirm the email arrives
- [ ] Remove leftover drops: `fab rm "$LH/Files/landing/fact_sales/fact_sales_BROKEN.csv" -f` (if present)
- [ ] Browser tabs open: workspace, lakehouse, pipeline, Monitor hub, report, SQL endpoint
- [ ] Spark session warm (run any notebook cell 5 min before)

15-minute session, high level: 1 min intro → **10 min demo in 4 stops, matching slide 3** → 2 min recap → 2 min Q&A.
One tip per stop. Stay high level and don't open code unless someone asks.

## 01 · Ingestion: land files, get tables (2 min)
1. Lakehouse → **Files/landing/**: one folder per table
2. Drop a new file live: `fab cp "$LH/Files/demo_drops/fact_sales_2026-11_mtd.csv" "$LH/Files/landing/fact_sales/"`
3. **Tables**: Delta tables, with audit columns showing which file each row came from
> 💡 Tip: one folder per table. New files just load, with no code change.

## 02 · Usage: query it straight away (2 min)
1. Lakehouse → **SQL analytics endpoint** → New query → paste the first query from `src/fabric/sql/03_reconciliation.sql` (revenue by year)
2. Mention it connects from SSMS, VS Code and Excel with the same connection string
> 💡 Tip: query before you model. The SQL endpoint is ready the moment tables exist.

## 03 · Build: pipelines, notebooks, semantic models (4 min)
1. **Pipeline:** open `pl_load_sales`: config lookup → ForEach → notebook. Run it with `simulate_failure_for_table = dim_product` (started during the title slide). In Monitor hub, the load fails once, retries and succeeds, and November loads.
2. **Notebook:** 20-second look at `nb_load_table`: the parameter cell and the MERGE ("re-runs never duplicate")
3. **Semantic model:** open `Sales`: the star schema and the `Revenue` measure. **Revenue MTD** now includes November, picked up by Direct Lake with no copy.
4. *Optional if time allows:* copy `fact_sales_BROKEN.csv` into `landing/fact_sales/` and run, to show the failure alert. Remove it afterwards.
> 💡 Tip: design for failure. Retry the blips, fail fast on bad data.

## 04 · Final state: reports (2 min)
Executive Overview → **Pipeline Health** (the retry from stop 03 is on it).
> 💡 Tip: ship a health page next to the business report. Trust comes from seeing freshness.

## Cut if running long
- Skip the notebook look in 03
- Skip the optional failure demo; describe it instead

## If things go wrong live
- Spark slow to start: talk through the pipeline JSON in VS Code while it spins up
- Notification delayed: show the run in Monitor hub and move on
- Report broken: open `vw_territory_monthly_attainment` in SQL and keep going
