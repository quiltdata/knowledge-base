# How-To: Deploy Quilt with Transit Gateway

## Tags

`aws`, `networking`, `transit-gateway`, `vpc-endpoints`, `enterprise`

## Summary

> Deploy Quilt using Transit Gateway by providing TGW-configured subnets. Optionally deploy VPC endpoints to reduce TGW data charges.

---

## Prerequisites

- VPC with Transit Gateway attachment (TGW routes to internet)
- Quilt deployment configured with `network.vpn: true` (sets `existing_vpc: true`)
- AWS networking knowledge (VPC, subnets, route tables, security groups)

### Subnet Requirements

**Private Subnets** (2, different AZs):

- Route: `0.0.0.0/0 → tgw-xxxxx`
- For: ECS containers, Lambda functions

**Intra Subnets** (2, different AZs):

- Route: Local VPC only
- For: RDS, ElasticSearch

**User Subnets** (load balancer):

- Internal: Use private subnets
- Public: Use public subnets with IGW

---

## Step 1: Deploy VPC Endpoints (Strongly Recommended)

Configuring these essential endpoints costs ~$35/month, but can reduce TGW charges by 90%+.

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

## Step 2: Configure Firewall Rules (If Applicable)

If TGW routes through firewall, allow HTTPS (443) to:

- `telemetry.quiltdata.cloud` (if telemetry enabled)
- `accounts.google.com` (if Google SSO)
- `login.microsoftonline.com` (if Azure SSO)
- `*.amazonaws.com` (if no VPC endpoints)

---

## Step 3: Prepare Parameters

```yaml
VPC: vpc-xxxxx
Subnets: subnet-private1,subnet-private2      # TGW routing
IntraSubnets: subnet-intra1,subnet-intra2     # No internet
UserSubnets: subnet-private1,subnet-private2  # Same as Subnets
UserSecurityGroup: sg-xxxxx
DBUser: quilt_admin
DBPassword: <password>
CertificateArnELB: arn:aws:acm:...
AdminEmail: admin@company.com
QuiltWebHost: quilt.company.com
```

---

## Step 4: Validate & Troubleshoot

Test deployment:

```bash
STACK_NAME="your-stack"
REGISTRY=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`RegistryHost`].OutputValue' --output text)
curl -s -o /dev/null -w "%{http_code}" https://$REGISTRY/  # Expect: 200 or 302
```

Verify VPC endpoints (DNS should resolve to 10.x.x.x):

```bash
nslookup s3.$REGION.amazonaws.com
nslookup logs.$REGION.amazonaws.com
```

**Common Issues:**

**ECS "CannotPullContainerError":** Deploy ECR VPC endpoints or verify TGW routes to `*.ecr.amazonaws.com`

**Lambda timeouts:** Deploy VPC endpoints or verify security groups allow 443 outbound

**High TGW costs:** Deploy missing VPC endpoints or set `DISABLE_QUILT_TELEMETRY=true`

---

**Support:** <support@quiltdata.com>
