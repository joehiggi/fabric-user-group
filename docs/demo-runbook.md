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

## Demo 1: Retry in action (~2 min)
1. Pipeline → **Run** with parameter `simulate_failure_for_table = dim_product`
2. Monitor hub → the `Load table` iteration for dim_product **fails, waits 30s, retries, succeeds**
3. SQL endpoint → `02_pipeline_monitoring.sql` retries query shows **2 attempts, eventually_succeeded = 1**
> 💬 "Retries handle the network blip at 2am. Nobody gets paged."

## Demo 2: Incremental load + Direct Lake (~2 min)
1. Report: note **Revenue MTD** for Nov 2026 (blank / partial)
2. Drop the new file:
   `fab cp "$LH/Files/demo_drops/fact_sales_2026-11_mtd.csv" "$LH/Files/landing/fact_sales/"`
3. Run the pipeline (no parameters). MERGE inserts only the new order lines.
4. Refresh the report and November appears, with no import refresh.
> 💬 "Same pipeline, new file, no code change. Run it twice and nothing duplicates."

## Demo 3: Bad data → fail fast → notification (~3 min)
1. `fab cp "$LH/Files/demo_drops/fact_sales_BROKEN.csv" "$LH/Files/landing/fact_sales/"`
2. Run the pipeline. `fact_sales` fails (renamed column `net_amt`, `"N/A"` quantity).
3. Show: failure email/Teams message → Monitor shows **Failed** (thanks to the Fail activity) → `etl_run_log.error_message`
4. Talking point: it retried twice anyway. **Data errors shouldn't retry.** Options: classify errors in the notebook, or validate in a separate step with retry = 0.
5. Clean up: `fab rm "$LH/Files/landing/fact_sales/fact_sales_BROKEN.csv" -f` and re-run.

## Demo 4: Report tour (~1 min)
Executive Overview → Sales Performance → **Pipeline Health** (the retry and the failure you just caused are on it).

## If things go wrong live
- Spark slow to start: talk through the pipeline JSON in VS Code while it spins up
- Notification delayed: show the run in Monitor hub and move on
- Report broken: open `vw_territory_monthly_attainment` in SQL and keep going
