# Quilt Platform Release 1.66.0

This release introduces the **Benchling Webhook Integration Service**, enabling seamless data synchronization between Benchling and Quilt. Additionally, this release includes important infrastructure upgrades and UI improvements for better security and user experience.

## New Quilt Platform Features

### Benchling Webhook Integration Service

Quilt now offers a **production-ready webhook integration service** for [Benchling](https://www.benchling.com/), the leading cloud platform for life sciences R&D. This integration automatically synchronizes research data from Benchling to your Quilt-managed S3 buckets in real-time.

#### Key Capabilities

- **Real-time Data Sync**: Automatically capture and store Benchling entries as they're created or updated
- **One-Command Deployment**: Deploy the entire AWS infrastructure with a single NPX command
- **Multi-Environment Support**: Easily manage dev, prod, and custom deployment profiles
- **Comprehensive Logging**: Built-in CloudWatch integration for monitoring and debugging
- **Secure by Default**: IAM-based authentication with configurable webhook security

#### Quick Start

Deploy the Benchling webhook service to your AWS account:

```bash
npx @quiltdata/benchling-webhook --yes
```

The service automatically provisions:
- API Gateway endpoint for receiving webhooks
- ECS Fargate container for processing events
- CloudWatch logs for monitoring
- All necessary IAM roles and permissions

For detailed configuration and usage, see the [Benchling Webhook Integration documentation](https://github.com/quiltdata/benchling-webhook).

## UI Improvements

### Enhanced Object Management Security

File and directory delete buttons in the Bucket tab are now **hidden by default** to prevent accidental deletions. Administrators can enable these actions using the `ui.actions.deleteObject` configuration parameter when needed for specific workflows.

This change provides an extra layer of protection for critical data while maintaining flexibility for teams that require direct object management capabilities.

## Bug Fixes

### Package Revision Search Fixed for 2026+

Resolved an issue where search and events for package revisions created in 2026 and later were not functioning correctly. The platform now properly indexes and retrieves packages regardless of creation date.

## Infrastructure Upgrades

### Elasticsearch 7.10 for CloudFormation Deployments

CloudFormation-based deployments now use **Elasticsearch 7.10**, providing improved performance, security patches, and better compatibility with modern AWS infrastructure.

### Extended SQS Retention for Indexer Queues

The retention period for indexer queues has been increased to **14 days** (the maximum allowed by AWS SQS). This enhancement provides better resilience against temporary processing delays and makes it easier to recover from extended service interruptions without data loss.

---

## Getting Started

To upgrade to Quilt Platform 1.66.0, follow the standard [upgrade procedures](https://docs.quilt.bio/quilt-platform-administrator/upgrade) in the documentation.

For questions or support, please contact the Quilt team or visit our [community forum](https://github.com/quiltdata/quilt/discussions).
