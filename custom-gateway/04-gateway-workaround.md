# Customer Gateway Workaround - Simplest Fix

**Date:** February 2, 2026
**For:** Customer Organization
**Goal:** Use Transit Gateway instead of NAT Gateway with minimal code changes

---

## TL;DR - The Simple Answer

**Customer can use their Transit Gateway with ZERO code changes to Quilt!**

The key is that the customer is already configured with `network.vpn: true` in their variant, which sets `existing_vpc: true`. This means:

✅ **Customer controls their own routing via their own route tables**
✅ **Quilt doesn't create NAT Gateway when `existing_vpc: true`**
✅ **Just provide TGW-configured subnets as parameters**

---

## Current Customer Configuration

From customer's variant files (`customer-prod.yaml`, `customer-staging.yaml`, `customer-dev.yaml`):

```yaml
factory:
  network:
    vpn: true  # This sets existing_vpc: true
  deployment: tf
```

This configuration means:
- Customer provides their own VPC
- Customer provides their own subnets
- Customer controls routing via their own route tables
- **Quilt does NOT create NAT Gateway**

---

## What Customer Needs to Do (Zero Code Changes Required)

### Step 1: Prepare Subnets with TGW Routing

Create or use existing subnets in your VPC with route tables that look like:

```
Destination         Target              Notes
-----------------------------------------------------------
10.0.0.0/16        local               Intra-VPC traffic
0.0.0.0/0          tgw-xxxxx           All internet via TGW
```

You need three types of subnets:

1. **Private Subnets** (for ECS tasks and Lambda functions)
   - Route 0.0.0.0/0 → TGW
   - 2 subnets in different AZs
   - Example: 10.0.1.0/24, 10.0.2.0/24

2. **Intra Subnets** (for RDS and ElasticSearch)
   - No internet routing at all
   - 2 subnets in different AZs
   - Example: 10.0.3.0/24, 10.0.4.0/24

3. **User/Public Subnets** (for load balancer)
   - For VPN access: Private subnets (same as #1)
   - For internet: Public subnets with route 0.0.0.0/0 → IGW

### Step 2: Deploy VPC Endpoints (Recommended)

To minimize TGW internet traffic, deploy these VPC Interface Endpoints:

**Essential (Tier 1):**
- `com.amazonaws.us-east-1.s3` (Gateway - free!)
- `com.amazonaws.us-east-1.logs` (CloudWatch Logs)
- `com.amazonaws.us-east-1.ecr.api` (ECR API)
- `com.amazonaws.us-east-1.ecr.dkr` (ECR Docker)
- `com.amazonaws.us-east-1.sqs`
- `com.amazonaws.us-east-1.sns`

With these endpoints, most AWS API calls bypass TGW entirely and stay within AWS network.

### Step 3: Provide Parameters During Deployment

When deploying the Quilt stack, provide these parameters:

```bash
# VPC Parameters
VPC=vpc-xxxxx                    # Your VPC ID
Subnets=subnet-xxx1,subnet-xxx2  # Private subnets with TGW routing
IntraSubnets=subnet-xxx3,subnet-xxx4  # Intra subnets (no internet)
UserSubnets=subnet-xxx1,subnet-xxx2   # Same as Subnets for VPN access
UserSecurityGroup=sg-xxxxx       # Security group for load balancer ingress
```

**Important:** The `Subnets` parameter description says "Must route traffic to public AWS services (e.g. via NAT Gateway)" but this is just a **comment**, not a technical requirement. The actual requirement is:

> "Subnets must be able to reach AWS services"

This can be satisfied via:
- ✅ NAT Gateway (Quilt's default)
- ✅ Transit Gateway (customer's preferred)
- ✅ VPC Endpoints (most private)

### Step 4: Configure External Services (Optional)

If you want to minimize TGW internet routing:

**Option A: Disable Telemetry**
```bash
export DISABLE_QUILT_TELEMETRY=true
```

**Option B: Skip External SSO**
- Don't configure Google/Azure/Okta/OneLogin credentials
- Use IAM-based authentication instead

**Option C: Use VPC Endpoints for Everything**
- Deploy all VPC endpoints from Tier 1 + 2 (see 03-gateway-audit.md)
- Only ECR pulls will need external routing (if using Quilt ECR)

---

## Code Analysis: Why This Works

### When `existing_vpc: true`

From `t4/template/network.py` line 246:

```python
if env["options"]["existing_vpc"]:
    vpc_id = Ref("VPC")
    subnet_ids = Ref("Subnets")
    # ... Quilt uses YOUR subnets, YOUR route tables
```

**Quilt doesn't create NAT Gateway at all!**

### When `existing_vpc: false`

From `t4/template/network.py` lines 393-399:

```python
nat_gateway = ec2.NatGateway(
    f"NatGateway{name}",
    template=cft,
    AllocationId=GetAtt(elastic_ip, "AllocationId"),
    ConnectivityType="public",
    SubnetId=public_subnet.ref(),
)
```

**Quilt creates NAT Gateway ONLY when it creates the VPC itself.**

---

## Routing Architecture Comparison

### Current Assumption (NAT Gateway)

```
ECS Task/Lambda → Private Subnet → NAT Gateway → Internet Gateway → AWS Services
```

### Customer's Transit Gateway Setup

```
ECS Task/Lambda → Private Subnet → Transit Gateway → Corporate Network → AWS Services
                                    ↓
                                 VPC Endpoints (for most AWS services)
```

### Recommended Hybrid (Best Performance)

```
ECS Task/Lambda → Private Subnet → VPC Endpoints → AWS Services (S3, SQS, etc.)
                                  ↘ Transit Gateway → Corporate Network → Internet
                                                                          (ECR, optional SSO)
```

---

## What Needs Internet Access via TGW

### Required (if not using VPC endpoints):

1. **ECR Image Pulls**
   - `*.ecr.us-east-1.amazonaws.com` (API)
   - `*.s3.amazonaws.com` (image layers)
   - Or deploy ECR VPC endpoints to avoid this

2. **AWS Service APIs**
   - S3, CloudWatch, SQS, SNS, etc.
   - Or deploy VPC endpoints to avoid this

### Optional (can be disabled):

3. **Quilt Telemetry**
   - `telemetry.quiltdata.cloud`
   - Disable with `DISABLE_QUILT_TELEMETRY=true`

4. **SSO Providers**
   - `accounts.google.com`, `login.microsoftonline.com`, etc.
   - Don't configure SSO to avoid this

---

## Terraform vs CloudFormation Note

Customer is using `deployment: tf` (Terraform), which means they're likely already managing their own VPC infrastructure via Terraform.

**Recommendation:**
1. Customer's Terraform manages: VPC, subnets, route tables, TGW attachment, VPC endpoints
2. Quilt's Terraform references: Existing VPC and subnets via parameters
3. No conflict, clean separation of concerns

---

## Testing Checklist

### Phase 1: Pre-Deployment Validation

- [ ] Verify TGW attachment to target VPC
- [ ] Verify route tables point 0.0.0.0/0 to TGW
- [ ] Verify TGW routes to internet (or corporate firewall → internet)
- [ ] Deploy VPC endpoints (at least S3 Gateway)
- [ ] Test DNS resolution from private subnets

### Phase 2: Deployment

- [ ] Deploy Quilt with `existing_vpc: true`
- [ ] Provide TGW-configured subnets as parameters
- [ ] Monitor CloudFormation/Terraform logs
- [ ] Verify no NAT Gateway created

### Phase 3: Functional Testing

- [ ] Verify ECS tasks launch successfully
- [ ] Check CloudWatch Logs for errors
- [ ] Test ECR image pulls (check ECS task startup time)
- [ ] Test S3 access (upload/download packages)
- [ ] Test search indexing
- [ ] Test catalog access

### Phase 4: Network Validation

- [ ] Verify no traffic to NAT Gateway (shouldn't exist)
- [ ] Verify traffic to VPC endpoints (if deployed)
- [ ] Verify traffic to TGW (for internet-bound requests)
- [ ] Check TGW metrics in CloudWatch
- [ ] Validate no connection timeouts

---

## Troubleshooting

### Issue: ECS tasks fail to start

**Possible Cause:** Cannot pull Docker images from ECR
**Solution:**
1. Deploy ECR VPC endpoints (`ecr.api` and `ecr.dkr`)
2. Or verify TGW routes to `*.ecr.us-east-1.amazonaws.com`
3. Check security groups allow HTTPS (443) from private subnets

### Issue: Lambda timeout errors

**Possible Cause:** Cannot reach AWS services
**Solution:**
1. Deploy VPC endpoints for services Lambda needs (S3, SQS, SNS)
2. Or verify TGW routes to `*.amazonaws.com`
3. Check Lambda VPC configuration and security groups

### Issue: Search indexing fails

**Possible Cause:** ElasticSearch in VPC cannot communicate
**Solution:**
1. Verify ElasticSearch is in intra subnets (no internet needed)
2. Check security groups allow traffic from Lambda/ECS to ElasticSearch
3. ElasticSearch should NOT need TGW or internet access

### Issue: Database connection errors

**Possible Cause:** RDS in wrong subnets
**Solution:**
1. Verify RDS is in intra subnets (no internet needed)
2. RDS should NEVER need TGW or internet access
3. Check security groups allow traffic from ECS/Lambda to RDS

---

## Cost Comparison

### Option 1: NAT Gateway (Quilt Default)
- NAT Gateway: $32.40/month (730 hours × $0.045)
- Data Processing: $0.045/GB
- **Total (1 TB/month):** $32.40 + $46.08 = **$78.48/month**

### Option 2: TGW Only (Customer's Request)
- TGW Attachment: $36.50/month (730 hours × $0.05)
- TGW Data: $0.02/GB
- **Total (1 TB/month):** $36.50 + $20.48 = **$56.98/month**
- **But:** TGW cost is shared across all VPCs (sunk cost)
- **Marginal cost for Quilt:** Just the data transfer (~$20/month)

### Option 3: TGW + VPC Endpoints (Recommended)
- TGW Attachment: $36.50/month (shared/sunk)
- VPC Endpoints (Tier 1): $35/month + $0.01/GB
- TGW Data (minimal): ~$2-5/month (only ECR/telemetry)
- **Total (1 TB/month):** $36.50 + $35 + $10.24 + $2 = **$83.74/month**
- **Marginal cost for Quilt:** ~$47/month (VPC endpoints + minimal TGW data)

**For Customer:**
- TGW attachment cost is already paid (shared resource)
- Only new cost is VPC endpoints
- **Net new cost: ~$35-47/month** (much cheaper than NAT Gateway data charges at scale)

---

## Recommended Action Plan

### Immediate (This Week)

1. **Confirm Customer's Current Setup**
   - Are they using `existing_vpc: true`? (Yes, based on `network.vpn: true`)
   - What subnets are they currently providing?
   - Are those subnets routing through TGW already?

2. **Deploy VPC Endpoints (Tier 1)**
   - S3 Gateway Endpoint (free)
   - CloudWatch Logs Interface Endpoint
   - ECR API and ECR Docker Interface Endpoints
   - SQS and SNS Interface Endpoints

3. **Test Deployment**
   - Deploy to dev environment first
   - Verify all functionality works
   - Monitor for connection issues
   - Validate performance

### Short-term (Next 2 Weeks)

4. **Deploy to Staging**
   - Use TGW-configured subnets
   - Full functional testing
   - Performance benchmarking

5. **Document Learnings**
   - Update customer's deployment documentation
   - Create runbook for TGW deployments
   - Share with other customers who might want this

### Medium-term (Next Month)

6. **Deploy to Production**
   - After successful staging validation
   - Monitor closely for first 48 hours
   - Compare metrics to baseline

7. **Product Enhancement**
   - Update parameter descriptions to be less NAT Gateway-specific
   - Add TGW example to documentation
   - Consider adding VPC endpoint auto-deployment option

---

## Documentation Updates Needed

### In Template Parameter Descriptions

**Current (misleading):**
```
"List of private subnets for Quilt service containers.
Must route traffic to public AWS services (e.g. via NAT Gateway)."
```

**Better (accurate):**
```
"List of private subnets for Quilt service containers.
Must have outbound connectivity to AWS services (via NAT Gateway,
Transit Gateway, or VPC Endpoints)."
```

### In Deployment Documentation

Add section:
- "Using Transit Gateway Instead of NAT Gateway"
- "Enterprise Network Integration"
- "VPC Endpoint Configuration"

---

## Key Takeaway for Customer

**You don't need to modify any Quilt code or templates!**

The solution is configuration-only:

1. ✅ Use `existing_vpc: true` (you already have this via `network.vpn: true`)
2. ✅ Provide your TGW-configured private subnets as the `Subnets` parameter
3. ✅ Deploy VPC endpoints for optimal performance
4. ✅ Optionally disable telemetry and external SSO

**That's it! No code changes required.**

The parameter description saying "e.g. via NAT Gateway" is just an example, not a requirement. The actual requirement is "can reach AWS services" which your TGW + VPC endpoint setup satisfies.

---

## Next Steps for Customer

1. **Share your subnet IDs** that are configured with TGW routing
2. **Confirm which VPC endpoints** you've already deployed
3. **Test in dev environment** with your TGW-configured subnets
4. **Report any issues** so we can help troubleshoot

We're here to help make this work smoothly!

---

**Contact:**
- Quilt Engineering Team
- Simon Kohnstamm (support@quiltdata.com)
- Ernest (ernest@quilt.bio)
