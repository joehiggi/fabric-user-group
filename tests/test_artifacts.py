"""
Consistency tests across the Fabric artifacts: notebooks <-> CSVs <-> config <-> pipeline <-> PBIP.
Catches the classic demo-day bugs (renamed column, measure typo, missing parameter) before Thursday.
    python3 -m unittest -v
"""
import ast
import csv
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "src/fabric/notebooks"
PIPE = ROOT / "src/fabric/pipelines/pl_load_sales.DataPipeline/pipeline-content.json"
SM = ROOT / "src/powerbi/Sales.SemanticModel/definition"
RP = ROOT / "src/powerbi/Sales.Report"
AUDIT = ["_source_file", "_batch_id", "_loaded_at"]


def notebook_schemas() -> dict[str, list[str]]:
    tree = ast.parse((NB / "nb_load_table.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "SCHEMAS":
            return {k.value: [e.elts[0].value for e in v.elts] for k, v in zip(node.value.keys, node.value.values)}
    raise AssertionError("SCHEMAS not found")


def parameter_names(nb_file: Path) -> set[str]:
    src = nb_file.read_text()
    block = src.split("# %% [parameters]", 1)[1].split("# %%", 1)[0]
    return {n.targets[0].id for n in ast.parse(block).body if isinstance(n, ast.Assign)}


def tmdl_model() -> dict[str, dict[str, set]]:
    model = {}
    for f in (SM / "tables").glob("*.tmdl"):
        text = f.read_text()
        name = re.search(r"^table (\S+)", text, re.M).group(1)
        cols = set(re.findall(r"^\tcolumn '?([^'\n]+?)'?$", text, re.M))
        measures = set(re.findall(r"^\tmeasure '?(.+?)'? = ", text, re.M))
        model[name] = {"columns": cols, "measures": measures}
    return model


class TestNotebooks(unittest.TestCase):
    def test_sources_parse(self):
        for f in NB.glob("nb_*.py"):
            ast.parse(f.read_text(), filename=str(f))

    def test_schema_matches_csv_headers(self):
        for table, cols in notebook_schemas().items():
            for f in (ROOT / "data/input/landing" / table).glob("*.csv"):
                with f.open() as fh:
                    self.assertEqual(next(csv.reader(fh)), cols, f.name)

    def test_built_notebooks_are_current(self):
        for f in NB.glob("nb_*.py"):
            item = NB / f"{f.stem}.Notebook" / "notebook-content.py"
            self.assertTrue(item.exists(), f"run src/tools/build_notebooks.py ({item})")
            first_code_line = "table_name" if f.stem == "nb_load_table" else ""
            self.assertIn(first_code_line, item.read_text())
            self.assertIn("{{LAKEHOUSE_ID}}", item.read_text())


class TestConfigAndPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "src/fabric/config/table_config.json").read_text())
        cls.pipe = json.loads(PIPE.read_text())["properties"]

    def test_config_tables_have_schema_and_data(self):
        schemas = notebook_schemas()
        for t in self.config:
            self.assertIn(t["table_name"], schemas)
            self.assertTrue((ROOT / "data/input/landing" / t["table_name"]).is_dir())
            self.assertIn(t["load_mode"], {"overwrite", "append", "merge"})
            for k in t["key_columns"].split(","):
                self.assertIn(k, schemas[t["table_name"]])

    def _all_activities(self, acts=None):
        for a in acts if acts is not None else self.pipe["activities"]:
            yield a
            yield from self._all_activities(a.get("typeProperties", {}).get("activities", []))

    def test_dependencies_point_to_real_activities(self):
        top = {a["name"] for a in self.pipe["activities"]}
        for a in self.pipe["activities"]:
            for d in a.get("dependsOn", []):
                self.assertIn(d["activity"], top, a["name"])

    def test_retries_configured_on_loads(self):
        load = next(a for a in self._all_activities() if a["name"] == "Load table")
        self.assertGreaterEqual(load["policy"]["retry"], 1)

    def test_notebook_parameters_exist_in_parameter_cell(self):
        params = parameter_names(NB / "nb_load_table.py")
        load = next(a for a in self._all_activities() if a["name"] == "Load table")
        self.assertTrue(set(load["typeProperties"]["parameters"]) <= params)

    def test_failure_path_exists(self):
        names = {a["name"]: a for a in self.pipe["activities"]}
        cond = names["Notify failure"]["dependsOn"][0]["dependencyConditions"]
        self.assertEqual(set(cond), {"Failed", "Skipped"})
        self.assertEqual(names["Mark run as failed"]["type"], "Fail")


class TestPbip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = tmdl_model()

    def test_all_json_valid(self):
        for f in list((ROOT / "src/powerbi").rglob("*.json")) + list((ROOT / "src/powerbi").rglob("*.pb*")) \
                + list((ROOT / "src/powerbi").rglob(".platform")):
            json.loads(f.read_text())

    def test_model_columns_match_lake_tables(self):
        for table, cols in notebook_schemas().items():
            self.assertEqual(self.model[table]["columns"], set(cols) | set(AUDIT), table)

    def test_relationships_reference_real_columns(self):
        for t, c in re.findall(r"(?:from|to)Column: (\w+)\.(\w+)", (SM / "relationships.tmdl").read_text()):
            self.assertIn(c, self.model[t]["columns"], f"{t}.{c}")

    def test_measure_references_resolve(self):
        all_measures = set().union(*(m["measures"] for m in self.model.values()))
        for f in (SM / "tables").glob("*.tmdl"):
            for line in f.read_text().splitlines():
                if line.startswith("\tmeasure "):
                    dax = line.split(" = ", 1)[1]
                    for ref in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", dax):
                        self.assertIn(ref, all_measures, f"{f.name}: [{ref}]")
                    for t, c in re.findall(r"(\w+)\[([^\]]+)\]", dax):
                        self.assertIn(c, self.model[t]["columns"], f"{t}[{c}]")

    def test_report_fields_exist_in_model(self):
        for vf in (RP / "definition/pages").rglob("visual.json"):
            text = vf.read_text()
            for kind, entity, prop in re.findall(
                    r'"(Column|Measure)": \{\s*"Expression": \{\s*"SourceRef": \{\s*"Entity": "(\w+)"\s*\}\s*\},\s*"Property": "([^"]+)"',
                    text):
                bucket = "columns" if kind == "Column" else "measures"
                self.assertIn(prop, self.model[entity][bucket], f"{vf.parent.name}: {entity}.{prop}")

    def test_pages_listed(self):
        pages = json.loads((RP / "definition/pages/pages.json").read_text())["pageOrder"]
        for p in pages:
            self.assertTrue((RP / "definition/pages" / p / "page.json").exists())


class TestDeploy(unittest.TestCase):
    def test_dry_run_fills_every_token(self):
        r = subprocess.run([sys.executable, str(ROOT / "src/deploy/deploy.py"), "--workspace", "UnitTest",
                            "--dry-run", "--with-notifications"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("unreplaced tokens", r.stdout)


if __name__ == "__main__":
    unittest.main()
