# Quilt Platform Release 1.67.0

This release introduces **API Keys** for programmatic authentication, enabling headless and automation workflows. It also includes infrastructure improvements with an Elasticsearch upgrade and cost optimizations.

## New Quilt Platform Features

### API Keys for Programmatic Authentication

Quilt now supports **API Keys** for headless and programmatic authentication, enabling secure automation workflows without interactive logins. Users can create and manage their own API keys through the Python API, eliminating the need to store SSO credentials or interactive sessions for automation.

**Key capabilities:**

- **Self-Service Management**: Create, list, and revoke your own API keys using `quilt3.api_keys.create()`, `list()`, and `revoke()`
- **Simple Authentication**: Use `quilt3.login_with_api_key(key)` to authenticate headless clients—no disk state or renewal required
- **Flexible Expiration**: Set key lifetimes from 1 day to 1 year based on your security requirements
- **Immediate Revocation**: Revoked keys fail instantly, enabling quick response to security incidents

**Use cases:**

- **CI/CD Pipelines**: Authenticate automated builds and deployments that push or pull Quilt packages
- **Batch Jobs**: Enable long-running data processing scripts to access Quilt data without user intervention
- **Scheduled Tasks**: Run automated workflows on recurring schedules without session expiration issues

API keys inherit the full permissions of the user who creates them and can be managed entirely through the `quilt3` Python API.

For detailed usage instructions, see the [API Keys documentation](https://docs.quilt.bio).

### Delete Object Configuration

The `deleteObject` property is now available in the GUI configuration editor, allowing administrators to explicitly enable or disable file and directory delete buttons in the Bucket tab. This configuration option provides fine-grained control over deletion capabilities for different deployments.

## Infrastructure Improvements

### Elasticsearch 7.10 Upgrade

CloudFormation deployments now support **Elasticsearch 7.10**, providing improved performance and compatibility with modern search features.

**Upgrade Recommendation**: For CloudFormation users upgrading from 1.66, following the standard upgrade process is recommended to minimize search downtime.

### Cost-Optimized Instance Types

Quilt now supports newer AWS Graviton-based instance types for Elasticsearch, offering improved price-performance. Deployments can benefit from reduced infrastructure costs while maintaining or improving search performance.
