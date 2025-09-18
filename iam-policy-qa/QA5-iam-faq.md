# Why does Quilt's CloudFormation template have broad IAM permissions?

## Tags

`iam`, `cloudformation`, `security`, `permissions`, `deployment`, `s3`, `athena`, `policies`

## Summary

Quilt's CloudFormation template uses wildcards and broad IAM permissions to support dynamic bucket registration and multi-tenant deployments. This article explains each permission's purpose and provides security hardening options for enterprise customers.

---

## Symptoms

**Observable indicators:**

- CloudFormation template contains `"Resource": "*"` in multiple IAM policies
- Security scanners flag overly permissive IAM policies
- IAM roles appear to have more permissions than necessary for basic functionality
- Dynamic policy creation capabilities raise security compliance concerns

**Affected areas:**

- S3 bucket access policies
- Athena workgroup permissions
- SNS topic management
- IAM policy creation for ECS roles

## Likely Causes

**Design requirements for vendored product:**

- **Unknown customer infrastructure** - Quilt must work with existing S3 buckets, Athena workgroups, and naming conventions without prior knowledge
- **Dynamic bucket registration** - Customers add buckets through UI without requiring CloudFormation updates
- **Multi-tenant architecture** - Single template must support diverse customer environments
- **Operational independence** - Reduces need for vendor support and custom deployments per customer

## Recommendation

### Understanding Each Broad Permission

**1. S3 Wildcard Permissions (`Resource: "*"`)**
- **Purpose:** Discover and register customer's existing S3 buckets
- **Scope:** Limited to read/write operations, no bucket creation/deletion
- **Hardening:** Specify bucket prefix parameter: `arn:aws:s3:::your-company-*`

**2. Athena Wildcard Permissions**
- **Purpose:** Query across customer's existing databases and workgroups
- **Scope:** Read-only catalog discovery and query execution
- **Hardening:** Restrict to specific workgroups: `arn:aws:athena:*:*:workgroup/your-prefix*`

**3. SNS Topic Management**
- **Purpose:** Create notification topics for bucket events across unknown bucket topology
- **Scope:** Topic creation/management for data pipeline notifications
- **Hardening:** Use conditional policies based on resource tags

**4. Dynamic IAM Policy Creation**
- **Purpose:** Create bucket-specific access policies when customers connect new S3 buckets
- **Scope:** Restricted to path `/quilt/${StackName}/${Region}/` with predefined templates
- **Hardening:** Enable manual approval mode or use pre-created conditional policies

### Security Hardening Options

**Option 1: Parameterized Deployment (Recommended)**
```yaml
Parameters:
  CustomerBucketPrefix:
    Type: String
    Default: ""
    Description: "Restrict S3 access to buckets with this prefix"

  AllowedAthenaWorkgroups:
    Type: CommaDelimitedList
    Default: ""
    Description: "Comma-separated list of allowed Athena workgroups"
```

**Option 2: Enhanced Security Mode**
- Enable manual approval for dynamic policy creation
- Restrict permissions to tagged resources only
- Provide compliance-focused deployment variant

**Option 3: Post-Deployment Hardening**
```bash
# Replace wildcards with specific resources after deployment
aws iam put-role-policy --role-name QuiltRole --policy-name RestrictedS3 \
  --policy-document file://restricted-s3-policy.json
```

### Deployment Validation

**Pre-deployment checklist:**
1. Review all wildcard permissions with security team
2. Determine acceptable bucket prefixes and Athena workgroups
3. Choose dynamic policy creation mode (auto/manual/disabled)
4. Configure CloudTrail integration for audit compliance

**Monitoring recommendations:**
1. Set up CloudWatch alerts for IAM policy creation events
2. Enable AWS Config rules for policy compliance monitoring
3. Regular access reviews using AWS Access Analyzer
4. Monitor CloudTrail for unusual S3 or Athena access patterns

### Common Compliance Frameworks

**SOC2 Type II:**
- Enable CloudTrail with CloudWatch integration
- Use KMS encryption for all logs
- Implement least privilege through bucket prefixes

**HIPAA:**
- Enable end-to-end TLS (requires custom ECS configuration)
- Use customer-managed KMS keys
- Enable enhanced CloudTrail logging

**FedRAMP:**
- Deploy in restricted security mode
- Use manual policy approval workflow
- Enable all monitoring and alerting features

### Alternative Architectures

**For maximum security compliance:**
1. **Pre-scoped deployment** - Provide bucket list and workgroup names during deployment
2. **Manual policy mode** - Approve each bucket connection individually
3. **Restricted template** - Use separate CloudFormation template with minimal permissions

**Trade-offs:**
- Increased deployment complexity
- Requires more customer infrastructure knowledge
- May need vendor support for bucket additions
- Reduced operational flexibility

### Getting Help

If your security requirements cannot be met with standard hardening options:

1. **Document specific compliance requirements** (framework, controls, restrictions)
2. **Identify acceptable trade-offs** between security and operational flexibility
3. **Request custom deployment consultation** for enterprise security requirements
4. **Consider hybrid approach** with some buckets in restricted mode, others standard