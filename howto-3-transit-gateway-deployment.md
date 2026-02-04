# How-To: Deploy Quilt with Transit Gateway Routing

## Tags

`aws`, `networking`, `transit-gateway`, `vpc-endpoints`, `enterprise`

## Summary

Deploy Quilt using your existing Transit Gateway instead of NAT Gateway. No code changes required - just provide TGW-configured subnets as parameters.

---

## The Simple Answer

**You don't need to modify Quilt.** When your variant has `network.vpn: true`, Quilt uses `existing_vpc: true` mode. This means:

- ✅ You provide your own VPC and subnets
- ✅ You control routing via your route tables
- ✅ Quilt doesn't create NAT Gateway

Just give Quilt subnets that route through your Transit Gateway.

---

## What You Need

### Prerequisites

1. VPC with Transit Gateway attachment
2. Your variant configured with `network.vpn: true` (sets `existing_vpc: true`)
3. Network 2.0 architecture (`network_version: "2.0"`)
4. TGW must route to internet (for ECR image pulls)

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

VPC endpoints eliminate 90%+ of internet traffic. This means less data through your TGW and better performance.

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

Deploy Quilt with your parameters. The stack will use your TGW-configured subnets.

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

Test DNS resolution from a private subnet (requires bastion or Session Manager):

```bash
# Should resolve to private IP (10.x.x.x)
nslookup s3.$REGION.amazonaws.com
nslookup logs.$REGION.amazonaws.com
```

### Check TGW Traffic

```bash
# TGW traffic should be minimal if VPC endpoints are working
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

### With VPC Endpoints (Minimal)

Only these need internet via TGW:

- Telemetry (optional - disable with `DISABLE_QUILT_TELEMETRY=true`)
- SSO providers (optional - Google, Azure, Okta)

**Result:** 95%+ of traffic uses VPC endpoints, not TGW.

### Without VPC Endpoints (Not Recommended)

All AWS API calls go through TGW to internet:

- S3, CloudWatch, ECR, SQS, SNS, etc.
- Higher latency, higher TGW costs

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

### With VPC Endpoints

**Allow HTTPS (443) to:**

- `telemetry.quiltdata.cloud` (if telemetry enabled)
- `accounts.google.com` (if Google SSO enabled)
- `login.microsoftonline.com` (if Azure SSO enabled)

### Without VPC Endpoints

**Allow HTTPS (443) to:**

- `*.amazonaws.com` (all AWS services)

---

## Cost Comparison

| Setup                  | Monthly Cost (1TB data) |
| ---------------------- | ----------------------- |
| NAT Gateway (default)  | $111                    |
| TGW + VPC Endpoints    | $83                     |
| TGW only (no endpoints)| $57                     |

**Note:** TGW cost is shared across your organization. Your marginal cost is ~$35-47/month for VPC endpoints.

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
