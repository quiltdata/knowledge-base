# Platform Update 1.68

This release introduces Connect Server, an internet-facing gateway that enables AI assistants to work with Quilt data via the Model Context Protocol (MCP). It also includes cross-region S3 fixes, catalog improvements, and infrastructure hardening.

## New Quilt Platform Features

### Connect Server for AI Assistant Integrations

Quilt now includes Connect Server, a new internet-facing gateway that exposes your Quilt platform to AI assistants and developer tools via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). Once enabled, AI assistants such as Claude Desktop and Cursor can search packages, browse buckets, and read objects using natural language -- all authenticated with per-user credentials.

Key capabilities:

- **Standards-Based Authentication**: OAuth 2.0 with RFC 8414 discovery, so MCP clients can authenticate automatically
- **Per-User Credentials**: Each session receives scoped credentials via JWT exchange with the Registry, ensuring actions respect existing user permissions
- **Opt-In Activation**: Connect Server is disabled by default and activated by setting the `ConnectAllowedHosts` CloudFormation parameter
- **Dedicated Infrastructure**: Runs on a separate internet-facing ALB with its own certificate, isolated from the main application load balancer

Stack administrators can find the MCP server URL in the `PlatformMcpServerUrl` stack output after enabling Connect.

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
- **Elasticsearch Instance Upgrade**: ES instances upgraded to 6g (Graviton) for all CloudFormation deployments, reducing costs.
- **GovCloud Compatibility**: Fixed a hardcoded ARN partition in the Benchling integration to support AWS GovCloud deployments.
