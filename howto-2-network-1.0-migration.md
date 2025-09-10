# How-To: Migrating from Network 1.0 to 2.0

## Tags

`aws`, `networking`, `vpc`, `migration`, `ecs`, `lambda`, `elasticsearch`

## Summary

Guidance on migrating from a legacy single-tier VPC setup (Network 1.0) to the more secure, three-tier architecture of Network 2.0. Covers architecture differences, necessary infrastructure changes, and considerations for coexisting subnet strategies.

---

## Why Use Network 2.0?

- Features in newer versions of the Quilt stack require Network 2.0 architecture
- Legacy stacks can't adopt newer secure configurations (e.g. `lambdas_in_vpc=true`)
- IP address overlap or exhaustion when provisioning new subnets

### What Is Network 1.0?

Network 1.0 is a **legacy flat VPC design** used for earlier stacks. It lacks formal network segmentation, placing all resources -- databases, load balancers, services -- in the same subnet and availability zone.

### What Is Network 2.0?

Network 2.0 introduces a **three-tier subnet architecture** to enforce secure-by-default infrastructure decisions, reducing misconfiguration risks:

1. **Intra Subnets** – private, internal-only (e.g., DBs, Elasticsearch)
2. **Private Subnets** – used by services not exposed to the internet
3. **Public Subnets** – for NAT gateways and internet-facing ELBs

Network 2.0 also requires specific values for variant options that are configurable in Network 1.0:

- `lambdas_in_vpc=true`
- `api_gateway_in_vpc=true` (required when `elb_scheme=internal`)
- `ecs_public_ip=false`
- `elastic_search_config.vpc=true`

To implement this architecture, it adds four new CloudFormation parameters:

- IntraSubnets
- UserSecurityGroup
- UserSubnets
- ApiGatewayVPCEndpoint

## Alternative Approaches

### Option A: New Stack

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

### Option B: Manual Migration

For cases where preserving existing database and Elasticsearch data is critical, manual migration is required. This approach is particularly relevant for configurations with `existing_vpc=true` like Tessera deployments. **Quilt will create the new Network 2.0 variant** - the following section covers the manual infrastructure preparation and migration steps required.

---

## Manual Migration Steps

We strongly encourage you to first test this process on a dev stack, to familiarize yourself with the process and identify any possible quirks in your local configuration.

### A. Pre-Migration Preparation

#### Step 1: Request a Network 2.0 Template

Fill out the Quilt Stack [Install Form](https://www.quilt.bio/install) so we can send you a modern template tailored for your environment.

#### Step 2: Create Backups

Create backups of critical data before beginning migration:

- [RDS database snapshot](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateSnapshot.html)
- [Elasticsearch indices backup](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html) (if possible)
- Screenshots of current VPC configuration
- Write down current subnets (these will be used for the new `UserSubnets` parameter)

#### Step 3: VPC Infrastructure Preparation

When `api_gateway_in_vpc=true` (which is required for `elb_scheme=internal` configurations), you will need to create and configure a new VPC endpoint. Otherwise, you can simply extend an existing VPC endpoint.

NOTE: This guide assumes you are only using IPv4 to access your Quilt stack. IPv6 access may require additional configuration.

1. **Assess Current VPC CIDR Allocation**
   - Review existing subnet allocations
   - If VPC CIDR is fully allocated, [add a secondary CIDR block](https://docs.aws.amazon.com/vpc/latest/userguide/configure-your-vpc.html#add-cidr-block-to-vpc) to accommodate new subnets

2. **Create Required Subnets**
   - [Create intra subnets](https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html) (2+ across different AZs) for databases and Elasticsearch
   - Create private subnets (2+ across different AZs) for application services
   - Create public subnets (2+ across different AZs) for NAT Gateways and internet-facing load balancers
   - [Deploy one NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html) in each AZ where you have private subnets to ensure high availability and minimize cross-AZ traffic charges
   - Ensure subnets align with the [enterprise architecture diagram](https://docs.quilt.bio/architecture#enterprise-architecture)

3. **Create Security Groups**
   - [Create `UserSecurityGroup`](https://docs.aws.amazon.com/vpc/latest/userguide/working-with-security-groups.html) for ELB
   - Configure security group rules to allow communication between subnet tiers

4. **Create API Gateway VPC Endpoint** (required when `elb_scheme=internal`)
   - [Create a VPC endpoint for API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-private-apis.html)
   - This endpoint will be passed to the `ApiGatewayVPCEndpoint` parameter

### B. Database Migration

**⚠️ Warning**: This process requires downtime and should be performed during a maintenance window.

#### Manual Database Subnet Migration Process

Since it's impossible to directly change DBSubnetGroup subnets when in use, use this workaround:

**Technical Constraints:**

- DBSubnetGroup subnets cannot be changed when in use
- CloudFormation can only change DBSubnetGroup by replacing the DB instance
- A new DBSubnetGroup cannot be in the same VPC as an existing one
- Moving to a new DBSubnetGroup requires Multi-AZ to be turned off temporarily

⚠️ **Important**: A new DBSubnetGroup cannot be created in the same VPC as an existing one. This is why a temporary VPC is required during migration.

**Migration Steps:**

1. **Create Temporary VPC Infrastructure**
   - Create temporary VPC with 2 subnets in different AZs
   - Include restrictive security group and [new DBSubnetGroup](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html#USER_VPC.Subnets)
   - Consider using CloudFormation template for consistency

2. **Modify Database Configuration**
   - [Turn off Multi-AZ](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html) on the RDS instance
   - [Modify DB instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.DBInstance.Modifying.html) to use the new DBSubnetGroup in temporary VPC
   - Update the original DBSubnetGroup to include new IntraSubnets
   - Modify DB instance back to the original DBSubnetGroup (now with new subnets)
   - Re-enable Multi-AZ on the RDS instance

3. **Clean Up**
   - Delete temporary VPC and DBSubnetGroup resources

### C. Elasticsearch Migration

Migrate Elasticsearch to new intra subnets:

1. **Check Domain Configuration**
   - Verify if existing domain can be reconfigured for new subnets
   - If not possible, plan for data migration to new domain

2. **Update Security Groups**
   - Add inbound rules allowing HTTPS (port 443) from Network 2.0 subnets
   - Source: Network 2.0 subnet CIDRs

### D. Apply Network 2.0 Configuration

Once the infrastructure is prepared, upgrade your stack using the Quilt-provided variant template:

1. **Install the Template as an Update**
   - Apply the Network 2.0 variant template to your existing stack

2. **Set New Stack Parameters**
   - `IntraSubnets`: New intra subnet IDs
   - `UserSubnets`: Current subnets become user subnets  
   - `UserSecurityGroup`: New security group for ELB
   - `ApiGatewayVPCEndpoint`: VPC endpoint created in Step 3 (if applicable)

3. **Monitor deployment for any issues**
   - Watch CloudFormation stack update progress
   - Verify all resources are created successfully

### E. Post-Migration Validation

1. **Connectivity Tests**
   - Verify login functionality (database connectivity)
   - Test package browsing (Elasticsearch connectivity)
   - Run the [smoke test](https://kb.quilt.bio/how-to-validate-my-quilt-stack-is-correctly-configured)

2. **Security Validation**
   - Confirm services are properly segmented in appropriate subnets
   - Verify security group rules are correctly applied
   - Test that API Gateway VPC endpoint is functioning (if applicable)

3. **Performance Monitoring**
   - Monitor application performance post-migration
   - Check for any network latency issues
   - Validate backup and monitoring systems

### F. Rollback Considerations

- Keep original subnet configurations documented
- Maintain database/ES snapshots from before migration
