# Platform Update 1.71

This release expands Quilt Connect (OAuth sign-in from local MCP clients now works on WAF-protected stacks, plus a safer `package_create`), brings Benchling Referenced Entities and bucket-optional deployments, improves image previews across many formats, and adds security updates plus an in-place network 1.0 → 2.0 migration path for stack admins.

## New Quilt Platform Features

### Benchling: Referenced Entities

Notebook entries can now be found by searching the human-readable names of the Benchling objects they reference — for example, finding every experiment that references plasmid `QB-2743.1`. Each entry package also records the full list of referenced objects.

### Benchling: Bucketless Deployments

The Benchling package bucket is now optional. Without a dedicated bucket, linked-package search on entry canvases spans all of your package-view buckets via a single Iceberg query.

### Quilt Connect: Sign-In from Local MCP Clients

OAuth sign-in from local MCP clients such as Claude Code now works on WAF-enabled stacks — the localhost callback address previously tripped a firewall rule on the authorization page.

### Safer MCP `package_create`

The `package_create` tool no longer silently replaces an existing package's entire manifest. It now refuses when the package already exists — steering you to `package_patch` for incremental changes — and requires `overwrite=true` to replace it. When it does overwrite, it reports an added / removed / kept entry diff against the previous revision.

### More Reliable Sign-In on Expired Sessions

An expired or rejected session now reliably redirects you to sign-in instead of showing a generic error page — for example, when a server-side SSO token refresh fails. Previously only one specific error was recognized; any other cause could strand you on an error page until a manual re-login.

### Iceberg Package Index in the Athena Dropdown

Managed users now see the Iceberg package-index database in the Athena Queries "Database" dropdown; previously it was queryable only by its fully-qualified name.

### Image Preview Improvements

A broad set of thumbnail and preview improvements:

- Multi-channel images render ~12–25% faster, and large floating-point multi-channel images near the memory limit (which previously failed intermittently) now render reliably.
- A channel containing NaN or infinite pixel values no longer blanks the entire thumbnail.
- Color CZI images stored in BGR pixel formats (e.g. `Bgr24` / `Bgr48`) now preview with correct colors.
- Signed and wider-than-16-bit integer images (`uint32` / `uint64`, `int8`–`int64`, and 32-bit-integer color) now preview, contrast-stretched, instead of failing or rendering dark.
- Previews are now 8-bit everywhere, producing smaller PNGs with no loss of meaningful detail.
- The source image streams to disk during rendering instead of buffering fully in memory, lowering peak memory on large images.

## Stack Admin Improvements

### In-Place Network 1.0 → 2.0 Migration

New tooling migrates a legacy network-1.0 stack to the 2.0 network layout in place — on the existing CloudFormation stack, with no new stack, no DNS or ARN changes, and no search reindexing. It ships transient template options plus an operator toolkit under `script/nw_migration/` (a gated changeset driver, Elasticsearch/DB operations, an expected-changes manifest generator, and a fail-closed guided runner) and a runbook at `script/nw_migration/NW_MIGRATION.md`. All options default unset, so existing builds are unchanged.

### Quilt Connect Server ALB Follows the Stack Scheme

The Quilt Connect ALB now follows the stack's `elb_scheme` instead of always being internet-facing. On an internal stack (`elb_scheme=internal`) the Connect ALB is now internal; public stacks keep it internet-facing.

### Lower Registry Memory Use

The registry now uses the **mimalloc** allocator instead of pymalloc, lowering per-worker memory and eliminating the intermittent out-of-memory worker kills that surfaced as a catalog "Unexpected Error".

### Managed Roles: Many-Bucket Read Access

Creating or editing managed policies and roles no longer fails once a single role spans roughly a dozen readable buckets.

### Iceberg Storage Cleanup and Output

Data from the obsolete pre-per-bucket global `package_*` Iceberg tables is now reclaimed by S3 lifecycle expiration, instead of relying on a synchronous Athena `DROP TABLE` that could time out on large stacks. The Iceberg Glue database name is also now exposed as the `IcebergDatabaseName` stack output.

### Security Updates

- **nginx**: the Amazon Linux base image was refreshed, picking up OS security patches accumulated since February.
- **Lambdas**: Quilt lambda images and zips were refreshed to a recent `quilt` build — notably **aiohttp 3.14.1** in the `tabular_preview`, `s3hash`, and `status_reports` lambdas (upstream HTTP-parser and connector hardening), plus an AWS Lambda base-image refresh (OS security patches) in the `tabular_preview` and `indexer` images.

## Other Improvements

- Clicking a package-name prefix on the package listing page filters the list to that prefix again.
- Syntax highlighting now loads language grammars on demand instead of all up front; code in an unsupported or unrecognized language is no longer highlighted.
