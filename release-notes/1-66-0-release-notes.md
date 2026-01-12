# Quilt Platform Release 1.66.0

This release integrates the **Benchling Webhook**, enabling seamless data synchronization between Benchling and Quilt. It also includes **QuiltSync v0.10** with enhanced usability features and improved macOS support. Additionally, this release switches GUI object deletion to opt-in and makes package indexing more robust.

## New Quilt Platform Features

### Benchling Webhook Integration Service

Quilt now offers **seamless integration** with [Benchling](https://www.benchling.com/), a leading cloud platform for life sciences R&D. This integration creates an automatic connection between Benchling's Electronic Lab Notebook and Quilt data packages.

#### What It Does

When scientists create or update notebook entries in Benchling, the webhook integration automatically:

- **Creates Quilt Packages**: Generates a dedicated package for each Benchling entry, preserving the complete experimental context
- **Transfers Files**: Copies all attachments from Benchling notebooks directly into Amazon S3 as part of the package structure
- **Synchronizes Metadata**: Captures experiment IDs, author information, and other laboratory data into Quilt package metadata
- **Enables Discovery**: Makes package content searchable through ElasticSearch and queryable via Amazon Athena for organizational data discovery

#### Benchling App Canvas Integration

The integration includes a **Benchling App Canvas** that creates a bidirectional bridge between Benchling notebooks and Quilt packages. When you or your template embeds the Quilt canvas in a notebook, you get:

- **Packages in Context**: Browse associated package filenames and metadata directly from inside Benchling notebook entries
- **One-Click Package Access**: Click package names to instantly open them in the Quilt Catalog for detailed exploration
- **QuiltSync Integration**: Use the sync button to open packages in QuiltSync for local file editing and uploads
- **Direct Updates**: Refresh package contents on-demand to reflect the latest entries, metadata, and attachments.
- **Linked Packages**: View associated Quilt packages whose (by default) `experiment_id` metadata field is set to that Benchling notebook ID (e.g., `EXP00001234`)

#### Command-line Configuration

Configure or customize the integrated Benchling Webhook using a single `npm` command:

```bash
npx @quiltdata/benchling-webhook@latest
```

For detailed configuration, setup instructions, and usage examples, see the [Benchling Integration documentation](https://docs.quilt.bio/quilt-ecosystem-integrations/benchling) or the [GitHub repository](https://github.com/quiltdata/benchling-webhook).

### Object Deletion Now Opt-In

File and directory delete buttons in the Bucket tab are now **hidden by default** to prevent accidental deletions. Administrators can enable these actions using the `ui.actions.deleteObject` configuration parameter when needed for specific workflows.

This change provides an extra layer of protection for critical data while maintaining flexibility for teams using Quilt as an alternative front-end to Amazon S3.

## Infrastructure Improvements

### Package Revision Search Fixed for 2026+

Resolved an issue where package revisions (other than `latest`) created in 2026 were not properly indexed. This update includes a fix and will automatically reindex any revisions that were overlooked.

### Preliminary Support for Elasticsearch 7.10

The registry server now uses the **Elasticsearch 7.10** client,
in preparation for an upcoming upgrade.

### Extended SQS Retention for Indexer Queues

The retention period for indexer queues has been increased to **14 days** (the maximum allowed by AWS SQS). This enhancement provides better resilience against temporary processing delays and makes it easier to recover from extended service interruptions without data loss.

---

## QuiltSync v0.10.0

[QuiltSync](https://www.quilt.bio/quiltsync), the desktop sync client for Quilt packages, has been updated with quality-of-life improvements for a smoother user experience:

### Enhanced Usability

- **Auto-Select Files on Install**: All checkboxes are now automatically selected when loading the file installation page, making it faster to download complete packages
- **Auto-Focus Commit Message**: The commit message input field now automatically receives focus, streamlining the workflow when creating package revisions

### QuiltSync Bug Fixes

- **Fixed macOS Deep Links**: Resolved an issue with handling macOS deep links (`quilt+s3://` URIs) on first application start, ensuring QuiltSync opens correctly when clicked from the Catalog

Download the latest version at [quilt.bio/quiltsync](https://www.quilt.bio/quiltsync).
