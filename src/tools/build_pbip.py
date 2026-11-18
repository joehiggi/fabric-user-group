#!/usr/bin/env python3
"""
Generate the Power BI Project (PBIP): a Direct Lake semantic model in TMDL plus a
3-page report in PBIR format, all from ONE spec in this file.

    python3 src/tools/build_pbip.py

Output: src/powerbi/Sales.pbip, Sales.SemanticModel/, Sales.Report/
The {{SQL_ENDPOINT_*}} tokens in expressions.tmdl are filled by src/deploy/deploy.py
(or replace them by hand to open the project in Power BI Desktop).
"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "src" / "powerbi"
NS = uuid.UUID("6f1c0e2a-6b7e-4c55-9a51-fab41c0de001")  # stable GUIDs across rebuilds
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"

USD, PCT, INT, DT = r"\$#,0", "0.0%;-0.0%;0.0%", "#,0", "yyyy-mm-dd"

# --------------------------------------------------------------------------- #
# Semantic model spec
#   column: (name, dataType, formatString|None, options)
#   options: hidden, sortBy, key, summarize
# --------------------------------------------------------------------------- #
AUDIT = [("_source_file", "string", None, {"hidden": True}),
         ("_batch_id", "string", None, {"hidden": True}),
         ("_loaded_at", "dateTime", "yyyy-mm-dd hh:nn", {"hidden": True})]

TABLES: dict[str, dict] = {
    "dim_date": {"dataCategory": "Time", "columns": [
        ("date", "dateTime", DT, {"key": True}),
        ("date_key", "int64", "0", {"hidden": True}),
        ("year", "int64", "0", {}),
        ("quarter", "string", None, {}),
        ("month_number", "int64", "0", {"hidden": True}),
        ("month_name", "string", None, {"sortBy": "month_number"}),
        ("month_short", "string", None, {"sortBy": "month_number"}),
        ("month_start_date", "dateTime", DT, {}),
        ("year_month", "string", None, {"sortBy": "year_month_sort"}),
        ("year_month_sort", "int64", "0", {"hidden": True}),
        ("day_of_week_number", "int64", "0", {"hidden": True}),
        ("day_name", "string", None, {"sortBy": "day_of_week_number"}),
        ("is_weekend", "boolean", None, {}),
        ("iso_week", "int64", "0", {}),
        ("fiscal_year_number", "int64", "0", {"hidden": True}),
        ("fiscal_year", "string", None, {"sortBy": "fiscal_year_number"}),
        ("fiscal_quarter", "string", None, {}),
        ("is_current_month", "boolean", None, {}),
        ("is_past_or_today", "boolean", None, {}),
        ("is_ytd", "boolean", None, {}),
    ]},
    "dim_customer": {"columns": [
        ("customer_id", "string", None, {"hidden": True}),
        ("customer_name", "string", None, {}),
        ("industry", "string", None, {}),
        ("segment", "string", None, {}),
        ("territory_id", "string", None, {"hidden": True}),
        ("city", "string", None, {}),
        ("country", "string", None, {}),
        ("customer_since", "dateTime", DT, {}),
    ] + AUDIT},
    "dim_product": {"columns": [
        ("product_id", "string", None, {"hidden": True}),
        ("product_name", "string", None, {}),
        ("category", "string", None, {}),
        ("subcategory", "string", None, {}),
        ("list_price", "decimal", USD, {"summarize": "none"}),
        ("unit_cost", "decimal", USD, {"summarize": "none"}),
    ] + AUDIT},
    "dim_territory": {"columns": [
        ("territory_id", "string", None, {"hidden": True}),
        ("territory_name", "string", None, {}),
        ("region", "string", None, {}),
    ] + AUDIT},
    "dim_sales_rep": {"columns": [
        ("sales_rep_id", "string", None, {"hidden": True}),
        ("sales_rep_name", "string", None, {}),
        ("title", "string", None, {}),
        ("region", "string", None, {}),
        ("territory_id", "string", None, {"hidden": True}),
        ("manager_id", "string", None, {"hidden": True}),
        ("hire_date", "dateTime", DT, {}),
    ] + AUDIT},
    "fact_sales": {"columns": [
        ("order_id", "string", None, {}),
        ("order_line", "int64", "0", {"hidden": True}),
        ("order_date", "dateTime", DT, {"hidden": True}),
        ("ship_date", "dateTime", DT, {}),
        ("customer_id", "string", None, {"hidden": True}),
        ("product_id", "string", None, {"hidden": True}),
        ("sales_rep_id", "string", None, {"hidden": True}),
        ("territory_id", "string", None, {"hidden": True}),
        ("channel", "string", None, {}),
        ("quantity", "int64", INT, {"hidden": True}),
        ("unit_price", "decimal", USD, {"hidden": True}),
        ("discount_pct", "decimal", PCT, {"hidden": True}),
        ("net_amount", "decimal", USD, {"hidden": True}),
        ("cost_amount", "decimal", USD, {"hidden": True}),
        ("order_status", "string", None, {}),
    ] + AUDIT},
    "fact_sales_target": {"columns": [
        ("territory_id", "string", None, {"hidden": True}),
        ("month_start_date", "dateTime", DT, {"hidden": True}),
        ("target_amount", "decimal", USD, {"hidden": True}),
    ] + AUDIT},
    "etl_run_log": {"columns": [
        ("batch_id", "string", None, {}),
        ("table_name", "string", None, {}),
        ("source_path", "string", None, {}),
        ("load_mode", "string", None, {}),
        ("status", "string", None, {}),
        ("rows_read", "int64", INT, {}),
        ("started_at", "dateTime", "yyyy-mm-dd hh:nn:ss", {}),
        ("ended_at", "dateTime", "yyyy-mm-dd hh:nn:ss", {}),
        ("duration_sec", "double", "0.0", {}),
        ("error_message", "string", None, {}),
    ]},
    "dq_results": {"columns": [
        ("batch_id", "string", None, {}),
        ("checked_at", "dateTime", "yyyy-mm-dd hh:nn:ss", {}),
        ("check_name", "string", None, {}),
        ("severity", "string", None, {}),
        ("bad_rows", "int64", INT, {}),
        ("result", "string", None, {}),
    ]},
}

REV = 'KEEPFILTERS ( fact_sales[order_status] IN { "Completed", "Shipped" } )'
# (table, name, DAX, formatString, displayFolder, description)
MEASURES = [
    ("fact_sales", "Revenue", f"CALCULATE ( SUM ( fact_sales[net_amount] ), {REV} )", USD, "Sales", "Net revenue from Completed + Shipped orders."),
    ("fact_sales", "Cost", f"CALCULATE ( SUM ( fact_sales[cost_amount] ), {REV} )", USD, "Sales", ""),
    ("fact_sales", "Gross Margin", "[Revenue] - [Cost]", USD, "Sales", ""),
    ("fact_sales", "Gross Margin %", "DIVIDE ( [Gross Margin], [Revenue] )", PCT, "Sales", ""),
    ("fact_sales", "Orders", f"CALCULATE ( DISTINCTCOUNT ( fact_sales[order_id] ), {REV} )", INT, "Sales", ""),
    ("fact_sales", "Avg Order Value", "DIVIDE ( [Revenue], [Orders] )", USD, "Sales", ""),
    ("fact_sales", "Units", f"CALCULATE ( SUM ( fact_sales[quantity] ), {REV} )", INT, "Sales", ""),
    ("fact_sales", "Avg Discount %", "AVERAGE ( fact_sales[discount_pct] )", PCT, "Sales", ""),
    ("fact_sales", "Cancellation Rate",
     'DIVIDE ( CALCULATE ( DISTINCTCOUNT ( fact_sales[order_id] ), fact_sales[order_status] = "Cancelled" ), DISTINCTCOUNT ( fact_sales[order_id] ) )',
     PCT, "Sales", ""),
    ("fact_sales", "Revenue PY", "CALCULATE ( [Revenue], SAMEPERIODLASTYEAR ( dim_date[date] ) )", USD, "Time Intelligence", ""),
    ("fact_sales", "Revenue YoY %", "DIVIDE ( [Revenue] - [Revenue PY], [Revenue PY] )", PCT, "Time Intelligence", ""),
    ("fact_sales", "Revenue YTD", "TOTALYTD ( [Revenue], dim_date[date] )", USD, "Time Intelligence", ""),
    ("fact_sales", "Revenue MTD", "TOTALMTD ( [Revenue], dim_date[date] )", USD, "Time Intelligence", ""),
    ("fact_sales", "Target", "SUM ( fact_sales_target[target_amount] )", USD, "Targets", "Monthly target, stored on the 1st of each month."),
    ("fact_sales", "Variance to Target", "[Revenue] - [Target]", USD, "Targets", ""),
    ("fact_sales", "Target Attainment %", "DIVIDE ( [Revenue], [Target] )", PCT, "Targets", ""),
    ("fact_sales", "Attainment Color",
     'SWITCH ( TRUE (), ISBLANK ( [Target] ), BLANK (), [Target Attainment %] >= 1, "#1B7F5C", [Target Attainment %] >= 0.9, "#C98A00", "#B23A3A" )',
     None, "Targets", "Use in conditional formatting: Format > Field value."),
    ("fact_sales", "Rep Revenue Rank",
     "IF ( HASONEVALUE ( dim_sales_rep[sales_rep_name] ), RANKX ( ALLSELECTED ( dim_sales_rep[sales_rep_name] ), [Revenue] ) )",
     "0", "Sales", ""),
    ("fact_sales", "Data As Of", "MAX ( fact_sales[_loaded_at] )", "yyyy-mm-dd hh:nn", "Ops", ""),
    ("etl_run_log", "Load Runs", "COUNTROWS ( etl_run_log )", INT, "Ops", ""),
    ("etl_run_log", "Failed Loads", 'CALCULATE ( COUNTROWS ( etl_run_log ), etl_run_log[status] = "Failed" )', INT, "Ops", ""),
    ("etl_run_log", "Rows Loaded", 'CALCULATE ( SUM ( etl_run_log[rows_read] ), etl_run_log[status] = "Succeeded" )', INT, "Ops", ""),
    ("etl_run_log", "Last Successful Load", 'CALCULATE ( MAX ( etl_run_log[ended_at] ), etl_run_log[status] = "Succeeded" )', "yyyy-mm-dd hh:nn", "Ops", ""),
    ("etl_run_log", "Avg Load Seconds", "AVERAGE ( etl_run_log[duration_sec] )", "0.0", "Ops", ""),
    ("dq_results", "DQ Checks Failed", 'CALCULATE ( COUNTROWS ( dq_results ), dq_results[result] = "Fail" )', INT, "Ops", ""),
]

RELATIONSHIPS = [
    ("fact_sales", "order_date", "dim_date", "date"),
    ("fact_sales", "customer_id", "dim_customer", "customer_id"),
    ("fact_sales", "product_id", "dim_product", "product_id"),
    ("fact_sales", "sales_rep_id", "dim_sales_rep", "sales_rep_id"),
    ("fact_sales", "territory_id", "dim_territory", "territory_id"),
    ("fact_sales_target", "month_start_date", "dim_date", "date"),
    ("fact_sales_target", "territory_id", "dim_territory", "territory_id"),
]

# --------------------------------------------------------------------------- #
# Report spec: page -> visuals (type, x, y, w, h, {role: [fields]})
#   field "t.c" = column, "t.[m]" = measure
# --------------------------------------------------------------------------- #
PAGES = [
    ("executive_overview", "Executive Overview", [
        ("slicer", 20, 20, 240, 60, {"Values": ["dim_date.year"]}),
        ("slicer", 270, 20, 240, 60, {"Values": ["dim_territory.region"]}),
        ("card", 20, 100, 300, 120, {"Values": ["fact_sales.[Revenue]"]}),
        ("card", 335, 100, 300, 120, {"Values": ["fact_sales.[Gross Margin %]"]}),
        ("card", 650, 100, 300, 120, {"Values": ["fact_sales.[Target Attainment %]"]}),
        ("card", 965, 100, 295, 120, {"Values": ["fact_sales.[Revenue YoY %]"]}),
        ("lineClusteredColumnComboChart", 20, 240, 780, 460,
         {"Category": ["dim_date.year_month"], "Y": ["fact_sales.[Revenue]"], "Y2": ["fact_sales.[Target]"]}),
        ("clusteredBarChart", 815, 240, 445, 460,
         {"Category": ["dim_territory.territory_name"], "Y": ["fact_sales.[Revenue]"]}),
    ]),
    ("sales_performance", "Sales Performance", [
        ("slicer", 20, 20, 240, 60, {"Values": ["dim_customer.segment"]}),
        ("slicer", 270, 20, 240, 60, {"Values": ["dim_date.fiscal_year"]}),
        ("pivotTable", 20, 100, 700, 600,
         {"Rows": ["dim_territory.region", "dim_territory.territory_name"],
          "Values": ["fact_sales.[Revenue]", "fact_sales.[Target]", "fact_sales.[Target Attainment %]",
                     "fact_sales.[Gross Margin %]", "fact_sales.[Orders]"]}),
        ("clusteredBarChart", 735, 100, 525, 290,
         {"Category": ["dim_sales_rep.sales_rep_name"], "Y": ["fact_sales.[Revenue]"]}),
        ("clusteredBarChart", 735, 410, 525, 290,
         {"Category": ["dim_product.category"], "Y": ["fact_sales.[Revenue]"]}),
    ]),
    ("pipeline_health", "Pipeline Health", [
        ("card", 20, 20, 300, 120, {"Values": ["etl_run_log.[Last Successful Load]"]}),
        ("card", 335, 20, 300, 120, {"Values": ["etl_run_log.[Failed Loads]"]}),
        ("card", 650, 20, 300, 120, {"Values": ["etl_run_log.[Rows Loaded]"]}),
        ("card", 965, 20, 295, 120, {"Values": ["dq_results.[DQ Checks Failed]"]}),
        ("tableEx", 20, 160, 760, 540,
         {"Values": ["etl_run_log.started_at", "etl_run_log.table_name", "etl_run_log.status",
                     "etl_run_log.rows_read", "etl_run_log.duration_sec", "etl_run_log.error_message"]}),
        ("tableEx", 795, 160, 465, 540,
         {"Values": ["dq_results.checked_at", "dq_results.check_name", "dq_results.severity",
                     "dq_results.result", "dq_results.bad_rows"]}),
    ]),
]


def gid(*parts: str) -> str:
    return str(uuid.uuid5(NS, "/".join(parts)))


def q(name: str) -> str:
    """TMDL object name quoting."""
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def wjson(path: Path, obj) -> None:
    write(path, json.dumps(obj, indent=2) + "\n")


def platform(kind: str, name: str) -> dict:
    return {"$schema": f"{SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": kind, "displayName": name},
            "config": {"version": "2.0", "logicalId": gid("platform", kind, name)}}


# --------------------------------------------------------------------------- #
def build_semantic_model(sm: Path) -> None:
    d = sm / "definition"
    wjson(sm / "definition.pbism", {"version": "4.0", "settings": {}})
    wjson(sm / ".platform", platform("SemanticModel", "Sales"))
    write(d / "database.tmdl", "database\n\tcompatibilityLevel: 1604\n")
    write(d / "model.tmdl",
          "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
          "\tsourceQueryCulture: en-US\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
          + "".join(f"ref table {q(t)}\n" for t in TABLES))
    write(d / "expressions.tmdl",
          "/// Direct Lake source. Lakehouse > SQL analytics endpoint > Settings: copy the\n"
          "/// SQL connection string and the endpoint ID (GUID in the browser URL).\n"
          "expression DatabaseQuery =\n\t\tlet\n"
          '\t\t    database = Sql.Database("{{SQL_ENDPOINT_CONNECTION_STRING}}", "{{SQL_ENDPOINT_ID}}")\n'
          "\t\tin\n\t\t    database\n\tlineageTag: " + gid("expr", "DatabaseQuery") + "\n")

    rels = []
    for ft, fc, tt, tc in RELATIONSHIPS:
        rels.append(f"relationship {gid('rel', ft, fc, tt, tc)}\n\tfromColumn: {ft}.{fc}\n\ttoColumn: {tt}.{tc}\n")
    write(d / "relationships.tmdl", "\n".join(rels))

    for t, spec in TABLES.items():
        lines = [f"table {q(t)}", f"\tlineageTag: {gid('table', t)}"]
        if spec.get("dataCategory"):
            lines.append(f"\tdataCategory: {spec['dataCategory']}")
        lines.append("")
        for (mt, name, dax, fmt, folder, desc) in MEASURES:
            if mt != t:
                continue
            if desc:
                lines.append(f"\t/// {desc}")
            lines.append(f"\tmeasure {q(name)} = {dax}")
            if fmt:
                lines.append(f"\t\tformatString: {fmt}")
            lines.append(f"\t\tdisplayFolder: {folder}")
            lines.append(f"\t\tlineageTag: {gid('measure', t, name)}")
            lines.append("")
        for (c, dtype, fmt, opt) in spec["columns"]:
            lines.append(f"\tcolumn {q(c)}")
            lines.append(f"\t\tdataType: {dtype}")
            if fmt:
                lines.append(f"\t\tformatString: {fmt}")
            if opt.get("key"):
                lines.append("\t\tisKey")
            if opt.get("hidden"):
                lines.append("\t\tisHidden")
            numeric = dtype in ("int64", "decimal", "double")
            lines.append(f"\t\tsummarizeBy: {opt.get('summarize', 'sum' if numeric and not fmt == '0' else 'none')}")
            lines.append(f"\t\tsourceColumn: {c}")
            if opt.get("sortBy"):
                lines.append(f"\t\tsortByColumn: {opt['sortBy']}")
            lines.append(f"\t\tlineageTag: {gid('column', t, c)}")
            lines.append("")
        lines += [f"\tpartition {q(t)} = entity", "\t\tmode: directLake", "\t\tsource",
                  f"\t\t\tentityName: {t}", "\t\t\tschemaName: dbo", "\t\t\texpressionSource: DatabaseQuery", ""]
        write(d / "tables" / f"{t}.tmdl", "\n".join(lines))


def field(ref: str) -> tuple[dict, str]:
    table, prop = ref.split(".", 1)
    src = {"Expression": {"SourceRef": {"Entity": table}}}
    if prop.startswith("[") and prop.endswith("]"):
        prop = prop[1:-1]
        return {"Measure": {**src, "Property": prop}}, f"{table}.{prop}"
    return {"Column": {**src, "Property": prop}}, f"{table}.{prop}"


def build_report(rp: Path) -> None:
    d = rp / "definition"
    wjson(rp / "definition.pbir", {"$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
                                   "version": "4.0", "datasetReference": {"byPath": {"path": "../Sales.SemanticModel"}}})
    wjson(rp / ".platform", platform("Report", "Sales"))
    wjson(d / "version.json", {"$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json",
                               "version": "2.0.0"})
    wjson(d / "report.json", {
        "$schema": f"{SCHEMA}/item/report/definition/report/1.0.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": "5.61",
                                          "type": "SharedResources"}},
        "layoutOptimization": "None"})
    wjson(rp / "StaticResources" / "SharedResources" / "BaseThemes" / "CY24SU10.json", {
        "name": "CY24SU10",
        "dataColors": ["#1F4E79", "#2E86AB", "#1B7F5C", "#C98A00", "#B23A3A", "#6C5B7B", "#5C6B73", "#9DB4C0"],
        "foreground": "#1F2933", "background": "#FFFFFF", "tableAccent": "#1F4E79"})
    wjson(d / "pages" / "pages.json", {"$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
                                       "pageOrder": [p[0] for p in PAGES], "activePageName": PAGES[0][0]})
    for page_id, title, visuals in PAGES:
        pd = d / "pages" / page_id
        wjson(pd / "page.json", {"$schema": f"{SCHEMA}/item/report/definition/page/1.0.0/schema.json",
                                 "name": page_id, "displayName": title, "displayOption": "FitToPage",
                                 "height": 720, "width": 1280})
        for i, (vtype, x, y, w, h, roles) in enumerate(visuals):
            name = f"{page_id[:12]}_{i:02d}"
            query = {role: {"projections": [
                {"field": f, "queryRef": qr, "nativeQueryRef": qr.split(".", 1)[1]}
                for f, qr in (field(r) for r in refs)]} for role, refs in roles.items()}
            wjson(pd / "visuals" / name / "visual.json", {
                "$schema": f"{SCHEMA}/item/report/definition/visualContainer/1.0.0/schema.json",
                "name": name,
                "position": {"x": x, "y": y, "z": i, "width": w, "height": h, "tabOrder": i},
                "visual": {"visualType": vtype, "query": {"queryState": query}, "drawVisualDataBars": False}})


def main() -> None:
    for sub in ("Sales.SemanticModel", "Sales.Report"):
        shutil.rmtree(OUT / sub, ignore_errors=True)
    wjson(OUT / "Sales.pbip", {"$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
                               "artifacts": [{"report": {"path": "Sales.Report"}}],
                               "settings": {"enableAutoRecovery": True}})
    build_semantic_model(OUT / "Sales.SemanticModel")
    build_report(OUT / "Sales.Report")
    print(f"PBIP written to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
