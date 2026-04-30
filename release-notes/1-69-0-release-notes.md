# Platform Update 1.69

## Qurator Platform Tools, Benchling Auto-Updates, Multi-Role SSO, Streamlined QuiltSync

This release enhances Qurator with first-class access to platform MCP tools, supports auto-updating Benchling canvases, grants SSO users access to multiple roles, adds major QuiltSync workflow improvements, and enables partial reindexing of buckets.

## New Quilt Platform Features

### Qurator Platform Tools

Qurator can now use the platform's MCP tools — package browse and search, object search, S3 reads, Athena queries, tabulator, and package create/edit — alongside its existing in-catalog navigation. Tools execute under the user's catalog session, so all access continues to respect existing role and bucket permissions.  This works even if Quilt Connect is not activated for public MCP access.

### Asynchronous Benchling Integration

The Benchling canvas now updates asynchronously whenever Quilt updates packages, and shows as pending when first creating a package. Benchling reviewRecord events can also trigger package updates. In addition, Benchling `reviewRecord` events will also trigger package updates.

### Union-of-Roles SSO Mode

Administrators can use the new `union_roles: true` flag in their SSO configuration to grant users access to **all** matching roles, instead of just the first. Users can switch among the assigned roles via the existing role switcher, and any role no longer in the match set is revoked on next login. Default behavior is unchanged — existing SSO configurations will see no difference.

### Prefix-Scoped Reindex

Stack admins can now scope a bucket reindexing to a single prefix. `POST /api/admin/reindex/<bucket>` accepts an optional `prefix` field; when supplied, Elasticsearch indices are left in place and only keys under that prefix are re-walked.

### Admin Theme Logo Upload

The Admin > Theme editor in Admin Settings now lets you optionally upload a catalog logo file directly (PNG, JPEG, WebP, or GIF), extending the previous URL-only flow.

## New QuiltSync Release

- **Commit and Push Workflow:** QuiltSync now includes a one-step **Commit and Push** action for publishing local package changes. The action is available from the installed packages list, the commit form, and the installed package page, with settings for default message templates, workflow selection, and metadata.
- **OAuth Login:** QuiltSync now supports browser-based OAuth 2.1 login via `quilt://` deep links, with legacy code-based login retained as a fallback for stacks that do not support OAuth.
- **Local Package Creation and First Push:** Users can create local packages directly in QuiltSync, optionally choose a source directory, set a remote, and complete the first-push workflow from the app.
- **`.quiltignore` Support:** QuiltSync surfaces junk file detection badges and ignore/un-ignore controls, then filters ignored entries during package operations.
- **Diagnostics from Settings:** The former debug toolbar has been replaced by a Settings page that can collect diagnostic logs and send them to Quilt support through Sentry or email.
- **Faster Package Views:** Installed packages now render immediately from cached lineage while QuiltSync refreshes per-package status in the background.
- **Release and UI Polish:** QuiltSync now shows release notes inside the app, uses Quilt.bio branding, prevents empty commit messages, highlights packages with uncommitted changes, and protects pulls when local changes would be overwritten.
- **Reliability Improvements:** The underlying `quilt-rs` client now retries transient HTTP failures with backoff, refreshes expired S3 credentials per request, redacts secrets from debug logs, and uses atomic storage writes.

## Stack Admin Improvements

- **Admin Bucket Listings Respect Role Scope:** Admin users now see role-appropriate bucket listings (catalog navbar, landing grid, search filter, and the MCP `bucket_list` tool) instead of all buckets.
- **Wildcard Connect Hosts:** `ConnectAllowedHosts` now supports leading-dot domain suffixes (e.g. `.benchling.com`) to allow any subdomain over HTTPS.
- **Stack-Managed Bucket Protections:** Manual bucket management operations on stack-managed S3 buckets are now denied by bucket policy. All bucket configuration changes must go through CloudFormation.

## Other Improvements

- **s3-proxy Base Image:** Bumped to an updated Amazon Linux 2023 base image.
- Fixed an "Error resolving revision" flash that briefly appeared when navigating to a just-created package.
- Fixed Admin > Theme **Save** silently failing with a 403 on managed-role stacks (the modern default).
- Removed the unused "Overview URL" and "Structured data (JSON-LD)" fields from the Admin Buckets editor.
