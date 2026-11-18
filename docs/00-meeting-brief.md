# Fabric Tips & Tricks — Session Brief

**Presenter:** Joey Higgins · **Event:** Fabric User Group · **Date:** Thursday, 19 Nov 2026 · **Format:** 15-min talk + live demo
**Repo branch:** `tips-and-tricks`

---

## Executive summary

One small, realistic B2B sales dataset goes from **raw CSV → Lakehouse → Pipeline → Semantic Model → Report**, built so you can re-run it, test it and deploy it from code.
The point is not the data. It's the **patterns** that keep a Fabric solution reliable once it's in production:

1. **Metadata-driven loading.** One notebook and one config file load every table. Adding a table means adding a line of JSON, not building a new pipeline.
2. **Design for failure.** Retries handle transient errors, idempotent MERGE makes re-runs safe, one catch-all failure path sends the alert, and a run log plus data-quality results tell you *why* something failed.
3. **Direct Lake semantic model.** Report-speed queries over Delta tables with no import refresh. The model is defined in code (TMDL), so it can be reviewed and diffed.
4. **Everything as code.** Notebooks, pipeline JSON, TMDL, PBIR and SQL live in Git, and one `fab` CLI script deploys them to any tenant.

## Agenda (15 min total)

| Slide | Segment | Doc |
|---|---|---|
| 1 | Title | |
| 2 | The dataset: a made-up B2B seller | this page (dataset section) |
| 3 | Live demo: 01 Ingest · 02 Transform · 03 Model · 04 Serve | [runbook](demo-runbook.md) · [01](01-lakehouse.md) · [02](02-notebooks.md) · [03](03-pipeline.md) · [06](06-sql.md) · [04](04-semantic-model.md) · [05](05-report.md) |
| 4 | Recap: four habits to take home | |
| 5 | Let's connect (LinkedIn + repo) · Q&A | |

Not on stage, but in the repo for anyone who asks: deep dives in each doc, and the fab CLI deploy ([07](07-deploy-fab-cli.md)).

## The dataset (company-agnostic)

A fictional solutions provider selling **Software, Services, Hardware and Support** to 60 business customers across **8 territories in 3 regions**, Jan 2025 to Nov 2026.

| Table | Rows | Grain |
|---|---|---|
| `fact_sales` | 2,901 (+~67 Nov MTD) | order line |
| `fact_sales_target` | 192 | territory × month |
| `dim_customer` / `dim_product` / `dim_sales_rep` / `dim_territory` | 60 / 16 / 12 / 8 | one row per member |
| `dim_date` | ~1,460 | day (generated, fiscal year starts July) |
| `etl_run_log`, `dq_results` | grows per run | ops tables written by the notebooks |

## Key takeaways (for the closing slide)

- **Retries are for transient faults. Bad data should fail fast and loudly.**
- **Make every load idempotent.** With MERGE on business keys you can always just re-run.
- **Model once, in code.** TMDL + PBIR + Git gives you real code review for BI.
- **Observe your pipelines like a product.** Run log, data-quality results and a health page.

---

## Meeting notes (fill in on the day)

**Attendees:**
**Questions asked:**
-
-

**Follow-ups / things to share after:**
- [ ] Share repo link
- [ ] Share slides
-

**Ideas for next session:**
-
