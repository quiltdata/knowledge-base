# How to Deploy Quilt with Transit Gateway Routing

**Audience:** Enterprise customers with existing Transit Gateway infrastructure
**Goal:** Deploy Quilt using Transit Gateway instead of NAT Gateway for outbound routing
**Difficulty:** Intermediate (requires AWS networking knowledge)

---

## Overview

This guide explains how to deploy Quilt in an existing VPC using AWS Transit Gateway for outbound connectivity instead of the default NAT Gateway configuration. This is common in enterprise environments where centralized routing and network security policies are managed through Transit Gateway.

### When to Use This Guide

Use Transit Gateway routing when:
- ✅ You have an existing Transit Gateway hub-and-spoke architecture
- ✅ Your corporate policy requires all outbound traffic to route through TGW
- ✅ You want to centralize network routing and firewall policies
- ✅ You're deploying into an existing VPC with pre-configured routing

### Prerequisites

- Existing VPC with Transit Gateway attachment
- Understanding of AWS networking (VPC, subnets, route tables, security groups)
- Familiarity with Transit Gateway routing
- Access to deploy VPC endpoints
- Quilt deployment using `existing_vpc: true` configuration

---

## Architecture Patterns

### Pattern 1: Default Quilt Architecture (NAT Gateway)

```
┌─────────────────────────────────────────────────┐
│ VPC (Created by Quilt)                          │
│                                                  │
│  ┌──────────────┐      ┌─────────────┐         │
│  │ ECS/Lambda   │──────│ NAT Gateway │─────────┼──> Internet
│  │ (Private     │      │             │         │    (AWS APIs,
│  │  Subnet)     │      │             │         │     ECR, etc.)
│  └──────────────┘      └─────────────┘         │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Characteristics:**
- Quilt creates VPC, subnets, and NAT Gateway
- Each AZ has its own NAT Gateway for high availability
- Cost: ~$32/month per NAT Gateway + $0.045/GB data transfer

### Pattern 2: Transit Gateway Routing

```
┌─────────────────────────────────────────────────┐
│ Customer VPC                                     │
│                                                  │
│  ┌──────────────┐      ┌─────────────┐         │
│  │ ECS/Lambda   │──────│   TGW       │─────────┼──> Corporate Network
│  │ (Private     │      │ Attachment  │         │    └─> Firewall
│  │  Subnet)     │      │             │         │         └─> Internet
│  └──────────────┘      └─────────────┘         │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Characteristics:**
- Customer manages VPC, subnets, and routing
- All outbound traffic goes through TGW to corporate network
- TGW cost is shared across all VPCs
- Centralized security and routing policies

### Pattern 3: Hybrid with VPC Endpoints (Recommended)

```
┌─────────────────────────────────────────────────┐
│ Customer VPC                                     │
│                                                  │
│  ┌──────────────┐                               │
│  │ ECS/Lambda   │──────┐                        │
│  │ (Private     │      │                        │
│  │  Subnet)     │      │                        │
│  └──────────────┘      │                        │
│                        │                        │
│                   ┌────┴────┐                   │
│                   │  Route  │                   │
│                   │ Decision│                   │
│                   └────┬────┘                   │
│                        │                        │
│        ┌───────────────┼───────────────┐        │
│        │               │               │        │
│        ▼               ▼               ▼        │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │   VPC    │   │   VPC    │   │   TGW    │───┼──> Internet
│  │ Endpoint │   │ Endpoint │   │          │   │    (minimal)
│  │  (S3)    │   │  (ECR)   │   │          │   │
│  └──────────┘   └──────────┘   └──────────┘   │
│                                                  │
│  Most AWS API traffic        External traffic   │
│  stays in AWS network         via TGW           │
└─────────────────────────────────────────────────┘
```

**Characteristics:**
- Best of both worlds: private AWS service access + TGW for internet
- 90%+ of traffic uses VPC endpoints (no TGW data charges)
- Only external services (ECR, telemetry, SSO) use TGW
- Optimal performance and security

---

## Step-by-Step Implementation

### Phase 1: Network Preparation

#### 1.1 Create or Identify Subnets

You need three types of subnets:

**Private Subnets** (for ECS tasks and Lambda functions)
- Purpose: Run Quilt service containers and Lambda functions
- Routing: 0.0.0.0/0 → Transit Gateway
- Quantity: 2 subnets in different Availability Zones
- Example CIDRs: 10.0.1.0/24, 10.0.2.0/24

**Intra Subnets** (for RDS and ElasticSearch)
- Purpose: Database and search cluster (no internet access needed)
- Routing: No default route (local VPC only)
- Quantity: 2 subnets in different Availability Zones
- Example CIDRs: 10.0.3.0/24, 10.0.4.0/24

**User/Load Balancer Subnets**
- For VPN/internal access: Use private subnets (same as above)
- For public access: Public subnets with 0.0.0.0/0 → Internet Gateway
- Quantity: 2 subnets in different Availability Zones

#### 1.2 Configure Route Tables

**Route Table for Private Subnets:**
```
Destination         Target              Notes
-----------------------------------------------------------
10.0.0.0/16        local               Intra-VPC communication
0.0.0.0/0          tgw-xxxxx           All internet via TGW
```

**Route Table for Intra Subnets:**
```
Destination         Target              Notes
-----------------------------------------------------------
10.0.0.0/16        local               Intra-VPC only (no internet)
```

**Route Table for Public Subnets** (if using public load balancer):
```
Destination         Target              Notes
-----------------------------------------------------------
10.0.0.0/16        local               Intra-VPC communication
0.0.0.0/0          igw-xxxxx           Internet via Internet Gateway
```

#### 1.3 Verify Transit Gateway Configuration

Ensure your Transit Gateway is configured to route traffic:

```bash
# Check TGW attachment
aws ec2 describe-transit-gateway-attachments \
  --filters "Name=vpc-id,Values=vpc-xxxxx"

# Check TGW route table
aws ec2 describe-transit-gateway-route-tables \
  --filters "Name=transit-gateway-id,Values=tgw-xxxxx"
```

Verify TGW routes traffic to:
- Your corporate network/firewall
- Internet (directly or via firewall)
- DNS resolvers

### Phase 2: Deploy VPC Endpoints (Strongly Recommended)

Deploy VPC Interface Endpoints to minimize TGW internet traffic and improve performance.

#### 2.1 Essential VPC Endpoints (Tier 1)

These endpoints handle 90%+ of Quilt's AWS API traffic:

**Deploy via Console:**
1. Go to VPC → Endpoints → Create Endpoint
2. Select service name
3. Choose your VPC
4. Select private subnets
5. Enable "Private DNS name"
6. Create security group allowing HTTPS (443) from private subnets

**Deploy via CLI:**

```bash
# S3 Gateway Endpoint (FREE!)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-xxxxx rtb-yyyyy

# CloudWatch Logs
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.logs \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled

# ECR API
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.ecr.api \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled

# ECR Docker (for image layers)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.ecr.dkr \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled

# SQS
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.sqs \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled

# SNS
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.sns \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled
```

**Security Group for VPC Endpoints:**
```
Ingress:
  - Port 443, Source: Private subnet CIDRs (10.0.1.0/24, 10.0.2.0/24)
Egress:
  - None required (endpoints are destination, not source)
```

**Estimated Cost:** ~$35/month + $0.01/GB (much cheaper than NAT Gateway's $0.045/GB)

#### 2.2 Additional VPC Endpoints (Tier 2 - Optional but Recommended)

```bash
# EventBridge (Events)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.events \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled

# KMS (encryption operations)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.kms \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled

# SSM Parameter Store
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.ssm \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled
```

**Estimated Cost:** Additional ~$35/month + $0.01/GB

#### 2.3 Analytics VPC Endpoints (Tier 3 - Optional)

If using Quilt's analytics features:

```bash
# Athena
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.athena \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled

# Glue (Data Catalog)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.glue \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled

# Kinesis Firehose
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxxxx \
  --service-name com.amazonaws.us-east-1.kinesis-firehose \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-xxxxx subnet-yyyyy \
  --security-group-ids sg-xxxxx \
  --private-dns-enabled
```

### Phase 3: Configure Quilt Deployment

#### 3.1 Update Variant Configuration

In your environment variant YAML file:

```yaml
factory:
  network:
    vpn: true          # Sets existing_vpc: true
    vpc: theirs        # Use customer-provided VPC (not applicable with vpn:true)
  deployment: tf       # or 'cf' for CloudFormation

options:
  existing_vpc: true   # Implicit when network.vpn: true
  network_version: "2.0"
  lambdas_in_vpc: true
  api_gateway_in_vpc: true  # Requires VPC endpoint for API Gateway
  elb_scheme: internal      # For VPN access
  # elb_scheme: internet-facing  # For public access
```

#### 3.2 Prepare Deployment Parameters

Create a parameters file or prepare CLI arguments:

```yaml
# parameters.yaml
Parameters:
  # Network Configuration
  VPC: vpc-xxxxx
  Subnets:
    - subnet-private1-id
    - subnet-private2-id
  IntraSubnets:
    - subnet-intra1-id
    - subnet-intra2-id
  UserSubnets:
    - subnet-private1-id  # Same as Subnets for VPN
    - subnet-private2-id
  # Or for public access:
  # PublicSubnets:
  #   - subnet-public1-id
  #   - subnet-public2-id

  UserSecurityGroup: sg-xxxxx  # Allow 443/80 from your users

  # VPC Endpoint for API Gateway (if api_gateway_in_vpc: true)
  ApiGatewayVPCEndpoint: vpce-xxxxx

  # Database Configuration
  DBUser: quilt_admin
  DBPassword: <secure-password>

  # Certificates
  CertificateArnELB: arn:aws:acm:us-east-1:xxxxx:certificate/xxxxx

  # Admin Configuration
  AdminEmail: admin@yourcompany.com
  QuiltWebHost: quilt.yourcompany.com
```

#### 3.3 Optional: Minimize External Dependencies

To reduce TGW internet traffic, disable optional external services:

**Disable Telemetry:**
Add to your environment configuration:
```yaml
# In deployment environment or container environment variables
DISABLE_QUILT_TELEMETRY: "true"
```

**Skip External SSO:**
Don't configure Google/Azure/Okta/OneLogin credentials. Use IAM-based authentication instead.

**Use Local ECR:**
Set `local_ecr: true` in options to use your account's ECR instead of Quilt's central registry.

```yaml
options:
  local_ecr: true
```

### Phase 4: Deploy and Validate

#### 4.1 Deploy Quilt Stack

**Using Terraform:**
```bash
cd deployment/t4
make variant=your-variant-name
cd ../tf
terraform init
terraform plan
terraform apply
```

**Using CloudFormation:**
```bash
cd deployment/t4
make variant=your-variant-name
aws cloudformation create-stack \
  --stack-name quilt-production \
  --template-body file://cloudformation.json \
  --parameters file://parameters.yaml \
  --capabilities CAPABILITY_IAM
```

#### 4.2 Monitor Deployment

Watch for common issues:

```bash
# Check CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name quilt-production \
  --max-items 20

# Or Terraform output
terraform apply -no-color 2>&1 | tee deploy.log

# Monitor ECS task launches
aws ecs list-tasks --cluster <cluster-name>
aws ecs describe-tasks --cluster <cluster-name> --tasks <task-arn>

# Check CloudWatch Logs
aws logs tail /aws/ecs/<service-name> --follow
```

#### 4.3 Validate Network Connectivity

**Test VPC Endpoints:**
```bash
# From a bastion or test instance in private subnet
nslookup logs.us-east-1.amazonaws.com
# Should resolve to private IP (10.x.x.x)

nslookup ecr.us-east-1.amazonaws.com
# Should resolve to private IP (10.x.x.x)
```

**Test TGW Routing:**
```bash
# Check route table
aws ec2 describe-route-tables --route-table-ids rtb-xxxxx

# Verify TGW attachment
aws ec2 describe-transit-gateway-vpc-attachments \
  --filters "Name=vpc-id,Values=vpc-xxxxx"
```

**Test Application Functionality:**
1. Access catalog via VPN: https://quilt.yourcompany.com
2. Upload a test package
3. Search for objects
4. Download a file
5. Check that all features work as expected

#### 4.4 Performance Validation

Monitor key metrics in CloudWatch:

- ECS task startup time (should be similar to baseline)
- S3 operation latency (should be better with S3 Gateway Endpoint)
- Search indexing performance
- API response times
- Lambda execution duration

**Expected Performance:**
- With VPC Endpoints: Similar or better than NAT Gateway
- Without VPC Endpoints: Slightly higher latency due to TGW hop

---

## Traffic Flow Analysis

### With VPC Endpoints (Recommended)

| Service | Traffic Path | Internet Required? |
|---------|--------------|-------------------|
| S3 API calls | Private subnet → S3 Gateway Endpoint | ❌ No |
| CloudWatch Logs | Private subnet → Logs VPC Endpoint | ❌ No |
| SQS messages | Private subnet → SQS VPC Endpoint | ❌ No |
| ECR image pulls | Private subnet → ECR VPC Endpoints | ❌ No |
| RDS queries | Private subnet → Intra subnet (local) | ❌ No |
| ElasticSearch | Private subnet → Intra subnet (local) | ❌ No |
| Telemetry (optional) | Private subnet → TGW → Internet | ✅ Yes |
| SSO (optional) | Private subnet → TGW → Internet | ✅ Yes |

**Result:** 95%+ of traffic stays within AWS network, minimal TGW internet routing.

### Without VPC Endpoints (Not Recommended)

| Service | Traffic Path | Internet Required? |
|---------|--------------|-------------------|
| S3 API calls | Private subnet → TGW → Internet → S3 | ✅ Yes |
| CloudWatch Logs | Private subnet → TGW → Internet → CloudWatch | ✅ Yes |
| All AWS APIs | Private subnet → TGW → Internet → AWS | ✅ Yes |

**Result:** High TGW data transfer costs, higher latency, more complex firewall rules.

---

## Firewall Configuration

If your TGW routes through a corporate firewall, you'll need to allow:

### With VPC Endpoints (Minimal Rules)

**HTTPS (443) Outbound:**
- `*.ecr.us-east-1.amazonaws.com` (if not using ECR VPC endpoints)
- `telemetry.quiltdata.cloud` (if telemetry enabled)
- `accounts.google.com` (if Google SSO enabled)
- `login.microsoftonline.com` (if Azure SSO enabled)
- `*.okta.com` (if Okta SSO enabled)

**DNS (53) Outbound:**
- Your DNS resolvers

### Without VPC Endpoints (Extensive Rules)

**HTTPS (443) Outbound:**
- `*.amazonaws.com` (all AWS services)
- `*.cloudfront.net` (CloudFront)
- Plus all external services listed above

---

## Troubleshooting

### Issue: ECS Tasks Fail to Start

**Symptoms:**
- Tasks transition from PENDING to STOPPED
- Error: "CannotPullContainerError"

**Diagnosis:**
```bash
# Check task stopped reason
aws ecs describe-tasks --cluster <cluster> --tasks <task-id>

# Check CloudWatch Logs
aws logs tail /aws/ecs/<service-name> --since 30m
```

**Solutions:**
1. Deploy ECR VPC endpoints (`ecr.api` and `ecr.dkr`)
2. Verify TGW routes to `*.ecr.amazonaws.com`
3. Check security groups allow HTTPS (443) outbound
4. Verify DNS resolution works from private subnets

### Issue: Lambda Functions Timeout

**Symptoms:**
- Lambda functions timeout at 30s or configured limit
- CloudWatch Logs show connection errors

**Diagnosis:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/<function-name> --since 30m --follow

# Look for connection errors, DNS failures
```

**Solutions:**
1. Deploy VPC endpoints for services Lambda calls (S3, SQS, SNS)
2. Verify Lambda security group allows HTTPS outbound
3. Check Lambda has ENI in correct subnets
4. Increase Lambda timeout if needed (but shouldn't be necessary)

### Issue: Search Indexing Fails

**Symptoms:**
- Objects uploaded but not appearing in search
- SQS queue growing without processing

**Diagnosis:**
```bash
# Check indexing Lambda logs
aws logs tail /aws/lambda/indexer --follow

# Check SQS queue depth
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/.../indexing \
  --attribute-names ApproximateNumberOfMessages
```

**Solutions:**
1. Verify ElasticSearch is in intra subnets
2. Check security group allows Lambda → ElasticSearch (port 443)
3. ElasticSearch should NOT need internet access
4. Verify Lambda can reach ElasticSearch endpoint

### Issue: Database Connection Errors

**Symptoms:**
- ECS tasks crash with "connection refused"
- Registry service unable to start

**Diagnosis:**
```bash
# Check registry container logs
aws logs tail /aws/ecs/registry --follow

# Check RDS endpoint
aws rds describe-db-instances --db-instance-identifier <name>
```

**Solutions:**
1. Verify RDS is in intra subnets
2. Check security group allows ECS/Lambda → RDS (port 5432)
3. RDS should NEVER need internet access
4. Verify database endpoint resolution from private subnets

### Issue: High TGW Data Transfer Costs

**Symptoms:**
- Unexpectedly high TGW data processing charges
- CloudWatch metrics show high TGW bytes

**Solutions:**
1. Deploy missing VPC endpoints (especially S3, CloudWatch, ECR)
2. Enable VPC Flow Logs to identify traffic patterns
3. Check for unnecessary external API calls
4. Consider disabling telemetry and external SSO

### Issue: Slow Performance

**Symptoms:**
- Catalog loads slowly
- Package operations take longer than expected

**Diagnosis:**
```bash
# Check VPC endpoint usage
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids vpce-xxxxx

# Check CloudWatch metrics for latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=... \
  --start-time 2026-02-02T00:00:00Z \
  --end-time 2026-02-02T23:59:59Z \
  --period 3600 \
  --statistics Average
```

**Solutions:**
1. Ensure S3 Gateway Endpoint is deployed (huge performance impact)
2. Deploy ECR VPC endpoints for faster image pulls
3. Verify TGW is not congested (check TGW CloudWatch metrics)
4. Consider enabling accelerated networking on EC2 instances

---

## Cost Analysis

### Scenario 1: NAT Gateway (Default)

**Monthly Costs (per AZ):**
- NAT Gateway: $32.40/month (730 hours × $0.045)
- Data Processing: $0.045/GB

**Total (2 AZs, 1 TB data/month):**
- NAT Gateway: $64.80
- Data Processing: $46.08
- **Total: $110.88/month**

### Scenario 2: Transit Gateway Only

**Monthly Costs:**
- TGW Attachment: $36.50/month (730 hours × $0.05)
- TGW Data Processing: $0.02/GB

**Total (1 TB data/month):**
- TGW Attachment: $36.50
- Data Processing: $20.48
- **Total: $56.98/month**

**Savings:** $53.90/month vs NAT Gateway

**However:** TGW cost is typically shared across many VPCs, so marginal cost is just data transfer (~$20/month).

### Scenario 3: Transit Gateway + VPC Endpoints (Recommended)

**Monthly Costs:**
- TGW Attachment: $36.50/month (shared)
- VPC Endpoints (Tier 1): ~$35/month (6 endpoints × ~$6)
- TGW Data (minimal): ~$2-5/month (only external traffic)
- VPC Endpoint Data: $0.01/GB

**Total (1 TB data/month, 90% via VPC endpoints):**
- TGW Attachment: $36.50
- VPC Endpoints: $35.00
- TGW Data (100 GB): $2.05
- VPC Endpoint Data (900 GB): $9.24
- **Total: $82.79/month**

**vs NAT Gateway:** Saves $28/month
**vs TGW only:** Costs $26/month more, but much better performance and security

---

## Best Practices

### Network Design

1. **Always use Network 2.0** with private subnets and proper subnet segmentation
2. **Deploy VPC endpoints** for all AWS services Quilt uses
3. **Use separate route tables** for private, intra, and public subnets
4. **Enable VPC Flow Logs** to monitor traffic patterns
5. **Use security groups** as primary firewall, not NACLs

### Security

1. **Enable private DNS** for all VPC endpoints
2. **Restrict security groups** to minimum required ports
3. **Use separate intra subnets** for RDS/ElasticSearch (no internet)
4. **Enable encryption** at rest and in transit
5. **Audit TGW routes** regularly for unexpected changes

### Operations

1. **Document your network architecture** with diagrams
2. **Create runbooks** for common troubleshooting scenarios
3. **Set up CloudWatch alarms** for network issues
4. **Monitor TGW CloudWatch metrics** for congestion
5. **Test failover scenarios** (TGW attachment failure, etc.)

### Cost Optimization

1. **Deploy Tier 1 VPC endpoints minimum** to eliminate most data transfer
2. **Disable optional external services** (telemetry, external SSO)
3. **Use S3 Gateway Endpoint** (free!) instead of routing S3 via TGW
4. **Monitor VPC Endpoint costs** and optimize based on usage patterns
5. **Consider Reserved Capacity** for TGW if heavily used

---

## Verification Checklist

### Pre-Deployment

- [ ] TGW attached to target VPC
- [ ] Route tables configured with 0.0.0.0/0 → TGW
- [ ] TGW routes to internet (directly or via firewall)
- [ ] DNS resolution works from private subnets
- [ ] Security groups created for VPC endpoints
- [ ] VPC endpoints deployed (at least S3 Gateway)
- [ ] Firewall rules configured (if applicable)
- [ ] Subnet IDs documented
- [ ] Parameters file prepared

### Post-Deployment

- [ ] CloudFormation/Terraform deployment succeeded
- [ ] No NAT Gateway created (verify in VPC console)
- [ ] ECS tasks launched successfully
- [ ] CloudWatch Logs receiving data
- [ ] RDS database accessible from ECS
- [ ] ElasticSearch accessible from Lambda/ECS
- [ ] Catalog accessible via VPN/public internet
- [ ] Test package upload successful
- [ ] Test search query returns results
- [ ] Test file download works
- [ ] VPC endpoints showing usage in CloudWatch metrics
- [ ] TGW metrics show expected traffic patterns
- [ ] No connection timeout errors in logs

### Performance Validation

- [ ] ECS task startup time < 2 minutes
- [ ] S3 operations < 500ms latency
- [ ] Search queries < 1 second
- [ ] API response time < 2 seconds
- [ ] No Lambda timeout errors
- [ ] CloudWatch metrics show healthy state

---

## Additional Resources

### AWS Documentation

- [AWS Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/)
- [VPC Endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)
- [VPC Endpoint Services (AWS PrivateLink)](https://docs.aws.amazon.com/vpc/latest/privatelink/endpoint-services-overview.html)
- [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)

### Quilt Documentation

- Network Architecture Guide (README.md)
- Private Endpoints Configuration (t4/template/PRIVATE_ENDPOINTS.md)
- Environment Configuration Schema (t4/template/environment/env_schema.py)

### Support

For questions or issues:
- Email: support@quiltdata.com
- Documentation: https://docs.quiltdata.com
- GitHub Issues: https://github.com/quiltdata/quilt

---

## Appendix: Example Terraform Configuration

```hcl
# Example: Create VPC endpoints for Quilt deployment

locals {
  vpc_id = "vpc-xxxxx"
  private_subnet_ids = ["subnet-xxxxx", "subnet-yyyyy"]
  vpc_endpoint_sg_id = aws_security_group.vpc_endpoints.id
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoints" {
  name        = "vpc-endpoints-quilt"
  description = "Allow HTTPS from private subnets to VPC endpoints"
  vpc_id      = local.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.1.0/24", "10.0.2.0/24"]  # Private subnet CIDRs
  }

  tags = {
    Name = "vpc-endpoints-quilt"
  }
}

# S3 Gateway Endpoint (FREE!)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = local.vpc_id
  service_name      = "com.amazonaws.us-east-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name = "s3-gateway-endpoint"
  }
}

# CloudWatch Logs Interface Endpoint
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.us-east-1.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_subnet_ids
  security_group_ids  = [local.vpc_endpoint_sg_id]
  private_dns_enabled = true

  tags = {
    Name = "logs-interface-endpoint"
  }
}

# ECR API Interface Endpoint
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.us-east-1.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_subnet_ids
  security_group_ids  = [local.vpc_endpoint_sg_id]
  private_dns_enabled = true

  tags = {
    Name = "ecr-api-interface-endpoint"
  }
}

# ECR Docker Interface Endpoint
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.us-east-1.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_subnet_ids
  security_group_ids  = [local.vpc_endpoint_sg_id]
  private_dns_enabled = true

  tags = {
    Name = "ecr-dkr-interface-endpoint"
  }
}

# SQS Interface Endpoint
resource "aws_vpc_endpoint" "sqs" {
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.us-east-1.sqs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_subnet_ids
  security_group_ids  = [local.vpc_endpoint_sg_id]
  private_dns_enabled = true

  tags = {
    Name = "sqs-interface-endpoint"
  }
}

# SNS Interface Endpoint
resource "aws_vpc_endpoint" "sns" {
  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.us-east-1.sns"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_subnet_ids
  security_group_ids  = [local.vpc_endpoint_sg_id]
  private_dns_enabled = true

  tags = {
    Name = "sns-interface-endpoint"
  }
}

# Output endpoint IDs for reference
output "vpc_endpoint_ids" {
  value = {
    s3       = aws_vpc_endpoint.s3.id
    logs     = aws_vpc_endpoint.logs.id
    ecr_api  = aws_vpc_endpoint.ecr_api.id
    ecr_dkr  = aws_vpc_endpoint.ecr_dkr.id
    sqs      = aws_vpc_endpoint.sqs.id
    sns      = aws_vpc_endpoint.sns.id
  }
}
```

---

**Document Version:** 1.0
**Last Updated:** February 2, 2026
**Maintained By:** Quilt Engineering Team
