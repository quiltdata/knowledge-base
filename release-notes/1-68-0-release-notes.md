# Platform Update 1.68

This release introduces Connect Server, an internet-facing gateway that enables AI assistants to work with Quilt data via an integrated Model Context Protocol (MCP) server. It also includes cross-region S3 fixes, catalog improvements, and infrastructure hardening. Note that we are also changing the default ElasticSearch cluster to use Graviton instances.

## New Quilt Platform Features

### Connect Server for AI Assistant Integrations

Quilt now includes Connect Server, a new internet-facing gateway that exposes your Quilt platform to AI assistants and developer tools via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). Once enabled, AI assistants such as Claude Desktop and Cursor can search packages, browse buckets, and read objects using natural language -- all authenticated with per-user credentials.

Key capabilities:

- **Standards-Based Authentication**: OAuth 2.0 with RFC 8414 discovery, so MCP and other clients can authenticate automatically
- **Per-User Credentials**: Each session receives scoped credentials via JWT exchange with the Registry, ensuring actions respect existing user permissions
- **Opt-In Activation**: Connect Server is disabled by default and activated by setting the `ConnectAllowedHosts` CloudFormation parameter
- **Dedicated Infrastructure**: Runs on a separate internet-facing ALB with its own certificate, isolated from the main application load balancer

### Platform MCP Server

This release includes general availability of our new stack-native MCP Server, which use the Connect Server to work seamlessly with claude.ai and any other web-based MCP client using standard authentication protocols. Stack administrators can find the MCP server URL in the `PlatformMcpServerUrl` stack output after enabling Connect.  The legacy `quilt-mcp` Python package remains available for running a local MCP server.

### Copy URI Button in S3 Browser

A new copy-URI button is available on download buttons for files and directories in the S3 browser, making it easy to copy S3 URIs for use in scripts, notebooks, and CLI workflows.

### Improved Package Destination Defaults

When creating a package from the File Browser, the current bucket is now offered as a destination only when no workflow configuration is present. When workflow successors are configured, they are always respected, reducing confusion about where packages are created.

## Bug Fixes

- Fixed an issue where presigned S3 URLs used the wrong region for cross-bucket package files, causing download failures.
- Fixed errors when working with newly created cross-region buckets.
- Fixed text selection in toolbar popover code samples so users can copy code snippets reliably.

## Other Improvements

- **ECS Task Tagging**: Running ECS tasks now propagate tags for AWS Cost Explorer visibility, improving cost attribution for Quilt workloads.
- **GovCloud Compatibility**: Fixed a hardcoded ARN partition in the Benchling integration to support AWS GovCloud deployments.

## Elasticsearch Defaults to Graviton2

Both CloudFormation and Terraform ([IAC v1.6.0](https://github.com/quiltdata/iac/releases/tag/1.6.0)) deployments now default Elasticsearch to Graviton2 (`m6g.xlarge` / `m6g.large`) for better price/performance.

> **Warning:** If you are using Elasticsearch reserved instances, contact Quilt support before upgrading to avoid paying for both.

## QuiltSync v0.14

### Auto-Generated Commit Messages

The commit page now pre-fills the message field with an automatically generated summary of changed files, streamlining the commit workflow.

### JSONL Manifest Format

QuiltSync has migrated its internal manifest format from Parquet to JSONL, improving performance and cross-platform compatibility. The app automatically re-fetches manifests from remote storage when a cached file is in the legacy Parquet format.

### Windows Code Signing

Release installers for Windows are now code-signed, reducing OS security warnings on install.

### QuiltSync Bug Fixes

- Fixed deep link handler failing on macOS and Linux due to URL scheme mismatch
- Fixed stale Parquet manifest cache that prevented app startup

