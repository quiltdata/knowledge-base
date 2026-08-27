# Platform Update 26.8

This release redesigns how you move through the Catalog: a persistent sidebar replaces the top navigation bar, queries get a single global page of their own, and the home page becomes one unified volume list. Packages can now be sorted by the metadata fields your team defines. Two security fixes ship — deactivating a user now cuts off their data access immediately, and advanced search queries are authorized against every index they touch — alongside a support diagnostics collector for admins and steadier behavior across package events, tabular queries, and package revisions.

## Quilt Platform Changes

### A New Catalog Shell

Navigation moves from the top bar to a persistent sidebar: Volumes, Search, Queries, Bookmarks, Qurator, and Admin are always one click away, and a search bar is always on screen. Inside a bucket, the tabs are renamed and reordered to Overview, Files, Packages, and Workflows.

The home page is now a single volume list with a text filter and a cards/list toggle — cards remain the default view, and a denser list view is new. Filtering to no matches now reports how many volumes were searched and offers to drop individual terms, instead of a dead end; on a first visit, admins get an Add Bucket action right in the empty state.

### One Queries Page

Queries move out of the per-bucket tabs onto a global Queries page, where the bucket is a parameter of the query rather than a place you have to navigate into first. Bookmarked bucket query URLs redirect to the new page.

The ElasticSearch query console is being sunset: it is no longer shown by default, and Queries is Athena-only out of the box. If your team still relies on the console, an admin can re-enable it with the `elasticsearch-queries` toggle in Admin Settings.

### Sort Packages by Metadata

Packages can now be sorted by metadata fields — sort a study list by a numeric field, a date, or any keyword your packages carry, ascending or descending. In the search sidebar, the metadata filter list itself can also be ordered by field name or type, and the arrangement rides the URL, so a shared link reproduces exactly the view you set up.

### Security: Deactivation Takes Effect Immediately

Deactivating a user now cuts off their access to bucket data immediately. Previously, a deactivated user who could still authenticate at your identity provider could regain read access — notably through package and directory downloads. Deactivated users now receive a `401` response on endpoints that previously returned `403`.

### Security: Advanced Searches Are Fully Authorized

Advanced ElasticSearch queries submitted through the search API are now authorized against every index the request body touches, not only the index named in the URL. Previously, an authenticated user with read access to one bucket could craft a query that read indexed metadata and file content from other buckets on the stack; such a query now returns a validation error.

## Stack Admin Improvements

### An IAM Role per Quilt Role

The registry can now provision a distinct IAM role for each Quilt managed role — "alias roles" — so a Quilt role becomes its own principal that AWS services such as Lake Formation and DataZone can grant against, instead of every managed role sharing one IAM identity. The permissions the registry gains for this are narrowly scoped, and a migration provisions alias roles for existing managed roles on upgrade.

If IAM role creation is governed in your account — service control policies, permission boundaries, or change alarms — account for one new IAM role per Quilt managed role before upgrading. Otherwise no action is required.

### Support Diagnostics

The stack now ships a support diagnostics collector: a dormant, read-only Lambda that gathers search-cluster health and stack infrastructure state into a short-lived bucket in your account, invoked from the AWS CLI or from the Catalog's admin Settings. Nothing outside your account — Quilt included — can invoke it or read a bundle. Use it to hand Quilt support a complete picture without granting anyone access.

### Sturdier Accounts Administration

The stack-managed `_canary` monitoring account can no longer be disabled, deleted, or have its role or email changed, so routine user administration cannot silently break stack monitoring. The admin Users table now also records a real last-login time for SSO and service accounts, which previously stayed frozen at account creation.

## Other Improvements

- Package events are now processed per message: a malformed or unprocessable event is retried and dead-lettered on its own, instead of failing the whole batch and silently dropping package notifications batched alongside it. The test event S3 sends when a bucket is added no longer causes failures.
- Tabulator queries against Parquet tables with text columns no longer fail with an internal Athena error.
- Revising a package whose existing contents fail to load is now blocked with the reason shown, instead of silently producing a revision containing only the newly added files.
- When the stack's web tier generates an error itself — a timeout or an oversized upload — the browser now shows the real status code instead of a misleading cross-origin error.
- The MCP server's package search works again with the new metadata-sorting search contract.
- Assorted polish: admin form actions stay visible while scrolling long forms, tabular previews that fail to render no longer take down the page, buckets without a custom icon get consistent identity marks everywhere, and animations respect your reduced-motion preference.
