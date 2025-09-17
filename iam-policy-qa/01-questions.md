# IAM Policy Q&A - Technical Review

## Overview

Technical questions regarding CloudFormation template review. Security-focused concerns that should be addressed by engineering/development team.

**Note:** This deployment can access AWS Bedrock (cloud AI service) - can be disabled during installation.

**CloudFormation Template:** `<redacted-url>`

## Security Concerns Identified

### 1. Blank IAM Access Policies

- **Issue:** Policies attached to several IAM roles but don't make sense in current form
- **Question:** What are these policies intended for?

### 2. Too Loose IAM Policies

- **Issue:** `"Resource: '*'"` being used inappropriately
- **Concern:** Overly permissive access patterns

### 3. Dynamic IAM Policy Creation

- **Critical Issue:** Multiple roles can create and edit IAM policies
  - `AmazonECSTaskExecutionRole`
  - `MigrationLambdaRole` (Lambda)
  - `TrackingCronRole` (EventBridge)
- **Security Risk:** Almost any resource can modify IAM policies
- **Questions:**
  - What are these policies for?
  - Can they be created manually or via CloudFormation instead?

### 4. CloudTrail Configuration

**Missing Required Security Features:**

1. CloudWatch destination must be configured:
   - `CloudWatchLogsLogGroupArn`
   - `CloudWatchLogsRoleArn`
2. Trail encryption required (`KMSKeyId`)

### 5. Lambda Configuration

- **Question:** Can Lambda policies be further restricted?
- Reference example provided for comparison

## Infrastructure Questions

### Stack Naming / DNS

- **Question:** Recommendations for CloudFormation stack name (`StackName`)?
- **Impact:** Will be used to create private Route53 zone

### Network Security

1. **ECS Tasks:** Open non-TLS ports (port 80) for incoming connections
   - End-users use ELB which terminates TLS
   - Security scanners may flag unencrypted traffic
   - All traffic must be encrypted per policy

2. **ELB Port 444:**
   - Purpose unclear
   - May be blocked by proxy/firewall (Security managed)

3. **ELB Certificate:**
   - Not defined in CF template
   - Must exist in same region as deployment
   - **Questions:**
     - Should certificate be created separately?
     - DNS name limitations?
