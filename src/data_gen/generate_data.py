#!/usr/bin/env python3
"""
Generate a tiny, reproducible, company-agnostic B2B sales dataset.

Story: a fictional solutions provider sells software subscriptions, professional
services, edge hardware and support to other businesses across 8 territories.

Outputs
  data/input/landing/...      files you upload to Lakehouse  Files/landing/
  data/input/incremental/...  month-to-date drop for the "incremental load" demo
  data/input/bad/...          a broken file for the "failure + notification" demo
  data/output/expected_kpis.csv  reconciliation totals (what the report SHOULD say)

Stdlib only. Same seed -> same data, every time.
    python3 src/data_gen/generate_data.py
"""
from __future__ import annotations

import csv
import datetime as dt
import random
import shutil
from collections import defaultdict
from pathlib import Path

SEED = 20261119
ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data" / "input"
OUTPUT = ROOT / "data" / "output"

HISTORY_START = dt.date(2025, 1, 1)
HISTORY_END = dt.date(2026, 10, 31)
INCREMENT_START = dt.date(2026, 11, 1)
INCREMENT_END = dt.date(2026, 11, 15)
AS_OF = dt.date(2026, 11, 16)  # "today" for order-status logic

REVENUE_STATUSES = {"Completed", "Shipped"}

# --------------------------------------------------------------------------- #
# Dimensions
# --------------------------------------------------------------------------- #
TERRITORIES = [
    # id, name, region, volume weight, cities
    ("T01", "North America East", "Americas", 1.30, [("New York", "United States"), ("Boston", "United States"), ("Atlanta", "United States"), ("Toronto", "Canada")]),
    ("T02", "North America Central", "Americas", 1.00, [("Chicago", "United States"), ("Dallas", "United States"), ("Minneapolis", "United States")]),
    ("T03", "North America West", "Americas", 1.15, [("Seattle", "United States"), ("San Francisco", "United States"), ("Denver", "United States"), ("Vancouver", "Canada")]),
    ("T04", "Latin America", "Americas", 0.60, [("Sao Paulo", "Brazil"), ("Mexico City", "Mexico"), ("Bogota", "Colombia"), ("Santiago", "Chile")]),
    ("T05", "Northern Europe", "EMEA", 1.05, [("London", "United Kingdom"), ("Dublin", "Ireland"), ("Amsterdam", "Netherlands"), ("Stockholm", "Sweden"), ("Berlin", "Germany")]),
    ("T06", "Southern Europe", "EMEA", 0.70, [("Paris", "France"), ("Madrid", "Spain"), ("Milan", "Italy"), ("Lisbon", "Portugal")]),
    ("T07", "Australia & New Zealand", "APAC", 0.55, [("Sydney", "Australia"), ("Melbourne", "Australia"), ("Auckland", "New Zealand")]),
    ("T08", "Southeast Asia", "APAC", 0.65, [("Singapore", "Singapore"), ("Kuala Lumpur", "Malaysia"), ("Manila", "Philippines")]),
]

REGION_DIRECTORS = {
    "Americas": ("SR01", "Morgan Ellis"),
    "EMEA": ("SR02", "Priya Raman"),
    "APAC": ("SR03", "Daniel Okafor"),
}
ACCOUNT_EXECS = [
    ("SR04", "Avery Chen", "T01"), ("SR05", "Jordan Brooks", "T01"),
    ("SR06", "Sam Whitaker", "T02"), ("SR07", "Elena Vasquez", "T03"),
    ("SR08", "Lucas Ferreira", "T04"), ("SR09", "Hannah Lindqvist", "T05"),
    ("SR10", "Marco Bellini", "T06"), ("SR11", "Grace Thompson", "T07"),
    ("SR12", "Wei Ling Tan", "T08"),
]

# id, name, category, subcategory, list price, unit cost, qty range
PRODUCTS = [
    ("P001", "Platform Subscription - Core", "Software", "Platform", 12000, 2400, (1, 2)),
    ("P002", "Platform Subscription - Professional", "Software", "Platform", 24000, 4800, (1, 2)),
    ("P003", "Platform Subscription - Enterprise", "Software", "Platform", 60000, 12000, (1, 1)),
    ("P004", "Analytics Add-on", "Software", "Add-on", 8000, 1600, (1, 3)),
    ("P005", "Security & Compliance Add-on", "Software", "Add-on", 9500, 1900, (1, 3)),
    ("P006", "Integration Add-on", "Software", "Add-on", 6000, 1200, (1, 3)),
    ("P007", "Implementation Services (day)", "Services", "Delivery", 1800, 1100, (3, 25)),
    ("P008", "Training Workshop", "Services", "Enablement", 3500, 1800, (1, 4)),
    ("P009", "Advisory Retainer (month)", "Services", "Advisory", 7500, 4500, (1, 6)),
    ("P010", "Data Migration Package", "Services", "Delivery", 15000, 9000, (1, 1)),
    ("P011", "Edge Gateway", "Hardware", "Devices", 2400, 1450, (2, 30)),
    ("P012", "Sensor Kit (10-pack)", "Hardware", "Devices", 950, 520, (5, 60)),
    ("P013", "Rugged Tablet", "Hardware", "Devices", 1600, 1050, (5, 40)),
    ("P014", "Standard Support (annual)", "Support", "Support Plans", 4000, 1200, (1, 1)),
    ("P015", "Premium Support (annual)", "Support", "Support Plans", 10000, 3500, (1, 1)),
    ("P016", "Extended Hardware Warranty", "Support", "Warranty", 600, 150, (2, 30)),
]
# relative pick-weights by segment (index aligned with PRODUCTS)
PRODUCT_WEIGHTS = {
    "Enterprise": [2, 4, 5, 4, 4, 3, 6, 3, 3, 2, 3, 3, 2, 2, 4, 2],
    "Mid-Market": [4, 5, 1, 3, 3, 3, 5, 3, 2, 1, 3, 3, 3, 3, 2, 2],
    "SMB":        [6, 2, 0, 2, 2, 2, 3, 3, 1, 0, 2, 3, 2, 4, 1, 2],
}

CUSTOMER_PREFIX = ["Apex", "Bluewater", "Cedar", "Summit", "Northbridge", "Ironwood",
                   "Silverline", "Harborview", "Keystone", "Meridian", "Pinecrest",
                   "Redstone", "Clearpath", "Brightwell", "Granite", "Lakeshore",
                   "Oakridge", "Stonegate", "Riverbend", "Westfield"]
CUSTOMER_SUFFIX = [("Logistics", "Transportation & Logistics"), ("Health", "Healthcare"),
                   ("Manufacturing", "Manufacturing"), ("Financial", "Financial Services"),
                   ("Energy", "Energy & Utilities"), ("Retail Group", "Retail"),
                   ("Foods", "Consumer Goods"), ("Engineering", "Professional Services"),
                   ("Partners", "Professional Services"), ("Labs", "Life Sciences")]

SEASONALITY = {1: .80, 2: .85, 3: 1.10, 4: .90, 5: .95, 6: 1.15,
               7: .80, 8: .80, 9: 1.10, 10: 1.00, 11: 1.10, 12: 1.40}
SEGMENT_DISCOUNT = {"Enterprise": (0.10, 0.25), "Mid-Market": (0.05, 0.15), "SMB": (0.00, 0.10)}
SEGMENT_FREQ = {"Enterprise": 3.0, "Mid-Market": 2.0, "SMB": 1.0}


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {path.relative_to(ROOT)}  ({len(rows)} rows)")


def month_start(d: dt.date) -> dt.date:
    return d.replace(day=1)


def build_dimensions(rng: random.Random):
    territories = [[t[0], t[1], t[2]] for t in TERRITORIES]

    reps = []
    for region, (rid, name) in REGION_DIRECTORS.items():
        reps.append([rid, name, "Regional Director", region, "", "", "2019-04-01"])
    for rid, name, tid in ACCOUNT_EXECS:
        region = next(t[2] for t in TERRITORIES if t[0] == tid)
        hire = dt.date(2020, 1, 1) + dt.timedelta(days=rng.randint(0, 1600))
        reps.append([rid, name, "Account Executive", region, tid,
                     REGION_DIRECTORS[region][0], hire.isoformat()])

    products = [[p[0], p[1], p[2], p[3], f"{p[4]:.2f}", f"{p[5]:.2f}"] for p in PRODUCTS]

    customers, used = [], set()
    tweights = [t[3] for t in TERRITORIES]
    for i in range(1, 61):
        while True:
            pre, (suf, industry) = rng.choice(CUSTOMER_PREFIX), rng.choice(CUSTOMER_SUFFIX)
            name = f"{pre} {suf}"
            if name not in used:
                used.add(name)
                break
        terr = rng.choices(TERRITORIES, weights=tweights)[0]
        city, country = rng.choice(terr[4])
        segment = rng.choices(["Enterprise", "Mid-Market", "SMB"], weights=[2, 3, 3])[0]
        since = dt.date(2018, 1, 1) + dt.timedelta(days=rng.randint(0, 2500))
        customers.append([f"C{i:04d}", name, industry, segment, terr[0], city, country,
                          min(since, HISTORY_START).isoformat()])
    return territories, reps, products, customers


def build_sales(rng, customers, start, end, first_order_no):
    cust_weights = [SEGMENT_FREQ[c[3]] for c in customers]
    aes_by_terr = defaultdict(list)
    for rid, _, tid in ACCOUNT_EXECS:
        aes_by_terr[tid].append(rid)

    rows, order_no, d = [], first_order_no, start
    while d <= end:
        if d.weekday() < 5:  # B2B: weekdays only
            years_in = (d - HISTORY_START).days / 365.0
            lam = 3.0 * SEASONALITY[d.month] * (1 + 0.14 * years_in)
            n_orders = sum(1 for _ in range(10) if rng.random() < lam / 10)
            for _ in range(n_orders):
                order_no += 1
                cust = rng.choices(customers, weights=cust_weights)[0]
                cid, segment, tid = cust[0], cust[3], cust[4]
                rep = rng.choice(aes_by_terr[tid])
                channel = rng.choices(["Direct", "Partner", "Online"],
                                      weights=[6, 3, 3 if segment == "SMB" else 0.5])[0]
                age = (AS_OF - d).days
                if age > 30:
                    status = rng.choices(["Completed", "Cancelled", "Returned"], weights=[92, 5, 3])[0]
                else:
                    status = rng.choices(["Shipped", "Open", "Cancelled"], weights=[70, 27, 3])[0]
                ship = "" if status in ("Cancelled", "Open") else (d + dt.timedelta(days=rng.randint(1, 10))).isoformat()
                lo, hi = SEGMENT_DISCOUNT[segment]
                n_lines = rng.choices([1, 2, 3, 4], weights=[40, 35, 18, 7])[0]
                picked, line = set(), 0
                for _ in range(n_lines):
                    idx = rng.choices(range(len(PRODUCTS)), weights=PRODUCT_WEIGHTS[segment])[0]
                    if idx in picked:
                        continue
                    picked.add(idx)
                    line += 1
                    pid, _, _, _, price, cost, (qlo, qhi) = PRODUCTS[idx]
                    unit_price = round(price * (1.04 if d.year >= 2026 else 1.0), 2)  # 2026 price uplift
                    qty = rng.randint(qlo, qhi)
                    disc = round(rng.uniform(lo, hi) + (0.05 if channel == "Partner" else 0), 2)
                    net = round(qty * unit_price * (1 - disc), 2)
                    rows.append([f"SO-{order_no:06d}", line, d.isoformat(), ship, cid, pid, rep, tid,
                                 channel, qty, f"{unit_price:.2f}", f"{disc:.2f}", f"{net:.2f}",
                                 f"{qty * cost:.2f}", status])
        d += dt.timedelta(days=1)
    return rows, order_no


SALES_HEADER = ["order_id", "order_line", "order_date", "ship_date", "customer_id", "product_id",
                "sales_rep_id", "territory_id", "channel", "quantity", "unit_price",
                "discount_pct", "net_amount", "cost_amount", "order_status"]


def build_targets(rng, sales_rows):
    actual = defaultdict(float)
    for r in sales_rows:
        if r[14] in REVENUE_STATUSES:
            actual[(r[7], month_start(dt.date.fromisoformat(r[2])))] += float(r[12])
    rows = []
    for t in TERRITORIES:
        for year in (2025, 2026):
            for m in range(1, 13):
                ms = dt.date(year, m, 1)
                base = actual.get((t[0], dt.date(2025, m, 1)), 0.0)
                if base == 0:
                    base = 40000 * t[3] * SEASONALITY[m]
                factor = rng.uniform(0.92, 1.10) if year == 2025 else rng.uniform(1.08, 1.25)
                rows.append([t[0], ms.isoformat(), f"{round(base * factor, -3):.2f}"])
    return rows


def build_expected(sales_rows):
    """Reconciliation targets: what Fabric should show after the HISTORY load."""
    by_year, by_terr = defaultdict(lambda: [0.0, 0.0, set()]), defaultdict(float)
    for r in sales_rows:
        if r[14] not in REVENUE_STATUSES:
            continue
        y = r[2][:4]
        by_year[y][0] += float(r[12])
        by_year[y][1] += float(r[13])
        by_year[y][2].add(r[0])
        by_terr[(y, r[7])] += float(r[12])
    out = []
    for y, (rev, cost, orders) in sorted(by_year.items()):
        out.append(["year", y, "ALL", "revenue", f"{rev:.2f}"])
        out.append(["year", y, "ALL", "gross_margin", f"{rev - cost:.2f}"])
        out.append(["year", y, "ALL", "orders", str(len(orders))])
    for (y, tid), rev in sorted(by_terr.items()):
        out.append(["year_territory", y, tid, "revenue", f"{rev:.2f}"])
    return out


def main() -> None:
    rng = random.Random(SEED)
    for sub in ("landing", "incremental", "bad"):
        shutil.rmtree(INPUT / sub, ignore_errors=True)

    print("Generating demo data ...")
    territories, reps, products, customers = build_dimensions(rng)
    land = INPUT / "landing"
    write_csv(land / "dim_territory" / "dim_territory.csv", ["territory_id", "territory_name", "region"], territories)
    write_csv(land / "dim_sales_rep" / "dim_sales_rep.csv",
              ["sales_rep_id", "sales_rep_name", "title", "region", "territory_id", "manager_id", "hire_date"], reps)
    write_csv(land / "dim_product" / "dim_product.csv",
              ["product_id", "product_name", "category", "subcategory", "list_price", "unit_cost"], products)
    write_csv(land / "dim_customer" / "dim_customer.csv",
              ["customer_id", "customer_name", "industry", "segment", "territory_id", "city", "country",
               "customer_since"], customers)

    history, last_no = build_sales(rng, customers, HISTORY_START, HISTORY_END, 250000)
    write_csv(land / "fact_sales" / "fact_sales_2025_2026-10.csv", SALES_HEADER, history)
    write_csv(land / "fact_sales_target" / "fact_sales_target.csv",
              ["territory_id", "month_start_date", "target_amount"], build_targets(rng, history))

    increment, _ = build_sales(rng, customers, INCREMENT_START, INCREMENT_END, last_no)
    write_csv(INPUT / "incremental" / "fact_sales_2026-11_mtd.csv", SALES_HEADER, increment)

    # Broken file: schema drift (renamed column) + a non-numeric quantity
    bad_header = [("net_amt" if c == "net_amount" else c) for c in SALES_HEADER]
    bad_rows = [list(r) for r in increment[:12]]
    bad_rows[3][9] = "N/A"
    write_csv(INPUT / "bad" / "fact_sales_BROKEN.csv", bad_header, bad_rows)

    write_csv(OUTPUT / "expected_kpis.csv", ["grain", "year", "territory_id", "metric", "value"],
              build_expected(history))
    print("Done.")


if __name__ == "__main__":
    main()
