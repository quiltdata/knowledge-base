# How-To: Deploy Quilt with Transit Gateway Routing

## Tags

`aws`, `networking`, `transit-gateway`, `vpc`, `vpc-endpoints`, `enterprise`, `security`, `network-2.0`

## Summary

Guide for deploying Quilt in enterprise environments using AWS Transit Gateway for outbound connectivity instead of NAT Gateway. Covers VPC endpoint configuration, routing setup, and validation procedures for centralized network architectures.

---

## Why Use Transit Gateway?

Transit Gateway (TGW) is common in enterprise AWS environments for centralized network routing and security policy enforcement. Key benefits:

- **Centralized routing**: All VPCs route through a single TGW hub
- **Corporate compliance**: Traffic inspected by corporate firewalls
- **Cost optimization**: Single TGW attachment shared across many VPCs
- **Simplified management**: One routing policy for entire organization

### Prerequisites

- Existing VPC with Transit Gateway attachment
- Network 2.0 architecture (`network_version: "2.0"`)
- Configuration with `existing_vpc: true` (automatically set when `network.vpn: true`)
- Understanding of AWS networking (VPC, subnets, route tables)

---

## Architecture Overview

### Default Quilt Architecture (NAT Gateway)

```
┌──────────────┐      ┌─────────────┐
│ ECS/Lambda   │──────│ NAT Gateway │─────> Internet (AWS APIs)
│ (Private)    │      │             │
└──────────────┘      └─────────────┘
```

- Quilt creates and manages NAT Gateway
- Cost: $32.40/month per NAT + $0.045/GB
- Each VPC has dedicated egress

### Transit Gateway Architecture

```
┌──────────────┐      ┌─────────────┐
│ ECS/Lambda   │──────│     TGW     │─────> Corporate Network
│ (Private)    │      │ Attachment  │         └─> Firewall
└──────────────┘      └─────────────┘              └─> Internet
```

- Customer manages VPC and routing
- TGW cost shared across all VPCs
- Centralized security and compliance

### Recommended: Hybrid with VPC Endpoints

```
┌──────────────┐
│ ECS/Lambda   │──────┐
│ (Private)    │      │
└──────────────┘      │
                 ┌────┴────┐
                 │  Route  │
                 │Decision │
                 └────┬────┘
         ┌───────────┼───────────┐
         ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────┐
   │   VPC    │ │   VPC    │ │ TGW  │──> Internet
   │Endpoint  │ │Endpoint  │ │      │    (minimal)
   │  (S3)    │ │  (ECR)   │ └──────┘
   └──────────┘ └──────────┘

   90%+ traffic         External only
   stays private        (telemetry, SSO)
```

- Best performance and security
- Minimal TGW data transfer costs
- Private access to AWS services

---

## Key Insight: No Code Changes Required

**Important**: When using `existing_vpc: true`, Quilt does NOT create NAT Gateway. You provide your own subnets with your own routing configuration.

From your variant YAML:
```yaml
factory:
  network:
    vpn: true  # This sets existing_vpc: true
```

This means:
- ✅ Quilt uses YOUR route tables
- ✅ You control routing (NAT Gateway, TGW, or VPC Endpoints)
- ✅ No code changes needed

---

## Implementation Steps

### Phase 1: Network Preparation

#### Step 1: Verify Transit Gateway Configuration

Confirm TGW is attached and routing is configured:

```bash
# Set your VPC ID
VPC_ID="vpc-xxxxx"

# Verify TGW attachment
aws ec2 describe-transit-gateway-attachments \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'TransitGatewayAttachments[*].[TransitGatewayId,State,TransitGatewayAttachmentId]' \
  --output table

# Get TGW ID for later use
TGW_ID=$(aws ec2 describe-transit-gateway-attachments \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'TransitGatewayAttachments[0].TransitGatewayId' \
  --output text)

echo "Transit Gateway ID: $TGW_ID"
```

#### Step 2: Create or Identify Subnets with TGW Routing

You need three types of subnets for Network 2.0:

**Private Subnets** (for ECS and Lambda):
- Route: 0.0.0.0/0 → Transit Gateway
- Quantity: 2 subnets in different AZs
- Used for: Service containers, Lambda functions

**Intra Subnets** (for RDS and ElasticSearch):
- Route: Local VPC only (no internet)
- Quantity: 2 subnets in different AZs
- Used for: Database, search cluster

**User/Load Balancer Subnets**:
- For VPN access: Same as private subnets
- For public access: Public subnets (0.0.0.0/0 → Internet Gateway)

```bash
# List existing subnets
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# Example: Create private subnets with TGW routing
# (Skip if you already have suitable subnets)

# Create first private subnet
PRIVATE_SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=quilt-private-1a}]' \
  --query 'Subnet.SubnetId' \
  --output text)

# Create second private subnet
PRIVATE_SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=quilt-private-1b}]' \
  --query 'Subnet.SubnetId' \
  --output text)

echo "Private Subnets: $PRIVATE_SUBNET_1, $PRIVATE_SUBNET_2"
```

#### Step 3: Configure Route Tables for TGW

Create route tables pointing to Transit Gateway:

```bash
# Create route table for private subnets
PRIVATE_RTB=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=quilt-private-tgw}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

# Add route to TGW (0.0.0.0/0 → TGW)
aws ec2 create-route \
  --route-table-id $PRIVATE_RTB \
  --destination-cidr-block 0.0.0.0/0 \
  --transit-gateway-id $TGW_ID

# Associate subnets with route table
aws ec2 associate-route-table \
  --subnet-id $PRIVATE_SUBNET_1 \
  --route-table-id $PRIVATE_RTB

aws ec2 associate-route-table \
  --subnet-id $PRIVATE_SUBNET_2 \
  --route-table-id $PRIVATE_RTB

# Verify routing
aws ec2 describe-route-tables --route-table-ids $PRIVATE_RTB \
  --query 'RouteTables[0].Routes[*].[DestinationCidrBlock,TransitGatewayId,GatewayId]' \
  --output table
```

Expected route table output:
```
Destination         Target
-----------------------------------
10.0.0.0/16        local
0.0.0.0/0          tgw-xxxxx
```

#### Step 4: Create Intra Subnets (No Internet Routing)

For RDS and ElasticSearch - these should NEVER have internet access:

```bash
# Create first intra subnet
INTRA_SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.3.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=quilt-intra-1a}]' \
  --query 'Subnet.SubnetId' \
  --output text)

# Create second intra subnet
INTRA_SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.4.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=quilt-intra-1b}]' \
  --query 'Subnet.SubnetId' \
  --output text)

# Create intra route table (local only, no default route)
INTRA_RTB=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=quilt-intra}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

# Associate intra subnets (no internet route added)
aws ec2 associate-route-table \
  --subnet-id $INTRA_SUBNET_1 \
  --route-table-id $INTRA_RTB

aws ec2 associate-route-table \
  --subnet-id $INTRA_SUBNET_2 \
  --route-table-id $INTRA_RTB

echo "Intra Subnets: $INTRA_SUBNET_1, $INTRA_SUBNET_2"
```

### Phase 2: Deploy VPC Endpoints (Strongly Recommended)

VPC Endpoints eliminate the need for TGW routing to most AWS services, improving performance and reducing costs.

#### Step 5: Create Security Group for VPC Endpoints

```bash
# Create security group for VPC endpoints
VPCE_SG=$(aws ec2 create-security-group \
  --group-name quilt-vpc-endpoints \
  --description "Security group for Quilt VPC endpoints" \
  --vpc-id $VPC_ID \
  --query 'GroupId' \
  --output text)

# Allow HTTPS (443) from private subnets
aws ec2 authorize-security-group-ingress \
  --group-id $VPCE_SG \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.1.0/24  # Private subnet 1

aws ec2 authorize-security-group-ingress \
  --group-id $VPCE_SG \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.2.0/24  # Private subnet 2

echo "VPC Endpoint Security Group: $VPCE_SG"
```

#### Step 6: Deploy Essential VPC Endpoints (Tier 1)

These endpoints handle 90%+ of Quilt's AWS API traffic:

```bash
# Get AWS region
REGION=$(aws configure get region)

# S3 Gateway Endpoint (FREE!)
S3_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.s3 \
  --route-table-ids $PRIVATE_RTB \
  --vpc-endpoint-type Gateway \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

echo "Created S3 Gateway Endpoint: $S3_VPCE"

# CloudWatch Logs Interface Endpoint
LOGS_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.logs \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

echo "Created CloudWatch Logs Endpoint: $LOGS_VPCE"

# ECR API Interface Endpoint
ECR_API_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.ecr.api \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

echo "Created ECR API Endpoint: $ECR_API_VPCE"

# ECR Docker Interface Endpoint (for image layers)
ECR_DKR_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.ecr.dkr \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

echo "Created ECR Docker Endpoint: $ECR_DKR_VPCE"

# SQS Interface Endpoint
SQS_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.sqs \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

echo "Created SQS Endpoint: $SQS_VPCE"

# SNS Interface Endpoint
SNS_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.sns \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

echo "Created SNS Endpoint: $SNS_VPCE"

# Summary
echo ""
echo "=== VPC Endpoints Created (Tier 1) ==="
echo "S3 (Gateway):      $S3_VPCE"
echo "CloudWatch Logs:   $LOGS_VPCE"
echo "ECR API:           $ECR_API_VPCE"
echo "ECR Docker:        $ECR_DKR_VPCE"
echo "SQS:               $SQS_VPCE"
echo "SNS:               $SNS_VPCE"
echo ""
echo "Estimated cost: ~$35/month + $0.01/GB"
```

#### Step 7: Deploy Additional VPC Endpoints (Tier 2 - Optional)

For better coverage and performance:

```bash
# EventBridge
EVENTS_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.events \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

# KMS
KMS_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.kms \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

# SSM Parameter Store
SSM_VPCE=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.ssm \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --security-group-ids $VPCE_SG \
  --private-dns-enabled \
  --query 'VpcEndpoint.VpcEndpointId' \
  --output text)

echo "Created Tier 2 endpoints: EventBridge, KMS, SSM"
echo "Additional cost: ~$35/month"
```

### Phase 3: Deploy Quilt Stack

#### Step 8: Prepare Deployment Parameters

Collect the subnet IDs and security group information:

```bash
# Save configuration for deployment
cat > quilt-tgw-params.txt <<EOF
=== Quilt Deployment Parameters for Transit Gateway ===

Network Configuration:
VPC=$VPC_ID
Subnets=$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2
IntraSubnets=$INTRA_SUBNET_1,$INTRA_SUBNET_2
UserSubnets=$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2

# Create UserSecurityGroup for load balancer
# (You need to create this based on your access requirements)
UserSecurityGroup=sg-xxxxx  # TODO: Create this

# If using api_gateway_in_vpc=true, create API Gateway VPC Endpoint:
# ApiGatewayVPCEndpoint=vpce-xxxxx  # TODO: Create this if needed

Database Configuration:
DBUser=quilt_admin
DBPassword=<secure-password>

Certificates:
CertificateArnELB=arn:aws:acm:$REGION:xxxxx:certificate/xxxxx

Admin:
AdminEmail=admin@yourcompany.com
QuiltWebHost=quilt.yourcompany.com

VPC Endpoints Created:
S3_Gateway=$S3_VPCE
CloudWatch_Logs=$LOGS_VPCE
ECR_API=$ECR_API_VPCE
ECR_Docker=$ECR_DKR_VPCE
SQS=$SQS_VPCE
SNS=$SNS_VPCE
EOF

cat quilt-tgw-params.txt
```

#### Step 9: Optional - Minimize External Dependencies

To reduce TGW internet traffic further:

```bash
# Disable telemetry (add to environment configuration)
echo "DISABLE_QUILT_TELEMETRY=true" >> .env

# Note: Skip configuring external SSO providers
# Use IAM-based authentication instead
```

#### Step 10: Deploy Stack

Deploy using your standard Quilt deployment process with the parameters from Step 8.

**Using Terraform:**
```bash
cd deployment/t4
make variant=your-variant-name
cd ../tf
terraform init
terraform plan -var-file=../quilt-tgw-params.tfvars
terraform apply
```

**Using CloudFormation:**
```bash
aws cloudformation create-stack \
  --stack-name quilt-tgw \
  --template-body file://cloudformation.json \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_IAM
```

### Phase 4: Validation

#### Step 11: Verify VPC Endpoint Usage

Confirm that VPC endpoints are being used (not TGW for AWS services):

```bash
# Test DNS resolution from private subnet
# (requires bastion or Systems Manager Session Manager)

# Check S3 endpoint resolution (should be private IP)
nslookup s3.$REGION.amazonaws.com
# Expected: 10.x.x.x (private IP range)

# Check ECR endpoint resolution (should be private IP)
nslookup api.ecr.$REGION.amazonaws.com
# Expected: 10.x.x.x (private IP range)

# Check CloudWatch Logs endpoint
nslookup logs.$REGION.amazonaws.com
# Expected: 10.x.x.x (private IP range)
```

#### Step 12: Monitor TGW Traffic

```bash
# Check TGW CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/TransitGateway \
  --metric-name BytesIn \
  --dimensions Name=TransitGateway,Value=$TGW_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --query 'Datapoints[*].[Timestamp,Sum]' \
  --output table

# Expected: Minimal traffic if VPC endpoints are working
# Most traffic should go through VPC endpoints, not TGW
```

#### Step 13: Application Functionality Tests

```bash
STACK_NAME="quilt-tgw"

# Get stack outputs
REGISTRY_HOST=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`RegistryHost`].OutputValue' --output text)

# Test application health
echo "Testing Quilt stack health..."

# Test catalog access
curl -s -o /dev/null -w "Catalog HTTP Status: %{http_code}\n" https://$REGISTRY_HOST/

# Test API health
curl -s -o /dev/null -w "API HTTP Status: %{http_code}\n" https://$REGISTRY_HOST/api/health

echo ""
echo "Manual validation required:"
echo "1. Login at https://$REGISTRY_HOST"
echo "2. Upload a test package"
echo "3. Search for objects (tests ElasticSearch)"
echo "4. Download a file (tests S3 access)"
```

---

## Traffic Flow Analysis

### What Uses VPC Endpoints (No TGW Internet)

With Tier 1 VPC endpoints deployed:

| Service | Route | Internet? |
|---------|-------|-----------|
| S3 API | VPC Gateway Endpoint | ❌ No |
| CloudWatch Logs | VPC Interface Endpoint | ❌ No |
| ECR Image Pulls | VPC Interface Endpoints | ❌ No |
| SQS Messages | VPC Interface Endpoint | ❌ No |
| SNS Notifications | VPC Interface Endpoint | ❌ No |
| RDS Queries | Local VPC (intra subnet) | ❌ No |
| ElasticSearch | Local VPC (intra subnet) | ❌ No |

**Result:** 95%+ of traffic stays within AWS network

### What Uses TGW (Requires Internet Routing)

| Service | Route | Optional? |
|---------|-------|-----------|
| Telemetry | TGW → Internet | ✅ Yes (can disable) |
| Google OAuth | TGW → Internet | ✅ Yes (can skip) |
| Azure SSO | TGW → Internet | ✅ Yes (can skip) |
| Okta SSO | TGW → Internet | ✅ Yes (can skip) |

**Result:** Minimal TGW internet traffic

---

## Firewall Configuration

If your TGW routes through corporate firewall, allow:

### With VPC Endpoints (Minimal Rules)

**HTTPS (443) Outbound:**
- `telemetry.quiltdata.cloud` (if telemetry enabled)
- `accounts.google.com` (if Google SSO enabled)
- `login.microsoftonline.com` (if Azure SSO enabled)
- `*.okta.com` (if Okta SSO enabled)

**DNS (53) Outbound:**
- Your corporate DNS resolvers

**Total:** 1-4 HTTPS destinations (most optional)

### Without VPC Endpoints (Extensive Rules)

**HTTPS (443) Outbound:**
- `*.amazonaws.com` (all AWS services)
- `*.s3.amazonaws.com`
- `*.ecr.amazonaws.com`
- Plus all external services above

**Total:** 50+ AWS service destinations

---

## Troubleshooting

### Issue: ECS Tasks Fail to Start with "CannotPullContainerError"

**Diagnosis:**
```bash
# Check ECS task stopped reason
CLUSTER_NAME="quilt-tgw-cluster"
aws ecs list-tasks --cluster $CLUSTER_NAME --desired-status STOPPED --max-items 1

# Get task ID and describe it
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --desired-status STOPPED --max-items 1 --query 'taskArns[0]' --output text)
aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN \
  --query 'tasks[0].stoppedReason' --output text
```

**Solutions:**
1. Verify ECR VPC endpoints deployed and available
2. Check private DNS enabled on ECR endpoints
3. Verify security group allows HTTPS (443) to VPC endpoints
4. Test DNS resolution: `nslookup api.ecr.$REGION.amazonaws.com`

### Issue: Lambda Functions Timeout

**Diagnosis:**
```bash
# Check Lambda logs for connection errors
FUNCTION_NAME="quilt-tgw-indexer"
aws logs tail /aws/lambda/$FUNCTION_NAME --since 30m --follow
```

**Solutions:**
1. Deploy VPC endpoints for services Lambda calls
2. Verify Lambda security group allows HTTPS outbound
3. Check Lambda has ENIs in correct private subnets
4. Verify route table has TGW route (0.0.0.0/0 → TGW)

### Issue: High TGW Data Transfer Costs

**Diagnosis:**
```bash
# Enable VPC Flow Logs to see traffic patterns
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids $VPC_ID \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flowlogs/$VPC_ID

# Check what's going through TGW
aws logs tail /aws/vpc/flowlogs/$VPC_ID --since 1h --filter-pattern "[version, account, eni, source, destination, srcport, destport, protocol, packets, bytes, start, end, action=ACCEPT, logstatus]"
```

**Solutions:**
1. Deploy missing VPC endpoints (check which AWS services are accessed)
2. Disable telemetry: `DISABLE_QUILT_TELEMETRY=true`
3. Remove external SSO configuration
4. Check for unnecessary external API calls in application

### Issue: VPC Endpoint Not Being Used

**Diagnosis:**
```bash
# Check VPC endpoint status
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids $ECR_API_VPCE \
  --query 'VpcEndpoints[0].[State,PrivateDnsEnabled,ServiceName]' \
  --output table

# Verify security group allows traffic
aws ec2 describe-security-groups --group-ids $VPCE_SG \
  --query 'SecurityGroups[0].IpPermissions[*].[FromPort,ToPort,IpRanges[*].CidrIp]' \
  --output table
```

**Solutions:**
1. Ensure `PrivateDnsEnabled: true` on interface endpoints
2. Verify security group allows 443 from private subnet CIDRs
3. Check route table still has S3 endpoint attached (for gateway endpoint)
4. Restart services to pick up DNS changes

---

## Cost Comparison

### Scenario 1: NAT Gateway (Default Quilt)

Monthly cost for 2 AZs, 1 TB data:
- NAT Gateway: $64.80 (2 × $32.40)
- Data Processing: $46.08 (1000 GB × $0.045)
- **Total: $110.88/month**

### Scenario 2: Transit Gateway Only (No VPC Endpoints)

Monthly cost for 1 TB data:
- TGW Attachment: $36.50 (shared across VPCs)
- TGW Data: $20.48 (1000 GB × $0.02)
- **Total: $56.98/month**
- **Marginal cost if TGW exists: $20.48/month**

### Scenario 3: Transit Gateway + VPC Endpoints (Recommended)

Monthly cost for 1 TB data (90% via VPC endpoints):
- TGW Attachment: $36.50 (shared)
- VPC Endpoints (Tier 1): $35.00
- TGW Data: $2.05 (100 GB × $0.02)
- VPC Endpoint Data: $9.24 (900 GB × $0.01)
- **Total: $82.79/month**
- **Marginal cost: ~$47/month** (VPC endpoints + minimal TGW data)

**Savings vs NAT Gateway:** $28.09/month
**Best Value:** TGW + VPC endpoints for performance and security

---

## Appendix: Validation Scripts

### Complete Network Validation

```bash
#!/bin/bash
# Complete validation script for Transit Gateway deployment

STACK_NAME="quilt-tgw"
VPC_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
  --query 'Stacks[0].Parameters[?ParameterKey==`VPC`].ParameterValue' --output text)

echo "=== Transit Gateway Validation ==="
echo ""

# 1. TGW Attachment
echo "1. Transit Gateway Attachment:"
aws ec2 describe-transit-gateway-attachments \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'TransitGatewayAttachments[*].[TransitGatewayId,State,TransitGatewayAttachmentId]' \
  --output table
echo ""

# 2. VPC Endpoints
echo "2. VPC Endpoints:"
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'VpcEndpoints[*].[ServiceName,VpcEndpointType,State,VpcEndpointId]' \
  --output table
echo ""

# 3. Route Tables
echo "3. Private Subnet Route Tables:"
PRIVATE_SUBNETS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
  --query 'Stacks[0].Parameters[?ParameterKey==`Subnets`].ParameterValue' --output text)

for subnet in ${PRIVATE_SUBNETS//,/ }; do
  echo "Routes for subnet $subnet:"
  RTB=$(aws ec2 describe-route-tables \
    --filters "Name=association.subnet-id,Values=$subnet" \
    --query 'RouteTables[0].RouteTableId' --output text)

  aws ec2 describe-route-tables --route-table-ids $RTB \
    --query 'RouteTables[0].Routes[*].[DestinationCidrBlock,TransitGatewayId,GatewayId,VpcPeeringConnectionId]' \
    --output table
  echo ""
done

# 4. Intra Subnet Validation
echo "4. Intra Subnet Route Tables (should have NO internet route):"
INTRA_SUBNETS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
  --query 'Stacks[0].Parameters[?ParameterKey==`IntraSubnets`].ParameterValue' --output text)

for subnet in ${INTRA_SUBNETS//,/ }; do
  echo "Routes for intra subnet $subnet:"
  RTB=$(aws ec2 describe-route-tables \
    --filters "Name=association.subnet-id,Values=$subnet" \
    --query 'RouteTables[0].RouteTableId' --output text)

  aws ec2 describe-route-tables --route-table-ids $RTB \
    --query 'RouteTables[0].Routes[*].[DestinationCidrBlock,TransitGatewayId,GatewayId]' \
    --output table
  echo ""
done

# 5. Security Groups
echo "5. VPC Endpoint Security Group Rules:"
VPCE_SG=$(aws ec2 describe-security-groups \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=*vpc-endpoint*" \
  --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)

if [ -n "$VPCE_SG" ]; then
  aws ec2 describe-security-groups --group-ids $VPCE_SG \
    --query 'SecurityGroups[0].IpPermissions[*].[IpProtocol,FromPort,ToPort,IpRanges[*].CidrIp]' \
    --output table
else
  echo "No VPC endpoint security group found"
fi
echo ""

# 6. Application Health
echo "6. Application Health Check:"
REGISTRY_HOST=$(aws cloudformation describe-stacks --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`RegistryHost`].OutputValue' --output text 2>/dev/null)

if [ -n "$REGISTRY_HOST" ]; then
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$REGISTRY_HOST/ 2>/dev/null)
  echo "Catalog Status: $HTTP_STATUS"

  API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$REGISTRY_HOST/api/health 2>/dev/null)
  echo "API Status: $API_STATUS"
else
  echo "Stack not yet deployed or registry host not available"
fi

echo ""
echo "=== Validation Complete ==="
```

### TGW Traffic Monitoring

```bash
#!/bin/bash
# Monitor TGW traffic over time

VPC_ID="vpc-xxxxx"
TGW_ID=$(aws ec2 describe-transit-gateway-attachments \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'TransitGatewayAttachments[0].TransitGatewayId' \
  --output text)

echo "Monitoring TGW traffic for $TGW_ID"
echo "Press Ctrl+C to stop"
echo ""

while true; do
  BYTES_IN=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/TransitGateway \
    --metric-name BytesIn \
    --dimensions Name=TransitGateway,Value=$TGW_ID \
    --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Sum \
    --query 'Datapoints[0].Sum' \
    --output text)

  BYTES_OUT=$(aws cloudwatch get-metric-statistics \
    --namespace AWS/TransitGateway \
    --metric-name BytesOut \
    --dimensions Name=TransitGateway,Value=$TGW_ID \
    --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Sum \
    --query 'Datapoints[0].Sum' \
    --output text)

  if [ "$BYTES_IN" != "None" ]; then
    BYTES_IN_MB=$(echo "scale=2; $BYTES_IN / 1024 / 1024" | bc)
    BYTES_OUT_MB=$(echo "scale=2; $BYTES_OUT / 1024 / 1024" | bc)
    echo "$(date): IN: ${BYTES_IN_MB} MB, OUT: ${BYTES_OUT_MB} MB"
  else
    echo "$(date): No traffic data available"
  fi

  sleep 60
done
```

---

## Additional Resources

- [AWS Transit Gateway Documentation](https://docs.aws.amazon.com/vpc/latest/tgw/)
- [VPC Endpoints Guide](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)
- [Quilt Network Architecture](https://docs.quilt.bio/architecture)
- [How-To: Network 1.0 to 2.0 Migration](howto-2-network-1.0-migration.md)

---

**Document Version:** 1.0
**Last Updated:** February 2, 2026
**Maintained By:** Quilt Engineering Team
