# Platform Update 1.69

## Qurator Platform Tools, Async Benchling Pipeline, Union-of-Roles SSO, Prefix Reindex

This release enhances Qurator with first-class access to platform MCP tools, support auto-update of Benchling canvases, grants SSO users access to multiple roles, and enables partial reindexing of buckets.

## New Quilt Platform Features

### Qurator Platform Tools

Qurator can now use the platform's MCP tools — package browse and search, object search, S3 reads, Athena queries, tabulator, and package create/edit — alongside its existing in-catalog navigation. Tools execute under the user's catalog session, so all access continues to respect existing role and bucket permissions.  This works even if Quilt Connect is not activated for public MCP access.

### Asynchronous Benchling Integration

The Benchling canvas now updates asynchronously as Quilt re-exports packages, showing a "pending → complete" state and remaining browsable throughout the re-export. In addition, Benchling `reviewRecord` events will also trigger package updates.

### Union-of-Roles SSO Mode

Adminstrators can use the new `union_roles: true` flag in their SSO configuration to grant users access to **all** matching roles, instead of just the first. Users can switch among the assigned roles via the existing role switcher, and any role no longer in the match set is revoked on next login. Default behavior is unchanged — existing SSO configurations will see no difference.

### Prefix-Scoped Reindex

Stack admins can now scope a bucket reindexing to a single prefix. `POST /api/admin/reindex/<bucket>` accepts an optional `prefix` field; when supplied, Elasticsearch indices are left in place and only keys under that prefix are re-walked.

### Admin Theme Logo Upload

The Admin > Theme editor in Adimin Settings now lets you optionally upload a catalog logo file directly (PNG, JPEG, WebP, or GIF), extending the previous URL-only flow.

## Stack Admin Improvements

- **Admin Bucket Listings Respect Role Scope:** User-facing bucket listings (catalog navbar, landing grid, search filter, and the MCP `bucket_list` tool) no longer bypass role scope for admins.
- **Wildcard Connect Hosts:** `ConnectAllowedHosts` now supports leading-dot domain suffixes (e.g. `.benchling.com`) to allow any subdomain over HTTPS.
- **Bucket Management Lockdown:** Manual bucket management operations on stack-managed S3 buckets are now denied by bucket policy. All bucket configuration changes must go through CloudFormation.

## Other Improvements

- **s3-proxy Base Image:** Bumped to an updated Amazon Linux 2023 base image.
- Fixed an "Error resolving revision" flash that briefly appeared when navigating to a just-created package.
- Fixed Admin > Theme **Save** silently failing with a 403 on managed-role stacks (the modern default).
- Removed the unused "Overview URL" and "Structured data (JSON-LD)" fields from the Admin Buckets editor.
