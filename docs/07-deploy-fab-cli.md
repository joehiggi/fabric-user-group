# 07 · Deploy with the Fabric CLI (`fab`)

## Core concepts
- `fab` is Microsoft's command-line tool for Fabric. It treats your tenant like a **file system**:
  `Workspace.Workspace/lh_sales.Lakehouse/Files/landing/...`
- Common commands: `ls`, `cd`, `mkdir`, `cp` (local ↔ OneLake), `import` / `export` (item definitions), `get -q` (JMESPath queries), `job run`, `open`.
- Item definitions on disk use the same folder format as Fabric Git integration (`*.Notebook/`, `*.DataPipeline/`, `*.SemanticModel/`, `*.Report/` + `.platform`).

## One-time setup
```bash
pip install ms-fabric-cli
fab auth login                 # interactive: pick the HOST tenant account
# service principal alternative (see `fab auth login -h` for exact flags):
# fab auth login -u <client-id> -p <secret> --tenant <tenant-id>
fab ls                         # sanity check: lists workspaces you can see
```

## Deploy everything
```bash
make deploy WS="Fabric User Group Demo" CAPACITY=<capacity-name>
# or
python3 src/deploy/deploy.py --workspace "Fabric User Group Demo" --capacity <capacity-name>
python3 src/deploy/deploy.py --workspace "Fabric User Group Demo" --dry-run   # preview commands
```
The script:
1. creates the workspace (if needed) and the `lh_sales` lakehouse
2. uploads landing files, config and demo drops
3. stages each item in `./build` with `{{TOKENS}}` replaced by real IDs (workspace, lakehouse, notebooks, SQL endpoint, model)
4. imports notebooks → pipeline → **runs** the pipeline → imports the semantic model + report
5. with `--with-notifications`, re-imports the full pipeline (refresh + Outlook + Fail). Open each Outlook/refresh activity once to sign in to its connection.

## Tips & tricks
- **Same code, any tenant.** Tokens, not hard-coded GUIDs.
- **Use `--dry-run`** to check a deploy before demo day. Unit tests run it too.
- **`fab export`** pulls UI changes back to disk, so you can tweak in the browser and then commit.
- For a long-term setup, connect the workspace to **Git integration** or use **deployment pipelines** (Dev → Test → Prod).

## Caveat
This was built and dry-run tested offline with no tenant access. Expect to fix one or two `fab` flag or format details on the first real run. Every command is printed, so failures are easy to spot.
