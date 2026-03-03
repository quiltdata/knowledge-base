# Platform Update 1.68

## Connect Server w/MCP, Copy URI button, ES Graviton2 defaults, QuiltSync commit messages

This release introduces Connect Server, an opt-in internet-facing gateway that enables AI assistants to work with Quilt data via the Model Context Protocol (MCP). It also adds a Copy URI button to the S3 browser, defaults Elasticsearch to Graviton2 instances, and ships QuiltSync with auto-generated commit messages.

## New Quilt Platform Features

### Connect Server for External Integrations

Quilt now includes Connect Server, a new internet-facing gateway that exposes your Quilt platform to external services and developer tools. In this release, Connect Server powers the new [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) integration, enabling AI assistants such as Claude Desktop and Cursor to search packages, browse buckets, and read objects using natural language -- all authenticated with per-user credentials.

Key capabilities:

- **Standards-Based Authentication**: OAuth 2.0 with RFC 8414 discovery, so MCP and other clients can authenticate automatically
- **Per-User Credentials**: Each session receives scoped credentials via JWT exchange with the Registry, ensuring actions respect existing user permissions
- **Opt-In Activation**: Connect Server is disabled by default and activated by setting the `ConnectAllowedHosts` CloudFormation parameter
- **Dedicated Infrastructure**: Runs on a separate internet-facing ALB with its own certificate, isolated from the main application load balancer

### Platform MCP Server

This release includes general availability of our new stack-native MCP Server, which use the Connect Server to work seamlessly with claude.ai and any other web-based MCP client using standard authentication protocols. Stack administrators can find the MCP server URL in the `PlatformMcpServerUrl` stack output after enabling Connect.  The legacy `quilt-mcp` Python package remains available for running a local MCP server.

### Copy URI Button in S3 Browser

A new copy-URI button is available on download buttons for files and directories in the S3 browser, making it easy to copy S3 URIs for use in scripts, notebooks, and CLI workflows.

## Elasticsearch Defaults to Graviton2

Both CloudFormation and Terraform ([IAC v1.6.0](https://github.com/quiltdata/iac/releases/tag/1.6.0)) deployments now default Elasticsearch to the Graviton2 (`m6g.xlarge` / `m6g.large`) instances enabled by the prior release, for better price/performance.

### Warnings

- If you are using Elasticsearch reserved instances, contact Quilt support before upgrading to avoid paying for both.

- If you are running 1.65 or earlier, we recommend updating to 1.66 first to avoid potential days-long delays while the indexes sync.

## Other Improvements

- Running ECS tasks now propagate tags for AWS Cost Explorer visibility, improving cost attribution for Quilt workloads.
- Package creation in the File Browser now respects configured workflow successors.
- Presigned S3 URLs now use the proper region for cross-bucket package files, avoiding download failures.
- The Benchling integration now supports AWS GovCloud deployments
- Fixed errors when working with newly created cross-region buckets.
- Fixed URI display in toolbar popover code samples.

## New QuiltSync Release

- **Auto-Generated Commit Messages:** The commit page now pre-fills the message field with an automatically generated summary of changed files, streamlining the commit workflow.
- **JSONL Manifest Format:** QuiltSync has migrated its internal manifest format from Parquet to JSONL, improving performance and cross-platform compatibility. The app automatically re-fetches manifests from remote storage when a cached file is in the legacy Parquet format.
- **Windows Code Signing:** Release installers for Windows are now code-signed, reducing OS security warnings on install.
- **Bug Fixes:**
  - Fixed deep link handler failing on macOS and Linux due to URL scheme mismatch
  - Fixed stale Parquet manifest cache that prevented app startup
