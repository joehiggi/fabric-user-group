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

The six steps match the demo slide one to one.

## 01 · Lakehouse: land the files (~1 min)
1. Lakehouse → **Files/landing/**: one folder per table
2. **Tables**: Delta tables created by the first run. Preview `fact_sales` and point out the audit columns (`_source_file`, `_batch_id`, `_loaded_at`)
> 💬 "Files are the raw landing zone, Tables are what everything else reads."

## 02 · Pipeline: retry wins (~2 min)
1. Pipeline → **Run** with parameter `simulate_failure_for_table = dim_product`
2. Monitor hub → the `Load table` iteration for dim_product **fails, waits 30s, retries, succeeds**
3. SQL endpoint → the retries query in `02_pipeline_monitoring.sql` shows **2 attempts, eventually_succeeded = 1**
> 💬 "Retries handle the network blip at 2am. Nobody gets paged."

## 03 · Notebooks: add November (~2 min)
1. `fab cp "$LH/Files/demo_drops/fact_sales_2026-11_mtd.csv" "$LH/Files/landing/fact_sales/"`
2. Open `nb_load_table` and show the parameter cell and the MERGE on `order_id, order_line`
3. Run the pipeline (no parameters). Only the new November rows are inserted.
> 💬 "Same pipeline, new file, no code change. Run it twice and nothing duplicates."

## 04 · Pipeline: break it (~2 min)
1. `fab cp "$LH/Files/demo_drops/fact_sales_BROKEN.csv" "$LH/Files/landing/fact_sales/"`
2. Run the pipeline. `fact_sales` fails (renamed column `net_amt`, `"N/A"` quantity).
3. Show the failure email/Teams message, then Monitor showing **Failed** (thanks to the Fail activity), then `etl_run_log.error_message`
4. Talking point: it retried twice anyway. **Data errors shouldn't retry.** Classify errors in the notebook, or validate in a step with retry = 0.
5. Clean up: `fab rm "$LH/Files/landing/fact_sales/fact_sales_BROKEN.csv" -f` and re-run.

## 05 · Semantic model: see it live (~1 min)
1. Open the `Sales` model. Show the star schema, the display folders and the `Revenue` measure (the business rule lives in one place)
2. **Revenue MTD** now includes November. Direct Lake read the new Delta version with no import refresh.

## 06 · Report: tell the story (~1 min)
Executive Overview → Sales Performance → **Pipeline Health** (the retry from 02 and the failure from 04 are both on it).
> 💬 "And all of this was deployed from one repo with one fab command."

## If things go wrong live
- Spark slow to start: talk through the pipeline JSON in VS Code while it spins up
- Notification delayed: show the run in Monitor hub and move on
- Report broken: open `vw_territory_monthly_attainment` in SQL and keep going
