# Quilt Platform Release 1.65.0

## From the [RC CHANGELOG](https://github.com/quiltdata/deployment/pull/XXXX/files#diff-XXXX)

This release enhances Quilt's data management capabilities with improved prefix-scoped bucket access, extended file format support, unified metadata viewing, and infrastructure upgrades for better security and performance.

## Platform Features

- **Prefix-Scoped Bucket Access via API**

  The `quilt3.admin` API now supports prefix-scoped bucket access control, enabling fine-grained permissions management. Administrators can programmatically configure access to specific prefixes within buckets, allowing teams to maintain secure separation of data while sharing the same S3 bucket infrastructure.

- **H5AD (AnnData) File Preview**

  Quilt now provides native preview support for `.h5ad` files, the standard format for annotated data matrices in single-cell genomics. Users can inspect AnnData file structure, metadata, and key attributes directly in the Quilt catalog without downloading files or using external tools.

- **Unified Metadata Display**

  The metadata viewing experience is now consistent across H5AD, Parquet, and Quilt package previews. All three file types now use the same clean, table-based metadata component, making it easier to understand file characteristics regardless of format. The unified interface provides consistent layouts, styling, and interaction patterns throughout the catalog.

- **CRC64NVME Checksum Support**

  Packages now support optional CRC64NVME checksums in addition to existing checksum algorithms. This modern checksum algorithm provides faster validation for large files while maintaining data integrity guarantees, particularly beneficial for high-throughput data workflows.

- **Benchling Webhook Integration Service**

  Quilt introduces a production-ready webhook integration service for Benchling, enabling automated synchronization between Benchling ELN entries and Quilt packages. When Benchling entries are created or updated, the webhook service automatically creates corresponding Quilt packages with metadata, attachments, and rich context. This integration streamlines data flow from laboratory information systems into validated, versioned data packages.

  The service is deployed as a containerized AWS ECS application with API Gateway, providing secure, scalable webhook processing with comprehensive logging and monitoring.

## Stack Administration

- **PostgreSQL 15.15 Upgrade**

  CloudFormation-based deployments now use PostgreSQL 15.15, bringing the latest security patches and performance improvements to the Quilt platform database layer.

## Infrastructure & Engineering

- **Python 3.13 Runtime for Lambda Functions**

  All `.zip` packaged Lambda functions have been upgraded to the Python 3.13 runtime, ensuring access to the latest language features, performance improvements, and security updates.

- **Variants Configuration Updates**

  Updated dev-auto variant test user list for STS access and S3 policy exclusions to improve development and testing workflows.

## Coming Soon

Future releases will continue to expand integration capabilities, add more file format previews, and enhance the AI-assisted data exploration experience through Qurator and MCP server improvements.
