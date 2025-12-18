# Quilt Platform Release 1.65.0

This release brings experimental support for AWS-native CRC64/NVMe checksums, anndata file preview, and quality of life improvements across the platform.

## New Features

- **Anndata (.h5ad) File Preview**
  Quilt now supports previewing .h5ad files directly in the Catalog. Anndata is a popular format for annotated data matrices, commonly used in single-cell genomics. The preview displays file metadata in a unified table design shared with Parquet and Quilt package previews.

- **CRC64/NVMe Checksum Support (Experimental)**
  Packages can now optionally use AWS-native CRC64/NVMe checksums instead of SHA256. This leverages S3's built-in checksum capabilities for improved performance on large files. This feature is opt-in and requires stack configuration.

- **Prefix-Scoped Bucket Access**
  Quilt now supports adding buckets where users only have access to specific prefixes. Previously, buckets required root-level permissions for Quilt to perform validation checks. With this update, administrators can configure prefix-scoped access via the `quilt3.admin` API, enabling teams to work with shared or multi-tenant buckets where they only have partial access.

## Improvements

- **Tabulator CSV Handling**
  Improved CSV validation to handle files with extra columns. When headers are present, columns are matched by name; otherwise by position. This makes Tabulator more flexible when working with CSVs that have additional columns not defined in the schema.

## Stack Admin

- PostgreSQL upgraded to version 15.15 for CloudFormation deployments.
- Lambda functions upgraded to Python 3.13 runtime.
