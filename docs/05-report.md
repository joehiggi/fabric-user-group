# 05 · Report (PBIR / PBIP)

## Core concepts
- **PBIP** (Power BI Project) saves a report and model as folders of text files instead of one binary `.pbix`.
- **PBIR** is the report part of that format: `pages/<page>/visuals/<visual>/visual.json`. One file per visual, so it's diffable and reviewable.
- A report **binds to a semantic model**. Locally it binds `byPath`, and in the service `byConnection` (the deploy script rewrites this).

## Pages
| Page | Audience | Visuals |
|---|---|---|
| **Executive Overview** | leadership | Year + Region slicers · KPI cards (Revenue, GM %, Attainment %, YoY %) · Revenue vs Target by month (combo) · Revenue by territory |
| **Sales Performance** | sales managers | Segment + fiscal-year slicers · Region → territory matrix (Revenue, Target, Attainment, GM %, Orders) · Rep leaderboard · Revenue by category |
| **Pipeline Health** | data team | Last successful load · Failed loads · Rows loaded · DQ checks failed · Run-log table · DQ results table |

## Tips & tricks
- **Put a Pipeline Health page** in the same app. Users can see data freshness themselves.
- **Use conditional formatting by measure.** Format › Field value › `Attainment Color` keeps colour rules in the model, not in each visual.
- **Show a "Data as of" stamp** using `MAX(_loaded_at)`. It ends "is this current?" questions.
- **Lead with KPI cards, then trend, then breakdown.** That's the order executives read.
- **Run the report through tests in CI.** `tests/test_artifacts.py` checks that every field a visual uses exists in the model.

## If the generated report won't open
The visuals are generated JSON. If Desktop or the service rejects one, create the report on the deployed `Sales` model in the service, build the three pages from the table above (≈10 min), then save as PBIP / sync via Git to replace the generated version.
