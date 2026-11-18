# 03 · Data Pipeline — retries, notifications, metadata-driven loads

## Core concepts
- A **pipeline** orchestrates **activities** (Copy, Notebook, Lookup, ForEach, Outlook/Teams, Fail, …).
- Activities connect with **dependency conditions**: Succeeded (green), Failed (red), Completed (blue) and Skipped (grey).
- Each activity has a **policy**: *Retry*, *Retry interval (sec)* and *Timeout* (General tab).
- **Expressions** (`@pipeline().RunId`, `@item()`, `@activity('X').output`) make it dynamic.

## Flow (`pl_load_sales`)
```
Get table config (Lookup: Files/config/table_config.json)
  └─ Enabled tables (Filter: enabled == true)
      └─ Load tables (ForEach, parallel x4)
           └─ Load table (Notebook nb_load_table)   retry 2, every 30s
      └─ Build dim_date (Notebook)
          └─ Data quality (Notebook; raises on critical failures)
              └─ Refresh semantic model
                  ├─ ✅ Succeeded          → Notify success (Outlook)
                  └─ ❌ Failed OR Skipped  → Notify failure → Mark run as failed (Fail)
```
Definition: `src/fabric/pipelines/pl_load_sales.DataPipeline/pipeline-content.json`

## Tips & tricks
1. **Metadata-driven ForEach.** One config file, one notebook, N tables. To add a table, add a JSON row.
2. **Use the Filter activity** to switch tables on or off (`enabled`) without editing the pipeline.
3. **Set retries per activity type.** Retry Lookups, notebooks and refreshes (transient). Keep data-quality checks at 0 retries, because bad data won't fix itself.
4. **Use one catch-all failure path.** When any step fails, everything after it is *Skipped*. Put **Failed OR Skipped** on the *last* step and you get one notification for the whole chain.
5. **Add a Fail activity after the failure notification.** A handled failure (catch path succeeded) shows the run as *Succeeded* in Monitor. The Fail activity keeps run status honest.
6. **Pass `@pipeline().RunId` into notebooks** as `batch_id`. That links Monitor hub ↔ `etl_run_log` ↔ every loaded row.
7. **Lower the default timeout** (it's hours). A hung activity should fail in minutes.
8. **Use pipeline parameters for demo and test switches**, e.g. `simulate_failure_for_table=dim_product` forces one transient failure so you can *see* the retry.

## Notifications
- **Office 365 Outlook** and **Teams** activities need a connection you sign into once in the UI.
- Put run context in the message: pipeline name, `@{pipeline().RunId}`, `@{utcNow()}` and the DQ notebook's `exitValue`.
- The deploy script pushes the pipeline **without** these activities by default, so add them live in the demo (good teaching moment). Or run deploy with `--with-notifications`, then authorise the connections.

## Gotchas
- ForEach can't nest another ForEach. Use *Invoke pipeline* instead.
- Lookup returns at most 5,000 rows / 4 MB. That's plenty for config, not for data.
