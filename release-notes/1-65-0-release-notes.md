# Quilt Platform Release 1.65.0

## From the [RC CHANGELOG](https://github.com/quiltdata/deployment/pull/XXXX/files#diff-XXXX)

This release enhances Quilt's data management capabilities with improved prefix-scoped bucket access, extended file format support, unified metadata viewing, and infrastructure upgrades for better security and performance.

## Platform Features

- **Prefix-Scoped Bucket Access via API**

  The `quilt3.admin` API now supports prefix-scoped bucket access control, enabling fine-grained permissions management. Administrators can programmatically configure user access to specific S3 bucket prefixes rather than entire buckets, allowing teams to maintain secure separation of data while sharing the same S3 bucket infrastructure. This feature is particularly valuable for multi-tenant environments where different teams need isolated access within a shared bucket.

- **H5AD (AnnData) File Preview**

  Quilt now provides native preview support for `.h5ad` files, the standard format for annotated data matrices in single-cell genomics. The preview capability required converting the `tabular_preview` Lambda function from a zip-packaged Python runtime to a Docker container image deployment to support the additional dependencies required for AnnData processing. Users can now inspect `.h5ad` file structure, metadata, and key attributes directly in the Quilt catalog without downloading files or using external tools.

- **Unified Metadata Display**

  The metadata viewing experience is now consistent across H5AD, Parquet, and Quilt package previews. All three file types now use the same clean, table-based metadata component (replacing the previous separate `ParquetMeta` component), making it easier to understand file characteristics regardless of format. The unified interface provides consistent layouts, styling, and interaction patterns throughout the catalog, with dynamic rendering based on metadata type.

- **CRC64NVME Checksum Support**

  Packages now support optional CRC64NVME checksums as an alternative to SHA256 checksums. This AWS-precomputed checksum algorithm provides significantly faster validation for large files while maintaining data integrity guarantees, particularly beneficial for high-throughput data workflows. The implementation uses a two-tier retrieval strategy: precomputed checksums when available, with multipart upload (MPU) fallback for calculation when needed. The feature is controlled by the new `CRC64Checksums` CloudFormation parameter (default: Disabled), replacing the legacy `ChunkedChecksums` parameter. When enabled, increased limits support larger packages: up to 5,100 files, 11 TiB total size, and 5 TiB individual file size.

## Stack Administration

- **PostgreSQL 15.15 Upgrade**

  CloudFormation-based deployments now use PostgreSQL 15.15 (upgraded from 15.12), bringing the latest security patches and performance improvements to the Quilt platform database layer. This minor patch upgrade is backwards-compatible and includes coordinated updates across the CloudFormation template and Terraform configurations.

## Infrastructure & Engineering

- **Python 3.13 Runtime for Lambda Functions**

  All 13 `.zip` packaged Lambda functions have been upgraded from Python 3.11 to Python 3.13 runtime, ensuring access to the latest language features, performance improvements, and security updates. Upgraded functions include: `access_counts`, `preview`, `tabular_preview`, `transcode`, `iceberg`, `pkgevents`, `pkgpush`, `s3hash`, `status_reports`, `es_ingest`, and `manifest_indexer`. Handler paths have been updated to use fully qualified module names (e.g., `t4_lambda_access_counts.index.handler`) for improved clarity.

- **Variants Configuration Updates**

  Updated dev-auto variant test user list for STS access and S3 policy exclusions to improve development and testing workflows.

## Coming Soon

Future releases will continue to expand integration capabilities, add more file format previews, and enhance the AI-assisted data exploration experience through Qurator and MCP server improvements.
