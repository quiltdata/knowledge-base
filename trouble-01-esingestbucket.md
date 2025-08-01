# CDK deployment fails with "Bucket name should not contain uppercase characters"

## Tags

`aws`, `cdk`, `s3`, `bucket`, `naming`, `cloudformation`, `deployment`

## Summary

AWS CDK deployment fails when creating EsIngestBucket due to uppercase characters in the CloudFormation stack name being used in S3 bucket naming, violating AWS S3 bucket naming requirements.

---

## Symptoms

- CDK deployment fails during stack update/creation with S3 bucket creation error
- Error message: "Bucket name should not contain uppercase characters"
- Stack enters UPDATE_ROLLBACK_FAILED state
- EsIngestBucket resource specifically fails to create

**Observable indicators:**

- CloudFormation deployment failure during bucket creation phase
- Error occurs when stack name contains uppercase letters (e.g., "QuiltStack")
- Other S3 buckets in the same stack create successfully
- Stack rollback may also fail due to dependency issues

## Likely Causes

**Root cause:**

- EsIngestBucket uses explicit bucket naming pattern: `${AWS::StackName}-${AWS::Region}-esingestbucket`
- When CloudFormation stack name contains uppercase characters, resulting bucket name violates AWS S3 naming rules
- S3 bucket names must be lowercase and follow DNS naming conventions

**Why explicit naming is required:**

- Bucket name must be known at template creation time for SQS queue policy conditions
- CloudFormation requires deterministic naming for cross-resource references
- Multiple stacks in same account/region need unique bucket names

## Recommendation

1. **Immediate fix:** Use lowercase CloudFormation stack names
   - Rename existing stacks to use lowercase characters only
   - Ensure new deployments use lowercase stack names (e.g., "quiltstack" instead of "QuiltStack")

2. **For existing uppercase stack names:**
   - Create new stack with lowercase name
   - Migrate resources if necessary
   - Delete old stack once migration is complete

3. **Long-term considerations:**
   - Document stack naming requirements in deployment guides
   - Consider alternative unique identifier patterns that don't rely on stack name
   - Add validation in deployment scripts to check stack name format

4. **If changing stack names is not feasible:**
   - Investigate using account ID + region + custom identifier pattern
   - Consider implementing custom CloudFormation macro for string manipulation
   - Evaluate if SQS queue policy can reference bucket differently

**Testing steps:**

- Verify stack name follows lowercase-only pattern before deployment
- Test deployment in non-production environment with realistic stack names
- Confirm all S3 bucket resources create successfully
