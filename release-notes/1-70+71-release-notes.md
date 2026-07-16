# Platform Update 1.71

Quilt Connect now also works on private stacks, and adds support for Databricks, ChatGPT, and Codex as MCP clients. This release also moves package metadata to per-bucket Iceberg tables for faster and cheaper querying, especially from Tabulator, and adds Glacier rehydration from file preview. Benchling entries gain referenced-entity search and multi-bucket search, while QuiltSync adds a CLI, background Autosync and workflows.

## New Quilt Platform Features

### Private Quilt Connect

Quilt Connect now uses the same network configuration as the rest of your Quilt stack. This allows OAuth sign-in to the Quilt Platform MCP Server from local MCP clients such as Claude Code, even if you don't have a public endpoint or are using a web-application firewall.

### MCP Support for Databricks, ChatGPT, and Codex

Quilt Connect now supports Databricks, ChatGPT, and Codex as MCP clients. Stack admins can specify Databricks and ChatGPT hosts in `ConnectAllowedHosts`, or use `localhost` for access by Codex.

### Benchling Entities and Cross-Bucket Search

This release bundles v0.19 of the Benchling Webhook:

- Each auto-generated entry package contains the full list of referenced objects, as both package metadata and a `links.json` file. This includes both the unique identifier and human-readable names, so you can search or query to find every experiment that references plasmid QB-2743.1.
- You can also disable automatic package creation by not setting a default bucket. Instead, the App Canvas will use the new Iceberg catalog to automatically search every bucket for packages with metadata that reference the notebook name (e.g., `experiment_id = EXP00012345`) and display those instead.

### Iceberg Package Metadata

Quilt users can now query package metadata directly as Iceberg tables in Athena — package revisions, tags, manifests, and entries — instead of relying on Athena crawling individual JSONL manifests on every query. If you can read a bucket in the catalog, you can query the Iceberg tables for it using your existing session credentials.

This uses per-bucket tables of the form:

```text
{bucket}_package_{revision,tag,manifest,entry}
```

Tabulator and in-catalog package surfaces use the new layout transparently, and Tabulator queries now hit this index instead of doing a full S3 scan through Glue/Athena SerDe tables — cheaper and faster end-to-end, with permissions unchanged.

> **NOTE:** External consumers of the old global tables must migrate to the per-bucket names and use `UNION ALL` for cross-bucket queries.

### Glacier Rehydration from File Preview

Archived S3 objects in Glacier or Deep Archive can now be restored directly from file preview in the Quilt Catalog. Choose restore tier and duration; Quilt tracks restore state from S3 metadata, and managed read/write roles get `s3:RestoreObject`.

## QuiltSync & CLI

### Background Autosync

QuiltSync adds an opt-in Autosync loop with independent Pull and Push toggles. Auto-pull refreshes latest for installed remote packages when the working tree is clean; auto-push can commit and publish quiet local changes using your publish settings, while pausing on pending changes or divergence.

A tray-resident shell keeps Autosync running with the main window closed. The optional Close to tray setting hides the window instead of quitting, and the tray shows idle, syncing, paused, or error status with Open Quilt and Quit actions.

A per-mapping filesystem watcher refreshes local package status when files change on disk, so status badges and entry lists update within about 500 ms without a reload. The watcher is guarded against feedback loops and only repaints when computed status changes.

[Get QuiltSync](https://quilt.bio/quiltsync/)

### Workflow Configuration

QuiltSync now enables you to specify per-bucket workflows, which is particularly useful with locally-created packages.

### Clearer Merge Actions

The merge page now labels actions by direction: **Promote my commit** pushes the local commit and tags it latest, while **Overwrite local with remote** resets local state and discards uncommitted edits.

### quilt-cli on crates.io

The new QuiltSync-based `quilt` CLI is now published to crates.io with prebuilt binaries for macOS and Linux, installable via `cargo binstall quilt-cli`. This is tightly integrated with QuiltSync's data directory so you can use either the CLI or the GUI to manage your packages.

### Robust Image Previewing

- Multi-channel images render ~12–25% faster, and large floating-point multi-channel images near the memory limit now render reliably.
- A channel containing NaN or infinite pixel values no longer blanks the entire thumbnail.
- Color CZI images stored in BGR pixel formats (e.g. `Bgr24` / `Bgr48`) now preview with correct colors.
- Signed and wider-than-16-bit integer images (`uint32` / `uint64`, `int8`, `int64`, and 32-bit-integer color) now preview contrast-stretched, instead of failing or rendering dark.
- `.jpeg`/`.webp` thumbnails, float and 16-bit-color images, and 16-bit greyscale now render correctly.
- Previews are now 8-bit everywhere, producing smaller PNGs with no loss of meaningful detail.
- The source image streams to disk during rendering instead of buffering fully in memory, lowering peak memory on large images.

### Other Catalog Improvements

- Landing page bucket cards now show configured bucket icons, matching the navbar selector.
- An expired or rejected session now reliably redirects to sign-in instead of showing a generic error page.
- The Admin > Theme logo preview no longer breaks the editor when the configured S3 URL is malformed.
- Markdown file previews now render using standard GitHub-Flavored Markdown (a superset of CommonMark). This means we no longer support idiosyncratic Pandoc/PHP-Markdown-Extra shortcuts.
- Syntax highlighting now loads language grammars on demand instead of all up front; code in an unsupported or unrecognized language is no longer highlighted.
- The Athena Queries tab no longer errors for accounts with more than 50 Athena workgroups.

## Stack Admin Improvements

### Lake Formation Grants (Opt-In)

A new `EnableLakeFormationGrants` stack parameter emits PrincipalPermissions grants from stack service roles to the data lake. If your AWS account enforces Lake Formation on the data lake, you must enable this parameter — otherwise Lake Formation denies the stack's roles and per-bucket Iceberg access (among other things) breaks. It is opt-in and off by default; leave it off only on accounts that do not enforce Lake Formation.

### Other Stack Improvements

- The Quilt Platform MCP server now returns the full package revision hash, avoiding errors due to truncated hashes. Registry errors are now also properly surfaced by the tool. The `package_create` tool avoids overwriting existing packages, steering clients to `package_patch` unless overridden (in which case it reports the diff).
- The registry now uses the mimalloc allocator instead of pymalloc, lowering per-worker memory and eliminating intermittent out-of-memory worker kills that surfaced as a catalog "Unexpected Error".
- Obsolete global Iceberg package tables are now cleaned up via S3 lifecycle expiration instead of a synchronous Athena `DROP TABLE` that could time out on large stacks; the Iceberg Glue database name is now exposed as the `IcebergDatabaseName` stack output.
- The CloudWatch Synthetics canary runtime is now Node 22 / Synthetics 15.1, replacing the previous v10 runtime that is on AWS's deprecation path.
- Customers still on Network 1.0 can easily migrate to Network 2.0 for improved security and configurability.

> These already shipped as part of the 1.69.4 security update, but are included here for completeness.

- Postgres engine upgraded to 15.18 for CloudFormation deployments.
- s3-proxy: nginx upgraded 1.24.0 → 1.30.2 with a refreshed Amazon Linux base image.

## Your CloudFormation Template

Find the CloudFormation YAML file available via the link below:

| Field            | Value                     |
| ---------------- | ------------------------- |
| Catalog URL      | No URL Found              |
| Template URL     | No Template Variant Found |
| Deployment Style | CF                        |
| Network Version  | 2                         |

For more information on how to apply this release for CloudFormation (CF), refer to our upgrade documentation or full installation guide.

Terraform users (TF) can use the public quilt module.

Please contact [support@quilt.bio](mailto:support@quilt.bio) if you have any questions.

---

Quilt Data, 595 Pacific Avenue, Floor 4, San Francisco, California, 94133, United States

781-277-2255

Unsubscribe · Manage Preferences
</content>
