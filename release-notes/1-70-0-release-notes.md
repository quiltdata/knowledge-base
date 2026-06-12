# Platform Update 1.70

## Connect for Databricks, ChatGPT & Codex; Per-Bucket Package Index, CommonMark Rendering, QuiltSync Autosync

This release adds Databricks, ChatGPT, and Codex as Quilt Connect (MCP) clients, moves the package index to per-bucket Iceberg tables with automatic role-scoped Athena access, tightens markdown rendering to CommonMark + GFM, adds an opt-in Lake Formation grants mode, and brings background Autosync to QuiltSync along with a crates.io release of the `quilt` CLI.

## New Quilt Platform Features

### Connect for Databricks, ChatGPT, and Codex

Quilt Connect now supports Databricks, ChatGPT, and Codex as MCP clients, alongside the existing client matrix. Stack admins enabling Databricks or ChatGPT need to allow the appropriate hosts (`.cloud.databricks.com`, `chat.openai.com`, `chatgpt.com`) in their stack's `ConnectAllowedHosts`. End users then pair their assistant once and can query Quilt buckets, packages, and metadata under their own catalog session.

Codex support comes from a registry-side OAuth fix: PRM (`oauth-protected-resource`) discovery now also accepts the MCP transport-suffixed well-known path, which Codex and other RFC 9728-strict clients request. No stack-level configuration is required.

### Per-Bucket Package Index

The package-index Iceberg tables have moved from a single global set (`package_*`) to per-bucket tables (`{bucket}_package_{revision,tag,manifest,entry}`). The `bucket` column is gone from every schema — the table name carries it. Every Quilt role now automatically receives Athena read access to the per-bucket tables for the buckets they can read: managed users are narrowed to their scoped buckets via the registry-applied session policy; non-managed roles are stack-wide. Tabulator and the in-catalog package surfaces query the new layout transparently.

External Athena/Iceberg consumers must migrate to the per-bucket table names — the legacy global tables are removed. Cross-bucket queries now require explicit `UNION ALL` across per-bucket tables (the prior unified view is gone).

### Tabulator on Per-Bucket Iceberg via Athena

Tabulator now resolves package-entry queries by joining the per-bucket Iceberg tables directly via Athena, under each caller's bucket-scoped credentials. Queries respect existing role and bucket permissions automatically — no separate Tabulator grant is required.

### CommonMark + GFM Markdown

Markdown rendering in the catalog now conforms to CommonMark + GFM. Non-standard Pandoc / PHP-Markdown-Extra shortcuts (`==mark==`, `^sup^`, `~sub~`, `++ins++`, abbreviations, definition lists, footnotes) are no longer parsed as syntax; raw inline HTML for these tags still renders.

## QuiltSync & CLI

### Background Autosync

QuiltSync gains an opt-in **Autosync** loop with independent **Pull** and **Push** toggles (Settings → Autosync), so users can enable cheap, idempotent auto-pulls without unattended pushes.

- **Auto-pull:** Periodically refreshes `latest` for every installed remote package and pulls when the package is behind and the working tree is clean. Packages with pending changes, pending commits, or divergence are paused (and surfaced in the UI) rather than clobbered.
- **Auto-push:** When a mapped package has local changes or a pending commit and the working tree has been quiet, the watcher commits and pushes automatically using the message, metadata, and workflow from your publish settings — no re-prompt. Autosync refuses to push when a teammate has already published under the same namespace (treated as diverged).
- **Independent cadence:** Pull interval and the post-edit quiet window before publishing ("wait after last edit before publishing", default 30 s) are separate knobs.

### Tray Icon & Close to Tray

A new tray-resident shell keeps Autosync running with the main window closed. An opt-in **Close to tray** setting (default off) hides the window to the tray instead of quitting; the tray shows a folded status (idle / syncing / paused / error) and an **Open Quilt** / **Quit** menu. Environments without a working tray fall back to today's quit-on-close behavior.

### Live Filesystem Watcher

A per-mapping filesystem watcher (default on, toggle under Settings → Filesystem Watcher) refreshes a package's local status live when files change on disk — from an editor save, `cp`, or a script — so status badges and entries lists update within ~500 ms without a reload. The watcher is guarded against feedback loops and only repaints when the computed status actually changes.

### Clearer Merge Actions

The merge page's actions are relabeled to name the direction of change: **Promote my commit** (push the local commit and tag it `latest`) and **Overwrite local with remote** (reset, discarding uncommitted edits). A related library fix ensures **Promote my commit** pushes any pending local commit *before* tagging `latest`, instead of rolling the remote pointer back to the install-time hash.

### quilt-cli on crates.io

The `quilt` CLI (`quilt-cli`) is now published to crates.io and installable via `cargo binstall quilt-cli`, with prebuilt binaries for macOS (x86_64/arm64) and Linux (x86_64).

The CLI now **shares its default data directory with QuiltSync** (`com.quiltdata.quilt-sync`), so state created by `quilt` (without `--domain`) is visible to QuiltSync and vice versa. Existing CLI users with a `com.quiltdata.quilt-rs` data directory should move it manually (see the quilt-cli changelog for per-platform commands).

*Released as quilt-sync 0.18.2, quilt-cli 0.27.0, quilt-rs 0.32.0.*

## Stack Admin Improvements

- **Lake Formation Grants (Opt-In):** A new `EnableLakeFormationGrants` stack parameter (default `Disabled`) emits `PrincipalPermissions` grants from stack service roles to the data lake. On stacks running with Lake Formation enforcement, this is required for the per-bucket Iceberg access (above) to take effect. The Data Lake Administrator IAM principal must be in place before enabling; see the README for prerequisites.
- **Canary Runtime v15.1:** The CloudWatch Synthetics canary runtime is now Node 22 / Synthetics 15.1 (`syn-nodejs-puppeteer-15.1`). The previous v10 runtime is on AWS's deprecation path.
- **Resilient Logo Preview:** The Admin > Theme logo preview no longer breaks the editor when the configured S3 URL is malformed.

## Other Improvements

- Fixed the "Workgroup not found" error on the Athena Queries tab for accounts that had accumulated more than 50 Athena workgroups in a region. The catalog now drains the full workgroup, catalog, and database listings on load rather than giving up after the first page.

> These already shipped as part of the 1.69.4 security update, but are included here for completeness.

- Postgres engine upgraded to 15.18 for CloudFormation deployments.
- `s3-proxy`: nginx upgraded 1.24.0 → 1.30.2 with a refreshed Amazon Linux base image.
