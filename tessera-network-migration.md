# Tessera Network 2.0 Migration Notes

> This is draft notes for migrating a Tessera network. To be made more general and merged into [howto-2-network-1.0-migration.md](howto-2-network-1.0-migration.md).

## Overview of Changes from Network 1.0 to 2.0

- Network 2.0 uses 3 pairs of subnets instead of 1 pair in Network 1.0.
- Network 2.0 requires specific values for variant options that are configurable in Network 1.0:
  - `lambdas_in_vpc=true`
  - `api_gateway_in_vpc=true` if `elb_scheme=internal`
  - `ecs_public_ip=false`
  - `elastic_search_config.vpc=true`

## Tessera-Specific Considerations

- Their variant has `existing_vpc=true`
- Their variant has all required variant options values for Network 2.0 except `api_gateway_in_vpc=true` which is required since they use `elb_scheme=internal`
- Migration adds these CloudFormation parameters:
  - IntraSubnets
  - UserSecurityGroup
  - UserSubnets
  - ApiGatewayVPCEndpoint

## Migration Steps

### Step 0: make backups of DB and ES?

### Step 1: make a new variant option for api_gateway_in_vpc=True?

They'll need to create a VPC endpoint for API Gateway and pass it to `ApiGatewayVPCEndpoint` parameter

### Step 2: prepare resources in VPC

- create SG for ELB (UserSecurityGroup)
- current Subnets parameter becomes UserSubnets?
- create subnets for new Subnets and IntraSubnets
- their setup should be aligned with [diagram](https://docs.quilt.bio/architecture#enterprise-architecture)
- if VPC CIDR is fully allocated to subnets, they may need to add secondary CIDR to VPC to create new subnets

### Step 3: move DB to new subnets

#### Notes

- it's impossible to change subnets of DBSubnetGroup if they are in use
- CloudFormation only can change DBSubnetGroup by replacing the DB instance, but it can be done manually
- a new DBSubnetGroup can't be in the same VPC
- moving to new DBSubnetGroup requires multi-AZ to be turned off temporarily

#### Steps (TODO: provide script?)

1. create temporary VPC with 2 subnets in different AZs, restrictive security group and new DBSubnetGroup (TODO: provide CloudFormation template?)
2. turn off multi-AZ on DB instance
3. modify DB instance to use new DBSubnetGroup in temporary VPC
4. set IntraSubnets on old DBSubnetGroup
5. modify DB instance to use old DBSubnetGroup
6. turn on multi-AZ on DB instance
7. delete temporary VPC and DBSubnetGroup

### Step 4: apply Network 2.0 variant with new parameters
