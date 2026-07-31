# Platform Update 26.7

This release combines a broad batch of security and reliability improvements across the stack with QuiltSync v0.20.0, which adds role switching, safer pulls, and clearer revision details. It also brings safer file deletion in the Catalog, clearer errors for malformed searches, steadier registry memory use under sustained load, and a new date-based numbering scheme for Quilt Platform releases.

## A Note on Version Numbering

Starting with this release, Quilt Platform version numbers are date-based: **26.7** is the release for July 2026. The previous release was 1.71.

Existing minimum-version constraints such as "1.70.0 or higher," along with tooling that compares release versions, continue to work because 26.7 sorts after every 1.x release.

This changes what the numbers mean, not the platform — it is not a jump of twenty-five major versions, and nothing about compatibility or the upgrade path changes with it. Version tags keep the same three-part form (`26.7.0`), and the third number still marks patch releases off a given month's release (`26.7.1`, `26.7.2`, and so on).

## Quilt Platform Changes

### Deleting a File Now Preserves Earlier Versions

Deleting a file from the Catalog on a versioning-enabled bucket now adds an S3 delete marker instead of erasing that version of the object. The file leaves the bucket listing as before, but earlier versions stay browsable and any package pinning them keeps resolving. On buckets without versioning enabled, deletion still removes the object permanently.

Deleting a specific object version requires `s3:DeleteObjectVersion`, which Quilt read-write roles do not grant by default. Ask a Quilt admin to attach a custom policy granting this action to your role; otherwise `delete_object` calls, including through `quilt3`, fail with `AccessDenied`. No action is required if nothing in your workflows deletes specific object versions.

### Clear Errors for Malformed Searches

A search query that cannot be parsed — an unparseable numeric term, an invalid regular expression, or malformed Lucene syntax — now returns a validation error instead of failing with a server error.

### Steadier Registry Memory Use

The registry now recycles its request-handling workers gracefully, using staggered worker lifetimes together with a per-worker memory cap, so gradual memory growth no longer ends in abrupt out-of-memory kills. Those kills could land mid-request and surface as an intermittent gateway error or a full-page Catalog error.

## QuiltSync v0.20.0

[QuiltSync](https://www.quilt.bio/quiltsync), the desktop sync client for Quilt packages, now handles multi-role access and local changes more gracefully.

### Role Switching

- **Switch Roles in QuiltSync:** Settings > Auth now shows the active role for each Quilt catalog login and lets users with multiple roles switch directly in the app. The selected role takes effect on the next read or write.
- **Clearer Permission Guidance:** When the active role cannot access a bucket, QuiltSync identifies the role and offers an opportunity to switch instead of showing a raw storage error or asking the user to sign in again. Commit is disabled before the operation starts, and Autosync pauses until the role changes.

### Safer Pulls and Clearer Revisions

- **Preserve Non-Conflicting Local Work:** Pull now keeps local edits that do not conflict with incoming remote changes. QuiltSync identifies conflicts before pulling and directs users to commit and resolve only when the same files changed locally and remotely. Autosync uses the same behavior.
- **Readable Revision Details:** Version-mismatch banners now show the revision's commit message instead of its top hash, with the full hash available on hover.

Download [QuiltSync v0.20.0](https://www.quilt.bio/quiltsync).

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
