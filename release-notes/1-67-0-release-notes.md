# Platform Update 1.67

This release introduces API Keys for programmatic authentication, Elasticsearch 7 for cost savings, and a GUI enabling object deletion. We are also releasing QuiltSync v0.12 with auto-updating and improved Windows support.

## New Quilt Platform Features

### API Keys for Programmatic Authentication

Quilt now supports API Keys for headless and programmatic authentication, enabling secure automation workflows without interactive logins. Users can create and manage their own API keys through the Python API, eliminating the need to store SSO credentials or use interactive sessions for automation.

API keys inherit the full permissions of the user who creates them and can be managed entirely through the quilt3 Python API (requires v7.2.0).

Key capabilities:

- **Self-Service Management**: Create, list, and revoke your own API keys using `quilt3.api_keys.create()`, `list()`, and `revoke()`
- **Simple Authentication**: Use `quilt3.login_with_api_key(key)` to authenticate headless clients—no disk state or renewal required
- **Flexible Expiration**: Set key lifetimes from 1 day to 1 year based on your security requirements
- **Immediate Revocation**: Revoked keys fail instantly, enabling quick response to security incidents
- **Admin Oversight**: Monitor and manage user keys via `quilt3.admin.api_keys.list()`, `get()`, and `revoke()` to ensure compliance

For detailed usage instructions, see the expanded Authentication documentation.

### GUI Delete Object Configuration

The `deleteObject` property is now available in the GUI configuration editor, allowing administrators to explicitly enable or disable file and directory delete buttons in the Bucket tab. This configuration option provides fine-grained control over deletion capabilities for different deployments.

### Elasticsearch 7.10

Release 1.67 completes the Elasticsearch 7 cluster migration begun last release, providing improved performance and compatibility with modern search features.

#### Install 1.66 First

We strongly recommend first installing 1.66 -- which updated the registry -- as otherwise search and package listings will be unavailable until the migration completes (which may take several days).

#### Graviton Cost Savings

Elasticsearch 7 also supports using more cost-effective Graviton (ARM) clusters. Terraform customers can migrate to such clusters themselves. In a future release we expect to automatically migrate CloudFormation customers.

WARNING: If you have purchased a Reserved Instance, you would continue paying for that even after the switch to Graviton. Please contact us to ensure an appropriate transition.

## QuiltSync v0.12

### Improved Deployability

- **Automated Updates**: QuiltSync will automatically detect and install newer versions on launch.
- **Improved Windows Support**: Fixed Windows deep link navigation issue when app is launched via deep link.
- **CRC64 Checksums**: Improves support for Quilt Platforms that have enabled the new checksums.
