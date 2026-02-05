# Product Management Summary: Customer Custom Network Routing Request

**Date:** February 2, 2026
**Customer:** Customer Organization
**Request Type:** Custom Network Architecture Support
**Priority:** High - Blocking Production Deployment

---

## 1. Executive Summary

The customer organization is requesting support for routing their Quilt deployment through their Transit Gateway (TGW) infrastructure instead of using Quilt's default NAT Gateway setup. This represents a common enterprise requirement where customers need Quilt to integrate with their existing network architecture for security, compliance, and operational reasons. The request requires clarification on Quilt's external service dependencies and network requirements to enable proper routing configuration.

**Key Ask:** Route all egress traffic (0.0.0.0/0) through customer's Transit Gateway instead of NAT Gateway, while maintaining full Quilt functionality.

---

## 2. Customer Context

### Organization
- **Company:** Customer Organization
- **Contact:** Customer Contact (contact@customer.com)
- **Industry:** Enterprise
- **Scale:** Enterprise customer

### Current Situation
- Customer has an established AWS network architecture with Transit Gateway
- They want to deploy Quilt within their existing VPC/networking infrastructure
- All egress traffic must route through their TGW for security/compliance
- This is blocking their production deployment of Quilt

### Strategic Context
- Represents common enterprise networking pattern
- Likely affects other enterprise customers with similar requirements
- Shows need for Quilt to support flexible network architectures
- May indicate gap in deployment documentation/configuration options

---

## 3. Core Requirements

### Primary Requirement
Route all Quilt egress traffic (0.0.0.0/0) through customer's Transit Gateway instead of NAT Gateway.

### Specific Configuration Needs
1. **No NAT Gateway:** Customer wants to eliminate Quilt-managed NAT Gateways
2. **TGW Routing:** All outbound traffic should route through their TGW
3. **AWS Service Access:** Quilt components must still access required AWS services
4. **Maintained Functionality:** All Quilt features must work without degradation

### Architecture Constraints
- Must work within customer's existing VPC structure
- Must comply with customer's network security policies
- Must support Lambda and ECS workloads
- Must handle both AWS service calls and external API calls

---

## 4. Technical Questions Asked

The customer has specific technical questions that need answers:

### Network Architecture Questions

1. **Primary Routing Question:**
   > "Can we route 0.0.0.0/0 through TGW instead of NAT Gateway?"
   - Need to confirm if this routing pattern is supported
   - Identify any Quilt-specific routing requirements

2. **Service Dependencies:**
   > "Do Lambda/ECS need to call any external services other than AWS services?"
   - Critical for routing design
   - Determines if TGW needs internet egress or just AWS service access

3. **AWS Service Requirements:**
   > "Which AWS services does Quilt need to call?"
   - Complete list needed for:
     - VPC Endpoint planning
     - Security group configuration
     - Route table design
   - Examples likely include: S3, DynamoDB, SQS, SNS, CloudWatch, etc.

4. **VPC Endpoints:**
   > "Do we need VPC endpoints for AWS services?"
   - Preferred approach for AWS service access in private subnets
   - Reduces/eliminates need for NAT Gateway or TGW internet routing
   - Need to provide complete list of required VPC endpoints

### Additional Implied Questions
- What are the minimum network requirements for Quilt?
- Are there any services that specifically require NAT Gateway?
- Can Quilt components run entirely in private subnets?
- What are the latency/bandwidth requirements?

---

## 5. Business Impact

### Impact to Customer
- **Deployment Blocked:** Cannot proceed with production deployment
- **Security Compliance:** Need to maintain network security posture
- **Cost Control:** TGW may reduce NAT Gateway costs
- **Operational Integration:** Want Quilt to fit existing infrastructure
- **Timeline Risk:** Delay affects their project timelines

### Impact to Quilt
- **Revenue Risk:** Enterprise deal potentially blocked
- **Product Gap:** May indicate limitation in network flexibility
- **Customer Satisfaction:** Responsiveness affects relationship
- **Competitive Position:** Competitors may support this use case
- **Technical Debt:** May need architecture changes to support

### Broader Market Impact
- **Enterprise Adoption:** Common requirement for large organizations
- **Product-Market Fit:** Shows need for enterprise networking support
- **Differentiation Opportunity:** Better support could be competitive advantage
- **Documentation Gap:** May need better network architecture docs
- **Sales Enablement:** Sales team needs clear guidance on network requirements

---

## 6. Dependencies & Blockers

### Information Needed (CRITICAL)

1. **Complete AWS Service List:**
   - All AWS services Quilt Lambda functions call
   - All AWS services Quilt ECS tasks call
   - Service-specific requirements (regional vs. global endpoints)
   - Authentication methods (IAM roles, API keys, etc.)

2. **External Service Dependencies:**
   - Any third-party APIs called by Quilt
   - Webhooks or callbacks that need internet access
   - License validation or telemetry endpoints
   - Container registries (ECR, Docker Hub, etc.)

3. **Network Requirements:**
   - Bandwidth requirements
   - Latency sensitivity
   - Port/protocol requirements
   - Any multicast or broadcast needs

4. **Current Architecture Documentation:**
   - Existing network diagrams
   - Default VPC/subnet configuration
   - Security group templates
   - IAM role assumptions

### Technical Decisions Needed

1. **Support Strategy:**
   - Should Quilt officially support TGW-only deployments?
   - Should this be a configuration option or custom deployment?
   - How to maintain compatibility with existing deployments?

2. **VPC Endpoint Strategy:**
   - Which VPC endpoints should be mandatory vs. optional?
   - Should Quilt CDK create VPC endpoints automatically?
   - How to handle VPC endpoint costs in pricing model?

3. **Documentation Updates:**
   - Network architecture guide needed
   - VPC endpoint setup instructions
   - Custom routing configuration examples
   - Troubleshooting guide for network issues

### Stakeholder Alignment Needed

- **Engineering:** Can we support this configuration?
- **Solutions Architecture:** What's the recommended approach?
- **Product:** Should this be a standard feature?
- **Sales:** What's the business priority?
- **Support:** Can we support troubleshooting?
- **Security:** Any security implications?

---

## 7. Recommended Next Steps

### Immediate Actions (This Week)

1. **Gather Service Dependencies (DAY 1)**
   - [ ] Audit all Lambda functions for AWS service calls
   - [ ] Audit all ECS tasks for AWS service calls
   - [ ] Identify external API dependencies
   - [ ] Document required network endpoints
   - **Owner:** Engineering Team
   - **Output:** Complete service dependency list

2. **Document VPC Endpoint Requirements (DAY 2)**
   - [ ] Create list of required VPC endpoints
   - [ ] Document optional VPC endpoints
   - [ ] Estimate VPC endpoint costs
   - [ ] Create VPC endpoint setup guide
   - **Owner:** Solutions Architecture
   - **Output:** VPC Endpoint guide

3. **Respond to Customer (DAY 3)**
   - [ ] Send complete AWS service list
   - [ ] Confirm external service dependencies
   - [ ] Provide VPC endpoint recommendations
   - [ ] Offer architecture review call
   - **Owner:** Product Manager + Solutions Architect
   - **Output:** Detailed technical response

### Short-term Actions (Next 2 Weeks)

4. **Create Reference Architecture**
   - [ ] Design TGW-based network architecture
   - [ ] Create network diagrams
   - [ ] Document routing configuration
   - [ ] Test with pilot customer
   - **Owner:** Solutions Architecture
   - **Output:** Reference architecture document

5. **Update Documentation**
   - [ ] Add network architecture section to docs
   - [ ] Create TGW deployment guide
   - [ ] Document VPC endpoint setup
   - [ ] Add troubleshooting guide
   - **Owner:** Technical Writing + Engineering
   - **Output:** Updated documentation

6. **Enable Customer Deployment**
   - [ ] Schedule architecture review with customer
   - [ ] Validate their proposed design
   - [ ] Provide deployment support
   - [ ] Monitor deployment success
   - **Owner:** Solutions Architecture + Support
   - **Output:** Successful production deployment

### Medium-term Actions (Next Quarter)

7. **Product Enhancement Planning**
   - [ ] Evaluate making TGW support a standard feature
   - [ ] Design CDK configuration options
   - [ ] Plan VPC endpoint automation
   - [ ] Create network architecture testing
   - **Owner:** Product Management
   - **Output:** Product roadmap items

8. **Sales Enablement**
   - [ ] Create network requirements guide for sales
   - [ ] Document enterprise networking capabilities
   - [ ] Train solutions architects
   - [ ] Add to RFP response templates
   - **Owner:** Product Marketing
   - **Output:** Sales enablement materials

9. **Market Research**
   - [ ] Survey other enterprise customers
   - [ ] Identify common network patterns
   - [ ] Benchmark competitor capabilities
   - [ ] Prioritize network features
   - **Owner:** Product Management
   - **Output:** Network feature prioritization

---

## 8. Success Metrics

### Immediate Success (Customer-Specific)
- Customer successfully deploys Quilt with TGW routing
- All Quilt functionality works as expected
- No performance degradation
- Customer satisfaction score: 9+/10

### Product Success (Organization-Wide)
- Reduction in network-related support tickets
- Increase in enterprise customer adoption
- Improved sales cycle time for enterprise deals
- Positive feedback on network flexibility

### Business Success
- Customer deployment generates reference architecture
- Convert to long-term customer
- Enable 3+ similar enterprise deployments
- Establish Quilt as enterprise-ready solution

---

## 9. Risk Assessment

### High Risks
- **Incomplete Service List:** May miss critical dependencies
- **Latency Issues:** VPC endpoints may introduce latency
- **Cost Surprise:** VPC endpoint costs may be significant
- **Support Complexity:** Harder to troubleshoot customer networks

### Medium Risks
- **Documentation Gaps:** Customers may struggle with setup
- **Version Compatibility:** Future Quilt versions may add dependencies
- **Regional Limitations:** Some VPC endpoints not available in all regions
- **Performance Variation:** Customer TGW performance varies

### Mitigation Strategies
- Comprehensive testing in customer-like environment
- Clear documentation and setup automation
- Ongoing monitoring of service dependencies
- Regular architecture reviews with customers

---

## 10. Open Questions

1. Does Quilt currently have any telemetry or phone-home requirements?
2. What container registries does Quilt pull from (ECR, Docker Hub)?
3. Are there any licensing or authentication services called at runtime?
4. How are Quilt updates delivered (new Lambda code, new containers)?
5. What's the expected bandwidth usage pattern?
6. Are there any services that specifically require public internet access?
7. How do we validate that TGW routing is working correctly?
8. What monitoring is needed to detect network issues?

---

## Appendix: Technical Context

### Transit Gateway (TGW) Overview
- AWS service for connecting multiple VPCs and on-premises networks
- Acts as cloud router with centralized control
- Common in enterprise AWS architectures
- Supports routing to internet via attached VPCs
- Can integrate with AWS services via VPC endpoints

### VPC Endpoints
- Private connections to AWS services without internet gateway
- Interface Endpoints (powered by PrivateLink) for most services
- Gateway Endpoints for S3 and DynamoDB
- Eliminate need for NAT Gateway for AWS service access
- Per-endpoint costs vary by service and data transfer

### Network Architecture Patterns
1. **Default Pattern:** Private subnet → NAT Gateway → Internet Gateway
2. **VPC Endpoint Pattern:** Private subnet → VPC Endpoints → AWS Services
3. **TGW Pattern (Customer Request):** Private subnet → TGW → Customer Network
4. **Hybrid Pattern:** TGW for some traffic, VPC Endpoints for AWS services

---

**Next Review Date:** February 9, 2026
**Document Owner:** Product Manager
**Stakeholders:** Engineering, Solutions Architecture, Sales, Support
