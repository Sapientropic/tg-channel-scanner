# Output Artifacts

Status: canonical artifact ownership note for local `output/` files.

T-Sense has two artifact lanes:

| Lane | Path | Purpose | Desk behavior |
| --- | --- | --- | --- |
| Run artifacts | `output/runs/<run_id>/` | Monitor runs, replay imports, run manifests, scan sidecars, Markdown/HTML reports. | Runs and Review cards may link to report/brief `.html` or `.md` files from here. |
| Standalone artifacts | `output/<name>` | Demo reports, manual one-off reports, feedback exports, screenshots, eval outputs. | Desk may open report/brief `.html` or `.md` files, but these do not automatically create Review cards. |

`output/` is local, ignored by Git, and may contain raw scan context. Do not
copy raw output artifacts into issues, public docs, prompts, or commits.

## Report vs Review Cards

`scripts/report.py` and `tgcs demo` can generate readable reports without
touching the Desk inbox. That is report-only output.

Use `tgcs monitor run` when the result should become Review cards:

```bash
tgcs monitor run --profile-id jobs-fast --delivery-mode dry-run
```

For historical or manually collected scans, import them through the monitor
lane instead of only rendering a report:

```bash
tgcs monitor run --profile-id jobs-fast \
  --scan-input output/runs/<run_id>/scan.jsonl \
  --delivery-mode dry-run
```

That route preserves run manifests, report artifacts, Review card upserts, and
`new` / `changed` / `seen` state semantics in the local DB.

## Openable Desk Artifacts

Signal Desk only opens report-style artifacts through the local `/artifacts/*`
route:

- allowed: `output/runs/<run_id>/report.html`
- allowed: `output/runs/<run_id>/<profile>-signal-report-<stamp>.html`
- allowed: `output/demo-report.html`
- rejected: raw scans such as `scan.jsonl`
- rejected: absolute paths, traversal paths, URLs, and private filesystem paths

Review cards should store only dashboard-openable report paths. If a card has
source refs but no openable report path, the Desk can still show Telegram source
metadata and links, but it cannot preview the original raw text from the report.

## Cleanup Policy

Keep generated files under `output/`, not under `docs/` or repo root. Use stable
public screenshots in `docs/screenshots/` only after deliberate review.

Suggested local cleanup:

```powershell
Get-ChildItem output -Directory |
  Where-Object LastWriteTime -lt (Get-Date).AddDays(-14) |
  Remove-Item -Recurse -Force
```

Do not delete `output/runs/<run_id>/` for a run you still need to inspect in
Signal Desk; the DB can remember the card, but the source preview needs the
report artifact to remain addressable.
