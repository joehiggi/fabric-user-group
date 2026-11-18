# Fabric Tips & Tricks

[![tests](https://github.com/joehiggi/fabric-user-group/actions/workflows/tests.yml/badge.svg)](https://github.com/joehiggi/fabric-user-group/actions/workflows/tests.yml)

A complete, runnable Microsoft Fabric demo, built entirely as code. A tiny fictional B2B sales dataset goes through the four stages most data teams use:

| Stage | Medallion | What happens | Fabric item |
|---|---|---|---|
| 01 Ingest | Bronze | Load from raw files | Lakehouse Files → Delta tables |
| 02 Transform | Silver | Join from loaded tables | Pipeline + notebooks (MERGE), SQL views |
| 03 Model | Gold | Model from joined tables | Direct Lake semantic model (TMDL) |
| 04 Serve | — | Report from the model | Power BI report (PBIR) |

The pipeline is metadata-driven, retries transient failures, fails fast on bad data, sends notifications and logs every run. Everything deploys to any tenant with one command using the [Fabric CLI](https://microsoft.github.io/fabric-cli/).

> 👉 **Attending or catching up? Start with [FOLLOW-ALONG.md](FOLLOW-ALONG.md)**, a step-by-step guide that matches the talk slide by slide.

Presented at a Fabric User Group by **Joey Higgins** · [LinkedIn](https://www.linkedin.com/in/your-handle)

## Quick start

```bash
git clone https://github.com/joehiggi/fabric-user-group.git && cd fabric-user-group
make            # regenerate data, build notebooks + PBIP, run tests (Python 3.10+, no packages needed)
make config     # create config/environment.json, then edit workspace + capacity
make dry-run    # see every fab command it would run, no tenant needed

pip install ms-fabric-cli
fab auth login  # sign in to your tenant
make deploy
```

Then follow [docs/demo-runbook.md](docs/demo-runbook.md) to walk through the demo.

## Configuration

All shareable configuration lives in **[`config/`](config/README.md)**:

| File | Purpose |
|---|---|
| [`config/table_config.json`](config/table_config.json) | The tables the pipeline loads, with their source folder, load mode and keys. Add a row to add a table. |
| [`config/environment.example.json`](config/environment.example.json) | Template for your workspace, capacity, lakehouse and notification email. Copy it to `config/environment.json` (git-ignored). |

No secrets are stored anywhere. Auth is `fab auth login`, and all Fabric IDs are looked up at deploy time and substituted into `{{TOKENS}}`.

## The dataset

A made-up company selling software, services, hardware and support to other businesses. It's small on purpose (~340 KB) and regenerated identically from a fixed seed.

| Table | Rows | Notes |
|---|---|---|
| `fact_sales` | 2,901 | order lines, Jan 2025 to Oct 2026 (+67 November rows for the incremental demo) |
| `fact_sales_target` | 192 | territory × month |
| `dim_customer` · `dim_product` · `dim_sales_rep` · `dim_territory` | 60 · 16 · 12 · 8 | |
| `dim_date` | generated in a notebook | fiscal year starts in July |

No real company data. Names are fictional.

## Repo layout

```
config/                          shareable configuration (start here)
src/
  data_gen/generate_data.py      deterministic fake data (stdlib only)
  fabric/notebooks/nb_*.py       notebook sources → built into ipynb/ and *.Notebook/
  fabric/pipelines/              pl_load_sales.DataPipeline (pipeline JSON + .platform)
  fabric/sql/                    SQL endpoint views, monitoring, reconciliation
  powerbi/Sales.pbip             Sales.SemanticModel (TMDL, Direct Lake) + Sales.Report (PBIR)
  tools/                         build_notebooks.py, build_pbip.py
  deploy/deploy.py               fab CLI deploy (idempotent, --dry-run)
data/
  input/landing/<table>/*.csv    → Lakehouse Files/landing/
  input/incremental/, bad/       → Files/demo_drops/ (live demo)
  output/expected_kpis.csv       reconciliation totals
docs/                            one short brief per component + demo runbook
tests/                           data integrity + cross-artifact consistency (run in CI)
```

## Docs

| | |
|---|---|
| [**Follow along**](FOLLOW-ALONG.md) | step-by-step guide matching the presentation |
| [Session brief](docs/00-meeting-brief.md) | summary, agenda, takeaways |
| [Demo runbook](docs/demo-runbook.md) | step-by-step live demo |
| [01 Lakehouse](docs/01-lakehouse.md) · [02 Notebooks](docs/02-notebooks.md) · [03 Pipeline](docs/03-pipeline.md) | ingest + transform |
| [04 Semantic model](docs/04-semantic-model.md) · [05 Report](docs/05-report.md) · [06 SQL](docs/06-sql.md) | model + serve |
| [07 Deploy with fab CLI](docs/07-deploy-fab-cli.md) | deployment |

## Status

The generated artifacts (pipeline JSON, TMDL, PBIR, Fabric notebook format) and the `fab` commands follow the published formats, and they are validated by tests and a dry-run. A first deploy into a new tenant may still need small adjustments. Issues and PRs are welcome.

## License

[MIT](LICENSE)
