# Quilt Platform Release 1.64.0

## From the [RC CHANGELOG](https://github.com/quiltdata/deployment/pull/2176/files#diff-06ee5dbd187ec4e5b38a42594456cb3c81699d4398919ebf1933765dcaa1c9fb)

This release strengthens Quilt's position as the integration point for AI science, with a new MCP server, visual diffs, external Iceberg support, and Qurator context enhancements.

## Quilt MCP Server

- **MCP Server Package**

  Quilt is excited to release an open source Model Context Protocol server via the [`quilt-mcp` package](https://pypi.org/project/quilt-mcp/), including comprehensive tools for:

  - creating rich packages, complete with auto-generated metadata, READMEs, summaries, and visualization
  - searching, querying, and browsing packages
  - setting up and using generic metadata templates
  - configuring and querying Tabulator tables
  - managing users and roles (if a Quilt admin)

- **Quilt MCP Workshop**

- **Tabulator Configuration for Non-Admin Users**
  ~Users with write access to a bucket can now configure tabulator tables without needing admin privileges, allowing anyone to quickly setup cross-package analyses of tabular data.~

  > EP: This is currently only for direct GraphQL calls, e.g. via MCP, not quilt3 or the catalog GUI, right? So we probably shouldn't mention it.

## New Catalog Features

- **Visual Revision Diffs**
  Quilt has always made it easy to track multiple versions of your packages and the data inside them. Now you can quickly see what has changed between revisions. Use the new double-arrow icon to quickly view What's Changed from the previous version:

  Or view the Detailed Comparision to see the exact diff between any two revisions:

- **External Iceberg Access to Package Information**
  Quilt package information is accessible as an Iceberg data catalog, enabling high-performance, low-cost SQL-based querying of packages and entries to external users (Athena, DataBricks, Snowflake, etc.). Access to Iceberg from inside the Quilt catalog is planned for a future release.
  
  > EP: Link to schema documentation? Partitioning?

## Qurator Enhancements

- **Qurator Auto-Context Loading**
  Qurator now automatically loads context files (AGENTS.md and README.md) and package metadata from the current and parent locations, providing richer context for AI-assisted data exploration without manual setup.

- **Enhanced Qurator Context Management**
  Qurator now intelligently limits search results context to 100k characters, preventing context window overflow and ensuring more reliable AI responses for large datasets.

- **Improved Qurator Tool Message Styling**
  Tool messages in Qurator conversations feature enhanced visual styling for better readability and a more polished user experience.

## Other Improvements

- Fixed an issue that prevented package creation from directories containing hash characters (`#`) in their names.

- Fixed search results and package listings to link directly to the "latest" package revision instead of specific revisions, so it is easier to edit files.

- Enabling circuit breakers when deploying ECS services, so that deployments fail quickly if the container fails health checks.
  
  > EP: Does this matter for anyone other than us?
