# Quilt Platform Release 1.64.0

This release brings powerful new capabilities for package management and data exploration, including Athena integration with Iceberg tables, package revision comparison, and enhanced Qurator context loading.

## New Features

- **Athena Database with Iceberg Tables**
  Quilt packages are now accessible via an Athena database using Iceberg table format, enabling SQL-based querying and analytics directly on your package data.

- **Package Revision Comparison**
  Compare different revisions of a package side-by-side to understand what changed between versions, making it easier to track data evolution and collaborate with confidence.

- **Direct Links to Latest Package Revisions**
  Search results and package listings now link directly to the "latest" revision, simplifying navigation and ensuring you're always viewing the most current version.

- **Qurator Auto-Context Loading**
  Qurator now automatically loads context files (AGENTS.md and README.md) and package metadata, providing richer context for AI-assisted data exploration without manual setup.

- **Tabulator Configuration for Non-Admin Users**
  Users with write permissions can now configure tabulator tables without requiring admin privileges, enabling more flexible data visualization workflows.

## Bug Fixes

- Fixed an issue that prevented package creation from directories containing hash characters (`#`) in their names.

## Other Improvements

- Limited Qurator search results context to 100k characters to prevent context window overflow and improve response reliability.
- Improved visual styling of tool messages in Qurator for better readability.
- Enhanced deployment stability with circuit breaker configuration for ECS services.
