# Quilt Deployment Network Dependencies Audit

**Date:** February 2, 2026
**Auditor:** Engineering Team
**Purpose:** Document all AWS services and external dependencies for Transit Gateway routing decisions
**Repository:** ~/GitHub/deployment/

---

## Executive Summary

This audit identifies **40+ AWS services** and **multiple external dependencies** that Quilt's deployment architecture requires. The findings directly answer the customer's questions about Transit Gateway routing feasibility.

**Key Findings:**
- ✅ Most AWS services can be accessed via VPC Endpoints (eliminating NAT/TGW internet routing)
- ⚠️ External services require internet egress: Telemetry, SSO providers, ECR image pulls
- ✅ Lambda and ECS can run entirely in private subnets with proper VPC endpoint configuration
- ⚠️ Optional features (SSO, telemetry) can be disabled to reduce external dependencies

---

## Quick Answer to Customer's Questions

### Q1: Can we route 0.0.0.0/0 through TGW instead of NAT Gateway?
**Answer:** Yes, with the following conditions:
- TGW must route to internet for: ECR pulls, telemetry (optional), SSO providers (optional)
- VPC Endpoints should be configured for AWS services to bypass TGW/internet routing
- Or deploy VPC Interface Endpoints for all services (see recommendations below)

### Q2: Do Lambda/ECS need to call external (non-AWS) services?
**Answer:** Yes, but mostly optional:
- **Required:** ECR (AWS service) for pulling Docker images
- **Optional:** Quilt telemetry service (`telemetry.quiltdata.cloud`)
- **Optional:** SSO providers (Google, Azure, Okta, OneLogin)
- **Optional:** External MCP/Benchling APIs (if configured)

### Q3: Which AWS services does Quilt need?
**Answer:** See complete list below. Primary services:
- **Core:** S3, RDS (PostgreSQL), ElasticSearch, ECS, Lambda
- **Messaging:** SQS, SNS, EventBridge
- **Networking:** VPC, ALB, Service Discovery
- **Monitoring:** CloudWatch Logs/Metrics, CloudWatch Synthetics
- **Analytics:** Athena, Glue, Firehose, CloudTrail
- **Security:** IAM, KMS, WAF v2

### Q4: Which VPC Endpoints do we need?
**Answer:** See "Recommended VPC Endpoint Configuration" section below.

---

## AWS Services Inventory

### 1. Compute Services

#### **Lambda (AWS Lambda)**
- **Usage:**
  - Search indexing (SearchHandler, EsIngest, ManifestIndexer)
  - Package creation/promotion handlers
  - API Gateway integrations
  - S3 to EventBridge conversion
  - DuckDB select operations
  - Custom CloudFormation resource handlers
- **Location:** `t4/template/search.py`, `pkg_push_lambdas.py`, `api_services.py`
- **Network:** Configurable with `lambdas_in_vpc` parameter
- **VPC Endpoint:** Use API Gateway endpoint if API Gateway is in VPC
- **Egress Needs:** AWS API calls, S3 access, CloudWatch Logs

#### **ECS (Elastic Container Service)**
- **Usage:**
  - Registry service container
  - MCP (Model Context Protocol) server
  - Benchling integration service
  - S3 proxy service
  - Voila notebook service
  - Bucket scanner tasks
  - Migration tasks
- **Location:** `t4/template/ecs.py`, `containers.py`
- **Network:** Private subnets with Service Discovery
- **Egress Needs:**
  - ECR image pulls (required)
  - CloudWatch Logs
  - S3 access
  - External SSO APIs (optional)
  - Telemetry (optional)

#### **EC2 (Elastic Compute Cloud)**
- **Usage:**
  - VPC infrastructure
  - NAT Gateways (can be replaced by TGW)
  - Security groups
  - Voila instance (optional)
- **Location:** `t4/template/network.py`, `voila.py`
- **Components:** VPC, Subnets, Route Tables, Internet Gateway, NAT Gateway

---

### 2. Storage Services

#### **S3 (Simple Storage Service)**
- **Usage:**
  - Data bucket storage for packages (primary use)
  - Analytics bucket for usage data
  - CloudTrail logs storage
  - Audit trail storage
  - Lambda code storage
  - Synthetics canary results
  - Service discovery bucket
- **Location:** Used throughout all templates
- **VPC Endpoint:** ✅ Gateway Endpoint (currently deployed)
- **Encryption:** KMS encryption supported
- **Access Pattern:** Heavy read/write from Lambda and ECS

#### **RDS (Relational Database Service)**
- **Usage:** PostgreSQL 15.12 for registry data
- **Location:** `t4/template/database.py`
- **Configuration:**
  - Multi-AZ optional
  - Storage encryption enabled
  - Private subnet deployment
  - CloudWatch Logs export (upgrade logs)
- **Port:** 5432 (internal only)
- **Network:** Private subnets, no internet access needed

---

### 3. Search & Database

#### **ElasticSearch (OpenSearch Service)**
- **Usage:** Full-text search and indexing for objects and packages
- **Location:** `t4/template/search.py`
- **Configuration:**
  - VPC or public deployment
  - Multi-AZ with zone awareness
  - Encryption at rest and in-transit
  - CloudWatch logging optional
- **Port:** 443 (HTTPS)
- **Network:** Private subnet deployment recommended
- **Access:** Lambda functions and ECS tasks

---

### 4. Messaging & Event Services

#### **SQS (Simple Queue Service)**
- **Usage:**
  - Search indexing queues
  - Package events queue
  - Dead letter queues
  - Event batching for Lambda
- **Location:** `t4/template/search.py`, `events.py`
- **Features:** Visibility timeout, DLQ, encryption
- **VPC Endpoint:** ✅ Interface Endpoint available (not deployed by default)

#### **SNS (Simple Notification Service)**
- **Usage:**
  - Canary failure notifications (email)
  - S3 bucket event notifications
  - Topic-based messaging
- **Location:** `t4/template/sns_kms.py`, `status/canaries.py`
- **Encryption:** KMS-encrypted topics
- **VPC Endpoint:** ✅ Interface Endpoint available (not deployed by default)

#### **EventBridge (CloudWatch Events)**
- **Usage:**
  - S3 to EventBridge event conversion
  - Scheduled events (canaries)
  - Service event routing
  - Synthetics state changes
- **Location:** `t4/template/events.py`, `s3_sns_to_eventbridge.py`
- **VPC Endpoint:** ✅ Interface Endpoint available (not deployed by default)

---

### 5. Networking & Load Balancing

#### **VPC (Virtual Private Cloud)**
- **Components:**
  - Multiple subnets (public, private, intra)
  - NAT Gateway (can be replaced by TGW)
  - Internet Gateway
  - Security groups
  - Route tables
  - VPC Endpoints
- **Location:** `t4/template/network.py`
- **Current Architecture:** Private subnets → NAT Gateway → Internet Gateway

#### **Application Load Balancer (ALB)**
- **Usage:**
  - HTTPS/HTTP routing
  - Path-based routing for services
  - Health checks
  - Private and public listeners
- **Services Routed:**
  - Priority 24: MCP server
  - Priority 25: Catalog
  - Priority 26: Benchling
  - Others: Registry, S3 proxy
- **Ports:** 80 (redirects to 443), 443 (HTTPS)
- **Location:** `t4/template/network.py`

#### **Service Discovery (AWS Cloud Map)**
- **Usage:** Private DNS namespace for ECS services
- **Services Registered:**
  - registry
  - mcp
  - benchling
  - s3-proxy
  - catalog
- **DNS TTL:** 10 seconds
- **Location:** `t4/template/dns.py`
- **Network:** Internal VPC only

#### **VPC Endpoints**
- **Currently Deployed:**
  - S3 Gateway Endpoint (for private S3 access)
  - API Gateway Interface Endpoint (optional, if `api_gateway_in_vpc=true`)
- **Available but Not Deployed:** See recommendations section

---

### 6. Security & Identity

#### **IAM (Identity & Access Management)**
- **Usage:**
  - Lambda execution roles
  - ECS task roles
  - Service-to-service permissions
  - User access policies (read/write/QPE)
  - Cross-service assume role policies
- **Location:** All template files
- **Key Roles:**
  - Lambda execution roles
  - ECS task roles
  - Database accessor roles
  - User roles (QPE, Read, Write)

#### **KMS (Key Management Service)**
- **Usage:**
  - SNS topic encryption
  - S3 bucket encryption
  - RDS database encryption
  - Service authentication (RSA_4096 for JWT signing)
- **Location:** `t4/template/sns_kms.py`, multiple files
- **VPC Endpoint:** ✅ Interface Endpoint available

#### **WAF v2 (Web Application Firewall)**
- **Usage:**
  - ALB protection
  - Geo-blocking (optional)
  - Rate-based rules
  - Account takeover prevention (ATP)
  - Account creation fraud prevention (ACFP)
- **Location:** `t4/template/waf.py`

#### **ACM (AWS Certificate Manager)**
- **Usage:** SSL/TLS certificates for ALB
- **Location:** `t4/template/s3_proxy.py`

---

### 7. Logging & Monitoring

#### **CloudWatch Logs**
- **Usage:**
  - ECS container logs
  - Lambda function logs
  - ElasticSearch logs
  - Audit trail logs
  - Synthetics canary logs
  - ALB access logs
- **Retention:** 90 days (configurable via `LOG_RETENTION_DAYS`)
- **VPC Endpoint:** ✅ Interface Endpoint available (not deployed by default)

#### **CloudWatch (Metrics & Alarms)**
- **Usage:**
  - CPU/memory metrics
  - Request count
  - Latency tracking
  - Custom metrics
- **VPC Endpoint:** ✅ Shared with CloudWatch Logs endpoint

#### **CloudWatch Synthetics**
- **Usage:**
  - Canary tests for catalog
  - Bucket access validation
  - Package push/search testing
  - Scheduled monitoring (hourly)
- **Location:** `t4/template/status/canaries.py`
- **Alerts:** SNS notifications on failure

---

### 8. Analytics & Query Services

#### **Athena**
- **Usage:**
  - Analytics queries on S3 data
  - Audit trail querying
  - User-provisioned databases
- **Location:** `t4/template/audit_trail.py`, `analytics.py`, `user_athena.py`
- **Query Results:** Stored in S3
- **VPC Endpoint:** ✅ Interface Endpoint available (not deployed by default)

#### **Glue (Data Catalog)**
- **Usage:**
  - Database and table definitions
  - Metadata catalog for audit/analytics
  - Schema management
- **Location:** `t4/template/audit_trail.py`, `analytics.py`
- **VPC Endpoint:** ✅ Interface Endpoint available (not deployed by default)

#### **Kinesis Data Firehose**
- **Usage:**
  - Audit trail delivery stream
  - Extended S3 destination
  - Lambda-based data transformation
  - Partitioned delivery
- **Location:** `t4/template/audit_trail.py`
- **Destination:** S3 with partitioning
- **VPC Endpoint:** ✅ Interface Endpoint available (not deployed by default)

#### **CloudTrail**
- **Usage:** Object access tracking for analytics
- **Location:** `t4/template/analytics.py`
- **Features:**
  - Multi-region trail
  - S3 event recording
  - Optional (can use existing trail)
- **Storage:** S3 bucket

---

### 9. Configuration & Deployment

#### **CloudFormation**
- **Usage:** Infrastructure as Code deployment
- **Location:** Entire deployment architecture
- **Stack Management:** Template generation via CDK

#### **SSM Parameter Store**
- **Usage:** Indexing per-bucket configurations
- **Location:** `t4/template/search.py`
- **VPC Endpoint:** ✅ Interface Endpoint available (not deployed by default)

---

## External Services (Non-AWS)

### 1. Telemetry & Analytics

#### **Quilt Telemetry Service**
- **URL:** `https://telemetry.quiltdata.cloud/Prod/metrics/installer`
- **Location:** `installer/quilt_stack_installer/session_log.py`
- **Purpose:** Installer usage metrics
- **Data Sent:**
  - Session ID
  - Installation events
  - CloudFormation stack events
  - Platform info
- **Optional:** ✅ Can be disabled via `DISABLE_QUILT_TELEMETRY` env var
- **Network Requirement:** HTTPS (443) to external service

#### **Mixpanel**
- **Configuration:** Token in environment (`constants["mixpanel"]`)
- **Purpose:** Client-side analytics for catalog UI
- **Used By:** Web catalog, registry container
- **Optional:** ✅ Can be disabled
- **Network Requirement:** HTTPS (443) to mixpanel.com

---

### 2. Third-Party Authentication (SSO)

All SSO providers are **optional** and can be disabled:

#### **Google OAuth**
- **Location:** `t4/template/containers.py`, `parameters.py`
- **Environment Variables:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- **Purpose:** Social sign-in
- **Network Requirement:** HTTPS (443) to accounts.google.com
- **Optional:** ✅ Yes

#### **Azure AD (Microsoft Entra)**
- **Environment Variables:** `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_BASE_URL`
- **Purpose:** Enterprise SSO
- **Network Requirement:** HTTPS (443) to login.microsoftonline.com
- **Optional:** ✅ Yes

#### **Okta**
- **Environment Variables:** `OKTA_CLIENT_ID`, `OKTA_CLIENT_SECRET`
- **Purpose:** Enterprise SSO
- **Network Requirement:** HTTPS (443) to customer's Okta domain
- **Optional:** ✅ Yes

#### **OneLogin**
- **Environment Variables:** `ONELOGIN_CLIENT_ID`, `ONELOGIN_CLIENT_SECRET`
- **Purpose:** Enterprise SSO
- **Network Requirement:** HTTPS (443) to api.onelogin.com
- **Optional:** ✅ Yes

---

### 3. Container Image Registries

#### **AWS ECR (Elastic Container Registry)**
- **Account (Quilt Images):** `709825985650` (Marketplace)
- **Account (Custom):** Customer account
- **Region:** `us-east-1` (Marketplace), customer region (custom)
- **Repositories:**
  - `quilt-data/quilt-payg-*` (pay-as-you-go)
  - `quiltdata/catalog`
  - `quiltdata/nginx`
  - `quiltdata/registry`
  - `quiltdata/s3-proxy`
  - `quiltdata/voila` (optional)
  - `quiltdata/mcp`
  - `quiltdata/benchling` (optional)
- **Network Requirement:** HTTPS (443) to ECR API and S3 (for image layers)
- **VPC Endpoint:** ✅ ECR Interface Endpoint available
- **Required:** ✅ Yes - ECS tasks must pull images

#### **Benchling Special Case**
- **Account:** `712023778557` (Quilt central)
- **Region:** `us-east-1`
- **Repository:** `quiltdata/benchling`
- **Full URI:** `712023778557.dkr.ecr.us-east-1.amazonaws.com/quiltdata/benchling:latest`
- **Used For:** Benchling webhook integration service
- **Note:** Hardcoded to central ECR account

---

### 4. External APIs

#### **Benchling API** (Optional)
- **Location:** `t4/template/benchling.py`
- **Purpose:** LIMS integration
- **Access:** Customer's Benchling instance
- **Ports:** 443 (HTTPS)
- **Optional:** ✅ Yes - only if Benchling integration enabled
- **Network:** Can be internal (VPC) or external

#### **MCP Server External** (Optional)
- **Configuration:** `RemoteMCPUrl` parameter
- **Location:** `t4/template/parameters.py`
- **Purpose:** Model Context Protocol for AI
- **Optional:** ✅ Yes - only if external MCP configured
- **Network:** HTTPS (443) to configured endpoint

---

### 5. Email Services (Optional)

#### **SMTP Server**
- **Configuration:** `EMAIL_SERVER` environment variable
- **Location:** `t4/template/containers.py`
- **Purpose:** Email notifications
- **Optional:** ✅ Yes - only if email configured
- **Network:** SMTP ports (25/465/587)

---

## Network Architecture Analysis

### Current Architecture (NAT Gateway)

```
Private Subnet (Lambda/ECS)
    ↓
NAT Gateway
    ↓
Internet Gateway
    ↓
Internet (external services, ECR, SSO, telemetry)
```

### Proposed Architecture (Transit Gateway)

```
Private Subnet (Lambda/ECS)
    ↓
Transit Gateway
    ↓
Corporate Network/Firewall
    ↓
Internet (external services, ECR, SSO, telemetry)
```

### Hybrid Architecture (Recommended)

```
Private Subnet (Lambda/ECS)
    ├─→ VPC Endpoints → AWS Services (S3, SQS, SNS, CloudWatch, etc.)
    └─→ Transit Gateway → Corporate Network → Internet (ECR, SSO, telemetry)
```

---

## Egress Requirements Summary

### Required External Access

| Destination | Port | Purpose | Optional? |
|-------------|------|---------|-----------|
| ECR API (*.amazonaws.com) | 443 | Pull Docker images | ❌ Required |
| S3 (*.amazonaws.com) | 443 | ECR image layers | ❌ Required (or use VPC endpoint) |

### Optional External Access

| Destination | Port | Purpose | Optional? |
|-------------|------|---------|-----------|
| telemetry.quiltdata.cloud | 443 | Usage metrics | ✅ Yes |
| accounts.google.com | 443 | Google OAuth | ✅ Yes |
| login.microsoftonline.com | 443 | Azure AD | ✅ Yes |
| *.okta.com | 443 | Okta SSO | ✅ Yes |
| api.onelogin.com | 443 | OneLogin SSO | ✅ Yes |
| mixpanel.com | 443 | Analytics | ✅ Yes |
| Customer SMTP server | 25/465/587 | Email | ✅ Yes |
| Customer Benchling | 443 | LIMS integration | ✅ Yes |
| Customer MCP server | 443 | AI integration | ✅ Yes |

### Internal (VPC-Only) Access

| Service | Port | Communication |
|---------|------|---------------|
| RDS PostgreSQL | 5432 | Lambda/ECS → Database |
| ElasticSearch | 443 | Lambda/ECS → Search |
| ALB | 80/443 | Internet → Services |
| Service Discovery | 53 | ECS → ECS (DNS) |
| ECS Services | Various | Internal service mesh |

---

## Recommended VPC Endpoint Configuration

For Transit Gateway routing with minimal internet egress, deploy these VPC Interface Endpoints:

### Tier 1: Essential (Recommended)

| Service | Endpoint Type | Cost/Month (approx) | Benefit |
|---------|---------------|---------------------|---------|
| **S3** | Gateway | Free | Already deployed ✅ |
| **CloudWatch Logs** | Interface | $7 + data | Essential for logging |
| **ECR API** | Interface | $7 + data | Docker image pulls |
| **ECR Docker** | Interface | $7 + data | Docker image layers |
| **SQS** | Interface | $7 + data | Message queuing |
| **SNS** | Interface | $7 + data | Notifications |

**Tier 1 Cost:** ~$35/month + data transfer

### Tier 2: High Value (Strongly Recommended)

| Service | Endpoint Type | Cost/Month (approx) | Benefit |
|---------|---------------|---------------------|---------|
| **Lambda** | Interface | $7 + data | Lambda management |
| **ECS** | Interface | $7 + data | ECS task management |
| **EventBridge** | Interface | $7 + data | Event routing |
| **KMS** | Interface | $7 + data | Encryption operations |
| **API Gateway** | Interface | $7 + data | API calls |

**Tier 2 Cost:** ~$35/month + data transfer

### Tier 3: Analytics & Management (Optional)

| Service | Endpoint Type | Cost/Month (approx) | Benefit |
|---------|---------------|---------------------|---------|
| **Athena** | Interface | $7 + data | Analytics queries |
| **Glue** | Interface | $7 + data | Data catalog |
| **Kinesis Firehose** | Interface | $7 + data | Stream delivery |
| **SSM** | Interface | $7 + data | Parameter Store |
| **CloudFormation** | Interface | $7 + data | Stack updates |

**Tier 3 Cost:** ~$35/month + data transfer

### Total VPC Endpoint Cost Estimate
- **Tier 1 only:** ~$35/month + data
- **Tier 1 + 2:** ~$70/month + data
- **All tiers:** ~$105/month + data
- **Data transfer:** Typically $0.01/GB (far cheaper than NAT Gateway at $0.045/GB)

**Cost Comparison:**
- NAT Gateway: ~$32/month base + $0.045/GB data
- VPC Endpoints (Tier 1+2): ~$70/month + $0.01/GB data
- **Break-even:** ~850 GB/month of traffic

---

## Transit Gateway Routing Configuration

### Routing Rules Required

#### Route Table for Private Subnets

```
Destination         Target              Purpose
-----------------------------------------------------------
10.0.0.0/16        Local               Intra-VPC communication
pl-xxxxx (S3)      vpce-xxxxx          S3 via VPC Gateway Endpoint
0.0.0.0/0          tgw-xxxxx           All other traffic via TGW
```

#### Services Requiring External Routing via TGW

1. **ECR Image Pulls** (if not using ECR VPC endpoints)
   - Destination: `*.ecr.us-east-1.amazonaws.com`, `*.s3.amazonaws.com`
   - Protocol: HTTPS (443)
   - Frequency: On deployment/task start

2. **Quilt Telemetry** (optional, can disable)
   - Destination: `telemetry.quiltdata.cloud`
   - Protocol: HTTPS (443)
   - Frequency: On installer events

3. **SSO Providers** (optional, if configured)
   - Destination: Various (google.com, microsoftonline.com, etc.)
   - Protocol: HTTPS (443)
   - Frequency: On user authentication

#### Services NOT Requiring External Routing

✅ Can use VPC Endpoints:
- S3
- CloudWatch Logs
- SQS, SNS
- EventBridge
- Athena, Glue, Firehose
- API Gateway
- KMS
- SSM

✅ Entirely internal:
- RDS PostgreSQL
- ElasticSearch
- Service Discovery (Cloud Map)
- ECS service-to-service communication

---

## Testing & Validation Plan

### Phase 1: VPC Endpoint Validation
1. Deploy Tier 1 VPC endpoints
2. Test Lambda S3 access via gateway endpoint
3. Test ECS CloudWatch Logs via interface endpoint
4. Verify no traffic to NAT Gateway for AWS services

### Phase 2: TGW Routing Validation
1. Update route tables to point 0.0.0.0/0 to TGW
2. Test ECR image pulls via TGW
3. Test external SSO authentication (if configured)
4. Verify telemetry calls route via TGW (if enabled)

### Phase 3: Functional Testing
1. Deploy full Quilt stack
2. Test package push/pull operations
3. Test search indexing
4. Test catalog access
5. Monitor CloudWatch Logs for connection errors
6. Verify no connection timeouts

### Phase 4: Performance Validation
1. Measure S3 operation latency
2. Measure ECR pull times
3. Compare against NAT Gateway baseline
4. Validate throughput for large file transfers

---

## Recommendations for Customer

### 1. Deploy Essential VPC Endpoints (Tier 1)

Deploy these endpoints to eliminate most NAT/TGW routing:
- ✅ S3 Gateway Endpoint (already deployed)
- CloudWatch Logs
- ECR API
- ECR Docker
- SQS
- SNS

**Benefit:** Eliminates NAT Gateway cost for 90%+ of AWS API traffic

### 2. Configure TGW Routing for Remaining Traffic

Point 0.0.0.0/0 to Transit Gateway for:
- ECR image pulls (or use ECR VPC endpoints from Tier 1)
- External SSO (if needed)
- Telemetry (or disable)

**Benefit:** Centralized routing control, compliance with network policies

### 3. Consider Disabling Optional External Services

To minimize TGW internet routing requirements:
- Set `DISABLE_QUILT_TELEMETRY=true` (no telemetry)
- Don't configure external SSO (use IAM-based auth)
- Use internal MCP/Benchling (if applicable)

**Benefit:** Reduces external dependencies to just ECR

### 4. Use ECR VPC Endpoints for Fully Private Architecture

Deploy ECR API and ECR Docker VPC endpoints:
- Zero internet routing needed
- All traffic stays within AWS network
- Eliminates TGW internet routing entirely

**Benefit:** Fully private architecture, no firewall rules for internet access

### 5. Monitoring & Validation

Set up CloudWatch metrics and alerts for:
- VPC endpoint connection counts
- Failed DNS resolutions
- ECS task launch failures
- Lambda timeout errors

**Benefit:** Early detection of routing issues

---

## Implementation Checklist for Customer

### Pre-Deployment
- [ ] Inventory existing VPC endpoints in target VPC
- [ ] Confirm TGW attachment to target VPC
- [ ] Verify TGW routing to internet (if needed)
- [ ] Plan DNS resolution for VPC endpoints
- [ ] Review security group rules for VPC endpoints

### VPC Endpoint Deployment
- [ ] Deploy S3 Gateway Endpoint (if not exists)
- [ ] Deploy CloudWatch Logs Interface Endpoint
- [ ] Deploy ECR API Interface Endpoint
- [ ] Deploy ECR Docker Interface Endpoint
- [ ] Deploy SQS Interface Endpoint
- [ ] Deploy SNS Interface Endpoint
- [ ] Enable Private DNS for all interface endpoints
- [ ] Update security groups to allow VPC endpoint access

### Route Table Configuration
- [ ] Backup existing route tables
- [ ] Update private subnet route tables:
  - [ ] Keep local VPC routes
  - [ ] Keep S3 Gateway Endpoint route
  - [ ] Change 0.0.0.0/0 target from NAT Gateway to TGW
- [ ] Verify route table associations

### Quilt Configuration
- [ ] Set `DISABLE_QUILT_TELEMETRY=true` (optional)
- [ ] Configure ECR repository (customer account or Quilt account)
- [ ] Decide on SSO providers (or disable)
- [ ] Configure `lambdas_in_vpc=true`
- [ ] Configure `api_gateway_in_vpc` (optional)

### Testing
- [ ] Deploy Quilt stack
- [ ] Verify ECS task launches successfully
- [ ] Verify ECR image pulls work
- [ ] Test S3 bucket access
- [ ] Test search indexing
- [ ] Test package push/pull
- [ ] Monitor CloudWatch Logs for errors
- [ ] Performance test: measure latency vs baseline

### Post-Deployment
- [ ] Remove NAT Gateway (if no longer needed)
- [ ] Update documentation
- [ ] Set up monitoring/alerts
- [ ] Schedule performance review

---

## Security Considerations

### Private Architecture Benefits
✅ No public IPs for Lambda/ECS
✅ All AWS API calls via private network
✅ Reduced attack surface
✅ Compliance with network isolation policies

### Transit Gateway Security
⚠️ Ensure TGW has proper routing rules
⚠️ Firewall rules for external access
⚠️ Monitor TGW traffic for anomalies
⚠️ Regularly audit TGW route tables

### VPC Endpoint Security
✅ Private DNS eliminates DNS hijacking
✅ Endpoint policies can restrict access
✅ Security groups control endpoint access
⚠️ Ensure endpoint security groups allow required traffic

---

## Cost Analysis

### Current Architecture (NAT Gateway)
- **NAT Gateway:** $32.40/month (730 hours × $0.045)
- **Data Processing:** $0.045/GB
- **Total (1 TB/month):** $32.40 + $46.08 = **$78.48/month**

### Proposed Architecture (TGW + VPC Endpoints)
- **TGW Attachment:** $36.50/month (730 hours × $0.05)
- **TGW Data:** $0.02/GB
- **VPC Endpoints (Tier 1):** $35/month + $0.01/GB
- **Total (1 TB/month):** $36.50 + $20.48 + $35 + $10.24 = **$102.22/month**

### Fully Private Architecture (TGW + All Endpoints)
- **TGW Attachment:** $36.50/month (minimal traffic)
- **VPC Endpoints (All tiers):** $105/month + $0.01/GB
- **Total (1 TB/month):** $36.50 + $105 + $10.24 = **$151.74/month**

### Cost Observations
- ⚠️ TGW + VPC endpoints cost more than NAT Gateway alone
- ✅ However, TGW cost is **shared** across all VPCs (sunk cost for customer)
- ✅ VPC endpoints eliminate data charges for AWS API calls
- ✅ Marginal cost for Quilt is just VPC endpoints (~$35-105/month)
- ✅ For multi-VPC environments, TGW + VPC endpoints is more cost-effective

---

## Conclusion

### Can Customer Use Transit Gateway? **YES ✅**

Quilt can successfully operate with Transit Gateway routing instead of NAT Gateway, with the following configuration:

1. **Deploy Tier 1 VPC Endpoints** to eliminate most external routing
2. **Route 0.0.0.0/0 via TGW** for remaining traffic (ECR pulls, optional SSO)
3. **Optionally disable external services** (telemetry, SSO) to minimize TGW internet routing
4. **For fully private architecture**, deploy all VPC endpoints and eliminate internet routing entirely

### Benefits for Customer
- ✅ Compliance with network security policies
- ✅ Centralized routing control via TGW
- ✅ Eliminates per-VPC NAT Gateway costs
- ✅ Consistent with enterprise network architecture
- ✅ All Quilt functionality preserved

### Next Steps
1. Review VPC endpoint requirements with customer's network team
2. Provide CDK template modifications for VPC endpoint deployment
3. Schedule deployment and testing window
4. Perform phased rollout with validation at each step

---

**Audit Completed By:** Engineering Team
**Review Date:** February 2, 2026
**Next Review:** Post-deployment validation

