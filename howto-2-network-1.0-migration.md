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

#### RDS Database

TBD

#### Elastic Search

TBD

### C. Test the stack to verify everything works

Once everything has been updated, verify that you can a) login (via the database), and b) view packages in the Packages tab (via ElasticSearch).

You may also want to run through a complete 'stack validation' to ensure there aren't any other difficulties.

### D. Upgrade to a standard 2.0 stack

For your next regular update, Quilt will provide you with a standard network 2.0 template.  This is a lower risk update,
but we still encourage you to a) first test on a dev stack, and b) carefully validate functionality after upgrading.
