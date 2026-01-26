# Quilt Platform Release 1.67.0

This release introduces **API Keys** for programmatic authentication, enabling headless and automation workflows. It also includes infrastructure improvements with an Elasticsearch upgrade and cost optimizations.

## New Quilt Platform Features

### API Keys for Programmatic Authentication

Quilt now supports **API Keys** for headless and programmatic authentication, enabling secure automation workflows without interactive logins. This feature is designed for:

- **CI/CD Pipelines**: Authenticate automated builds and deployments that push or pull Quilt packages
- **Data Processing Scripts**: Enable long-running batch jobs to access Quilt data without user intervention
- **Service Accounts**: Create dedicated credentials for applications and services integrating with Quilt
- **Command-Line Tools**: Simplify authentication for CLI-based workflows and automation scripts

API Keys can be created and managed through the Quilt Platform interface. Each key can be scoped to specific permissions and revoked independently for security control.

For detailed usage instructions, see the [API Keys documentation](https://docs.quilt.bio).

### Delete Object Configuration

The `deleteObject` property is now available in the GUI configuration editor, allowing administrators to explicitly enable or disable file and directory delete buttons in the Bucket tab. This configuration option provides fine-grained control over deletion capabilities for different deployments.

## Infrastructure Improvements

### Elasticsearch 7.10 Upgrade

CloudFormation deployments now support **Elasticsearch 7.10**, providing improved performance and compatibility with modern search features.

**Upgrade Recommendation**: For CloudFormation users upgrading from 1.66, following the standard upgrade process is recommended to minimize search downtime.

### Cost-Optimized Instance Types

Quilt now supports newer AWS Graviton-based instance types for Elasticsearch, offering improved price-performance. Deployments can benefit from reduced infrastructure costs while maintaining or improving search performance.
