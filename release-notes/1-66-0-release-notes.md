# Quilt Platform Release 1.66.0

This release introduces the **Benchling Webhook Integration Service**, enabling seamless data synchronization between Benchling and Quilt. Additionally, this release includes important infrastructure upgrades and UI improvements for better security and user experience.

## New Quilt Platform Features

### Benchling Webhook Integration Service

Quilt now offers a **seamless integration** with [Benchling](https://www.benchling.com/), the leading cloud platform for life sciences R&D. This integration creates an automatic connection between Benchling's Electronic Lab Notebook and Quilt's scientific data management capabilities.

#### What It Does

When scientists create or update notebook entries in Benchling, the webhook integration automatically:

- **Creates Quilt Packages**: Generates a dedicated package for each Benchling entry, preserving the complete experimental context
- **Transfers Files**: Copies all attachments from Benchling notebooks directly into Amazon S3 as part of the package structure
- **Synchronizes Metadata**: Captures experiment IDs, author information, and other laboratory data into Quilt package metadata
- **Enables Discovery**: Makes all content searchable through ElasticSearch and queryable via Amazon Athena for organizational data discovery
- **Links Systems**: Allows bidirectional connections by tagging Quilt packages with Benchling notebook IDs (e.g., `EXP00001234`)

#### Benchling App Canvas Integration

The integration includes a **Benchling App Canvas** that lets users view, browse, and synchronize associated Quilt packages directly within Benchling. From the canvas, users can open packages in the Quilt Catalog or QuiltSync for deeper analysis.

#### Quick Deployment

Deploy the complete integration infrastructure to your AWS account with a single command:

```bash
npx @quiltdata/benchling-webhook --yes
```

For detailed configuration, setup instructions, and usage examples, see the [Benchling Integration documentation](https://docs.quilt.bio/quilt-ecosystem-integrations/benchling) or the [GitHub repository](https://github.com/quiltdata/benchling-webhook).

## UI Improvements

### Enhanced Object Management Security

File and directory delete buttons in the Bucket tab are now **hidden by default** to prevent accidental deletions. Administrators can enable these actions using the `ui.actions.deleteObject` configuration parameter when needed for specific workflows.

This change provides an extra layer of protection for critical data while maintaining flexibility for teams that require direct object management capabilities.

## Bug Fixes

### Package Revision Search Fixed for 2026+

Resolved an issue where search and events for package revisions created in 2026 and later were not functioning correctly. The platform now properly indexes and retrieves packages regardless of creation date.

## QuiltSync v0.10.0

[QuiltSync](https://www.quilt.bio/quiltsync), the desktop sync client for Quilt packages, has been updated with quality-of-life improvements for a smoother user experience:

### Enhanced Usability

- **Auto-Select Files on Install**: All checkboxes are now automatically selected when loading the file installation page, making it faster to download complete packages
- **Auto-Focus Commit Message**: The commit message input field now automatically receives focus, streamlining the workflow when creating package revisions

### QuiltSync Bug Fixes

- **Fixed macOS Deep Links**: Resolved an issue with handling macOS deep links (`quilt+s3://` URIs) on first application start, ensuring QuiltSync opens correctly when clicked from the Catalog

Download the latest version at [quilt.bio/quiltsync](https://www.quilt.bio/quiltsync) or view the [full release notes](https://github.com/quiltdata/quilt-rs/releases/tag/QuiltSync%2Fv0.10.0).

## Infrastructure Upgrades

### Elasticsearch 7.10 for CloudFormation Deployments

CloudFormation-based deployments now use **Elasticsearch 7.10**, providing improved performance, security patches, and better compatibility with modern AWS infrastructure.

### Extended SQS Retention for Indexer Queues

The retention period for indexer queues has been increased to **14 days** (the maximum allowed by AWS SQS). This enhancement provides better resilience against temporary processing delays and makes it easier to recover from extended service interruptions without data loss.

---

## Getting Started

To upgrade to Quilt Platform 1.66.0, follow the standard [upgrade procedures](https://docs.quilt.bio/quilt-platform-administrator/upgrade) in the documentation.

For questions or support, please contact the Quilt team or visit our [community forum](https://github.com/quiltdata/quilt/discussions).
