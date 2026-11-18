#!/usr/bin/env python3
"""
Deploy the whole demo to a Fabric workspace with the Fabric CLI (`fab`).

Prereqs
    pip install ms-fabric-cli
    fab auth login                      # sign in to the HOST tenant (interactive)

Usage
    python3 src/deploy/deploy.py --workspace "Fabric User Group Demo" --capacity <capacity-name>
    python3 src/deploy/deploy.py --workspace "Fabric User Group Demo" --dry-run   # print commands only

What it does (idempotent; safe to re-run)
    1. Creates the workspace (if --capacity given and it doesn't exist) and lakehouse
    2. Uploads data/input/landing -> Files/landing, config -> Files/config,
       incremental + bad files -> Files/demo_drops (for the live demo)
    3. Imports the 4 notebooks (bound to the lakehouse)
    4. Imports pl_load_sales and runs it (creates all Delta tables)
    5. Imports the Direct Lake semantic model + report
    6. --with-notifications: re-imports the pipeline WITH the semantic-model refresh,
       Outlook notifications and Fail activity (these need connections you authorise
       once in the UI - see docs/03-pipeline.md)

Everything is staged in ./build (git-ignored) with {{TOKENS}} replaced by real IDs.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
BUILD = ROOT / "build"
NOTEBOOKS = ["nb_load_table", "nb_build_dim_date", "nb_data_quality", "nb_table_maintenance"]
NEEDS_CONNECTIONS = {"Office365Outlook", "PBISemanticModelRefresh", "Fail", "Teams"}
FAKE_ID = "00000000-0000-0000-0000-000000000000"
TOKEN = re.compile(r"\{\{[A-Z_]+\}\}")


class Fab:
    def __init__(self, dry_run: bool):
        self.dry = dry_run

    def __call__(self, *args: str, check: bool = True) -> str:
        print("  $ fab " + " ".join(shlex.quote(a) for a in args))
        if self.dry:
            return ""
        r = subprocess.run(["fab", *args], capture_output=True, text=True)
        if check and r.returncode != 0:
            sys.exit(f"fab failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        return r.stdout.strip()

    def exists(self, path: str) -> bool:
        return False if self.dry else "true" in self("exists", path, check=False).lower()

    def get(self, path: str, query: str):
        if self.dry:
            return {"id": FAKE_ID, "connectionString": "dry-run.datawarehouse.fabric.microsoft.com"} \
                if "sqlEndpoint" in query else FAKE_ID
        out = self("get", path, "-q", query)
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return out.strip().strip('"')


def stage(src: Path, dest_name: str, tokens: dict[str, str]) -> Path:
    """Copy an item folder into ./build and replace {{TOKENS}}."""
    dest = BUILD / dest_name
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    for f in dest.rglob("*"):
        if f.is_file() and f.suffix in {".py", ".json", ".tmdl", ".pbism", ".pbir", ".platform", ""}:
            text = f.read_text(encoding="utf-8")
            for k, v in tokens.items():
                text = text.replace("{{" + k + "}}", v)
            f.write_text(text, encoding="utf-8")
    return dest


def leftover_tokens(folder: Path) -> list[str]:
    hits = []
    for f in folder.rglob("*"):
        if f.is_file():
            for m in TOKEN.findall(f.read_text(encoding="utf-8", errors="ignore")):
                hits.append(f"{f.relative_to(BUILD)}: {m}")
    return hits


def stage_pipeline(tokens: dict[str, str], with_notifications: bool, notify_to: str | None) -> Path:
    dest = stage(SRC / "fabric/pipelines/pl_load_sales.DataPipeline", "pl_load_sales.DataPipeline", tokens)
    content = dest / "pipeline-content.json"
    pl = json.loads(content.read_text())
    if not with_notifications:
        pl["properties"]["activities"] = [a for a in pl["properties"]["activities"]
                                          if a["type"] not in NEEDS_CONNECTIONS]
    if notify_to:
        pl["properties"]["parameters"]["notify_to"]["defaultValue"] = notify_to
    content.write_text(json.dumps(pl, indent=2))
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", required=True, help="Workspace display name")
    ap.add_argument("--capacity", help="Capacity name - only needed if the workspace must be created")
    ap.add_argument("--lakehouse", default="lh_sales")
    ap.add_argument("--with-notifications", action="store_true")
    ap.add_argument("--notify-to", help="Email for pipeline notifications")
    ap.add_argument("--skip-run", action="store_true", help="Don't run the pipeline")
    ap.add_argument("--dry-run", action="store_true", help="Print fab commands; use fake IDs")
    a = ap.parse_args()

    fab = Fab(a.dry_run)
    ws = f"{a.workspace}.Workspace"
    lh = f"{ws}/{a.lakehouse}.Lakehouse"
    BUILD.mkdir(exist_ok=True)

    print("\n[0] Auth check")
    fab("auth", "status")

    print("\n[1] Workspace + lakehouse")
    if not fab.exists(ws):
        if not a.capacity and not a.dry_run:
            sys.exit(f"Workspace '{a.workspace}' not found. Pass --capacity <name> to create it.")
        fab("mkdir", ws, "-P", f"capacityname={a.capacity or 'CAPACITY'}")
    if not fab.exists(lh):
        fab("mkdir", lh)
    ws_id, lh_id = fab.get(ws, "id"), fab.get(lh, "id")

    sql = {}
    for attempt in range(12):  # SQL endpoint provisions a few seconds after the lakehouse
        sql = fab.get(lh, "properties.sqlEndpointProperties") or {}
        if isinstance(sql, dict) and sql.get("id"):
            break
        print("  ... waiting for SQL analytics endpoint")
        time.sleep(10)
    tokens = {"WORKSPACE_ID": ws_id, "LAKEHOUSE_ID": lh_id, "LAKEHOUSE_NAME": a.lakehouse,
              "SQL_ENDPOINT_ID": sql.get("id", ""), "SQL_ENDPOINT_CONNECTION_STRING": sql.get("connectionString", "")}

    print("\n[2] Upload files to OneLake")
    uploads = [(p, f"Files/landing/{p.parent.name}") for p in sorted((ROOT / "data/input/landing").rglob("*.csv"))]
    uploads.append((SRC / "fabric/config/table_config.json", "Files/config"))
    uploads += [(p, "Files/demo_drops") for p in sorted((ROOT / "data/input").glob("[ib]*/*.csv"))]
    made = set()
    for local, folder in uploads:
        parts = folder.split("/")
        for i in range(2, len(parts) + 1):
            sub = "/".join(parts[:i])
            if sub not in made and not fab.exists(f"{lh}/{sub}"):
                fab("mkdir", f"{lh}/{sub}")
            made.add(sub)
        fab("cp", str(local), f"{lh}/{folder}/{local.name}", "-f")

    print("\n[3] Notebooks")
    for nb in NOTEBOOKS:
        staged = stage(SRC / f"fabric/notebooks/{nb}.Notebook", f"{nb}.Notebook", tokens)
        fab("import", f"{ws}/{nb}.Notebook", "-i", str(staged), "-f")
        tokens[f"NB_{nb.removeprefix('nb_').upper()}_ID"] = fab.get(f"{ws}/{nb}.Notebook", "id")

    print("\n[4] Pipeline (core activities)")
    pipe = f"{ws}/pl_load_sales.DataPipeline"
    staged = stage_pipeline(tokens, with_notifications=False, notify_to=a.notify_to)
    fab("import", pipe, "-i", str(staged), "-f")
    if not a.skip_run:
        print("  running pipeline - first run takes a few minutes (Spark session start-up) ...")
        fab("job", "run", pipe)

    print("\n[5] Semantic model + report")
    model = f"{ws}/Sales.SemanticModel"
    staged = stage(SRC / "powerbi/Sales.SemanticModel", "Sales.SemanticModel", tokens)
    fab("import", model, "-i", str(staged), "-f")
    tokens["SEMANTIC_MODEL_ID"] = fab.get(model, "id")
    staged = stage(SRC / "powerbi/Sales.Report", "Sales.Report", tokens)
    (staged / "definition.pbir").write_text(json.dumps({
        "version": "4.0",
        "datasetReference": {"byConnection": {"connectionString": f"semanticmodelid={tokens['SEMANTIC_MODEL_ID']}"}}},
        indent=2))
    fab("import", f"{ws}/Sales.Report", "-i", str(staged), "-f")

    if a.with_notifications:
        print("\n[6] Pipeline (full: refresh + notifications + fail)")
        staged = stage_pipeline(tokens, with_notifications=True, notify_to=a.notify_to)
        fab("import", pipe, "-i", str(staged), "-f")

    left = leftover_tokens(BUILD)
    if left:
        print("\nWARNING - unreplaced tokens:\n  " + "\n  ".join(left))
    print(f"\nDone. Open: fab open {ws}")


if __name__ == "__main__":
    main()
