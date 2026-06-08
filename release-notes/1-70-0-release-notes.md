# Platform Update 1.70

## Connect for Databricks & ChatGPT, Per-Bucket Package Index, CommonMark Rendering

This release adds Databricks and ChatGPT as Quilt Connect (MCP) clients, moves the package index to per-bucket Iceberg tables with automatic role-scoped Athena access, tightens markdown rendering to CommonMark + GFM, and adds an opt-in Lake Formation grants mode.

## New Quilt Platform Features

### Connect for Databricks and ChatGPT

Quilt Connect now supports Databricks and ChatGPT as MCP clients, alongside the existing client matrix. Stack admins enabling these targets need to allow the appropriate hosts (`.cloud.databricks.com`, `chat.openai.com`, `chatgpt.com`) in their stack's `ConnectAllowedHosts`. End users then pair their assistant once and can query Quilt buckets, packages, and metadata under their own catalog session.

### Per-Bucket Package Index

The package-index Iceberg tables have moved from a single global set (`package_*`) to per-bucket tables (`{bucket}_package_{revision,tag,manifest,entry}`). The `bucket` column is gone from every schema — the table name carries it. Every Quilt role now automatically receives Athena read access to the per-bucket tables for the buckets they can read: managed users are narrowed to their scoped buckets via the registry-applied session policy; non-managed roles are stack-wide. Tabulator and the in-catalog package surfaces query the new layout transparently.

External Athena/Iceberg consumers must migrate to the per-bucket table names — the legacy global tables are removed. Cross-bucket queries now require explicit `UNION ALL` across per-bucket tables (the prior unified view is gone).

### Tabulator on Per-Bucket Iceberg via Athena

Tabulator now resolves package-entry queries by joining the per-bucket Iceberg tables directly via Athena, under each caller's bucket-scoped credentials. Queries respect existing role and bucket permissions automatically — no separate Tabulator grant is required.

### CommonMark + GFM Markdown

Markdown rendering in the catalog now conforms to CommonMark + GFM. Non-standard Pandoc / PHP-Markdown-Extra shortcuts (`==mark==`, `^sup^`, `~sub~`, `++ins++`, abbreviations, definition lists, footnotes) are no longer parsed as syntax; raw inline HTML for these tags still renders.

## Stack Admin Improvements

- **Lake Formation Grants (Opt-In):** A new `EnableLakeFormationGrants` stack parameter (default `Disabled`) emits `PrincipalPermissions` grants from stack service roles to the data lake. On stacks running with Lake Formation enforcement, this is required for the per-bucket Iceberg access (above) to take effect. The Data Lake Administrator IAM principal must be in place before enabling; see the README for prerequisites.
- **Canary Runtime v15.1:** The CloudWatch Synthetics canary runtime is now Node 22 / Synthetics 15.1 (`syn-nodejs-puppeteer-15.1`). The previous v10 runtime is on AWS's deprecation path.
- **Resilient Logo Preview:** The Admin > Theme logo preview no longer breaks the editor when the configured S3 URL is malformed.

## Other Improvements

- Cleaner variant set: removed unused variants (`dsp-concepts`, `seqera`, `interline-stage`, `hudl`) and the dead `localhost` environment option.
- Postgres engine upgraded to 15.18 for CloudFormation deployments (already shipped via the 1.69.4 patch; included here for completeness).
