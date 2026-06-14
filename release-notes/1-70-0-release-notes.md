# Platform Update 1.70

This release adds Databricks, ChatGPT, and Codex as Quilt Connect (MCP) clients, moves the package index to per-bucket Iceberg tables with automatic role-scoped Athena access, tightens Markdown rendering to CommonMark + GFM, and adds QuiltSync Autosync plus a crates.io release of the `quilt` CLI.

## New Quilt Platform Features

### Connect for Databricks, ChatGPT, and Codex

Quilt Connect now supports Databricks, ChatGPT, and Codex as MCP clients. Stack admins can allow Databricks and ChatGPT hosts in ConnectAllowedHosts; Codex works using the existing `localhost`.

### Direct Iceberg Access to Package Metadata

Quilt users can now query package metadata directly as Iceberg tables in Athena — package revisions, tags, manifests, and entries — instead of relying on Athena crawling individual JSONL manifests on every query. If you can read a bucket in the catalog, you can query the iceberg tables for it using your existing session credentials.

This replaces the single global table set with per-bucket tables (`{bucket}_package_{revision,tag,manifest,entry}`). Tabulator and in-catalog package surfaces use the new layout transparently. External consumers of the old (now removed) global tables must migrate to the per-bucket names and use `UNION ALL` for cross-bucket queries.

### Glacier Rehydration from File Preview

Archived S3 objects in Glacier or Deep Archive can now be restored directly from file preview in the Quilt Catalog. Choose restore tier and duration; Quilt tracks restore state from S3 metadata, and managed read/write roles get s3:RestoreObject.

### Faster, Cheaper Tabulator

Tabulator queries now hit the Iceberg package index instead of doing a full S3 scan through Glue/Athena SerDe tables on every call. Cheaper for users, faster end-to-end. The per-bucket Iceberg restructure is what makes this possible. Permissions are unchanged: each caller queries under their own bucket-scoped credentials, and existing role and bucket permissions apply automatically.

## QuiltSync & CLI

### Background Autosync

QuiltSync adds an opt-in Autosync loop with independent Pull and Push toggles. Auto-pull refreshes latest for installed remote packages when the working tree is clean; auto-push can commit and publish quiet local changes using your publish settings, while pausing on pending changes or divergence.

### Tray Icon & Close to Tray

A tray-resident shell keeps Autosync running with the main window closed. The optional Close to tray setting hides the window instead of quitting, and the tray shows idle, syncing, paused, or error status with Open Quilt and Quit actions.

### Live Filesystem Watcher

A per-mapping filesystem watcher refreshes local package status when files change on disk, so status badges and entry lists update within about 500 ms without a reload. The watcher is guarded against feedback loops and only repaints when computed status changes.

### Clearer Merge Actions

The merge page now labels actions by direction: Promote my commit pushes the local commit and tags it latest, while Overwrite local with remote resets local state and discards uncommitted edits. Promote my commit now pushes before tagging latest.

### quilt-cli on crates.io

The new QuiltSync-based `quilt` CLI is now published to [crates.io](https://crates.io) with prebuilt binaries for macOS and Linux, installable via `cargo binstall quilt-cli`. This is tightly integrated with QuiltSync's data directory so you can use either the CLI or the GUI to manage your packages.

## Stack Admin Improvements

### Lake Formation Grants (Opt-In)

A new EnableLakeFormationGrants stack parameter emits PrincipalPermissions grants from stack service roles to the data lake. On stacks with Lake Formation enforcement, this is required for per-bucket Iceberg access to take effect.

### Canary Runtime v15.1

The CloudWatch Synthetics canary runtime is now Node 22 / Synthetics 15.1, replacing the previous v10 runtime that is on AWS's deprecation path.

### Resilient Logo Preview

The Admin > Theme logo preview no longer breaks the editor when the configured S3 URL is malformed.

## Other Improvements

- Landing page bucket cards now show configured bucket icons, matching the navbar selector.
- Image previews now correctly render .jpeg/.webp thumbnails, float and 16-bit-color images, and 16-bit greyscale.
- Markdown file previews now render using standard [GitHub-Flavored Markdown](https://github.github.com/gfm/) (a superset of [CommonMark](https://commonmark.org/)). This means we no longer support idiosyncratic Pandoc/PHP-Markdown-Extra shortcuts.
- The Athena Queries tab no longer errors for accounts with more than 50 Athena workgroups.
- The Quilt Platform MCP server now returns the full package revision hash, avoiding errors due to truncated hashes. Registry errors are now also properly surfaced by the tool.

> These already shipped as part of the 1.69.4 security update, but are included here for completeness.

- Postgres engine upgraded to 15.18 for CloudFormation deployments.
- `s3-proxy`: nginx upgraded 1.24.0 → 1.30.2 with a refreshed Amazon Linux base image.
