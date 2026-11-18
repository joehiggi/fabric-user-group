"""Data integrity tests for the generated demo data.   python3 -m unittest -v"""
import csv
import unittest
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "data" / "input" / "landing"


def read(table: str) -> list[dict]:
    rows = []
    for f in sorted((LANDING / table).glob("*.csv")):
        with f.open(encoding="utf-8") as fh:
            rows += list(csv.DictReader(fh))
    return rows


def read_file(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class TestGeneratedData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sales = read("fact_sales")
        cls.dims = {t: read(t) for t in ("dim_customer", "dim_product", "dim_sales_rep", "dim_territory")}

    def test_tiny_but_not_trivial(self):
        self.assertGreater(len(self.sales), 1000)
        self.assertLess(len(self.sales), 10000)

    def test_primary_keys_unique(self):
        for table, key in [("dim_customer", "customer_id"), ("dim_product", "product_id"),
                           ("dim_sales_rep", "sales_rep_id"), ("dim_territory", "territory_id")]:
            ids = [r[key] for r in self.dims[table]]
            self.assertEqual(len(ids), len(set(ids)), table)
        keys = [(r["order_id"], r["order_line"]) for r in self.sales]
        self.assertEqual(len(keys), len(set(keys)))

    def test_foreign_keys_resolve(self):
        for fk, table in [("customer_id", "dim_customer"), ("product_id", "dim_product"),
                          ("sales_rep_id", "dim_sales_rep"), ("territory_id", "dim_territory")]:
            valid = {r[fk] for r in self.dims[table]}
            orphans = {r[fk] for r in self.sales} - valid
            self.assertFalse(orphans, f"orphan {fk}: {orphans}")

    def test_amount_math(self):
        for r in self.sales:
            expected = (Decimal(r["quantity"]) * Decimal(r["unit_price"]) * (1 - Decimal(r["discount_pct"]))).quantize(Decimal("0.01"))
            self.assertLessEqual(abs(expected - Decimal(r["net_amount"])), Decimal("0.01"), r["order_id"])
            self.assertGreaterEqual(Decimal(r["net_amount"]), 0)

    def test_dates_and_status(self):
        for r in self.sales:
            self.assertTrue("2025-01-01" <= r["order_date"] <= "2026-10-31")
            if r["ship_date"]:
                self.assertGreaterEqual(r["ship_date"], r["order_date"])
            if r["order_status"] in ("Cancelled", "Open"):
                self.assertEqual(r["ship_date"], "")

    def test_targets_cover_every_territory_month(self):
        targets = read("fact_sales_target")
        self.assertEqual(len(targets), 8 * 24)
        self.assertEqual({r["territory_id"] for r in targets}, {r["territory_id"] for r in self.dims["dim_territory"]})

    def test_incremental_is_new_rows_only(self):
        inc = read_file(ROOT / "data/input/incremental/fact_sales_2026-11_mtd.csv")
        self.assertTrue(inc)
        hist = {(r["order_id"], r["order_line"]) for r in self.sales}
        self.assertFalse(hist & {(r["order_id"], r["order_line"]) for r in inc})
        self.assertTrue(all(r["order_date"].startswith("2026-11") for r in inc))

    def test_bad_file_is_actually_bad(self):
        with (ROOT / "data/input/bad/fact_sales_BROKEN.csv").open() as fh:
            header = next(csv.reader(fh))
        self.assertIn("net_amt", header)
        self.assertNotIn("net_amount", header)

    def test_expected_kpis_reconcile(self):
        rev = defaultdict(Decimal)
        for r in self.sales:
            if r["order_status"] in ("Completed", "Shipped"):
                rev[r["order_date"][:4]] += Decimal(r["net_amount"])
        expected = {(r["year"], r["metric"]): Decimal(r["value"])
                    for r in read_file(ROOT / "data/output/expected_kpis.csv") if r["grain"] == "year"}
        for year, total in rev.items():
            self.assertEqual(expected[(year, "revenue")], total.quantize(Decimal("0.01")))


if __name__ == "__main__":
    unittest.main()
