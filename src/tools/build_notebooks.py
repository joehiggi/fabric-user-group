#!/usr/bin/env python3
"""
Convert the reviewable `# %%` notebook sources into:
  1. ipynb/<name>.ipynb         - manual import (Workspace > Import > Notebook)
  2. <name>.Notebook/           - Fabric item folder (notebook-content.py + .platform)
                                  used by `fab import` in src/deploy/deploy.py.
                                  Default lakehouse bound via {{LAKEHOUSE_ID}}/{{WORKSPACE_ID}} tokens.

Cell markers:
  # %%              code cell
  # %% [markdown]   markdown cell (leading '# ' stripped)
  # %% [parameters] code cell tagged as the Fabric/papermill parameter cell

    python3 src/tools/build_notebooks.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "fabric" / "notebooks"
OUT = SRC / "ipynb"
MARK = re.compile(r"^# %%(?: \[(\w+)\])?\s*$")


def to_cells(text: str):
    cells, kind, buf = [], None, []

    def flush():
        if kind is None:
            return
        lines = buf[:]
        while lines and not lines[-1].strip():
            lines.pop()
        if kind == "markdown":
            lines = [re.sub(r"^# ?", "", l) for l in lines]
        src = [l + "\n" for l in lines]
        if src:
            src[-1] = src[-1].rstrip("\n")
        cell = {"cell_type": "markdown" if kind == "markdown" else "code", "metadata": {}, "source": src}
        if kind != "markdown":
            cell.update(execution_count=None, outputs=[])
        if kind == "parameters":
            cell["metadata"]["tags"] = ["parameters"]
        cells.append(cell)

    for line in text.splitlines():
        m = MARK.match(line)
        if m:
            flush()
            kind, buf = (m.group(1) or "code"), []
        else:
            buf.append(line)
    flush()
    return cells


META_NB = {
    "kernel_info": {"name": "synapse_pyspark"},
    "dependencies": {"lakehouse": {
        "default_lakehouse": "{{LAKEHOUSE_ID}}",
        "default_lakehouse_name": "{{LAKEHOUSE_NAME}}",
        "default_lakehouse_workspace_id": "{{WORKSPACE_ID}}"}},
}
META_CELL = {"language": "python", "language_group": "synapse_pyspark"}


def meta_block(obj) -> str:
    body = json.dumps(obj, indent=2).splitlines()
    return "# METADATA ********************\n\n" + "\n".join("# META " + l for l in body) + "\n\n"


def to_fabric_source(cells) -> str:
    out = "# Fabric notebook source\n\n" + meta_block(META_NB)
    for c in cells:
        text = "".join(c["source"])
        if c["cell_type"] == "markdown":
            out += "# MARKDOWN ********************\n\n" + "\n".join("# " + l if l else "#" for l in text.splitlines()) + "\n\n"
        else:
            header = "# PARAMETERS CELL ********************" if "parameters" in c["metadata"].get("tags", []) \
                else "# CELL ********************"
            out += f"{header}\n\n{text}\n\n" + meta_block(META_CELL)
    return out


def platform(name: str) -> dict:
    import uuid
    return {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Notebook", "displayName": name},
            "config": {"version": "2.0",
                       "logicalId": str(uuid.uuid5(uuid.UUID("6f1c0e2a-6b7e-4c55-9a51-fab41c0de001"), "nb/" + name))}}


def main():
    OUT.mkdir(exist_ok=True)
    for py in sorted(SRC.glob("nb_*.py")):
        nb = {
            "nbformat": 4, "nbformat_minor": 5, "cells": to_cells(py.read_text()),
            "metadata": {"kernelspec": {"name": "synapse_pyspark", "display_name": "Synapse PySpark"},
                         "language_info": {"name": "python"}},
        }
        target = OUT / f"{py.stem}.ipynb"
        target.write_text(json.dumps(nb, indent=1) + "\n")
        item = SRC / f"{py.stem}.Notebook"
        item.mkdir(exist_ok=True)
        (item / "notebook-content.py").write_text(to_fabric_source(nb["cells"]))
        (item / ".platform").write_text(json.dumps(platform(py.stem), indent=2) + "\n")
        print(f"  {target.relative_to(ROOT)}  +  {item.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
