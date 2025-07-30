# How-To: Migrating from Network 1.0 to 2.0

## Tags

`aws`, `networking`, `vpc`, `migration`, `ecs`, `lambda`, `elasticsearch`

## Summary

Guidance on migrating from a legacy single-tier VPC setup (Network 1.0) to the more secure, three-tier architecture of Network 2.0. Covers architecture differences, necessary infrastructure changes, and considerations for coexisting subnet strategies.

---

## Background

### What Is Network 1.0?

Network 1.0 is a **legacy flat VPC design** used for earlier stacks. It lacks formal network segmentation, placing all resources—databases, load balancers, services—in the same subnet layers.

### What Is Network 2.0?

Network 2.0 introduces a **three-tier subnet architecture**:

1. **Intra Subnets** – private, internal-only (e.g., DBs, Elasticsearch)
2. **Private Subnets** – used by services not exposed to the internet
3. **Public Subnets** – for NAT gateways and internet-facing ELBs

It enforces secure-by-default infrastructure decisions, reducing misconfiguration risks.

---

## Motivation

- Features in newer versions of the Quilt stack require Network 2.0 architecture
- Legacy stacks can't adopt newer secure configurations (e.g. `lambdas_in_vpc=true`)
- IP address overlap or exhaustion when provisioning new subnets

### Recommendation: Use a New Stack

The simplest option is to directly upgrade to a brand-new stack to take advantage of network 2.0:

- Set `network_version=2.0`
- Accept secure defaults:  
  - `elb_scheme=internal`  
  - `lambdas_in_vpc=true`  
  - `api_gateway_in_vpc=true`  
  - `ecs_public_ip=false`  
  - `elastic_search_config.vpc=true`

This will preserve your existing S3 Buckets and stack configuration.
However, that would require:

- automatically reindexing all your S3 buckets (which can be slow and expensive)
- manually recreating user accounts and other database-backed configuration

While it is technically possible to backup and restore the database, there is no way to restore ElasticSearch.
In order to do that, you would need to follow the steps below.

---

## Migration Steps

We strongly encourage you to first test this process on a dev stack, to familiarize yourself with the process and identify any possible quirks in your local configuration.

### A. Request and Install a Network 1.5 Stack

- Submit a request to Quilt via [support@quilt.bio](mailto:support@quilt.bio) for a "Network 1.5" stack.
- This transitional stack includes:
  - A three-tier subnet structure (intra, private, public)
  - All secure 2.0 defaults:
    - `elb_scheme=internal`
    - `lambdas_in_vpc=true`
    - `api_gateway_in_vpc=true`
    - `ecs_public_ip=false`
    - `elastic_search_config.vpc=true`
- Critically, **existing Network 1.0 Elasticsearch and database resources are preserved** in place (not replaced or migrated).

> INTERNAL NOTE: For 1.0 customers using a Quilt-provided VPC (e.g., Inari), we need to create the 2.0 subnets in a different location (perhaps via `subnet_ip_base`), as otherwise we'd collide with the 1.0 subnets.

You should verify that you can still a) login, and b) view packages in the Packages tab before we start the reconfiguration process.

### B. Reconfigure services to use the new subnets

We recommend doing this via the AWS console, though you can perform some steps using the `aws` cli.

**Important**: Network 1.5 has already created the new Network 2.0 subnets. We're simply reconfiguring existing resources to use them.

#### RDS Database

**⚠️ Warning**: This process requires a maintenance window and will cause downtime.

1. **Identify the existing Network 2.0 DB Subnet Group**:
   - Navigate to **RDS** → **Subnet groups** in the AWS Console
   - Look for a subnet group that includes the new Network 2.0 intra subnets
   - This should have been created automatically by the Network 1.5 deployment

2. **Modify the RDS Instance to use Network 2.0 subnets**:
   - Navigate to **RDS** → **Databases**
   - Select your existing Quilt database instance  
   - Click **Modify**
   - Scroll to **Network & Security**
   - **DB subnet group**: Change to the Network 2.0 subnet group
   - **Apply immediately**: Check this box (or schedule for maintenance window)
   - Click **Continue** → **Modify DB instance**

3. **Monitor the modification**:
   - The instance will show "Modifying" status
   - This process typically takes 5-15 minutes
   - The database will be briefly unavailable during the subnet change

#### Elasticsearch

> INTERNAL NOTE: Can existing Elasticsearch domains be reconfigured to use different subnets within the same VPC?

**If subnet reconfiguration is possible**:

1. Navigate to **Amazon Elasticsearch Service** → **Domains**
2. Select your existing Quilt Elasticsearch domain
3. Look for options to modify VPC/subnet configuration
4. Update to use Network 2.0 intra subnets

**If subnet reconfiguration is NOT possible**:

- Elasticsearch domains may be locked to their original subnets
- This would require data migration to a new domain
- **Need to test/verify** which approach is required

#### Security Groups

Update security groups to allow communication from Network 2.0 subnets:

1. **Navigate to EC2** → **Security Groups**
2. **Find your RDS security group**:
   - Add inbound rules allowing access from Network 2.0 private/intra subnets
   - Port: 5432 (PostgreSQL) or 3306 (MySQL)
   - Source: Network 2.0 subnet CIDRs
3. **Find your Elasticsearch security group**:
   - Add inbound rules allowing access from Network 2.0 private/intra subnets
   - Port: 443 (HTTPS)
   - Source: Network 2.0 subnet CIDRs

**Note**: You may want to keep the old Network 1.0 security group rules temporarily until you verify everything works, then remove them.

### C. Test the stack to verify everything works

Once everything has been updated, verify that you can a) login (via the database), and b) view packages in the Packages tab (via ElasticSearch).

You may also want to run through a complete 'stack validation' to ensure there aren't any other difficulties.

### D. Upgrade to a standard 2.0 stack

For your next regular update, Quilt will provide you with a standard network 2.0 template. This is a lower risk update, but we still encourage you to a) first test on a dev stack, and b) carefully validate functionality after upgrading.

1. **Update application configuration**:

   - Update your Quilt stack configuration to point to the new Elasticsearch endpoint
   - This typically involves updating environment variables or configuration files
   - **Do not delete the old domain yet** - keep it as backup until migration is verified

2. **Verify the migration**:

   - Test search functionality in the Quilt web interface
   - Verify all indices are present and searchable
   - Check that document counts match between old and new domains

### E. Retest the stack to verify everything still works

Once everything has been updated, verify that you can a) login (via the database), and b) view packages in the Packages tab (via ElasticSearch).

You may also want to run through a complete 'stack validation' to ensure there aren't any other difficulties.
You may also want to run through a complete 'stack validation' to ensure there aren't any other difficulties.
