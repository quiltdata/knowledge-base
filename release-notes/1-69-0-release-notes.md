# Platform Update 1.69

## Qurator Platform Tools, Async Benchling Pipeline, Union-of-Roles SSO, Prefix Reindex

This release expands Qurator with first-class platform data tools, makes the Benchling integration fully asynchronous, introduces an opt-in union-of-roles mode for SSO, and lets administrators rescan a single prefix instead of the whole bucket.

## New Quilt Platform Features

### Qurator Platform Tools

Qurator can now use the platform's data tools — package browse and search, object search, S3 reads, Athena queries, tabulator, and package create/edit — alongside its existing in-catalog navigation. Tools execute under the user's catalog session, so all access continues to respect existing role and bucket permissions.

To support this, the Platform MCP Server now also deploys when Qurator is enabled (in addition to Connect) and is served from the main ALB at `registry-<stack>.<domain>/mcp/platform/*`, so the Qurator assistant can call it with the user's session token. Stacks that don't enable Qurator are unaffected.

### Asynchronous Benchling Integration

The Benchling canvas now updates asynchronously as Quilt re-exports packages, showing a "pending → complete" state and remaining browsable throughout the re-export. In addition, Benchling `reviewRecord` entry events now trigger the standard package export workflow, bringing review records into parity with other entry types.

### Union-of-Roles SSO Mode

A new opt-in `union_roles: true` flag in SSO config changes role assignment from first-match-wins to a union of **all** matching mapping roles. Users switch among the assigned roles via the existing role switcher, and any role no longer in the match set is revoked on next login. Default behavior is unchanged — existing SSO configs see no difference.

Under `union_roles`, the mapping `admin` field becomes tri-state: omitted means non-vote, `true` grants admin, and `false` vetoes — an explicit `admin: false` blocks admin even if another matching mapping grants it.

### Prefix-Scoped Reindex

Stack admins can now scope a reindex to a single prefix. `POST /api/admin/reindex/<bucket>` accepts an optional `prefix` field; when supplied, Elasticsearch indices are left in place and only keys under that prefix are re-walked. Concurrent prefix reindexes on distinct prefixes are allowed; same-prefix and full-vs-prefix collisions return HTTP 409.

### Admin Theme Logo Upload

The Admin > Theme editor now lets you upload a catalog logo file directly (PNG, JPEG, WebP, or GIF), replacing the previous URL-only flow.

## Stack Admin Improvements

- **Bucket Management Lockdown:** Manual bucket management operations on stack-managed S3 buckets are now denied by bucket policy. All bucket configuration changes must go through CloudFormation.
- **Admin Bucket Listings Respect Role Scope:** User-facing bucket listings (catalog navbar, landing grid, search filter, and the MCP `bucket_list` tool) no longer bypass role scope for admins.
- **Wildcard Connect Hosts:** `ConnectAllowedHosts` now supports leading-dot domain suffixes (e.g. `.benchling.com`) to allow any subdomain over HTTPS.
- **s3-proxy Base Image:** Bumped to an updated Amazon Linux 2023 base image.

## Bug Fixes

- Fixed Admin > Theme **Save** silently failing with a 403 on managed-role stacks (the modern default); the settings JSON write is now granted to `ManagedUserRoleBasePolicy`.
- Fixed an "Error resolving revision" flash that briefly appeared when navigating to a just-created package.
- Fixed Okta `ClientId` and `BaseUrl` in Terraform configs.

## Other Improvements

- Removed the unused "Overview URL" and "Structured data (JSON-LD)" fields from the Admin Buckets editor, along with the obsolete OPEN-stack features they enabled.
