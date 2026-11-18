# Fabric User Group: Tips & Tricks

End-to-end Microsoft Fabric demo built **as code**: tiny company-agnostic B2B sales data →
**Lakehouse** → **Pipeline** (metadata-driven, retries, notifications) → **Direct Lake semantic model** → **Report**.
Everything lives locally and deploys to any tenant with the Fabric CLI (`fab`).

Start with the session brief: **[docs/00-meeting-brief.md](docs/00-meeting-brief.md)**

## Layout
```
src/
  data_gen/generate_data.py        deterministic fake data (stdlib only)
  fabric/
    config/table_config.json       metadata driving the ForEach load
    notebooks/nb_*.py              notebook sources (# %% cells)  → built into ipynb/ and *.Notebook/
    pipelines/pl_load_sales.DataPipeline/   pipeline JSON + .platform
    sql/                           SQL endpoint views, monitoring, reconciliation
  powerbi/Sales.pbip               PBIP: Sales.SemanticModel (TMDL, Direct Lake) + Sales.Report (PBIR)
  tools/                           build_notebooks.py, build_pbip.py
  deploy/deploy.py                 fab CLI deploy (token substitution, idempotent)
data/
  input/landing/<table>/*.csv      → Lakehouse Files/landing/
  input/incremental/, input/bad/   → Files/demo_drops/ (live demo)
  output/expected_kpis.csv         reconciliation totals
docs/                              one brief per component + demo runbook
tests/                             data integrity + cross-artifact consistency
```

## Quick start
```bash
make            # regenerate data, build notebooks + PBIP, run tests
make dry-run    # print every fab command the deploy would run

pip install ms-fabric-cli
fab auth login  # sign in to the host tenant
make deploy WS="Fabric User Group Demo" CAPACITY=<capacity-name>
```

## Docs
| | |
|---|---|
| [00 Meeting brief](docs/00-meeting-brief.md) | exec summary, agenda, takeaways, notes |
| [01 Lakehouse](docs/01-lakehouse.md) | OneLake, Files vs Tables, Delta |
| [02 Notebooks](docs/02-notebooks.md) | parameter cells, schemas, MERGE, audit |
| [03 Pipeline](docs/03-pipeline.md) | retries, catch-all failure path, notifications |
| [04 Semantic model](docs/04-semantic-model.md) | Direct Lake, TMDL, measures |
| [05 Report](docs/05-report.md) | PBIR, page design |
| [06 SQL](docs/06-sql.md) | SQL endpoint views & monitoring |
| [07 Deploy](docs/07-deploy-fab-cli.md) | fab CLI |
| [Demo runbook](docs/demo-runbook.md) | step-by-step live demo |
