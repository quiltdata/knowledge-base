# How-To: Deploy Quilt with Transit Gateway Routing

## Tags

`aws`, `networking`, `transit-gateway`, `vpc-endpoints`, `enterprise`

## Summary

> Deploy Quilt using your existing Transit Gateway instead of NAT Gateway by providing TGW-configured subnets as parameters.
> Optionally use private VPCs to save costs for high-volume deployments.

---

## Overview

Deploy Quilt using Transit Gateway for outbound routing instead of NAT Gateway—common in enterprise environments with centralized network routing and security policies.

### When to Use This Guide

Use Transit Gateway routing when:

- ✅ You have existing Transit Gateway infrastructure
- ✅ Corporate policy requires traffic through TGW
- ✅ You want centralized routing and firewall policies

### How It Works

Provide subnet IDs with `0.0.0.0/0 → tgw-xxxxx` routes to your Quilt deployment (`network.vpn: true`)—Quilt uses your existing VPC and route tables, no NAT Gateway created.

---

## VPC Endpoints: Optional but Recommended

VPC endpoints save 90%+ of TGW data charges (~$35/month cost for significant organizational savings) and improve performance by routing AWS traffic through AWS's private network.

---

## What You Need

### Prerequisites

1. **VPC with Transit Gateway attachment** (TGW must route to internet for ECR/AWS service access)
2. **Quilt deployment with `network.vpn: true`** (set by Quilt - uses your existing VPC, skips NAT Gateway)
3. **AWS networking knowledge** (VPC, subnets, route tables, security groups, Transit Gateway)

### Three Types of Subnets

**Private Subnets** (2, different AZs):
- For ECS containers and Lambda functions
- Route table: `0.0.0.0/0 → tgw-xxxxx`

**Intra Subnets** (2, different AZs):
- For RDS and ElasticSearch
- Route table: Local VPC only (NO internet route)

**User Subnets** (for load balancer):

- Internal access: Use private subnets
- Public access: Use public subnets with IGW

---

## Step 1: Deploy VPC Endpoints (Recommended)

VPC endpoints eliminate 90%+ of internet traffic—less data through your TGW, better performance.

**Essential endpoints** (~$35/month):

```bash
VPC_ID="vpc-xxxxx"
REGION=$(aws configure get region)
PRIVATE_SUBNET_1="subnet-xxxxx"
PRIVATE_SUBNET_2="subnet-yyyyy"

# Create security group for endpoints
VPCE_SG=$(aws ec2 create-security-group \
  --group-name quilt-vpc-endpoints \
  --description "VPC endpoints for Quilt" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# Allow HTTPS from private subnets
aws ec2 authorize-security-group-ingress \
  --group-id $VPCE_SG \
  --protocol tcp --port 443 --cidr 10.0.0.0/16  # Adjust CIDR

# S3 Gateway (FREE)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.s3 \
  --route-table-ids rtb-private1 rtb-private2 \
  --vpc-endpoint-type Gateway

# CloudWatch Logs
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.logs \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled

# ECR (for Docker images)
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.ecr.api \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled

aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.ecr.dkr \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled

# SQS
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.sqs \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled

# SNS
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.sns \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled
```

---

## Step 2: Prepare Deployment Parameters

Collect your subnet IDs:

```yaml
# CloudFormation/Terraform Parameters
VPC: vpc-xxxxx
Subnets: subnet-private1,subnet-private2      # With TGW routing
IntraSubnets: subnet-intra1,subnet-intra2     # No internet
UserSubnets: subnet-private1,subnet-private2  # Same as Subnets for VPN
UserSecurityGroup: sg-xxxxx                   # Create for load balancer access

# Standard parameters
DBUser: quilt_admin
DBPassword: <password>
CertificateArnELB: arn:aws:acm:...
AdminEmail: admin@company.com
QuiltWebHost: quilt.company.com
```

---

## Step 3: Deploy

Deploy Quilt with your TGW-configured subnet parameters.

**CloudFormation:**
```bash
aws cloudformation create-stack \
  --stack-name quilt-tgw \
  --template-body file://cloudformation.json \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_IAM
```

**Terraform:**
```bash
cd deployment/t4
make variant=your-variant
cd ../tf
terraform apply
```

---

## Step 4: Validate

### Quick Health Check

```bash
STACK_NAME="your-stack"

# Get registry URL
REGISTRY=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`RegistryHost`].OutputValue' --output text)

# Test access
curl -s -o /dev/null -w "%{http_code}" https://$REGISTRY/
# Expected: 200 or 302
```

### Verify VPC Endpoints Are Working

From a private subnet (bastion or Session Manager), verify DNS resolves to private IPs (10.x.x.x):

```bash
nslookup s3.$REGION.amazonaws.com
nslookup logs.$REGION.amazonaws.com
```

### Check TGW Traffic

Verify minimal TGW traffic (indicates VPC endpoints working):

```bash
TGW_ID=$(aws ec2 describe-transit-gateway-attachments \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'TransitGatewayAttachments[0].TransitGatewayId' --output text)

aws cloudwatch get-metric-statistics \
  --namespace AWS/TransitGateway \
  --metric-name BytesOut \
  --dimensions Name=TransitGateway,Value=$TGW_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 --statistics Sum
```

---

## What Goes Through TGW?

**With VPC endpoints:** Only telemetry and SSO providers (if enabled)
**Without VPC endpoints:** All AWS API traffic

---

## Troubleshooting

### ECS Tasks Won't Start

**Error:** "CannotPullContainerError"

**Fix:**

- Deploy ECR VPC endpoints (see Step 1)
- Or verify TGW routes to `*.ecr.amazonaws.com`

### Lambda Functions Timeout

**Fix:**

- Deploy VPC endpoints for services Lambda calls
- Verify security groups allow HTTPS (443) outbound

### High TGW Costs

**Fix:**

- Deploy missing VPC endpoints (check which AWS services are accessed)
- Disable telemetry: `DISABLE_QUILT_TELEMETRY=true`

---

## Firewall Rules (If TGW Routes Through Firewall)

**Allow HTTPS (443) to:**

- `telemetry.quiltdata.cloud` (if telemetry enabled)
- `accounts.google.com` (if Google SSO enabled)
- `login.microsoftonline.com` (if Azure SSO enabled)
- `*.amazonaws.com` (if not using VPC endpoints)

---

## Summary Checklist

- [ ] VPC has Transit Gateway attachment
- [ ] Private subnets route `0.0.0.0/0` to TGW
- [ ] Intra subnets have NO internet route
- [ ] VPC endpoints deployed (at least S3, CloudWatch, ECR)
- [ ] Security group allows 443 to VPC endpoints
- [ ] Deploy Quilt with TGW-configured subnet IDs
- [ ] Verify DNS resolves to private IPs
- [ ] Test application works

---

## Need Help?

- **Support:** <support@quiltdata.com>
- **Related Guide:** [Network 1.0 to 2.0 Migration](howto-2-network-1.0-migration.md)
- **AWS Docs:** [Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/), [VPC Endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)
