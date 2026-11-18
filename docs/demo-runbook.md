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

15-minute session: 1 min intro → **10 min demo (4 parts, matching slide 2)** → 2 min recap → 2 min Q&A.

## 01 · Lakehouse: land the files (2 min)
1. Lakehouse → **Files/landing/**: one folder per table
2. **Tables**: preview `fact_sales` and point out the audit columns (`_source_file`, `_batch_id`, `_loaded_at`)
> 💬 "Files are the raw landing zone, Tables are what everything else reads."

## 02 · Pipeline: retry it, reload it, break it (4 min)
1. **Retry:** Run with `simulate_failure_for_table = dim_product`. In Monitor hub, the dim_product load fails, waits 30s, retries and succeeds.
   > 💬 "Retries handle the network blip at 2am."
2. **Reload:** `fab cp "$LH/Files/demo_drops/fact_sales_2026-11_mtd.csv" "$LH/Files/landing/fact_sales/"`, then run. The notebook's MERGE inserts only the new November rows.
   > 💬 "Same pipeline, new file, no code change. Re-runs never duplicate."
3. **Break:** `fab cp "$LH/Files/demo_drops/fact_sales_BROKEN.csv" "$LH/Files/landing/fact_sales/"`, then run. Show the alert, then the **Failed** status in Monitor.
   > 💬 "Data errors shouldn't retry. Fail fast and tell someone."
4. Clean up: `fab rm "$LH/Files/landing/fact_sales/fact_sales_BROKEN.csv" -f` (re-run after the talk)

Time saver: kick off the Retry run during the intro slide, so it's already in Monitor when you switch.

## 03 · Semantic model: see November appear (2 min)
1. Open the `Sales` model. Show the star schema and the `Revenue` measure (the business rule lives in one place)
2. **Revenue MTD** now includes November. Direct Lake picked it up with no import refresh.

## 04 · Report: tell the story (2 min)
Executive Overview → **Pipeline Health** (the retry and the failure from part 02 are both on it).
> 💬 "And all of this deploys from one repo with one fab command."

## Cut if running long
- Skip the Sales Performance page
- In part 02, describe the Break step instead of running it, and show the email from your rehearsal run

## If things go wrong live
- Spark slow to start: talk through the pipeline JSON in VS Code while it spins up
- Notification delayed: show the run in Monitor hub and move on
- Report broken: open `vw_territory_monthly_attainment` in SQL and keep going
