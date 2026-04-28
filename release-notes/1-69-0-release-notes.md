# Platform Update 1.69

This release introduces **Union Role Mapping** for SSO, scopes bucket listings to a user's actual access (including admins), and improves the Benchling integration with auto-refreshing canvases and review-record export. Several stack-admin and variant changes round out the release.

## New Quilt Platform Features

### Union Role Mapping for SSO

SSO configurations can now opt into a `union_roles: true` flag that assigns users the **union of all matching mapping roles** at login, instead of stopping at the first match. Users switch between assigned roles via the existing role switcher, and roles that are no longer matched on a subsequent login are automatically revoked.

Key behavior under `union_roles: true`:

- **Union assignment**: Every mapping rule whose match condition fires contributes its role to the user
- **Auto-revocation**: Roles no longer in the matched set are removed on next login
- **Tri-state admin**: The `admin` field becomes three-valued — omitted (no vote), `true` (grant), `false` (veto). An explicit `admin: false` blocks admin even if another matching mapping grants it
- **Backward compatible**: Default remains first-match-wins. Existing SSO configs see no behavior change

This is opt-in; existing customers do not need to take action.

### Role-Scoped Bucket Listings (including Admins)

User-facing bucket listings — the catalog navbar, the landing-page grid, the bucket-search filter, and the MCP `bucket_list` tool — now respect a user's role scope. Previously, admins always saw the full bucket inventory regardless of role; admins now see the same scoped list as other users with the same roles.

Administrators who need access to additional buckets can still manage them through the Admin → Buckets interface.

### Benchling Integration Improvements

The Benchling integration adds two notable behaviors in this release:

- **Auto-refreshing canvas**: After a Quilt package revision is exported, the Benchling canvas refreshes automatically — the "pending → complete" transition is now seamless, and the canvas remains reachable for browsing while a re-export is in flight
- **Review-record export trigger**: `reviewRecord` entry events from Benchling now trigger the standard package export workflow, so reviewed entries flow through the same path as primary entries

## Other Improvements

- The Admin Buckets editor no longer surfaces the **Overview URL** and **Structured data (JSON-LD)** fields. Both supported features that were specific to the obsolete OPEN stack
- Fixed an "Error resolving revision" flash that briefly appeared when navigating to a just-created package
- `ConnectAllowedHosts` now supports leading-dot domain suffixes (e.g. `.benchling.com`) to allow any subdomain over HTTPS, simplifying configuration for SaaS integrations with sub-domain rotation
- Deny manual bucket management via bucket policies — all bucket configuration changes must now go through CloudFormation, eliminating drift between deployed and declared state
- Fixed Okta `ClientId` and `BaseUrl` resolution in Terraform configurations
- The `s3-proxy` container image is rebased on an updated Amazon Linux 2023 base for routine security maintenance

## Variants

- **open-quilt-bio**: Replaced specific Benchling hostnames with domain-suffix wildcards (`.benchling.com`, `.bnchdev.org`, `.bnch.us`); added HubSpot marketing analytics tracking
- **nightly**: Adopted the same Benchling suffix wildcards; dropped Google and OneLogin SSO providers (Okta, Microsoft/Entra, and password remain)
