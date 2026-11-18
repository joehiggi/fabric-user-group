# Configuration

Everything you'd change to run this demo in your own tenant lives here.

| File | Shared? | Purpose |
|---|---|---|
| `table_config.json` | ✅ committed | Which tables the pipeline loads, from where, and how (`overwrite` / `append` / `merge`). Add a row to add a table. Uploaded to `Files/config/` and read by the pipeline's Lookup activity. |
| `environment.example.json` | ✅ committed | Template for your deployment settings. |
| `environment.json` | ❌ git-ignored | Your copy: workspace, capacity, lakehouse, notification email. |

```bash
cp config/environment.example.json config/environment.json   # then edit it
fab auth login                                                # sign in to your tenant
make deploy                                                   # reads config/environment.json
```

Nothing secret goes in these files. Authentication is handled by `fab auth login`, and every ID is looked up at deploy time.

## table_config.json fields
| Field | Example | Notes |
|---|---|---|
| `table_name` | `fact_sales` | Delta table name. Must have a schema in `nb_load_table` |
| `source_path` | `Files/landing/fact_sales` | Folder, not file: every CSV in it is loaded |
| `load_mode` | `merge` | `overwrite`, `append` or `merge` |
| `key_columns` | `order_id,order_line` | Business key for `merge` |
| `load_order` | `1` | Informational (dims 1, facts 2) |
| `enabled` | `true` | `false` skips the table (pipeline Filter activity) |
