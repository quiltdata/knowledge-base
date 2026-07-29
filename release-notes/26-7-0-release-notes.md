# Platform Update 26.7

This is primarily a security and reliability release: a broad batch of infrastructure hardening across the stack, safer file deletion in the Catalog, clearer errors for malformed searches, and steadier registry memory use under sustained load. It also changes how Quilt Platform releases are numbered.

## A Note on Version Numbering

Starting with this release, Quilt Platform version numbers are date-based: **26.7** is the release for July 2026. The previous release was 1.71.

This changes what the numbers mean, not the platform — it is not a jump of twenty-five major versions, and nothing about compatibility or the upgrade path changes with it. Version tags keep the same three-part form (`26.7.0`), and the third number still marks patch releases off a given month's release (`26.7.1`, `26.7.2`, and so on). Documentation that gives a minimum version as "1.70.0 or higher" continues to read correctly: 26.7 is later than any 1.x release.

## Quilt Platform Changes

### Deleting a File Now Preserves Earlier Versions

Deleting a file from the Catalog on a versioning-enabled bucket now adds an S3 delete marker instead of erasing that version of the object. The file leaves the bucket listing as before, but earlier versions stay browsable and any package pinning them keeps resolving. On buckets without versioning enabled, deletion still removes the object permanently.

A permission change comes with this. Managed read-write roles no longer grant `s3:DeleteObjectVersion`, so permanently erasing a specific object version is now an administrator operation: a Quilt admin can grant that action through a custom policy for roles that genuinely need it. If you previously relied on a managed read-write role to permanently delete object versions — including via `quilt3` — those calls will now fail with `AccessDenied` until an admin grants the action.

### Clear Errors for Malformed Searches

A search query that cannot be parsed — an unparseable numeric term, an invalid regular expression, or malformed Lucene syntax — now returns a validation error instead of failing with a server error.

### Steadier Registry Memory Use

The registry now recycles its request-handling workers gracefully, using staggered worker lifetimes together with a per-worker memory cap, so gradual memory growth no longer ends in abrupt out-of-memory kills. Those kills could land mid-request and surface as an intermittent gateway error or a full-page Catalog error.

## Stack Admin Improvements

This release closes a large batch of security-scanner findings across the CloudFormation template. Nearly all of them are configuration changes with no effect on how the stack behaves; the exceptions are called out below.

### Encryption and Transport

- All HTTPS listeners — the main, private, and Quilt Connect load balancers — now use AWS's current recommended TLS policy, which keeps TLS 1.3 and 1.2 with forward-secret ciphers, adds post-quantum key exchange, and drops only legacy CBC ciphers. Client impact is negligible.
- Both load balancers now drop incoming HTTP headers containing characters that are invalid per the HTTP specification, rather than forwarding them upstream. Well-formed traffic is unaffected.
- Every SQS queue now explicitly requires TLS for sending and receiving messages. The queues were already encrypted, so this is a belt-and-braces change with no effect on delivery.

### Storage and Key Configuration

- The internal service buckets (DuckDB-select, ES-ingest, Iceberg, Tabulator, and user Athena results) now declare S3 Block Public Access and enforced bucket-owner object ownership explicitly. These buckets were already private; stating the settings in the template makes the configuration visible to scanners and detectable if it ever drifts.
- The SNS notification encryption key now has automatic key rotation enabled. Existing key material is retained, so data encrypted before the change stays readable.
- The analytics bucket no longer declares a CORS configuration. The rule was unused — the Catalog reads access counts through the registry API rather than from the bucket directly — so removing it changes no access.

### Least-Privilege Roles

- The package-events Lambda's role no longer carries a broad managed EventBridge policy. It now grants only the single action the Lambda uses, on the account's default event bus, which also removes the account-wide role-passing permission that managed policy included.
- The access-counts Lambda's role no longer grants its Athena and Glue actions on all resources; they are now scoped to its own workgroup and to the stack's own Glue catalog, database, and tables.
- Every role trusted by ECS or EventBridge now requires the calling service to be acting for this account, the cross-service guard both services' documentation prescribes. Trust-policy updates apply without interruption.

### Athena Workgroups

- The Iceberg and audit-trail workgroups now enforce their workgroup configuration, so client-side query settings can no longer override it. For the audit-trail workgroup this guarantees what the documentation already describes: audit query results are written to the audit-trail bucket.
- The access-counts Lambda now runs its hourly queries in a dedicated, stack-owned Athena workgroup instead of the account-shared `primary` workgroup. Administrators will see one additional workgroup in the stack.

### Logging and Service Configuration

- CloudWatch log groups — the registry and nginx group, and all platform Lambda groups — now retain logs for 365 days, up from 90. Logs are kept roughly four times longer; the only cost change is CloudWatch Logs archival storage, as log ingestion is unchanged.
- All security-group rules now carry a description naming the traffic they permit.
- Fargate services now state their platform version explicitly, matching the value Fargate already used by default.

## Other Improvements

- The S3-notification forwarding Lambda no longer writes the full event payload to CloudWatch on every invocation. This was a debugging leftover that dominated log volume on busy stacks; it now logs only on failure, including the record that failed.
- That same Lambda now ignores the test event S3 sends when a bucket's notification configuration is created, instead of failing on it. Previously each test event cycled through retries into the dead-letter queue and could take genuine events batched alongside it.
