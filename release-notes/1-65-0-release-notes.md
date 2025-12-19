# Quilt Platform Release 1.65.0

This release adds fast packaging for S3 data by leveraging AWS-native CRC64/NVMe checksums, adds a preview for H5AD (AnnData) files, and introduces a number of quality of life improvements across the platform.

## New Quilt Platform Features

### CRC64/NVMe Checksum Support (Experimental)

Packaging large files that are already in S3 is now up to **10x faster** with the new CRC64/NVMe checksum option. Instead of computing SHA256 hashes manually, Quilt can leverage S3's built-in AWS-native checksums for dramatically improved performance.

This feature is opt-in and requires enabling the `CRC64Checksums` stack parameter.

![enable CRC64Checksums](./1-65-media/enable-checksums.png)

### AnnData (`.h5ad`) File Preview

Quilt now supports previewing **AnnData files** directly in the Catalog. [AnnData](https://anndata.readthedocs.io/en/stable/) is a widely used data model for annotated matrices, particularly in [single-cell genomics](https://www.nature.com/articles/nmeth.3862).

#### Tabular Metadata View

![Tabular Metadata View](./1-65-media/h5ad-preview.png)

The preview displays AnnData metadata in a new, unified table design shared with Parquet and Quilt package previews. For small H5AD files it will also show a table of QC metrics.

### Increased Tabulator Flexibility

Tabulator's CSV validation has been enhanced to handle files with extra columns. Columns are matched by name when headers are present (otherwise by position). This makes Tabulator more flexible when working with CSVs that have additional columns not defined in the schema.

## New Python SDK Features

### Bucket Management API

The `quilt3` Python SDK now includes a complete API for programmatic bucket management through the new `quilt3.admin.buckets` module. Administrators can now register, configure, and manage S3 buckets in Quilt entirely through code.

The new module provides functions to add, retrieve, update, and remove bucket configurations with comprehensive error handling. This complements the existing graphical Admin Settings interface and enables automation of bucket management workflows. See the [Admin API documentation](https://docs.quilt.bio/quilt-platform-administrator/admin-1) for details.

#### New: Prefix-Scoped Bucket Access

The add bucket API can also be used when the Quilt account only has access to specific prefixes of a bucket, enabling teams to add selected portions of shared or multi-tenant buckets to the search index. Note that the bucket itself will be visible but not browsable in the Quilt Catalog.

![cross-account espresso prefix search](./1-65-media/cross-account-espresso.png)

## Other Improvements

- PostgreSQL upgraded to version 15.15 for CloudFormation deployments.
- Several Lambda functions upgraded to work with Python 3.13 runtime.
